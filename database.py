import sqlite3
import pandas as pd

DB_PATH = "students.db"


def get_connection():
    return sqlite3.connect(DB_PATH)


def init_db():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS students (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_id TEXT,
        name TEXT,
        college TEXT,
        major TEXT,
        grade INTEGER,
        gender TEXT,
        phone TEXT
    )
    """)

    # 检查是否已有数据
    cursor.execute("SELECT COUNT(*) FROM students")
    count = cursor.fetchone()[0]

    if count == 0:
        cursor.executemany("""
        INSERT INTO students (student_id, name, college, major, grade, gender, phone)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """, [
            ("2023001", "张三", "计算机学院", "软件工程", 2023, "男", "13800000001"),
            ("2023002", "李四", "计算机学院", "计算机科学", 2023, "女", "13800000002"),
            ("2023003", "王五", "自动化学院", "自动化", 2022, "男", "13800000003"),
            ("2023004", "赵六", "信息工程学院", "通信工程", 2022, "女", "13800000004"),
        ])

    conn.commit()
    conn.close()


def query_df(sql: str) -> pd.DataFrame:
    conn = get_connection()
    try:
        return pd.read_sql_query(sql, conn)
    finally:
        conn.close()


def get_distinct_values(column: str):
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(f"SELECT DISTINCT {column} FROM students")
        return [row[0] for row in cursor.fetchall()]
    finally:
        conn.close()
