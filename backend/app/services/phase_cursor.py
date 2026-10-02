"""相位游标：round-robin 落位时的相位状态机（读 = peek/position，写 = advance/reset）。

拍板：游标状态内聚在生成服务内，不建独立仓储。
理由：游标的唯一消费者是单次生成过程——每次生成从相位 0 起步、生成结束即弃；
落库成仓储表会让“重新生成同一周”产生相位漂移（与改造前行为不一致），
且没有第二个读者，白增一张表和一类故障面。
"""


class PhaseCursor:
    """在 [0, span) 上循环的相位游标。span 为成员数，必须为正。"""

    def __init__(self, span: int, position: int = 0):
        if span <= 0:
            raise ValueError("span_must_be_positive")
        if not 0 <= position < span:
            raise ValueError("position_out_of_range")
        self._span = span
        self._position = position

    @property
    def span(self) -> int:
        return self._span

    @property
    def position(self) -> int:
        return self._position

    def peek(self) -> int:
        """读：返回当前相位，不推进。"""
        return self._position

    def advance(self) -> int:
        """写：返回当前相位并推进一格，到界回卷到 0。"""
        pos = self._position
        self._position = (self._position + 1) % self._span
        return pos

    def reset(self) -> None:
        """写：回到初始相位。"""
        self._position = 0
