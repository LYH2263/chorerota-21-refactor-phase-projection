import pytest

from app import seed
from app.db import connect


@pytest.fixture()
def fresh_db(tmp_path, monkeypatch):
    """每个用例一座独立库：DATA_DIR 指向临时目录后重建表与种子。"""
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    seed.init_db()
    return tmp_path


@pytest.fixture()
def week_3x2(fresh_db):
    """验收夹具：三活跃成员（阿明/小雨/爷爷）+ 洗碗/倒垃圾 + 一个 draft 周。

    清库重插使 id 确定：成员 1/2/3，任务 1/2；返回 week_id。
    """
    c = connect()
    for t in ("assignments", "swap_requests", "members", "tasks", "weeks"):
        c.execute(f"DELETE FROM {t}")
    c.executemany("INSERT INTO members(name,active,data_quality) VALUES (?,?,?)",
                  [("阿明", 1, "clean"), ("小雨", 1, "clean"), ("爷爷", 1, "clean")])
    c.executemany("INSERT INTO tasks(title,weight,data_quality) VALUES (?,?,?)",
                  [("洗碗", 1, "clean"), ("倒垃圾", 1, "clean")])
    cur = c.execute("INSERT INTO weeks(label,status) VALUES ('第12周','draft')")
    wid = cur.lastrowid
    c.commit()
    c.close()
    return wid
