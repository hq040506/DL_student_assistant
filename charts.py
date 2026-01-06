import matplotlib.pyplot as plt
import pandas as pd
import streamlit as st
from typing import Optional

# =========================
# 全局绘图配置（中文支持）
# =========================
plt.rcParams["font.sans-serif"] = ["SimHei"]      # 中文字体
plt.rcParams["axes.unicode_minus"] = False        # 负号正常显示


def smart_plot(
    df: pd.DataFrame,
    title: str = "统计分析结果",
    max_categories: int = 20
) -> Optional[plt.Figure]:
    """
    智能可视化函数（课程设计完整版）

    功能说明：
    1. 自动分析 DataFrame 列类型
    2. 智能选择合适的可视化方式
    3. 支持多列数据，不限制列数
    4. 适用于数据库查询结果的统计分析展示

    可视化策略：
    - 单列：
        - 数值型 → 直方图
        - 分类型 → 频次柱状图
    - 两列：
        - 类别 + 数值 → 分组均值柱状图
    - 多列：
        - 多数值列 → 折线图（趋势）
        - 其余情况 → 自动降级为描述性统计表

    参数：
        df (pd.DataFrame): 查询得到的数据
        title (str): 图表标题
        max_categories (int): 最大分类数量，防止图表过密
    """

    if df is None or df.empty:
        st.warning("⚠️ 当前查询结果为空，无法进行可视化分析")
        return None

    fig, ax = plt.subplots(figsize=(8, 5))
    columns = df.columns.tolist()

    # =========================
    # 情况 1：只有一列
    # =========================
    if len(columns) == 1:
        col = columns[0]

        if pd.api.types.is_numeric_dtype(df[col]):
            ax.hist(df[col], bins=10)
            ax.set_xlabel(col)
            ax.set_ylabel("频数")
            ax.set_title(f"{title}（数值分布）")
        else:
            value_counts = df[col].value_counts().head(max_categories)
            value_counts.plot(kind="bar", ax=ax)
            ax.set_xlabel(col)
            ax.set_ylabel("数量")
            ax.set_title(f"{title}（类别分布）")

    # =========================
    # 情况 2：正好两列
    # =========================
    elif len(columns) == 2:
        col_x, col_y = columns

        # 类别 + 数值 → 分组统计
        if (
            not pd.api.types.is_numeric_dtype(df[col_x])
            and pd.api.types.is_numeric_dtype(df[col_y])
        ):
            grouped = (
                df.groupby(col_x)[col_y]
                .mean()
                .sort_values(ascending=False)
                .head(max_categories)
            )
            grouped.plot(kind="bar", ax=ax)
            ax.set_xlabel(col_x)
            ax.set_ylabel(f"{col_y}（均值）")
            ax.set_title(f"{title}（分组统计）")

        # 两个数值列 → 散点图
        elif (
            pd.api.types.is_numeric_dtype(df[col_x])
            and pd.api.types.is_numeric_dtype(df[col_y])
        ):
            ax.scatter(df[col_x], df[col_y])
            ax.set_xlabel(col_x)
            ax.set_ylabel(col_y)
            ax.set_title(f"{title}（相关性分析）")

        # 其他情况 → 降级为频次分析
        else:
            value_counts = df[col_x].value_counts().head(max_categories)
            value_counts.plot(kind="bar", ax=ax)
            ax.set_xlabel(col_x)
            ax.set_ylabel("数量")
            ax.set_title(f"{title}（主键分布）")

    # =========================
    # 情况 3：多列（≥3）
    # =========================
    else:
        numeric_cols = df.select_dtypes(include="number").columns.tolist()

        # 多个数值列 → 趋势/对比分析
        if len(numeric_cols) >= 2:
            df[numeric_cols].plot(ax=ax)
            ax.set_ylabel("数值")
            ax.set_title(f"{title}（多指标趋势分析）")
            ax.legend(title="指标")

        # 无法合理绘图 → 描述性统计
        else:
            st.info("📊 当前数据不适合直接绘图，已展示描述性统计结果")
            st.dataframe(df.describe(include="all"))
            return None

    plt.tight_layout()
    st.pyplot(fig)
    return fig
