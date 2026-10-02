"""对调事务：从申请到确认的提交路径。

确认对调的两段 UPDATE（改 assignments、改 swap_requests）只能在这里
同事务提交；路由只允许调用本文件，禁止手写 UPDATE。
"""

from app.engines.rota import apply_swap, swap_legal


class SwapNotFound(Exception):
    """对调单不存在（路由映射为 404）。"""


class SwapRejected(Exception):
    """对调不合法或状态不对（路由映射为 400，message 即 reason）。"""


def _week_slot_rows(conn, week_id: int) -> list[dict]:
    rows = conn.execute(
        "SELECT id,day,task_id,member_id FROM assignments WHERE week_id=? ORDER BY id",
        (week_id,),
    ).fetchall()
    return [dict(r) for r in rows]


def request_swap(conn, week_id: int, a_day: int, a_task: int,
                 b_day: int, b_task: int, note: str = "") -> dict:
    """申请对调：合法性校验通过后落库为 pending，同一事务提交。"""
    slots = _week_slot_rows(conn, week_id)
    check = swap_legal(slots, a_day, a_task, b_day, b_task)
    if not check["ok"]:
        raise SwapRejected(check["reason"])
    with conn:
        cur = conn.execute(
            "INSERT INTO swap_requests(week_id,a_day,a_task,b_day,b_task,status,note)"
            " VALUES (?,?,?,?,?,?,?)",
            (week_id, a_day, a_task, b_day, b_task, "pending", note))
    return {"id": cur.lastrowid, "status": "pending", **check}


def confirm_swap(conn, swap_id: int) -> dict:
    """确认对调：重校验后交换两格归属并改单状态，两段 UPDATE 同事务提交。"""
    sw = conn.execute("SELECT * FROM swap_requests WHERE id=?", (swap_id,)).fetchone()
    if sw is None:
        raise SwapNotFound("swap not found")
    if sw["status"] != "pending":
        raise SwapRejected("not_pending")
    rows = _week_slot_rows(conn, sw["week_id"])
    slots = [{"day": r["day"], "task_id": r["task_id"], "member_id": r["member_id"]} for r in rows]
    try:
        new_slots = apply_swap(slots, sw["a_day"], sw["a_task"], sw["b_day"], sw["b_task"])
    except ValueError as e:
        raise SwapRejected(str(e))
    # apply_swap 保持格位顺序，rows 与 new_slots 按下标一一对应
    with conn:
        for row, s in zip(rows, new_slots):
            conn.execute("UPDATE assignments SET member_id=? WHERE id=?",
                         (s["member_id"], row["id"]))
        conn.execute("UPDATE swap_requests SET status='confirmed' WHERE id=?", (swap_id,))
    return {"ok": True, "swap_id": swap_id}
