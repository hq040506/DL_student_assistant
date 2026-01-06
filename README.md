# 基于大语言模型的学生信息管理助手

## 项目简介
本项目基于大语言模型技术，实现一个支持自然语言交互的学生信息管理智能助手。系统能够通过自然语言自动生成 SQL 查询语句，对学生信息数据库进行管理，并将查询结果以表格和统计图的形式展示。

## 功能模块
- ChatGPT 风格对话式交互界面
- 学生信息数据库管理（增删改查）
- 自然语言到 SQL 的转换（text2sql）
- 多轮对话上下文管理
- 查询结果智能可视化展示

## 技术栈
- Python
- Streamlit
- SQLite
- Pandas
- Matplotlib

## 运行方式
```bash
conda activate student_ai
cd D:\DL_student_assistant
streamlit run app.py
