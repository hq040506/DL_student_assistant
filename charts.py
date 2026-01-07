import plotly.express as px
import pandas as pd
import streamlit as st
from typing import Optional

def smart_plot(
    df: pd.DataFrame,
    title: str = "统计分析结果",
    max_categories: int = 20,
    key: Optional[str] = None
):
    """
    智能可视化函数（Plotly 版）
    
    功能说明：
    1. 使用 Plotly 替代 Matplotlib，提供交互式图表
    2. 自动适配 Streamlit 主题
    3. 尺寸自适应
    """

    if df is None or df.empty:
        st.warning("⚠️ 当前查询结果为空，无法进行可视化分析")
        return None

    # 如果数据只有一个值（例如 count=1），不需要画图，直接返回 None
    if len(df) == 1 and len(df.columns) == 1:
        return None

    columns = df.columns.tolist()
    fig = None

    # =========================
    # 情况 1：只有一列
    # =========================
    if len(columns) == 1:
        col = columns[0]
        if pd.api.types.is_numeric_dtype(df[col]):
            # 数值型 -> 直方图
            fig = px.histogram(df, x=col, title=f"{title}（数值分布）")
        else:
            # 类别型 -> 频次柱状图
            # 先统计频次
            counts = df[col].value_counts().head(max_categories).reset_index()
            counts.columns = [col, 'count']
            fig = px.bar(counts, x=col, y='count', title=f"{title}（类别分布）", text='count')

    # =========================
    # 情况 2：正好两列
    # =========================
    elif len(columns) == 2:
        col_x, col_y = columns
        
        # 尝试识别数值列和类别列
        num_cols = df.select_dtypes(include="number").columns.tolist()
        cat_cols = df.select_dtypes(exclude="number").columns.tolist()

        if len(num_cols) == 1 and len(cat_cols) == 1:
            # 类别 + 数值 -> 柱状图
            # 自动聚合
            grouped = df.groupby(cat_cols[0])[num_cols[0]].sum().reset_index()
            # 排序
            grouped = grouped.sort_values(by=num_cols[0], ascending=False).head(max_categories)
            
            fig = px.bar(
                grouped, 
                x=cat_cols[0], 
                y=num_cols[0], 
                title=f"{title}（统计图）",
                text=num_cols[0],
                color=cat_cols[0] # 自动配色
            )
        
        elif len(num_cols) == 2:
            # 两个数值 -> 散点图
            fig = px.scatter(df, x=col_x, y=col_y, title=f"{title}（相关性分析）")
        
        else:
            # 两个类别 -> 热力图或堆叠柱状图（简化处理：只画第一列的分布）
            counts = df[col_x].value_counts().head(max_categories).reset_index()
            counts.columns = [col_x, 'count']
            fig = px.bar(counts, x=col_x, y='count', title=f"{title}（{col_x}分布）")

    # =========================
    # 情况 3：多列
    # =========================
    else:
        num_cols = df.select_dtypes(include="number").columns.tolist()
        if len(num_cols) >= 2:
            # 多数值 -> 平行坐标图或折线图
            fig = px.line(df, y=num_cols, title=f"{title}（趋势分析）")
        else:
            st.info("📊 数据维度较多，建议直接查看表格。")
            return None

    if fig:
        # 优化图表布局
        fig.update_layout(
            xaxis_title=None,
            yaxis_title=None,
            showlegend=False,
            height=400, # 限制高度
            width=600,  # 限制宽度，防止在宽屏下过于拉伸
            margin=dict(l=20, r=20, t=40, b=20)
        )
        # 显示图表 (use_container_width=False 以保持固定宽度，更像 ChatGPT 的插图)
        st.plotly_chart(fig, use_container_width=False, key=key)
    
    return fig
