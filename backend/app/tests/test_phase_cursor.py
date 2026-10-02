import pytest

from app.services.phase_cursor import PhaseCursor


def test_advance_returns_current_phase_then_wraps():
    c = PhaseCursor(3)
    assert [c.advance() for _ in range(7)] == [0, 1, 2, 0, 1, 2, 0]


def test_peek_reads_phase_without_advancing():
    c = PhaseCursor(2)
    assert c.peek() == 0
    assert c.peek() == 0
    c.advance()
    assert c.peek() == 1


def test_reset_returns_cursor_to_initial_phase():
    c = PhaseCursor(3)
    c.advance()
    c.advance()
    c.reset()
    assert c.position == 0
    assert c.advance() == 0


def test_empty_span_is_rejected():
    with pytest.raises(ValueError):
        PhaseCursor(0)


def test_start_position_must_be_inside_span():
    with pytest.raises(ValueError):
        PhaseCursor(3, position=3)
