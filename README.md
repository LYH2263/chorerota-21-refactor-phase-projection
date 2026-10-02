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

周表读改路径拆在 `backend/app/services/`：`phase_cursor`（相位游标读写；状态内聚于生成服务，不落独立仓储）、`board_projection`（格位行→看板卡片的唯一投影口，前端只渲染该回包）、`swap_tx`（对调申请→确认的两段 UPDATE 同事务提交，路由不手写 UPDATE）。
