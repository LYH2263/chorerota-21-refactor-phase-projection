"""对调事务（app/services/swap_tx.py）的可失败测例。

生成落位（相位 0，成员 1/2/3，任务 1/2）：
  d0T1→M1, d0T2→M2, d1T1→M3, d1T2→M1, d2T1→M2, d2T2→M3, ...
"""
import pytest
from fastapi import HTTPException

from app import main
from app.db import connect
from app.main import GenBody, SwapBody, generate
from app.services.swap_tx import SwapTxError, confirm_swap, request_swap


@pytest.fixture()
def generated(week_3x2):
    generate(week_3x2, GenBody(days=7))
    return week_3x2


def _assignee(wid, day, task):
    c = connect()
    row = c.execute(
        "SELECT member_id FROM assignments WHERE week_id=? AND day=? AND task_id=?",
        (wid, day, task)).fetchone()
    c.close()
    return row["member_id"]


def _swap_row(sid):
    c = connect()
    row = c.execute("SELECT * FROM swap_requests WHERE id=?", (sid,)).fetchone()
    c.close()
    return dict(row) if row else None


def test_request_then_confirm_flips_assignees(generated):
    c = connect()
    req = request_swap(c, generated, 0, 1, 0, 2, note="换班")
    assert req["status"] == "pending" and req["a_member"] == 1 and req["b_member"] == 2
    out = confirm_swap(c, req["id"])
    assert out == {"ok": True, "swap_id": req["id"]}
    c.close()
    # 重连验证事务确已提交：归属互换 + 申请置 confirmed
    assert _assignee(generated, 0, 1) == 2
    assert _assignee(generated, 0, 2) == 1
    assert _swap_row(req["id"])["status"] == "confirmed"


def test_same_person_swap_rejected(generated):
    # 同人两格：d0T1 与 d1T2 都是 M1
    assert _assignee(generated, 0, 1) == _assignee(generated, 1, 2) == 1
    c = connect()
    with pytest.raises(SwapTxError) as ei:
        request_swap(c, generated, 0, 1, 1, 2)
    assert ei.value.reason == "same_assignee"
    c.close()
    c = connect()
    n = c.execute("SELECT COUNT(*) c FROM swap_requests").fetchone()["c"]
    c.close()
    assert n == 0  # 拒绝即不落申请行


def test_request_missing_slot_rejected(generated):
    c = connect()
    with pytest.raises(SwapTxError) as ei:
        request_swap(c, generated, 0, 1, 6, 99)
    assert ei.value.reason == "slot_missing"
    c.close()


def test_confirm_twice_rejected(generated):
    c = connect()
    sid = request_swap(c, generated, 0, 1, 0, 2)["id"]
    confirm_swap(c, sid)
    with pytest.raises(SwapTxError) as ei:
        confirm_swap(c, sid)
    assert ei.value.reason == "not_pending"
    c.close()


def test_confirm_missing_swap(fresh_db):
    with pytest.raises(SwapTxError) as ei:
        confirm_swap(connect(), 404)
    assert ei.value.reason == "swap not found"


def test_confirm_with_deleted_slot_stays_pending(generated):
    c = connect()
    sid = request_swap(c, generated, 0, 1, 0, 2)["id"]
    before = [dict(r) for r in c.execute(
        "SELECT id,member_id FROM assignments WHERE week_id=?", (generated,)).fetchall()]
    c.execute("DELETE FROM assignments WHERE week_id=? AND day=0 AND task_id=2", (generated,))
    c.commit()
    with pytest.raises(SwapTxError) as ei:
        confirm_swap(c, sid)
    assert ei.value.reason == "slot_missing"
    c.close()
    assert _swap_row(sid)["status"] == "pending"  # 失败不置 confirmed
    c = connect()
    after = {r["id"]: r["member_id"] for r in c.execute(
        "SELECT id,member_id FROM assignments WHERE week_id=?", (generated,)).fetchall()}
    c.close()
    for r in before:  # 幸存格位归属未被失败的事务改动
        if r["id"] in after:
            assert after[r["id"]] == r["member_id"]


def test_routes_map_tx_errors(generated):
    # 路由只做映射：同人两格 → 400；确认不存在 → 404；正常确认 → 200 路径
    with pytest.raises(HTTPException) as ei:
        main.request_swap(generated, SwapBody(a_day=0, a_task=1, b_day=1, b_task=2))
    assert ei.value.status_code == 400 and ei.value.detail == "same_assignee"
    with pytest.raises(HTTPException) as ei:
        main.confirm_swap(404)
    assert ei.value.status_code == 404 and ei.value.detail == "swap not found"
    c = connect()
    sid = request_swap(c, generated, 0, 1, 0, 2)["id"]
    c.close()
    assert main.confirm_swap(sid) == {"ok": True, "swap_id": sid}
