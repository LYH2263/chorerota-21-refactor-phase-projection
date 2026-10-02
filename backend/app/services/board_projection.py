"""格位行 → 看板卡片投影。

assignments 表的一行是一个格位（week_id, day, task_id, member_id）；
看板卡片 = 格位行 + 成员名/任务标题。拼卡片字典只准发生在本文件 ——
生成服务/路由一律不得自行拼，前端只渲染本投影的结果、不得本地重算归属。

卡片顺序与库内格位行序（rowid 自然序）一致，二者同钉。
"""


def project_week_board(conn, week_id: int) -> dict | None:
    """把某周的格位行投影为看板卡片；周不存在返回 None（由路由映射 404）。"""
    week = conn.execute("SELECT * FROM weeks WHERE id=?", (week_id,)).fetchone()
    if week is None:
        return None
    rows = conn.execute(
        "SELECT id, week_id, day, task_id, member_id FROM assignments WHERE week_id=?",
        (week_id,),
    ).fetchall()
    members = {r["id"]: r["name"] for r in conn.execute("SELECT id,name FROM members")}
    tasks = {r["id"]: r["title"] for r in conn.execute("SELECT id,title FROM tasks")}
    cards = [
        {
            "id": r["id"],
            "week_id": r["week_id"],
            "day": r["day"],
            "task_id": r["task_id"],
            "member_id": r["member_id"],
            "member_name": members.get(r["member_id"], "?"),
            "task_title": tasks.get(r["task_id"], "?"),
        }
        for r in rows
    ]
    return {"week": dict(week), "cards": cards}
