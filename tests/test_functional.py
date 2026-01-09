import os
import sys

ROOT_DIR = os.path.dirname(os.path.dirname(__file__))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

import pandas as pd

import database
from llm_interface import LLMInterface


class _DummyResponse:
    status_code = 500

    class output:
        class choices:
            message = type("obj", (), {"content": ""})


def _run_test(name, fn):
    try:
        fn()
        print(f"[PASS] {name}")
    except Exception as exc:
        print(f"[FAIL] {name}: {exc}")
        raise


def test_db_init_and_schema():
    database.init_db()
    conn = database.get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(students)")
        cols = [row[1] for row in cursor.fetchall()]
    finally:
        conn.close()

    required = {
        "id",
        "student_id",
        "name",
        "class_name",
        "college",
        "major",
        "grade",
        "gender",
        "phone",
    }
    missing = required - set(cols)
    if missing:
        raise AssertionError(f"Missing columns: {missing}")


def test_query_students_filters():
    df = database.query_students(college=None)
    if df.empty:
        raise AssertionError("Database has no data")

    sample = df.iloc[0]
    sub = database.query_students(name=str(sample["name"]))
    if sub.empty:
        raise AssertionError("Filter by name returned empty")


def test_llm_fallback_rules():
    # Force LLM path to fail so fallback rules are exercised.
    import dashscope

    dashscope.Generation.call = lambda **kwargs: _DummyResponse()
    llm = LLMInterface()

    result = llm.handle("统计各学院人数")
    if result["type"] != "sql" or "group by college" not in result["sql"].lower():
        raise AssertionError("Expected group by college SQL for count query")

    result = llm.handle("查询张三信息")
    if result["type"] != "sql" or "select" not in result["sql"].lower():
        raise AssertionError("Expected SQL for select query")

    result = llm.handle("张三是男生吗")
    if result["type"] not in {"chat", "sql"}:
        raise AssertionError("Unexpected response type for boolean check")

    result = llm.handle("修改张三的手机号为13800000000")
    if result["type"] != "sql" or not result["sql"].lower().startswith("update"):
        raise AssertionError("Expected UPDATE SQL for modify command")


def main():
    _run_test("db init and schema", test_db_init_and_schema)
    _run_test("query students filters", test_query_students_filters)
    _run_test("llm fallback rules", test_llm_fallback_rules)
    print("All tests passed.")


if __name__ == "__main__":
    sys.exit(main())
