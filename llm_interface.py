import re
import json
import os
from typing import Dict, Any, Optional

import dashscope
from dashscope import Generation
from database import get_distinct_values, query_df, get_connection

# =========================
# 配置 DashScope
# =========================
# 优先从环境变量读取（请确保环境变量 DASHSCOPE_API_KEY 已设置）
dashscope.api_key = os.getenv("DASHSCOPE_API_KEY", "").strip()
MODEL_NAME = "qwen-turbo"


class LLMInterface:
    """
    三段式架构：
    A. 意图识别
    B. 查询规划
    C. SQL 生成
    """

    def __init__(self):
        # 数据库字段白名单（严格）
        self.table = "students"
        self.fields = {
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

        # 统计支持的维度
        self.stat_dims = {"学院", "专业", "性别", "人数", "总人数", "专业数", "班级"}

    def set_api_key(self, api_key: str):
        dashscope.api_key = (api_key or "").strip()

    def has_api_key(self) -> bool:
        return bool(dashscope.api_key)

    # =====================================================
    # 主入口
    # =====================================================
    def handle(self, text: str, context: Optional[str] = None, pending: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        text = text.strip()
        
        # ---------- 二次确认流程 ----------
        if pending:
            return self._handle_pending(text, pending)

        # ---------- 0. 简单规则过滤 (打招呼/帮助) ----------
        # 优先处理简单的闲聊，避免浪费 LLM Token
        simple_reply = self._chat_reply(text)
        if simple_reply:
             return {
                "type": "chat",
                "message": simple_reply
            }

        # ---------- 1. 调用大模型进行智能分析 (Text2SQL + 意图识别) ----------
        # 获取元数据以辅助 LLM
        try:
            colleges = get_distinct_values("college")
            majors = get_distinct_values("major")
        except:
            colleges = []
            majors = []

        # 构造 Prompt
        prompt = f"""
你是一个智能学生信息管理助手。请根据用户输入和上下文，判断用户意图并生成相应的操作。

数据库表结构：
students (
    id INTEGER PRIMARY KEY,
    student_id TEXT (学号),
    name TEXT (姓名),
    class_name TEXT (班级),
    college TEXT (学院),
    major TEXT (专业),
    grade INTEGER (年级),
    gender TEXT (性别),
    phone TEXT (手机号)
)

数据库现有数据参考：
学院列表: {colleges}
专业列表: {majors}

用户输入: "{text}"
上下文: "{context if context else ''}"

请以 JSON 格式返回结果，不要包含 Markdown 格式标记（如 ```json）：
{{
    "type": "sql" | "chat" | "ask" | "boolean_check",
    // sql: 普通查询; chat: 闲聊/上下文回顾; ask: 追问; boolean_check: 是非判断(如"张三是男生吗")
    
    "sql": "SELECT ...",             // type="sql" 或 "boolean_check" 时需要。
    "response_type": "count" | "select", // type="sql" 时需要。
    "message": "...",                // type="chat" 或 "ask" 时需要。
    "expected_value": "..."          // type="boolean_check" 时需要。用户预期的值(如"男")。
}}

注意：
1. 如果用户询问之前的对话内容（如“我刚才问了什么”、“重复一遍”），请务必根据【上下文】中的信息进行回答，并将 type 设为 "chat"。
2. 如果用户问“统计学院人数”或“各学院人数”，请使用 GROUP BY college。同理适用于专业、班级等。
3. 如果用户问“张三是男生吗”，请返回 type="boolean_check"，生成查询性别的 SQL，并将 "男" 放入 expected_value。
4. 如果用户只说“统计人数”且未指定维度，请返回 type="ask"，并在 message 中列出具体的学院或专业供用户选择（参考上面的列表）。
5. 如果用户请求修改/删除/添加，请生成对应的 UPDATE/DELETE/INSERT 语句，并将 type 设为 "sql"。
6. 模糊查询请使用 LIKE。
7. 确保 SQL 语法正确。
"""
        
        try:
            # 调用 DashScope Qwen 模型
            resp = dashscope.Generation.call(
                model=dashscope.Generation.Models.qwen_turbo,
                prompt=prompt,
                result_format='message'
            )
            
            if resp.status_code == 200:
                content = resp.output.choices[0].message.content
                # 清理可能的 Markdown 标记
                content = content.replace("```json", "").replace("```", "").strip()
                result = json.loads(content)
                
                if result["type"] == "sql":
                    self._validate_sql(result["sql"])
                    
                    # 检查是否是修改操作 (INSERT/UPDATE/DELETE)
                    sql_lower = result["sql"].lower().strip()
                    if not sql_lower.startswith("select"):
                        # 尝试获取变更前的上下文信息 (仅针对 UPDATE)
                        context_msg = ""
                        if sql_lower.startswith("update") and "where" in sql_lower:
                            try:
                                # 提取 WHERE 子句
                                where_idx = sql_lower.index("where")
                                where_clause = result["sql"][where_idx:]
                                
                                # 查询当前值
                                check_sql = f"SELECT * FROM students {where_clause}"
                                current_df = query_df(check_sql)
                                
                                if not current_df.empty:
                                    # 尝试提取被修改的字段名
                                    # 假设格式: SET field = value
                                    m_set = re.search(r"set\s+(\w+)\s*=", sql_lower)
                                    if m_set:
                                        field = m_set.group(1)
                                        if field in current_df.columns:
                                            current_val = current_df.iloc[0][field]
                                            context_msg = f"\nℹ️ **当前状态**：该学生的 `{field}` 目前为 `{current_val}`"
                            except Exception as e:
                                print(f"Context fetch error: {e}")
                                pass

                        return {
                            "type": "ask",
                            "message": f"⚠️ **高风险操作确认**{context_msg}\n\n您即将执行以下数据库修改操作：\n```sql\n{result['sql']}\n```\n\n请回复 **“是”** 确认执行，或回复 **“否”** 取消。",
                            "pending": {
                                "intent": "execute_modify",
                                "sql": result["sql"]
                            }
                        }

                    return {
                        "type": "sql",
                        "sql": result["sql"],
                        "response_type": result.get("response_type", "select"),
                        "explain": f"🤖 已为您执行查询：\n`{result['sql']}`"
                    }
                elif result["type"] == "boolean_check":
                    # 内部执行 SQL 并进行判断
                    self._validate_sql(result["sql"])
                    try:
                        df = query_df(result["sql"])
                        if df.empty:
                            return {"type": "chat", "message": "⚠️ 未找到相关数据，无法判断。"}
                        
                        actual_value = str(df.iloc[0, 0])
                        expected = str(result.get("expected_value", ""))
                        
                        # 简单包含匹配
                        if expected in actual_value or actual_value in expected:
                            reply = f"✅ 是的，查询结果为：{actual_value}"
                        else:
                            reply = f"❌ 不是，查询结果为：{actual_value}"
                            
                        return {"type": "chat", "message": reply}
                    except Exception as e:
                        return {"type": "chat", "message": f"⚠️ 判断出错：{e}"}

                elif result["type"] == "chat":
                    return {
                        "type": "chat",
                        "message": result["message"]
                    }
                elif result["type"] == "ask":
                    return {
                        "type": "ask",
                        "message": result["message"],
                        "pending": None
                    }
            else:
                print(f"LLM Error: {resp}")
        except Exception as e:
            print(f"LLM Exception: {e}")
            pass

        # ---------- 回退：原有规则逻辑 (作为兜底) ----------
        prompt = f"""
你是一个智能学生信息管理助手。请根据用户输入和上下文，判断用户意图并生成相应的操作。

数据库表结构：
students (
    id INTEGER PRIMARY KEY,
    student_id TEXT (学号),
    name TEXT (姓名),
    class_name TEXT (班级),
    college TEXT (学院),
    major TEXT (专业),
    grade INTEGER (年级),
    gender TEXT (性别),
    phone TEXT (手机号)
)

用户输入: "{text}"
上下文: "{context if context else ''}"

请以 JSON 格式返回结果，不要包含 Markdown 格式标记（如 ```json）：
{{
    "type": "sql" | "chat" | "ask",  // sql: 需要查询数据库; chat: 普通闲聊/上下文回顾; ask: 需要用户补充信息
    "sql": "SELECT ...",             // 仅当 type="sql" 时需要。请生成标准的 SQLite 查询语句。
    "response_type": "count" | "select", // 仅当 type="sql" 时需要。count: 统计类; select: 明细类
    "message": "..."                 // 仅当 type="chat" 或 "ask" 时需要。
}}

注意：
1. 如果用户询问之前的对话内容（如“我刚才问了什么”），请务必根据【上下文】中的信息进行回答，并将 type 设为 "chat"。
2. 如果用户问“张三是男生吗”，请生成查询性别的 SQL，不要直接回答。
3. 如果用户问“一共有几个专业”，请使用 SELECT COUNT(DISTINCT major)...
4. 模糊查询请使用 LIKE。
5. 确保 SQL 语法正确，字段名符合表结构。
"""
        
        try:
            # 调用 DashScope Qwen 模型
            resp = dashscope.Generation.call(
                model=dashscope.Generation.Models.qwen_turbo,
                prompt=prompt,
                result_format='message'  # 确保返回格式兼容
            )
            
            if resp.status_code == 200:
                content = resp.output.choices[0].message.content
                # 清理可能的 Markdown 标记
                content = content.replace("```json", "").replace("```", "").strip()
                result = json.loads(content)
                
                if result["type"] == "sql":
                    self._validate_sql(result["sql"])
                    return {
                        "type": "sql",
                        "sql": result["sql"],
                        "response_type": result.get("response_type", "select"),
                        "explain": f"🤖 已为您执行查询：\n`{result['sql']}`"
                    }
                elif result["type"] == "chat":
                    return {
                        "type": "chat",
                        "message": result["message"]
                    }
                elif result["type"] == "ask":
                    return {
                        "type": "ask",
                        "message": result["message"],
                        "pending": None
                    }
            else:
                # LLM 调用失败，回退到规则逻辑
                print(f"LLM Error: {resp}")
        except Exception as e:
            print(f"LLM Exception: {e}")
            # 出错时回退到规则逻辑
            pass

        # ---------- 回退：原有规则逻辑 (作为兜底) ----------
        # 如果 LLM 失败，继续使用原来的逻辑
        original_text = text  # 保留原始输入用于展示
        
        if context:
            text = f"{context} {text}"
            
        intent = self._detect_intent(text)
        if intent == "chat":
             return {"type": "chat", "message": "抱歉，我暂时无法理解您的问题，请换种说法试试。"}

        plan = self._plan(text, intent)
        if plan["type"] == "ask":
            return plan
        
        if plan["type"] == "chat":
            return {"type": "chat", "message": "抱歉，我暂时无法理解您的问题，请换种说法试试。"}

        result = self._generate_sql(plan)
        if isinstance(result, dict):
            return result

        sql, response_type = result

        self._validate_sql(sql)

        return {
            "type": "sql",
            "sql": sql,
            "response_type": response_type,
            "explain": self._explain(original_text, plan, response_type)
        }

    # =====================================================
    # A. 意图识别（修复重点）
    # =====================================================
    def _detect_intent(self, text: str) -> str:
        # 存在性检查 / Boolean
        if "有" in text and "吗" in text: # e.g. 有张三这个人吗
            return "boolean"
        if "是" in text and "吗" in text: # e.g. 张三是男生吗
            return "boolean"

        # 明确数据库操作
        if any(k in text for k in ["查询", "查一下", "查看", "搜索", "找"]):
            if any(k in text for k in ["和", "或", "且"]):
                return "complex_select"
            return "select"
        if any(k in text for k in ["统计", "人数", "多少"]):
            return "count"
        if any(k in text for k in ["新增", "添加", "插入"]):
            return "insert"
        if any(k in text for k in ["修改", "更新"]):
            return "update"
        if any(k in text for k in ["删除", "移除"]):
            return "delete"

        # 兜底：chat
        return "chat"

    # =====================================================
    # ⭐ Chat 智能回复（核心修补点）
    # =====================================================
    def _chat_reply(self, text: str) -> Optional[str]:
        """简单的规则回复，如果匹配不到返回 None"""
        t = text.lower()

        # 如果包含具体操作指令，则不拦截，交给后续逻辑处理
        if any(k in t for k in ["查", "统计", "多少", "是", "修改", "删除", "增加", "班", "级", "学院", "专业"]):
            return None

        if any(k in t for k in ["你好", "您好", "嗨", "hello"]):
            return (
                "👋 你好！我是学生信息管理助手。\n\n"
                "我可以帮你：\n"
                "• 查询学生信息（如：查询张三信息）\n"
                "• 查询单个字段（如：张三的性别）\n"
                "• 统计人数（如：统计计算机学院人数）"
            )

        if any(k in t for k in ["你能干什么", "会什么", "功能", "可以做什么"]):
            return (
                "🤖 我主要负责学生信息管理相关任务，包括：\n\n"
                "📌 学生信息查询\n"
                "📌 学院 / 专业 / 性别 / 总人数统计\n"
                "📌 支持自然语言多轮对话\n\n"
                "你可以直接试试：`查询张三信息`"
            )

        if any(k in t for k in ["怎么用", "帮助"]):
            return (
                "📖 使用示例：\n\n"
                "• 查询张三信息\n"
                "• 张三的性别\n"
                "• 统计计算机学院人数\n"
                "• 一共有几个专业"
            )

        if any(k in t for k in ["谢谢", "感谢"]):
            return "😊 不客气！有需要随时找我。"

        # 移除兜底回复，交给 LLM 处理
        return None

    # =====================================================
    # B. 查询规划
    # =====================================================
    def _plan(self, text: str, intent: str) -> Dict[str, Any]:
        # --- 统计缺参反问 ---
        if intent == "count":
            if not any(k in text for k in ["学院", "专业", "性别", "班", "级", "总", "全部"]):
                # 动态获取列表以引导用户
                try:
                    colleges = [str(c) for c in get_distinct_values("college") if c]
                    majors = [str(m) for m in get_distinct_values("major") if m]
                    classes = [str(c) for c in get_distinct_values("class_name") if c]
                    
                    # 格式化列表，如果太长则截断
                    def fmt_list(lst, limit=5):
                        return "、".join(lst[:limit]) + (f" 等{len(lst)}个" if len(lst) > limit else "")

                    college_str = fmt_list(colleges)
                    major_str = fmt_list(majors)
                    class_str = fmt_list(classes)
                except:
                    college_str = "计算机学院..."
                    major_str = "软件工程..."
                    class_str = "..."

                return {
                    "type": "ask",
                    "message": (
                        "您需要统计哪个维度的人数？支持以下统计维度：\n\n"
                        f"🏫 **按学院** (例如：统计计算机学院人数)\n"
                        f"   *可选：{college_str}*\n\n"
                        f"📚 **按专业** (例如：统计软件工程人数)\n"
                        f"   *可选：{major_str}*\n\n"
                        f"👥 **按班级** (例如：统计软件2301班人数)\n"
                        f"   *可选：{class_str}*\n\n"
                        "📅 **按年级** (例如：统计2023级人数)\n"
                        "👫 **按性别** (例如：统计男生人数)\n\n"
                        "💡 **提示**：您也可以直接问“统计各学院人数”来查看所有学院的分布情况。"
                    ),
                    "pending": {"intent": "count"}
                }

            return {"type": "count", "text": text}

        # --- SELECT / BOOLEAN ---
        if intent == "complex_select":
            return {"type": "complex_select", "text": text}
        if intent == "select":
            return {"type": "select", "text": text}
        if intent == "boolean":
            return {"type": "complex_select", "text": text} # 复用 complex_select 的逻辑

        # --- INSERT / UPDATE / DELETE（简化保留） ---
        if intent in {"insert", "update", "delete"}:
            return {"type": intent, "text": text}

        return {"type": "chat"}

    # =====================================================
    # C. SQL 生成
    # =====================================================
    def _generate_sql(self, plan: Dict[str, Any]):
        t = plan["text"]

        # ---------- COUNT ----------
        if plan["type"] == "count":
            # --- 1. 聚合统计 (GROUP BY) ---
            if "各学院" in t or ("学院" in t and "人数" in t and not any(c in t for c in get_distinct_values("college"))):
                return ("SELECT college, COUNT(*) as count FROM students GROUP BY college", "select")
            
            if "各专业" in t or ("专业" in t and "人数" in t and "统计" in t and not re.search(r"统计(.+?)专业", t)):
                 return ("SELECT major, COUNT(*) as count FROM students GROUP BY major", "select")

            if "各班级" in t or ("班" in t and "人数" in t and "统计" in t):
                 # 检查是否指定了具体班级 (e.g. 软件2301班)
                 # 如果包含具体班级名，则不应该是 GROUP BY，除非显式包含 "各"
                 m = re.search(r"(.+?班)", t)
                 # 排除 "统计班级人数" 这种泛指
                 is_specific = m and "班级" not in m.group(1)
                 
                 if (not is_specific) or "各" in t:
                     return ("SELECT class_name, COUNT(*) as count FROM students GROUP BY class_name", "select")

            if "各年级" in t or ("级" in t and "人数" in t and "统计" in t):
                 m = re.search(r"(\d{4})", t)
                 if not m or "各" in t:
                     return ("SELECT grade, COUNT(*) as count FROM students GROUP BY grade", "select")

            # --- 2. 过滤统计 (WHERE) ---
            if "学院" in t:
                name = self._normalize_college(t)
                return (
                    f"SELECT COUNT(*) AS count FROM students WHERE college='{name}'",
                    "count"
                )

            if "专业" in t:
                majors = get_distinct_values("major")
                target_major = None
                
                # 1. 精确包含匹配
                for major in majors:
                    if major in t:
                        target_major = major
                        break
                
                # 2. 模糊匹配 (去除通用后缀)
                if not target_major:
                    for major in majors:
                        # 移除 "工程", "科学", "技术" 等后缀进行匹配
                        # e.g. "软件" -> "软件工程", "机设" -> "机械设计..."
                        simple = major.replace("工程", "").replace("科学", "").replace("技术", "").replace("与", "")
                        if simple in t and len(simple) >= 2:
                            target_major = major
                            break
                            
                if target_major:
                    return (
                        f"SELECT COUNT(*) AS count FROM students WHERE major='{target_major}'",
                        "count"
                    )
                
                # 3. 正则提取兜底
                m = re.search(r"统计(.+?)专业", t)
                if m:
                    return (
                        f"SELECT COUNT(*) AS count FROM students WHERE major='{m.group(1)}'",
                        "count"
                    )

            if "班" in t:
                m = re.search(r"(.+?班)", t)
                if m:
                    class_name = m.group(1)
                    # 清理前缀
                    for prefix in ["统计", "查询", "查看", "计算"]:
                        if class_name.startswith(prefix):
                            class_name = class_name[len(prefix):]
                    
                    # 排除 "班级" 这个词本身被匹配的情况
                    if class_name != "班级" and class_name.strip():
                        # --- 智能引导逻辑 ---
                        # 1. 先查询数据库看有几个匹配项
                        conn = get_connection()
                        cursor = conn.cursor()
                        cursor.execute(f"SELECT DISTINCT class_name FROM students WHERE class_name LIKE '%{class_name}%'")
                        matches = [row[0] for row in cursor.fetchall()]
                        conn.close()

                        if len(matches) == 0:
                            return {
                                "type": "chat",
                                "message": f"⚠️ 未找到包含「{class_name}」的班级。"
                            }
                        
                        elif len(matches) == 1:
                            # 只有一个匹配，直接使用该全名进行精确查询（比 LIKE 更准）
                            target = matches[0]
                            return (
                                f"SELECT COUNT(*) AS count FROM students WHERE class_name='{target}'",
                                "count"
                            )
                        
                        else:
                            # 多个匹配，发起追问
                            options = "\n".join([f"• {m}" for m in matches])
                            return {
                                "type": "ask",
                                "message": f"🤔 找到了多个包含「{class_name}」的班级，请问您指的是哪一个？\n\n{options}\n\n请直接回复班级全名（例如“{matches[0]}”）。",
                                "pending": {"intent": "count"}
                            }

            if "级" in t or re.search(r"\d{4}", t):
                m = re.search(r"(\d{4})", t)
                if m:
                    grade = m.group(1)
                    return (
                        f"SELECT COUNT(*) AS count FROM students WHERE grade={grade}",
                        "count"
                    )

            if "性别" in t:
                m = re.search(r"(男|女)", t)
                if m:
                    g = m.group(1)
                    return (
                        f"SELECT COUNT(*) AS count FROM students WHERE gender='{g}'",
                        "count"
                    )

            if "专业数" in t or "几个专业" in t:
                return (
                    "SELECT COUNT(DISTINCT major) AS count FROM students",
                    "count"
                )

            return ("SELECT COUNT(*) AS count FROM students", "count")

        # ---------- SELECT ----------
        if plan["type"] == "complex_select":
            # 处理“是吗”类型的查询
            # 增强正则以支持更多句式，如 "有张三这个人吗"
            if "有" in t and "吗" in t:
                m = re.search(r"有(.+)这个人吗", t) or re.search(r"有(.+)吗", t)
                if m:
                    name = m.group(1).strip()
                    sql = f"SELECT COUNT(*) FROM students WHERE name='{name}'"
                    count = query_df(sql).iloc[0, 0]
                    return {
                        "type": "chat",
                        "message": f"✅ 数据库中包含「{name}」的信息。" if count > 0 else f"❌ 数据库中没有找到「{name}」。"
                    }

            m = re.search(r"(.+)是(.+)吗", t)
            if m:
                subject, value = m.groups()
                subject = subject.strip()
                value = value.strip()
                
                # 尝试查询该主语（假设是人名）
                sql = f"SELECT * FROM students WHERE name='{subject}'"
                try:
                    df = query_df(sql)
                    if df.empty:
                        return {
                            "type": "chat",
                            "message": f"⚠️ 找不到学生「{subject}」，无法判断。"
                        }
                    
                    # 检查 value 是否在任何字段中
                    # 将整行数据转换为字符串列表进行模糊匹配
                    row_values = [str(v) for v in df.iloc[0].values]
                    # 双向包含匹配：value in v OR v in value
                    # 例如：value="男生", v="男" -> "男" in "男生" -> True
                    found = any(value in v or v in value for v in row_values)
                    
                    if found:
                        return {
                            "type": "chat",
                            "message": f"✅ 是的，{subject}确实是「{value}」。"
                        }
                    else:
                        # 尝试找到相关的正确信息（例如如果是问性别，就返回实际性别）
                        # 这里简单处理，直接说不是
                        return {
                            "type": "chat",
                            "message": f"❌ 不是，{subject}的信息中未包含「{value}」。"
                        }
                except Exception as e:
                    return {
                        "type": "chat",
                        "message": f"⚠️ 判断出错：{e}"
                    }

            # 查询张三信息
            m = re.search(r"查询(.+?)信息", t)
            if m:
                name = m.group(1)
                return (
                    f"SELECT * FROM students WHERE name='{name}'",
                    "select"
                )
            else:
                return {
                    "type": "ask",
                    "message": "请提供学生的姓名以查询信息。例如：查询张三信息。",
                    "pending": {"intent": "select"}
                }

            return ("SELECT * FROM students", "select")

        # ---------- UPDATE ----------
        if plan["type"] == "update":
            # 尝试匹配：修改 [姓名] 的 [字段] 为 [值]
            # 字段映射
            field_map = {
                "手机": "phone", "手机号": "phone", "电话": "phone",
                "班级": "class_name", "班": "class_name",
                "专业": "major",
                "学院": "college",
                "年级": "grade",
                "性别": "gender"
            }
            
            # 简单正则：修改张三的手机号为138...
            m = re.search(r"修改(.+)的(.+)为(.+)", t)
            if m:
                name, field_cn, value = m.groups()
                name = name.strip()
                field_cn = field_cn.strip()
                value = value.strip()
                
                db_field = field_map.get(field_cn)
                if not db_field:
                    # 尝试直接匹配
                    for k, v in field_map.items():
                        if k in field_cn:
                            db_field = v
                            break
                
                if db_field:
                    return (
                        f"UPDATE students SET {db_field}='{value}' WHERE name='{name}'",
                        "update" # response_type 不重要，因为 handle 会拦截
                    )
            
            return {
                "type": "chat",
                "message": "⚠️ 抱歉，我没能理解您的修改指令。请尝试使用标准格式，例如：“修改张三的手机号为13800000000”。"
            }

        # ---------- DELETE ----------
        if plan["type"] == "delete":
            # 删除张三
            m = re.search(r"删除(.+)", t)
            if m:
                name = m.group(1).strip()
                # 简单防误删：如果名字太短或包含特殊词
                if len(name) > 1 and name not in ["学生", "记录", "所有", "全部"]:
                    return (
                        f"DELETE FROM students WHERE name='{name}'",
                        "delete"
                    )
            
            return {
                "type": "chat",
                "message": "⚠️ 请指定要删除的学生姓名，例如：“删除张三”。"
            }

        # ---------- INSERT ----------
        if plan["type"] == "insert":
            return {
                "type": "chat",
                "message": "⚠️ 暂不支持通过规则模式添加学生，请尝试使用更详细的自然语言描述，让大模型为您处理。"
            }

        # 处理查询学生信息的操作
        if plan["type"] == "select":
            m = re.search(r"查询(.+?)信息", t)
            if m:
                name = m.group(1)
                return (
                    f"SELECT * FROM students WHERE name='{name}'",
                    "select"
                )
            return ("SELECT * FROM students", "select")

    # =====================================================
    # SQL 安全校验（已修复 distinct / count / students 误杀）
    # =====================================================
    def _validate_sql(self, sql: str):
        tokens = re.findall(r"[a-zA-Z_]+", sql.lower())
        allowed = (
            self.fields
            | {"select", "from", "where", "count", "distinct", "as", "sum", "avg", "min", "max"}
            | {"insert", "into", "values", "update", "set", "delete", "and", "or", "like", "in", "group", "by", "order", "limit", "asc", "desc", "null"}
            | {self.table}
        )

        for t in tokens:
            if t.isalpha() and t not in allowed:
                raise RuntimeError(f"❌ 非法字段：{t}")

    # =====================================================
    # 二次确认（占位保留）
    # =====================================================
    def _handle_pending(self, text: str, pending: Dict[str, Any]):
        # 处理统计追问的回答
        if pending.get("intent") == "count":
            # 构造新的查询文本，并清空 pending 以避免死循环
            new_text = text
            if "统计" not in text:
                new_text = f"统计{text}"
            # 递归调用，pending 置为 None
            return self.handle(new_text, pending=None)

        if pending.get("intent") == "select":
            # 用户补充了查询对象（如姓名）
            new_text = f"查询{text}信息"
            return self.handle(new_text, pending=None)

        if pending.get("intent") == "execute_modify":
            t = text.lower()
            # 扩展确认词库
            affirmative = {"是", "是的", "确认", "yes", "ok", "好的", "对", "没错", "行", "可以", "没问题"}
            negative = {"不", "不是", "否", "取消", "no", "cancel", "wrong", "错了", "不对", "别", "不要"}
            
            if t in affirmative:
                # 执行 SQL
                try:
                    from database import execute_sql
                    rowcount = execute_sql(pending["sql"])
                    return {"type": "chat", "message": f"✅ 操作成功，影响了 {rowcount} 行数据。"}
                except Exception as e:
                    return {"type": "chat", "message": f"❌ 执行失败：{e}"}
            elif t in negative:
                return {"type": "chat", "message": "❌ 已取消操作。"}
            else:
                return {"type": "chat", "message": "⚠️ 未识别的指令，为确保安全，已取消操作。"}

        if text in {"是", "确认", "yes"}:
            return pending["action"]
        return {
            "type": "chat",
            "message": "❌ 已取消该操作。"
        }

    # =====================================================
    # 辅助
    # =====================================================
    def _normalize_college(self, text: str) -> str:
        colleges = get_distinct_values("college")
        
        # 1. 全名或去后缀匹配 (e.g. "计算机" -> "计算机学院")
        for college in colleges:
            if college in text:
                return college
            if college.replace("学院", "") in text:
                return college
        
        # 2. 简称匹配 (e.g. "机院" -> "机械工程学院", "信院" -> "信息工程学院")
        # 简单的首字+院匹配逻辑
        for college in colleges:
            abbr = college[0] + "院"
            if abbr in text:
                return college
                
        return text

    def _explain(self, text: str, plan: Dict[str, Any], response_type: str) -> str:
        if response_type == "count":
            return f"📊 正在统计「{text}」的学生人数，结果如下："
        return f"🤖 我已根据你的问题「{text}」从学生数据库中查询到以下结果："
