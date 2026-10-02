"""格位行 → 看板卡片投影。

看板卡片只允许在这里拼；生成服务与路由都不得直接拼卡片字典。
投影是纯函数：输入库内格位行，输出按天分桶的看板回包，
回包里的 (day, task_id, member_id) 与库内格位一一同钉。
"""

BOARD_DAYS = 7


def project_board(week: dict, slot_rows: list[dict],
                  member_names: dict[int, str], task_titles: dict[int, str],
                  days: int = BOARD_DAYS) -> dict:
    """把一周的作业格位行投影为看板回包 {week, days:[{day, cards}]}。

    - 每天一个桶（含空桶），前端按桶渲染即可，无需本地重算归属；
    - 卡片顺序跟随格位行顺序（调用方按 id 排序传入即稳定）；
    - 落在本周网格外（day 越界）的格位不上板。
    """
    buckets = [{"day": d, "cards": []} for d in range(days)]
    for row in slot_rows:
        d = row["day"]
        if not 0 <= d < days:
            continue
        buckets[d]["cards"].append({
            "id": row.get("id"),
            "day": d,
            "task_id": row["task_id"],
            "task_title": task_titles.get(row["task_id"], "?"),
            "member_id": row["member_id"],
            "member_name": member_names.get(row["member_id"], "?"),
        })
    return {"week": week, "days": buckets}
