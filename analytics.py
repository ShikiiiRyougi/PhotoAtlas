from sqlalchemy import create_engine
import pandas as pd
import streamlit as st


# ---------- 配置数据库连接 ----------
def fetch_data_from_db():
    """
    从 PostgreSQL 读取 photos 表数据
    """
    try:
        DB_URL = st.secrets["DB_URL"]
    except Exception:
        st.error("未找到数据库连接配置 DB_URL。请检查 Streamlit secrets 设置。")
        return pd.DataFrame()

    try:
        engine = create_engine(DB_URL)
        query = "SELECT * FROM photos;"
        df = pd.read_sql(query, engine)
        engine.dispose()
        return df

    except Exception as e:
        st.error("从数据库读取 photos 表失败，请检查数据库连接或表名。")
        st.exception(e)
        return pd.DataFrame()


def process_analytics(df):
    """
    处理数据：
    1. 热门景点按 likes 总和排序
    2. 每月拍摄趋势统计
    """
    if df is None or df.empty:
        return pd.DataFrame(), pd.DataFrame()

    df = df.copy()

    required_columns = [
        "capture_time",
        "location_name",
        "likes"
    ]

    missing_columns = [col for col in required_columns if col not in df.columns]

    if missing_columns:
        st.error(f"analytics.py 数据分析缺少必要字段：{missing_columns}")
        return pd.DataFrame(), pd.DataFrame()

    # 时间字段处理
    df["capture_time"] = pd.to_datetime(df["capture_time"], errors="coerce")
    df = df.dropna(subset=["capture_time"])

    # 点赞数字段处理
    df["likes"] = pd.to_numeric(df["likes"], errors="coerce").fillna(0)

    # 提取月份
    df["month"] = df["capture_time"].dt.month

    # 热门景点排行榜：按地点统计点赞总数和照片数量
    top_locations = (
        df.groupby("location_name", as_index=False)
        .agg(
            total_likes=("likes", "sum"),
            photo_count=("location_name", "count")
        )
        .sort_values(by="total_likes", ascending=False)
    )

    # 月份趋势分析：按月份统计作品数量
    monthly_trend = (
        df.groupby("month", as_index=False)
        .size()
        .rename(columns={"size": "photo_count"})
        .sort_values("month")
    )

    return top_locations, monthly_trend


if __name__ == "__main__":
    df = fetch_data_from_db()
    top_locations, monthly_trend = process_analytics(df)

    print("🔥 热门景点排行榜（按点赞总数）：")
    print(top_locations)

    print("\n📊 每月拍摄趋势：")
    print(monthly_trend)
