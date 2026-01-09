import sqlite3
import pandas as pd
import random
from faker import Faker
from typing import Optional, Dict, Any

DB_PATH = "students.db"


def get_connection():
    return sqlite3.connect(DB_PATH)


def init_db():
    conn = get_connection()
    cursor = conn.cursor()

    # ===== 创建表（字段完整符合任务书）=====
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS students (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_id TEXT,
        name TEXT,
        class_name TEXT,     -- 班级（新增，任务书要求）
        college TEXT,
        major TEXT,
        grade INTEGER,
        gender TEXT,
        phone TEXT
    )
    """)

    # ===== 初始化数据 =====
    cursor.execute("SELECT COUNT(*) FROM students")
    count = cursor.fetchone()[0]

    if count == 0:
        print("Initializing database with Faker data...")
        generate_random_data(300)

    conn.commit()
    conn.close()


def query_df(sql: str) -> pd.DataFrame:
    """只用于 SELECT / COUNT"""
    conn = get_connection()
    try:
        return pd.read_sql_query(sql, conn)
    finally:
        conn.close()


def query_students(
    name: Optional[str] = None,
    student_id: Optional[str] = None,
    class_name: Optional[str] = None,
    college: Optional[str] = None,
    major: Optional[str] = None,
    grade: Optional[int] = None,
    gender: Optional[str] = None
) -> pd.DataFrame:
    conditions = []
    params = []

    if name:
        conditions.append("name LIKE ?")
        params.append(f"%{name}%")
    if student_id:
        conditions.append("student_id LIKE ?")
        params.append(f"%{student_id}%")
    if class_name:
        conditions.append("class_name LIKE ?")
        params.append(f"%{class_name}%")
    if college:
        conditions.append("college = ?")
        params.append(college)
    if major:
        conditions.append("major = ?")
        params.append(major)
    if grade:
        conditions.append("grade = ?")
        params.append(int(grade))
    if gender:
        conditions.append("gender = ?")
        params.append(gender)

    sql = "SELECT * FROM students"
    if conditions:
        sql += " WHERE " + " AND ".join(conditions)
    sql += " ORDER BY id DESC"

    conn = get_connection()
    try:
        return pd.read_sql_query(sql, conn, params=params)
    finally:
        conn.close()

def generate_random_data(num_records: int = 300):
    """使用 Faker 生成随机学生信息数据并导入数据库"""
    conn = get_connection()
    cursor = conn.cursor()
    
    fake = Faker('zh_CN')
    
    colleges_majors = {
        "计算机学院": ["软件工程", "计算机科学与技术", "网络工程", "信息安全"],
        "自动化学院": ["自动化", "测控技术与仪器", "机器人工程"],
        "信息工程学院": ["通信工程", "电子信息工程", "光电信息科学与工程"],
        "机械工程学院": ["机械设计制造及其自动化", "车辆工程", "工业设计"]
    }
    grades = [2021, 2022, 2023, 2024]

    records = []

    for _ in range(num_records):
        # 基础信息
        gender = random.choice(["男", "女"])
        name = fake.name_male() if gender == "男" else fake.name_female()
        phone = fake.phone_number()
        
        # 学业信息
        grade = random.choice(grades)
        college = random.choice(list(colleges_majors.keys()))
        major = random.choice(colleges_majors[college])
        
        # 简单的学院代码映射
        college_code = {
            "计算机学院": "01", "自动化学院": "02",
            "信息工程学院": "03", "机械工程学院": "04"
        }.get(college, "00")
        
        student_id = f"{grade}{college_code}{random.randint(1000, 9999)}"
        
        # 班级 (专业简称 + 年级后两位 + 班号)
        major_short = major[:2]
        class_num = random.randint(1, 4)
        class_name = f"{major_short}{str(grade)[-2:]}0{class_num}班"

        records.append((student_id, name, class_name, college, major, grade, gender, phone))

    cursor.executemany("""
    INSERT INTO students
    (student_id, name, class_name, college, major, grade, gender, phone)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, records)

    conn.commit()
    conn.close()
    print(f"Successfully generated {len(records)} student records using Faker.")

    return len(records)


def execute_sql(sql: str) -> int:
    """用于 INSERT / UPDATE / DELETE"""
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(sql)
        conn.commit()
        return cursor.rowcount
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
