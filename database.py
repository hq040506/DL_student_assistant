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
    college: Any = None, # str or List[str]
    major: Any = None,   # str or List[str]
    grade: Any = None,   # int or List[int]
    gender: Any = None   # str or List[str]
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
    
    # 支持多选 (List/Tuple) 或单选
    if college:
        if isinstance(college, (list, tuple)):
            placeholders = ",".join(["?"] * len(college))
            conditions.append(f"college IN ({placeholders})")
            params.extend(college)
        else:
            conditions.append("college = ?")
            params.append(college)
            
    if major:
        if isinstance(major, (list, tuple)):
            placeholders = ",".join(["?"] * len(major))
            conditions.append(f"major IN ({placeholders})")
            params.extend(major)
        else:
            conditions.append("major = ?")
            params.append(major)
            
    if grade:
        if isinstance(grade, (list, tuple)):
            placeholders = ",".join(["?"] * len(grade))
            conditions.append(f"grade IN ({placeholders})")
            params.extend([int(g) for g in grade])
        else:
            conditions.append("grade = ?")
            params.append(int(grade))
            
    if gender:
        if isinstance(gender, (list, tuple)):
            placeholders = ",".join(["?"] * len(gender))
            conditions.append(f"gender IN ({placeholders})")
            params.extend(gender)
        else:
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


def get_students_by_student_id(student_id: str) -> pd.DataFrame:
    conn = get_connection()
    try:
        return pd.read_sql_query(
            "SELECT * FROM students WHERE student_id = ?",
            conn,
            params=[student_id]
        )
    finally:
        conn.close()


def insert_student(student: Dict[str, Any]) -> int:
    fields = [
        "student_id",
        "name",
        "class_name",
        "college",
        "major",
        "grade",
        "gender",
        "phone",
    ]
    values = [student.get(field) for field in fields]

    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO students
            (student_id, name, class_name, college, major, grade, gender, phone)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            values,
        )
        conn.commit()
        return cursor.lastrowid
    finally:
        conn.close()


def update_student_by_id(row_id: int, updates: Dict[str, Any]) -> int:
    allowed_fields = {
        "student_id",
        "name",
        "class_name",
        "college",
        "major",
        "grade",
        "gender",
        "phone",
    }
    fields = [field for field in updates.keys() if field in allowed_fields]
    if not fields:
        return 0

    set_clause = ", ".join([f"{field} = ?" for field in fields])
    params = [updates[field] for field in fields]
    params.append(row_id)

    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            f"UPDATE students SET {set_clause} WHERE id = ?",
            params
        )
        conn.commit()
        return cursor.rowcount
    finally:
        conn.close()


def delete_student_by_id(row_id: int) -> int:
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM students WHERE id = ?", (row_id,))
        conn.commit()
        return cursor.rowcount
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
