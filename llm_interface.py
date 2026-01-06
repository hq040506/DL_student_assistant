import re
from database import get_distinct_values


class LLMInterface:
    def __init__(self):
        # 从数据库动态加载“可理解实体”
        self.names = get_distinct_values("name")
        self.colleges = get_distinct_values("college")
        self.majors = get_distinct_values("major")

    # ========== 1. 意图识别 ==========
    def detect_intent(self, text: str) -> str:
        if any(k in text for k in ["统计", "人数", "多少"]):
            return "count"
        if any(k in text for k in ["查询", "查看", "信息"]):
            return "query"
        return "unknown"

    # ========== 2. 槽位抽取（不是硬编码） ==========
    def extract_entities(self, text: str) -> dict:
        entities = {
            "name": None,
            "college": None,
            "major": None
        }

        for name in self.names:
            if name in text:
                entities["name"] = name
                break

        for college in self.colleges:
            if college in text:
                entities["college"] = college
                break

        for major in self.majors:
            if major in text:
                entities["major"] = major
                break

        return entities

    # ========== 3. 决策核心 ==========
    def handle(self, user_input: str, context: dict | None = None) -> dict:
        intent = self.detect_intent(user_input)
        entities = self.extract_entities(user_input)

        # --- 查询 ---
        if intent == "query":
            if entities["name"]:
                return {
                    "type": "sql",
                    "response_type": "query",
                    "sql": f"SELECT * FROM students WHERE name = '{entities['name']}'"
                }

            return {
                "type": "ask",
                "message": "你想查询哪位学生？请提供姓名。",
                "pending": {
                    "intent": "query"
                }
            }

        # --- 统计 ---
        if intent == "count":
            if entities["college"]:
                return {
                    "type": "sql",
                    "response_type": "count",
                    "sql": f"""
                        SELECT college AS 学院, COUNT(*) AS 人数
                        FROM students
                        WHERE college = '{entities["college"]}'
                        GROUP BY college
                    """
                }

            return {
                "type": "ask",
                "message": "你想统计哪个学院的人数？",
                "pending": {
                    "intent": "count"
                }
            }

        # --- 无法理解 ---
        return {
            "type": "ask",
            "message": "我可以帮你查询学生信息或统计人数，例如：查询张三信息、统计计算机学院人数。"
        }
