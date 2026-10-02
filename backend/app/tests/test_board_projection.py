import pytest

from app.services.board_projection import project_board


def test_projects_slot_rows_into_day_buckets():
    week = {"id": 1, "label": "第12周", "status": "ready"}
    rows = [
        {"id": 1, "day": 0, "task_id": 10, "member_id": 1},
        {"id": 2, "day": 0, "task_id": 20, "member_id": 2},
        {"id": 3, "day": 2, "task_id": 10, "member_id": 3},
    ]
    board = project_board(week, rows, {1: "阿明", 2: "小雨", 3: "爷爷"},
                          {10: "洗碗", 20: "倒垃圾"}, days=7)
    assert board["week"] == week
    assert [len(d["cards"]) for d in board["days"]] == [2, 0, 1, 0, 0, 0, 0]
    assert board["days"][0]["cards"][0] == {
        "id": 1, "day": 0, "task_id": 10, "task_title": "洗碗",
        "member_id": 1, "member_name": "阿明",
    }


def test_unknown_member_or_task_falls_back_to_question_mark():
    rows = [{"id": 9, "day": 1, "task_id": 99, "member_id": 99}]
    board = project_board({}, rows, {}, {}, days=7)
    card = board["days"][1]["cards"][0]
    assert card["member_name"] == "?"
    assert card["task_title"] == "?"


def test_rows_outside_the_week_grid_are_not_projected():
    rows = [{"id": 1, "day": 9, "task_id": 1, "member_id": 1}]
    board = project_board({}, rows, {1: "阿明"}, {1: "洗碗"}, days=7)
    assert all(not d["cards"] for d in board["days"])


def test_projection_stays_pinned_to_db_slot_rows(tmp_path, monkeypatch):
    """种子三活跃成员 + clean 任务七天生成：投影回包与库内格位同钉。

    改造前看板卡片数 = 7 天 × clean 任务数（洗碗/倒垃圾/扫地 = 3）= 21，
    改造后必须一致，且每张卡片的 (day, task_id, member_id) 与库内格位对齐。
    """
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    from app import seed
    from app.db import connect
    from app.main import GenBody, generate, week_board

    seed.init_db()
    generate(1, GenBody(days=7))
    board = week_board(1)
    cards = [card for d in board["days"] for card in d["cards"]]

    conn = connect()
    db_rows = conn.execute(
        "SELECT day,task_id,member_id FROM assignments WHERE week_id=1").fetchall()
    conn.close()

    assert len(db_rows) == 21  # 改造前同一种子下的卡片数
    assert len(cards) == len(db_rows)
    proj = sorted((c["day"], c["task_id"], c["member_id"]) for c in cards)
    db = sorted((r["day"], r["task_id"], r["member_id"]) for r in db_rows)
    assert proj == db
