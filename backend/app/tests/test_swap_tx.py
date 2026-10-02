import pytest

from app.services.swap_tx import (
    SwapNotFound,
    SwapRejected,
    confirm_swap,
    request_swap,
)


@pytest.fixture()
def conn(tmp_path, monkeypatch):
    """种子库 + 七天已生成周表（3 活跃成员 × 3 clean 任务）。"""
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    from app import seed
    from app.db import connect
    from app.main import GenBody, generate

    seed.init_db()
    generate(1, GenBody(days=7))
    c = connect()
    yield c
    c.close()


def _member_of(conn, day, task):
    r = conn.execute(
        "SELECT member_id FROM assignments WHERE week_id=1 AND day=? AND task_id=?",
        (day, task)).fetchone()
    return r["member_id"]


def test_request_rejects_same_assignee_pair(conn):
    # 3 成员 3 任务轮转：(day0,task1) 与 (day1,task1) 落在同一人
    assert _member_of(conn, 0, 1) == _member_of(conn, 1, 1)
    with pytest.raises(SwapRejected) as ei:
        request_swap(conn, 1, 0, 1, 1, 1)
    assert str(ei.value) == "same_assignee"
    n = conn.execute("SELECT COUNT(*) c FROM swap_requests").fetchone()["c"]
    assert n == 0  # 拒绝时不得落库


def test_request_missing_slot_rejected(conn):
    with pytest.raises(SwapRejected) as ei:
        request_swap(conn, 1, 0, 1, 6, 99)
    assert str(ei.value) == "slot_missing"


def test_confirm_commits_exchange_and_status(conn):
    ma, mb = _member_of(conn, 0, 1), _member_of(conn, 0, 2)
    assert ma != mb
    req = request_swap(conn, 1, 0, 1, 0, 2)
    assert req["status"] == "pending"
    out = confirm_swap(conn, req["id"])
    assert out == {"ok": True, "swap_id": req["id"]}
    assert _member_of(conn, 0, 1) == mb
    assert _member_of(conn, 0, 2) == ma
    status = conn.execute(
        "SELECT status FROM swap_requests WHERE id=?", (req["id"],)).fetchone()["status"]
    assert status == "confirmed"


def test_confirm_twice_is_rejected(conn):
    req = request_swap(conn, 1, 0, 1, 0, 2)
    confirm_swap(conn, req["id"])
    with pytest.raises(SwapRejected) as ei:
        confirm_swap(conn, req["id"])
    assert str(ei.value) == "not_pending"


def test_confirm_missing_swap_raises_not_found(conn):
    with pytest.raises(SwapNotFound):
        confirm_swap(conn, 999)
