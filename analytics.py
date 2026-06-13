from sqlalchemy import create_engine
import pandas as pd
import streamlit as st
import base64


def fetch_data_from_db():
    """
    从 PostgreSQL 读取 photos 表数据。

    支持两种图片来源：
    1. image_url：网络图片链接
    2. image_data：数据库中保存的本地上传图片二进制数据
    """
    try:
        DB_URL = st.secrets["DB_URL"]
    except Exception:
        st.error("未找到数据库连接配置 DB_URL，请检查 Streamlit secrets 设置。")
        return pd.DataFrame()

    try:
        engine = create_engine(DB_URL)

        query = "SELECT * FROM photos;"
        df = pd.read_sql(query, engine)

        engine.dispose()

        if df.empty:
            return df

        # 如果数据库里有 image_data 字段，把二进制图片转换成网页可显示的 base64 图片
        if "image_data" in df.columns:
            def convert_image(row):
                image_data = row.get("image_data")
                image_mime = row.get("image_mime")

                if image_data is not None:
                    try:
                        if isinstance(image_data, memoryview):
                            image_data = image_data.tobytes()

                        if isinstance(image_data, bytes):
                            mime = image_mime if image_mime else "image/jpeg"
                            encoded = base64.b64encode(image_data).decode("utf-8")
                            return f"data:{mime};base64,{encoded}"
                    except Exception:
                        pass

                # 没有本地上传图片时，继续使用原本的网络图片链接
                if "image_url" in row and pd.notna(row["image_url"]):
                    return row["image_url"]

                return None

            df["image_url"] = df.apply(convert_image, axis=1)

        return df

    except Exception as e:
        st.error("从数据库读取 photos 表失败，请检查数据库连接、表名或字段。")
        st.exception(e)
        return pd.DataFrame()


def process_analytics(df):
    """
    处理数据：
    1. 热门摄影目的地排行榜
    2. 每月拍摄趋势
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

    df["capture_time"] = pd.to_datetime(df["capture_time"], errors="coerce")
    df = df.dropna(subset=["capture_time"])

    df["likes"] = pd.to_numeric(df["likes"], errors="coerce").fillna(0)
    df["month"] = df["capture_time"].dt.month

    top_locations = (
        df.groupby("location_name", as_index=False)
        .agg(
            total_likes=("likes", "sum"),
            photo_count=("location_name", "count")
        )
        .sort_values(by="total_likes", ascending=False)
    )

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

    print("热门摄影目的地排行榜：")
    print(top_locations)

    print("\n每月拍摄趋势：")
    print(monthly_trend)
