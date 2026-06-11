import analytics  # 你之前写的 fetch_data_from_db 和 process_analytics 模块
import pydeck as pdk
import streamlit as st
import pandas as pd
import random

st.set_page_config(layout="wide", page_title="全球摄影热点云分析平台")

st.title("全球摄影热点与视觉趋势云分析平台")
st.caption("基于云计算架构的摄影大数据实时分析系统")

# 1️⃣ 从云端拉取并分析数据
with st.spinner("正在从云端数据库加载实时流数据..."):
    df = analytics.fetch_data_from_db()
    top_loc, monthly_trend = analytics.process_analytics(df)

# # 处理标签数据（你现在没有 tags 字段，所以直接空字典）
# tag_counts = {}

if df.empty:
    st.warning("云数据库中暂无数据，请先运行 data_loader.py 导入数据。")
else:
    # 2️⃣ 侧边栏过滤器
    st.sidebar.header("🎛️ 数据过滤中心")

    uploaded_file = st.sidebar.file_uploader(
        "上传摄影作品（限制 2MB）",
        type=["jpg", "jpeg", "png"],
        accept_multiple_files=False
    )

    # 初始化上传图片列表（SessionState 保存用户上传的多张图片）
    if "uploaded_photos" not in st.session_state:
        st.session_state.uploaded_photos = []

    if uploaded_file is not None:
        # 限制文件大小 2MB
        file_size_mb = uploaded_file.size / (1024 * 1024)
        if file_size_mb > 2:
            st.sidebar.error("图片不能超过 2MB ❌")
        else:
            st.sidebar.success("上传成功 ✅")
            
            # 保存到 session_state 归档
            st.session_state.uploaded_photos.append({
                "name": uploaded_file.name,
                "data": uploaded_file
            })

    # 展示已上传图片列表（缩略图画廊）
    if st.session_state.uploaded_photos:
        st.subheader("📦 上传图片归档")
        cols = st.columns(4)  # 每行显示 4 张缩略图
        for idx, photo in enumerate(st.session_state.uploaded_photos):
            with cols[idx % 4]:
                st.image(photo["data"], caption=photo["name"], use_container_width=True)


    selected_month = st.sidebar.slider("选择拍摄月份筛选", 1, 12, (1, 12))

    df["month"] = pd.to_datetime(df["capture_time"]).dt.month
    filtered_df = df[(df["month"] >= selected_month[0]) & (df["month"] <= selected_month[1])]

    # 3️⃣ 核心可视化：全球摄影点位与图片展示
    st.subheader("🗺️ 全球摄影足迹地图（鼠标悬停显示照片）")

    if not filtered_df.empty:
        # 定义 Pydeck 图层
        hex_layer = pdk.Layer(
            "HexagonLayer",
            filtered_df,
            get_position=["longitude", "latitude"],
            radius=50000,
            elevation_scale=1000,
            elevation_range=[0, 5000],
            pickable=False,
            extruded=True,
        )

        scatter_layer = pdk.Layer(
            "ScatterplotLayer",
            filtered_df,
            get_position=["longitude", "latitude"],
            get_radius=10000,
            get_fill_color=[255, 100, 100, 180],
            pickable=True,
            auto_highlight=True,
        )

        # 鼠标悬停 tooltip
        tooltip = {
            "html": """
            <b>{location_name}</b><br/>
            摄影师：{photographer}<br/>
            点赞数：{likes}<br/>
            拍摄时间：{capture_time}<br/>
            <img src="{image_url}" width="250">
            """
        }

        view_state = pdk.ViewState(latitude=20.0, longitude=0.0, zoom=1.5, pitch=45)
        st.pydeck_chart(
            pdk.Deck(
                layers=[hex_layer, scatter_layer],
                initial_view_state=view_state,
                tooltip=tooltip
            )
        )
    else:
        st.info("筛选月份范围内暂无数据。")

    # 🔹 在地图下面，排行榜上面插入“随机摄影流动画廊”
    st.markdown("---")
    st.subheader("🎞️ 随机摄影流动画廊")

    if not df.empty:
        # 随机打乱
        random_df = df.sample(frac=1).reset_index(drop=True)
        
        # 限制只显示前 8 张（2 行 × 4 列）
        display_df = random_df.head(8)
        
        cols = st.columns(4)  # 每行 4 张缩略图
        for i, row in display_df.iterrows():
            with cols[i % 4]:
                st.image(row["image_url"], use_container_width=True)
                st.caption(f"{row['location_name']} · {row['photographer']}")

    # 刷新随机流
    if st.button("🔄 刷新随机流"):
        st.rerun()

    # 4️⃣ 下方图表：排行榜与趋势分析
    st.markdown("---")
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("🏆 热门摄影目的地（按获赞总量）")
        st.dataframe(top_loc, use_container_width=True)

    with col2:
        st.subheader("📅 摄影作品拍摄月份分布趋势")
        st.line_chart(monthly_trend.set_index("month"))

    # # 5️⃣ 附加亮点：标签热度展示（当前无标签）
    # st.subheader("🏷️ 热门摄影标签 Top 10")
    # if tag_counts:
    #     st.bar_chart(pd.Series(tag_counts))
    # else:
    #     st.info("当前数据库暂无标签数据，可在 photo_tags 表中添加后显示。")