"""格位行 → 看板卡片投影（app/services/board_projection.py）的可失败测例。

验收钉：三活跃成员 + 洗碗/倒垃圾生成七天后，看板卡片数与改造前一致（14），
且投影回包与库内格位行同钉。
"""
import pytest
from fastapi import HTTPException

from app.db import connect
from app.engines.rota import build_week_slots
from app.main import GenBody, generate, week_board
from app.services.board_projection import project_week_board

MEMBERS = [1, 2, 3]  # 阿明/小雨/爷爷（week_3x2 夹具重插后的确定 id）
TASKS = [1, 2]       # 洗碗/倒垃圾


def _db_slots(wid):
    c = connect()
    rows = c.execute(
        "SELECT id, day, task_id, member_id FROM assignments WHERE week_id=?", (wid,)
    ).fetchall()
    c.close()
    return [dict(r) for r in rows]


def test_generate_returns_raw_slots_not_card_dicts(week_3x2):
    resp = generate(week_3x2, GenBody(days=7))
    assert resp["count"] == 14
    # 生成服务禁止拼看板卡片：回包格位不得带显示名字段
    for s in resp["slots"]:
        assert set(s.keys()) == {"day", "task_id", "member_id"}


def test_first_generation_matches_legacy_engine_layout(week_3x2):
    generate(week_3x2, GenBody(days=7))
    legacy = build_week_slots(MEMBERS, TASKS, days=7)
    got = [(r["day"], r["task_id"], r["member_id"]) for r in _db_slots(week_3x2)]
    want = [(s["day"], s["task_id"], s["member_id"]) for s in legacy]
    assert got == want


def test_projection_card_count_matches_pre_refactor(week_3x2):
    generate(week_3x2, GenBody(days=7))
    proj = project_week_board(connect(), week_3x2)
    assert len(proj["cards"]) == len(build_week_slots(MEMBERS, TASKS, days=7)) == 14


def test_projection_pinned_to_db_slots(week_3x2):
    generate(week_3x2, GenBody(days=7))
    proj = project_week_board(connect(), week_3x2)
    rows = _db_slots(week_3x2)
    assert len(proj["cards"]) == len(rows)
    for card, row in zip(proj["cards"], rows):
        assert card["id"] == row["id"]
        assert (card["day"], card["task_id"], card["member_id"]) == \
               (row["day"], row["task_id"], row["member_id"])
    # 显示名来自维表，不是格位行自带
    assert proj["cards"][0]["member_name"] == "阿明"
    assert proj["cards"][0]["task_title"] == "洗碗"


def test_projection_unknown_week_returns_none(fresh_db):
    assert project_week_board(connect(), 999) is None


def test_projection_marks_orphan_names(fresh_db):
    c = connect()
    wid = c.execute("SELECT id FROM weeks LIMIT 1").fetchone()["id"]
    c.execute("INSERT INTO assignments(week_id,day,task_id,member_id) VALUES (?,?,?,?)",
              (wid, 0, 999, 999))
    c.commit()
    card = project_week_board(c, wid)["cards"][0]
    assert card["member_name"] == "?" and card["task_title"] == "?"
    c.close()


def test_board_route_serves_projection_and_404s(week_3x2):
    generate(week_3x2, GenBody(days=7))
    board = week_board(week_3x2)
    assert len(board["cards"]) == 14
    assert board["week"]["status"] == "ready"
    with pytest.raises(HTTPException) as ei:
        week_board(999)
    assert ei.value.status_code == 404
