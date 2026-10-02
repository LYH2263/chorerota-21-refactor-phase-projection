"""相位游标仓储：round-robin 相位（起始成员偏移）的持久化读写。

拍板：游标状态放【独立仓储】（本模块 + rota_cursor 单行表），不内聚在生成服务里。
理由：相位要跨进程重启、跨周延续，是共享持久状态而非一次生成的局部变量；
生成路径只做无状态编排（读相位 → 引擎落位 → 推进相位），状态的读写收敛在此，
可脱离服务单测、可独立失败。

游标为全局单行（id=1），不按周分行：每次成功生成都会消费相位，
下一周从上一周落位的终点继续轮转，保证跨周公平。
"""

DDL = "CREATE TABLE IF NOT EXISTS rota_cursor(id INTEGER PRIMARY KEY CHECK(id=1), phase INTEGER NOT NULL DEFAULT 0)"


def read_phase(conn) -> int:
    """读当前相位；游标行尚未写入时视为 0（首轮生成与改造前一致）。"""
    row = conn.execute("SELECT phase FROM rota_cursor WHERE id=1").fetchone()
    return int(row["phase"]) if row else 0


def save_phase(conn, phase: int) -> None:
    """写相位（单行 upsert）。不 commit —— 由调用方并入自己的事务。"""
    conn.execute(
        "INSERT INTO rota_cursor(id,phase) VALUES(1,?) "
        "ON CONFLICT(id) DO UPDATE SET phase=excluded.phase",
        (int(phase),),
    )


def advance_phase(conn, slots: int, members: int) -> int:
    """按本次落位数推进游标：phase = (phase + slots) % members。

    members<=0（无活跃成员）时游标不动，避免除零；返回推进后的相位。
    """
    cur = read_phase(conn)
    if members <= 0:
        return cur
    nxt = (cur + slots) % members
    save_phase(conn, nxt)
    return nxt
