"""对调事务：从申请到确认的提交路径，是本文件独占的写边界。

- request_swap：校验合法性（引擎 swap_legal）后落一条 pending 申请并提交。
- confirm_swap：重放引擎 apply_swap 得到新归属，然后在【一个事务】里
  提交两段 UPDATE（assignments 改归属 + swap_requests 置 confirmed）。
  路由禁止手写这两段 UPDATE —— 只能调本函数；任何一步失败整体回滚。

领域失败抛 SwapTxError，reason 为稳定错误码，由路由映射 HTTP 状态。
"""

from app.engines.rota import apply_swap, swap_legal


class SwapTxError(Exception):
    """对调事务的领域失败；reason 是稳定错误码（路由据此选 400/404）。"""

    def __init__(self, reason: str):
        super().__init__(reason)
        self.reason = reason


def request_swap(conn, week_id: int, a_day: int, a_task: int,
                 b_day: int, b_task: int, note: str = "") -> dict:
    """申请对调：非法（含同人两格 same_assignee）抛 SwapTxError，否则落 pending。"""
    assigns = [dict(r) for r in conn.execute(
        "SELECT day,task_id,member_id FROM assignments WHERE week_id=?", (week_id,))]
    check = swap_legal(assigns, a_day, a_task, b_day, b_task)
    if not check["ok"]:
        raise SwapTxError(check["reason"])
    cur = conn.execute(
        "INSERT INTO swap_requests(week_id,a_day,a_task,b_day,b_task,status,note)"
        " VALUES (?,?,?,?,?,?,?)",
        (week_id, a_day, a_task, b_day, b_task, "pending", note))
    conn.commit()
    return {"id": cur.lastrowid, "status": "pending", **check}


def confirm_swap(conn, swap_id: int) -> dict:
    """确认对调：两段 UPDATE 在单个事务里提交，失败整体回滚。"""
    sw = conn.execute("SELECT * FROM swap_requests WHERE id=?", (swap_id,)).fetchone()
    if sw is None:
        raise SwapTxError("swap not found")
    if sw["status"] != "pending":
        raise SwapTxError("not_pending")
    assigns = [dict(r) for r in conn.execute(
        "SELECT id,day,task_id,member_id FROM assignments WHERE week_id=?", (sw["week_id"],))]
    slots = [{"day": a["day"], "task_id": a["task_id"], "member_id": a["member_id"]} for a in assigns]
    try:
        new_slots = apply_swap(slots, sw["a_day"], sw["a_task"], sw["b_day"], sw["b_task"])
    except ValueError as e:
        raise SwapTxError(str(e))
    try:
        for a, s in zip(assigns, new_slots):
            conn.execute("UPDATE assignments SET member_id=? WHERE id=?",
                         (s["member_id"], a["id"]))
        conn.execute("UPDATE swap_requests SET status='confirmed' WHERE id=?", (swap_id,))
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    return {"ok": True, "swap_id": swap_id}
