"""相位游标仓储（app/repos/rota_cursor.py）的可失败测例。"""
from app.db import connect
from app.main import GenBody, generate
from app.repos.rota_cursor import advance_phase, read_phase, save_phase


def test_default_phase_is_zero(fresh_db):
    c = connect()
    assert read_phase(c) == 0
    c.close()


def test_save_then_read_roundtrip(fresh_db):
    c = connect()
    save_phase(c, 5)
    assert read_phase(c) == 5
    c.close()


def test_phase_survives_reconnect(fresh_db):
    c = connect()
    save_phase(c, 3)
    c.commit()
    c.close()
    c2 = connect()
    assert read_phase(c2) == 3
    c2.close()


def test_advance_wraps_mod_members(fresh_db):
    c = connect()
    save_phase(c, 2)
    # 2 + 14 格，3 名成员 → 落回 1
    assert advance_phase(c, slots=14, members=3) == 1
    assert read_phase(c) == 1
    c.close()


def test_advance_without_members_keeps_phase(fresh_db):
    c = connect()
    save_phase(c, 4)
    assert advance_phase(c, slots=10, members=0) == 4
    assert read_phase(c) == 4
    c.close()


def test_generate_consumes_cursor_across_weeks(week_3x2):
    # 首轮：相位 0，落位与改造前一致；14 格 / 3 人 → 游标推进到 2
    r1 = generate(week_3x2, GenBody(days=7))
    assert r1["phase"] == 2
    assert r1["slots"][0]["member_id"] == 1
    # 次轮：从相位 2 续转（成员序旋为 [3,1,2]），首格落 M3，游标到 (2+14)%3=1
    r2 = generate(week_3x2, GenBody(days=7))
    assert r2["phase"] == 1
    assert r2["slots"][0]["member_id"] == 3
    assert read_phase(connect()) == 1
