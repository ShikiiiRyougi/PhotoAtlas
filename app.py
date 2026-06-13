import analytics
import pydeck as pdk
import streamlit as st
import pandas as pd
import random
from sqlalchemy import create_engine, text


# =========================
# 页面基础配置
# =========================
st.set_page_config(
    layout="wide",
    page_title="全球摄影热点云分析平台",
    page_icon="📸"
)


# =========================
# 读取数据
# =========================
@st.cache_data(show_spinner=False)
def load_data():
    return analytics.fetch_data_from_db()


with st.spinner("正在从云端数据库加载实时流数据..."):
    df = load_data()


# =========================
# 空数据检查
# =========================
if df is None or df.empty:
    st.warning("云数据库中暂无数据，请先运行 data_loader.py 导入数据。")
    st.stop()


# =========================
# 必要字段检查
# =========================
required_columns = [
    "capture_time",
    "longitude",
    "latitude",
    "location_name",
    "photographer",
    "likes",
    "image_url"
]

missing_columns = [col for col in required_columns if col not in df.columns]

if missing_columns:
    st.error(f"数据缺少必要字段：{missing_columns}")
    st.info("请检查数据库表结构，或检查 analytics.fetch_data_from_db() 返回的数据字段名称。")
    st.stop()


# =========================
# 数据预处理
# =========================
df = df.copy()

df["capture_time"] = pd.to_datetime(df["capture_time"], errors="coerce")
df["longitude"] = pd.to_numeric(df["longitude"], errors="coerce")
df["latitude"] = pd.to_numeric(df["latitude"], errors="coerce")
df["likes"] = pd.to_numeric(df["likes"], errors="coerce").fillna(0)

df = df.dropna(subset=["capture_time", "longitude", "latitude"])
df["month"] = df["capture_time"].dt.month

if df.empty:
    st.warning("数据中没有有效的时间或经纬度信息，无法生成可视化结果。")
    st.stop()


# =========================
# 上传图片写入数据库
# =========================
def insert_uploaded_photo_to_db(
    location_name,
    photographer,
    latitude,
    longitude,
    uploaded_file
):
    """
    将用户上传的本地图片以二进制形式存入 PostgreSQL 数据库。
    """
    try:
        DB_URL = st.secrets["DB_URL"]
        engine = create_engine(DB_URL)

        image_bytes = uploaded_file.getvalue()

        with engine.begin() as conn:
            conn.execute(
                text("""
                    INSERT INTO photos (
                        location_name,
                        photographer,
                        likes,
                        capture_time,
                        latitude,
                        longitude,
                        image_url,
                        image_data,
                        image_mime,
                        image_filename
                    )
                    VALUES (
                        :location_name,
                        :photographer,
                        :likes,
                        NOW(),
                        :latitude,
                        :longitude,
                        :image_url,
                        :image_data,
                        :image_mime,
                        :image_filename
                    )
                """),
                {
                    "location_name": location_name,
                    "photographer": photographer,
                    "likes": 0,
                    "latitude": latitude,
                    "longitude": longitude,
                    "image_url": None,
                    "image_data": image_bytes,
                    "image_mime": uploaded_file.type,
                    "image_filename": uploaded_file.name
                }
            )

        engine.dispose()
        return True

    except Exception as e:
        st.error("图片写入数据库失败，请检查数据库连接或 photos 表字段。")
        st.exception(e)
        return False


def get_location_options(dataframe):
    """
    从现有数据库中提取地点、纬度、经度，供用户上传时选择。
    """
    if dataframe.empty:
        return pd.DataFrame(columns=["location_name", "latitude", "longitude"])

    location_df = (
        dataframe[["location_name", "latitude", "longitude"]]
        .dropna()
        .drop_duplicates(subset=["location_name"])
        .sort_values("location_name")
        .reset_index(drop=True)
    )

    return location_df


# =========================
# 从 image_url 中提取有效图片链接
# 包括网络图片和数据库二进制转换后的 data:image 图片
# =========================
def get_valid_image_urls(dataframe):
    if "image_url" not in dataframe.columns:
        return []

    urls = dataframe["image_url"].dropna().astype(str)
    urls = urls[
        urls.str.startswith(("http://", "https://", "data:image"))
    ]
    urls = list(pd.unique(urls))

    return urls


# =========================
# 生成视觉图片集合
# page_bg：网页大背景
# module_bg：顶部横幅和左侧所有按钮共用图
# 尽量保证 page_bg 和 module_bg 不同
# =========================
def generate_visual_image_set(dataframe):
    urls = get_valid_image_urls(dataframe)

    if not urls:
        return {
            "page_bg": None,
            "module_bg": None
        }

    urls = urls.copy()
    random.shuffle(urls)

    page_bg = urls[0]

    if len(urls) >= 2:
        module_bg = urls[1]
    else:
        module_bg = urls[0]

    return {
        "page_bg": page_bg,
        "module_bg": module_bg
    }


# =========================
# SessionState 初始化
# =========================
if "uploaded_photos" not in st.session_state:
    st.session_state.uploaded_photos = []

if "uploaded_photo_names" not in st.session_state:
    st.session_state.uploaded_photo_names = set()

if "visual_images" not in st.session_state:
    st.session_state.visual_images = generate_visual_image_set(df)


page_background_image_url = st.session_state.visual_images.get("page_bg")
module_background_image_url = st.session_state.visual_images.get("module_bg")


# =========================
# 页面路由
# =========================
page_options = {
    "home": "首页概览",
    "map": "全球地图",
    "gallery": "摄影画廊",
    "upload": "上传归档",
    "rank": "排行趋势"
}

current_page_key = st.query_params.get("page", "home")

if current_page_key not in page_options:
    current_page_key = "home"

current_page = page_options[current_page_key]


# =========================
# 动态 CSS：页面大背景
# =========================
if page_background_image_url:
    page_background_css = f"""
    .stApp {{
        background-image:
            linear-gradient(rgba(15, 23, 42, 0.60), rgba(15, 23, 42, 0.60)),
            url("{page_background_image_url}");
        background-size: cover;
        background-position: center;
        background-attachment: fixed;
        background-repeat: no-repeat;
    }}
    """
else:
    page_background_css = """
    .stApp {
        background: linear-gradient(135deg, #f5f7fb 0%, #eef2ff 45%, #f8fafc 100%);
    }
    """


# =========================
# 动态 CSS：顶部横幅
# =========================
if module_background_image_url:
    hero_card_css = f"""
    .hero-card {{
        padding: 34px 38px;
        border-radius: 24px;
        color: white;
        margin-bottom: 24px;
        box-shadow: 0 18px 45px rgba(15, 23, 42, 0.35);
        backdrop-filter: blur(10px);
        background-image:
            linear-gradient(
                90deg,
                rgba(17, 24, 39, 0.97) 0%,
                rgba(30, 58, 138, 0.94) 36%,
                rgba(59, 130, 246, 0.84) 55%,
                rgba(99, 102, 241, 0.54) 70%,
                rgba(124, 58, 237, 0.22) 86%,
                rgba(124, 58, 237, 0.10) 100%
            ),
            url("{module_background_image_url}");
        background-size: cover;
        background-position: center right;
        background-repeat: no-repeat;
        overflow: hidden;
    }}
    """
else:
    hero_card_css = """
    .hero-card {
        padding: 34px 38px;
        border-radius: 24px;
        background: linear-gradient(
            135deg,
            rgba(17, 24, 39, 0.92) 0%,
            rgba(30, 58, 138, 0.88) 52%,
            rgba(124, 58, 237, 0.86) 100%
        );
        color: white;
        box-shadow: 0 18px 45px rgba(15, 23, 42, 0.35);
        margin-bottom: 24px;
        backdrop-filter: blur(10px);
    }
    """


# =========================
# 动态 CSS：左侧按钮统一背景图
# =========================
if module_background_image_url:
    sidebar_button_css = f"""
    .menu-link {{
        background-image:
            linear-gradient(
                90deg,
                rgba(37, 99, 235, 0.98) 0%,
                rgba(59, 130, 246, 0.95) 34%,
                rgba(79, 70, 229, 0.82) 54%,
                rgba(99, 102, 241, 0.50) 72%,
                rgba(124, 58, 237, 0.16) 100%
            ),
            url("{module_background_image_url}");
        background-size: cover;
        background-position: center right;
        background-repeat: no-repeat;
    }}

    section[data-testid="stSidebar"] .stButton > button {{
        background-image:
            linear-gradient(
                90deg,
                rgba(37, 99, 235, 0.98) 0%,
                rgba(59, 130, 246, 0.95) 36%,
                rgba(79, 70, 229, 0.82) 56%,
                rgba(99, 102, 241, 0.50) 72%,
                rgba(124, 58, 237, 0.16) 100%
            ),
            url("{module_background_image_url}");
        background-size: cover;
        background-position: center right;
        background-repeat: no-repeat;
    }}
    """
else:
    sidebar_button_css = """
    .menu-link {
        background: linear-gradient(135deg, #2563eb, #7c3aed);
    }

    section[data-testid="stSidebar"] .stButton > button {
        background: linear-gradient(135deg, #2563eb, #7c3aed);
    }
    """


# =========================
# 总体 CSS
# =========================
st.markdown(
    f"""
    <style>
    {page_background_css}
    {hero_card_css}
    {sidebar_button_css}

    .hero-title {{
        font-size: 38px;
        font-weight: 800;
        margin-bottom: 8px;
        letter-spacing: 0.5px;
    }}

    .hero-subtitle {{
        font-size: 16px;
        color: rgba(255, 255, 255, 0.90);
        line-height: 1.7;
    }}

    .section-card {{
        background: rgba(255, 255, 255, 0.92);
        padding: 24px 26px;
        border-radius: 20px;
        border: 1px solid rgba(226, 232, 240, 0.75);
        box-shadow: 0 12px 28px rgba(15, 23, 42, 0.16);
        margin-bottom: 22px;
        backdrop-filter: blur(12px);
    }}

    .title-card {{
        background: rgba(255, 255, 255, 0.96);
        padding: 18px 24px;
        border-radius: 18px;
        border: 1px solid rgba(226, 232, 240, 0.9);
        box-shadow: 0 10px 26px rgba(15, 23, 42, 0.18);
        backdrop-filter: blur(12px);
        margin-top: 18px;
        margin-bottom: 18px;
    }}

    .title-card h2 {{
        color: #0f172a !important;
        text-shadow: none !important;
        margin: 0;
        font-size: 28px;
        font-weight: 850;
    }}

    .title-card p {{
        color: #64748b !important;
        margin-top: 8px;
        margin-bottom: 0;
        font-size: 14px;
        line-height: 1.7;
    }}

    .block-title {{
        font-size: 24px;
        font-weight: 800;
        color: #0f172a;
        margin-bottom: 8px;
    }}

    .block-caption {{
        font-size: 14px;
        color: #64748b;
        line-height: 1.7;
        margin-bottom: 18px;
    }}

    .photo-card {{
        background: rgba(255, 255, 255, 0.94);
        border-radius: 18px;
        padding: 10px;
        border: 1px solid rgba(229, 231, 235, 0.8);
        box-shadow: 0 8px 22px rgba(15, 23, 42, 0.14);
        margin-bottom: 16px;
        backdrop-filter: blur(10px);
    }}

    .feature-card {{
        background: rgba(255, 255, 255, 0.94);
        border-radius: 18px;
        padding: 22px 24px;
        border: 1px solid rgba(229, 231, 235, 0.8);
        box-shadow: 0 8px 22px rgba(15, 23, 42, 0.12);
        min-height: 150px;
        backdrop-filter: blur(10px);
    }}

    .feature-title {{
        font-size: 18px;
        font-weight: 800;
        color: #1e3a8a;
        margin-bottom: 8px;
    }}

    .feature-text {{
        font-size: 14px;
        color: #64748b;
        line-height: 1.7;
    }}

    div[data-testid="stMetric"] {{
        background: rgba(255, 255, 255, 0.94);
        padding: 18px;
        border-radius: 16px;
        border: 1px solid rgba(229, 231, 235, 0.8);
        box-shadow: 0 8px 20px rgba(15, 23, 42, 0.12);
        backdrop-filter: blur(10px);
    }}

    section[data-testid="stSidebar"] {{
        background: rgba(255, 255, 255, 0.94);
        border-right: 1px solid rgba(226, 232, 240, 0.8);
        backdrop-filter: blur(14px);
    }}

    .menu-link {{
        display: flex;
        align-items: center;
        justify-content: center;
        width: 100%;
        min-height: 74px;
        border-radius: 18px;
        margin-bottom: 16px;
        color: white !important;
        text-decoration: none !important;
        font-size: 20px;
        font-weight: 800;
        box-shadow: 0 10px 24px rgba(37, 99, 235, 0.22);
        transition: all 0.18s ease;
        overflow: hidden;
    }}

    .menu-link:hover {{
        transform: translateY(-2px);
        box-shadow: 0 14px 30px rgba(37, 99, 235, 0.32);
        color: white !important;
        text-decoration: none !important;
    }}

    .menu-link-active {{
        outline: 3px solid rgba(255, 255, 255, 0.95);
        box-shadow: 0 14px 32px rgba(37, 99, 235, 0.40);
    }}

    .menu-label {{
        background: rgba(15, 23, 42, 0.10);
        padding: 6px 14px;
        border-radius: 999px;
        text-shadow: 0 2px 8px rgba(15, 23, 42, 0.55);
    }}

    .stButton > button {{
        width: 100%;
        min-height: 54px;
        border-radius: 15px;
        margin-bottom: 8px;
        font-size: 16px;
        font-weight: 750;
        color: white;
        border: none;
        box-shadow: 0 8px 18px rgba(37, 99, 235, 0.20);
    }}

    .stButton > button:hover {{
        transform: translateY(-1px);
        box-shadow: 0 12px 24px rgba(37, 99, 235, 0.30);
    }}

    [data-testid="stDataFrame"] {{
        border-radius: 16px;
        overflow: hidden;
        border: 1px solid rgba(229, 231, 235, 0.85);
    }}

    h1, h2, h3 {{
        color: #ffffff;
        text-shadow: 0 2px 8px rgba(15, 23, 42, 0.45);
    }}

    .stMarkdown p {{
        color: inherit;
    }}
    </style>
    """,
    unsafe_allow_html=True
)


# =========================
# 页面头部
# =========================
def render_header():
    st.markdown(
        """
        <div class="hero-card">
            <div class="hero-title">📸 全球摄影热点与视觉趋势云分析平台</div>
            <div class="hero-subtitle">
                基于云计算架构的摄影大数据实时分析系统，聚合全球摄影点位、热门目的地、
                图片流与月份趋势，帮助用户快速发现视觉热点与摄影趋势。
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )


# =========================
# 标题卡片
# =========================
def render_title_card(title, caption=None):
    if caption:
        st.markdown(
            f"""
            <div class="title-card">
                <h2>{title}</h2>
                <p>{caption}</p>
            </div>
            """,
            unsafe_allow_html=True
        )
    else:
        st.markdown(
            f"""
            <div class="title-card">
                <h2>{title}</h2>
            </div>
            """,
            unsafe_allow_html=True
        )


# =========================
# 统计分析
# =========================
try:
    top_loc, monthly_trend = analytics.process_analytics(df)
except Exception as e:
    render_header()
    st.error("数据分析过程出现错误，请检查 analytics.process_analytics(df) 函数。")
    st.exception(e)
    st.stop()

if top_loc is None:
    top_loc = pd.DataFrame()

if monthly_trend is None:
    monthly_trend = pd.DataFrame()


# =========================
# 侧边栏：功能目录
# =========================
st.sidebar.markdown("## 功能目录")

menu_items = [
    ("home", "首页概览", "🏠"),
    ("map", "全球地图", "🗺️"),
    ("gallery", "摄影画廊", "🎞️"),
    ("upload", "上传归档", "📦"),
    ("rank", "排行趋势", "📈")
]

for key, name, icon in menu_items:
    active_class = "menu-link-active" if current_page_key == key else ""
    st.sidebar.markdown(
        f"""
        <a href="?page={key}" target="_self" class="menu-link {active_class}">
            <span class="menu-label">{icon} {name}</span>
        </a>
        """,
        unsafe_allow_html=True
    )


# =========================
# 侧边栏：背景控制
# =========================
st.sidebar.markdown("---")
st.sidebar.markdown("## 背景控制")

if st.sidebar.button("更换背景", use_container_width=True):
    st.session_state.visual_images = generate_visual_image_set(df)
    st.rerun()

if st.session_state.visual_images.get("page_bg"):
    st.sidebar.caption("当前页面背景与模块背景来自摄影数据库中的随机图片。")
else:
    st.sidebar.caption("当前未检测到有效图片链接，使用默认背景样式。")


# =========================
# 侧边栏：数据过滤中心
# =========================
st.sidebar.markdown("---")
st.sidebar.markdown("## 🎛️ 数据过滤中心")

selected_month = st.sidebar.slider(
    "选择拍摄月份范围",
    min_value=1,
    max_value=12,
    value=(1, 12)
)

filtered_df = df[
    (df["month"] >= selected_month[0]) &
    (df["month"] <= selected_month[1])
]

st.sidebar.caption(f"当前筛选：{selected_month[0]} 月 - {selected_month[1]} 月")


# =========================
# 侧边栏：图片上传到数据库
# =========================
st.sidebar.markdown("---")
st.sidebar.markdown("## 🖼️ 摄影作品上传")

location_df = get_location_options(df)

uploaded_file = st.sidebar.file_uploader(
    "上传摄影作品（限制 2MB）",
    type=["jpg", "jpeg", "png"],
    accept_multiple_files=False
)

photographer_name = st.sidebar.text_input(
    "摄影师名称",
    value="用户上传"
)

upload_mode = st.sidebar.radio(
    "选择拍摄地点方式",
    ["选择已有地点", "手动输入新地点"]
)

selected_location_name = None
selected_latitude = None
selected_longitude = None

if upload_mode == "选择已有地点":
    if not location_df.empty:
        location_names = location_df["location_name"].tolist()

        selected_location_name = st.sidebar.selectbox(
            "选择拍摄地点",
            location_names
        )

        selected_row = location_df[
            location_df["location_name"] == selected_location_name
        ].iloc[0]

        selected_latitude = float(selected_row["latitude"])
        selected_longitude = float(selected_row["longitude"])

        st.sidebar.caption(
            f"经纬度：{selected_latitude:.4f}, {selected_longitude:.4f}"
        )
    else:
        st.sidebar.warning("当前数据库中没有可选择的已有地点，请选择手动输入新地点。")

else:
    selected_location_name = st.sidebar.text_input(
        "输入新地点名称",
        value=""
    )

    selected_latitude = st.sidebar.number_input(
        "输入纬度 latitude",
        min_value=-90.0,
        max_value=90.0,
        value=0.0,
        step=0.0001,
        format="%.6f"
    )

    selected_longitude = st.sidebar.number_input(
        "输入经度 longitude",
        min_value=-180.0,
        max_value=180.0,
        value=0.0,
        step=0.0001,
        format="%.6f"
    )

if uploaded_file is not None:
    file_size_mb = uploaded_file.size / (1024 * 1024)

    if file_size_mb > 2:
        st.sidebar.error("图片不能超过 2MB ❌")
    else:
        st.sidebar.image(
            uploaded_file,
            caption="待上传预览",
            use_container_width=True
        )

        if st.sidebar.button("保存照片到数据库", use_container_width=True):
            if not selected_location_name:
                st.sidebar.error("请先选择或输入拍摄地点。")
            elif selected_latitude is None or selected_longitude is None:
                st.sidebar.error("缺少经纬度信息，无法保存。")
            else:
                success = insert_uploaded_photo_to_db(
                    location_name=selected_location_name,
                    photographer=photographer_name,
                    latitude=selected_latitude,
                    longitude=selected_longitude,
                    uploaded_file=uploaded_file
                )

                if success:
                    st.sidebar.success("照片已成功保存到数据库 ✅")

                    st.cache_data.clear()
                    st.rerun()


# =========================
# 模块一：首页概览
# =========================
def render_home():
    render_header()

    total_photos = len(df)
    total_locations = df["location_name"].nunique()
    total_photographers = df["photographer"].nunique()
    total_likes = int(df["likes"].sum())

    st.markdown(
        """
        <div class="section-card">
            <div class="block-title">📊 平台数据概览</div>
            <div class="block-caption">
                本页面展示云端摄影数据的整体情况，包括作品数量、覆盖地点、摄影师规模和累计点赞数。
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )

    m1, m2, m3, m4 = st.columns(4)

    with m1:
        st.metric("摄影作品总数", f"{total_photos:,}")

    with m2:
        st.metric("覆盖目的地", f"{total_locations:,}")

    with m3:
        st.metric("摄影师数量", f"{total_photographers:,}")

    with m4:
        st.metric("累计点赞数", f"{total_likes:,}")

    st.markdown("---")

    render_title_card(
        "☁️ 平台云端架构说明",
        "本平台将云端代码托管、云数据库、云端部署和实时数据分析结合起来，形成完整的数据可视化应用。"
    )

    c1, c2, c3 = st.columns(3)

    with c1:
        st.markdown(
            """
            <div class="feature-card">
                <div class="feature-title">GitHub 云端代码托管</div>
                <div class="feature-text">
                    项目代码通过 GitHub 进行版本管理，支持多人协作、代码更新与项目维护。
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )

    with c2:
        st.markdown(
            """
            <div class="feature-card">
                <div class="feature-title">Streamlit Cloud 云端部署</div>
                <div class="feature-text">
                    应用可部署到 Streamlit Cloud，用户无需本地环境即可通过浏览器访问系统。
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )

    with c3:
        st.markdown(
            """
            <div class="feature-card">
                <div class="feature-title">PostgreSQL 云数据库</div>
                <div class="feature-text">
                    摄影作品、地点、经纬度、点赞数和图片链接等数据集中存储在云端数据库。
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )

    st.markdown("---")

    render_title_card(
        "🔎 当前筛选数据预览",
        "该表格展示当前月份范围内的数据片段，方便检查筛选结果。"
    )

    preview_columns = [
        "location_name",
        "photographer",
        "likes",
        "capture_time",
        "latitude",
        "longitude"
    ]

    existing_preview_columns = [col for col in preview_columns if col in filtered_df.columns]

    if not filtered_df.empty:
        st.dataframe(
            filtered_df[existing_preview_columns].head(20),
            use_container_width=True,
            hide_index=True
        )
    else:
        st.info("当前筛选月份范围内暂无数据。")


# =========================
# 模块二：全球地图
# =========================
def render_map():
    render_header()

    render_title_card(
        "🗺️ 全球摄影足迹地图",
        "通过六边形热力层展示摄影热点密度，通过散点层展示具体摄影点位。鼠标悬停可查看照片信息。"
    )

    if filtered_df.empty:
        st.info("筛选月份范围内暂无数据。")
        return

    hex_layer = pdk.Layer(
        "HexagonLayer",
        filtered_df,
        get_position=["longitude", "latitude"],
        radius=50000,
        elevation_scale=1000,
        elevation_range=[0, 5000],
        pickable=False,
        extruded=True,
        coverage=0.85,
    )

    scatter_layer = pdk.Layer(
        "ScatterplotLayer",
        filtered_df,
        get_position=["longitude", "latitude"],
        get_radius=11000,
        get_fill_color=[255, 90, 90, 185],
        get_line_color=[255, 255, 255],
        line_width_min_pixels=1,
        pickable=True,
        auto_highlight=True,
    )

    tooltip = {
        "html": """
        <div style="
            background: rgba(15,23,42,0.92);
            color: white;
            padding: 12px 14px;
            border-radius: 12px;
            width: 280px;
            font-family: Arial;
        ">
            <div style="font-size: 16px; font-weight: 700; margin-bottom: 6px;">
                {location_name}
            </div>
            <div style="font-size: 13px; line-height: 1.7;">
                摄影师：{photographer}<br/>
                点赞数：{likes}<br/>
                拍摄时间：{capture_time}
            </div>
            <img src="{image_url}" width="250" style="
                margin-top: 10px;
                border-radius: 10px;
            ">
        </div>
        """
    }

    view_state = pdk.ViewState(
        latitude=20.0,
        longitude=0.0,
        zoom=1.5,
        pitch=45,
        bearing=0
    )

    try:
        st.pydeck_chart(
            pdk.Deck(
                layers=[hex_layer, scatter_layer],
                initial_view_state=view_state,
                tooltip=tooltip
            ),
            use_container_width=True
        )
    except Exception as e:
        st.error("地图加载失败，请检查经纬度数据或 pydeck 配置。")
        st.exception(e)

    st.markdown("---")

    render_title_card("📍 地图数据说明")

    st.markdown(
        """
        <div class="section-card">
            地图中的柱状六边形区域表示摄影作品的空间聚集程度，柱体越高代表该区域摄影点位越密集。
            红色散点代表具体摄影作品位置，鼠标悬停后可以查看地点、摄影师、点赞数、拍摄时间和图片预览。
        </div>
        """,
        unsafe_allow_html=True
    )


# =========================
# 模块三：摄影画廊
# =========================
def render_gallery():
    render_header()

    left_title, right_button = st.columns([4, 1])

    with left_title:
        render_title_card(
            "🎞️ 随机摄影流动画廊",
            "随机展示云端摄影作品，用于模拟实时摄影流推荐效果。"
        )

    with right_button:
        st.write("")
        st.write("")
        st.write("")
        if st.button("🔄 刷新随机流"):
            st.rerun()

    if filtered_df.empty:
        st.info("当前筛选月份范围内暂无摄影作品。")
        return

    random_df = filtered_df.sample(
        frac=1,
        random_state=random.randint(1, 999999)
    ).reset_index(drop=True)

    display_df = random_df.head(12)

    cols = st.columns(4)

    for i, row in display_df.iterrows():
        with cols[i % 4]:
            st.markdown('<div class="photo-card">', unsafe_allow_html=True)

            image_url = str(row["image_url"])

            if pd.notna(row["image_url"]) and image_url.startswith(("http://", "https://", "data:image")):
                st.image(image_url, use_container_width=True)
            else:
                st.info("图片链接无效，无法展示。")

            st.markdown(
                f"""
                <div style="padding: 6px 2px 2px 2px;">
                    <div style="font-weight: 700; color: #0f172a;">
                        {row['location_name']}
                    </div>
                    <div style="font-size: 13px; color: #64748b;">
                        摄影师：{row['photographer']}
                    </div>
                    <div style="font-size: 13px; color: #64748b;">
                        点赞数：{int(row['likes'])}
                    </div>
                </div>
                """,
                unsafe_allow_html=True
            )

            st.markdown('</div>', unsafe_allow_html=True)


# =========================
# 模块四：上传归档
# =========================
def render_upload_archive():
    render_header()

    render_title_card(
        "📦 上传图片归档",
        "这里展示已经保存到数据库中的摄影作品。用户上传的新照片会在保存后出现在这里。"
    )

    if df.empty:
        st.info("当前数据库中暂无图片数据。")
        return

    display_df = df.copy()

    if "capture_time" in display_df.columns:
        display_df = display_df.sort_values("capture_time", ascending=False)

    display_df = display_df.head(16)

    cols = st.columns(4)

    for idx, row in display_df.iterrows():
        with cols[idx % 4]:
            st.markdown('<div class="photo-card">', unsafe_allow_html=True)

            image_url = str(row["image_url"])

            if pd.notna(row["image_url"]) and image_url.startswith(("http://", "https://", "data:image")):
                st.image(image_url, use_container_width=True)
            else:
                st.info("图片无法展示。")

            st.markdown(
                f"""
                <div style="padding: 6px 2px 2px 2px;">
                    <div style="font-weight: 700; color: #0f172a;">
                        {row['location_name']}
                    </div>
                    <div style="font-size: 13px; color: #64748b;">
                        摄影师：{row['photographer']}
                    </div>
                    <div style="font-size: 13px; color: #64748b;">
                        拍摄时间：{row['capture_time']}
                    </div>
                </div>
                """,
                unsafe_allow_html=True
            )

            st.markdown('</div>', unsafe_allow_html=True)


# =========================
# 模块五：排行趋势
# =========================
def render_ranking_trend():
    render_header()

    render_title_card(
        "📈 热点排行与趋势分析",
        "从地点热度和月份分布两个角度分析摄影数据。"
    )

    col1, col2 = st.columns(2)

    with col1:
        st.markdown(
            """
            <div class="section-card">
                <div class="block-title">🏆 热门摄影目的地</div>
                <div class="block-caption">按照地点累计获赞量进行排序。</div>
            </div>
            """,
            unsafe_allow_html=True
        )

        if not top_loc.empty:
            st.dataframe(top_loc, use_container_width=True, hide_index=True)
        else:
            st.info("暂无热门目的地统计数据。")

    with col2:
        st.markdown(
            """
            <div class="section-card">
                <div class="block-title">📅 拍摄月份分布趋势</div>
                <div class="block-caption">展示不同月份摄影作品数量变化。</div>
            </div>
            """,
            unsafe_allow_html=True
        )

        if not monthly_trend.empty and "month" in monthly_trend.columns:
            st.line_chart(
                monthly_trend.set_index("month"),
                use_container_width=True
            )
        else:
            st.info("当前暂无月份趋势数据，或 monthly_trend 中缺少 month 字段。")

    st.markdown("---")

    render_title_card("📊 当前筛选范围内的局部统计")

    if filtered_df.empty:
        st.info("当前筛选月份范围内暂无数据。")
        return

    filtered_top = (
        filtered_df.groupby("location_name", as_index=False)
        .agg(
            total_likes=("likes", "sum"),
            photo_count=("location_name", "count")
        )
        .sort_values(by="total_likes", ascending=False)
    )

    filtered_monthly = (
        filtered_df.groupby("month", as_index=False)
        .size()
        .rename(columns={"size": "photo_count"})
        .sort_values("month")
    )

    c1, c2 = st.columns(2)

    with c1:
        st.markdown(
            """
            <div class="section-card">
                <div class="block-title">当前筛选热门地点</div>
            </div>
            """,
            unsafe_allow_html=True
        )
        st.dataframe(filtered_top, use_container_width=True, hide_index=True)

    with c2:
        st.markdown(
            """
            <div class="section-card">
                <div class="block-title">当前筛选月份趋势</div>
            </div>
            """,
            unsafe_allow_html=True
        )
        st.line_chart(filtered_monthly.set_index("month"), use_container_width=True)


# =========================
# 根据目录切换页面
# =========================
if current_page == "首页概览":
    render_home()

elif current_page == "全球地图":
    render_map()

elif current_page == "摄影画廊":
    render_gallery()

elif current_page == "上传归档":
    render_upload_archive()

elif current_page == "排行趋势":
    render_ranking_trend()


# =========================
# 底部说明
# =========================
st.markdown("---")
st.markdown(
    """
    <div style="
        text-align: center;
        color: rgba(255, 255, 255, 0.82);
        font-size: 13px;
        padding: 18px 0 8px 0;
        text-shadow: 0 2px 8px rgba(15, 23, 42, 0.55);
    ">
        全球摄影热点与视觉趋势云分析平台 · Cloud Photography Analytics Dashboard
    </div>
    """,
    unsafe_allow_html=True
)
