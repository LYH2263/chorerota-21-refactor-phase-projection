# Chorerota · 家庭值日轮转

底座：成员+任务 → round-robin 生成周表 → 申请对调 → 确认改表。

| 服务 | 端口 |
| --- | --- |
| 前端 | 5100 |
| API | 10100 |

```bash
docker compose up --build
pytest backend/app/tests
```

种子含 clean/dirty。0-1 空桩：`streak_badge` / `skip_week` / `chore_photo`。

周表读改路径三分：`repos/rota_cursor.py`（相位游标读写，独立仓储持久化）、
`services/board_projection.py`（格位行→看板卡片投影，卡片只在此拼）、
`services/swap_tx.py`（对调申请→确认的事务提交，两段 UPDATE 只在此）。
前端看板只渲染投影回包，不本地重算归属。
