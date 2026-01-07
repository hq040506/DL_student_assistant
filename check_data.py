from database import query_df, init_db

init_db()
print("--- All Students ---")
print(query_df("SELECT * FROM students"))
print("\n--- Count Gender='男' ---")
print(query_df("SELECT COUNT(*) FROM students WHERE gender='男'"))