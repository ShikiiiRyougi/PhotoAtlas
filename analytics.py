from sqlalchemy import create_engine
import pandas as pd
import streamlit as st

# ---------- 配置数据库连接 ----------
def fetch_data_from_db():
    """
    从 PostgreSQL 读取 photos 表数据
    """
    DB_URL = st.secrets["DB_URL"]
    engine = create_engine(DB_URL)

    query = "SELECT * FROM photos;"

    # 直接用 pandas 读取 SQLAlchemy engine
    df = pd.read_sql(query, engine)

    # 关闭 engine
    engine.dispose()

    return df


def process_analytics(df):
    """
    处理数据：
    1️⃣ 热门景点按 likes 总和
    2️⃣ 每月拍摄趋势
    """
    if df is None or df.empty:
        return pd.DataFrame(), pd.DataFrame()

    # 处理 capture_time 为空或格式错误的情况
    df["capture_time"] = pd.to_datetime(df["capture_time"], errors="coerce")
    df["month"] = df["capture_time"].dt.month

    # 1️⃣ 热门景点排行榜（按 likes 总和）
    top_locations = (
        df.groupby("location_name")["likes"]
        .sum()
        .sort_values(ascending=False)
        .reset_index()
    )

    # 2️⃣ 月份趋势分析（按 1-12 排序）
    monthly_trend = (
        df.groupby("month")["photo_id"]
        .count()
        .reset_index()
        .rename(columns={"photo_id": "photo_count"})
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