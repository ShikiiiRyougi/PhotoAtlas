import analytics
import pydeck as pdk
import streamlit as st
import pandas as pd
import random
import datetime

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
# 从 image_url 中提取有效图片链接
# =========================
def get_valid_image_urls(dataframe):
    if "image_url" not in dataframe.columns:
        return []

    urls = dataframe["image_url"].dropna().astype(str)
    urls = urls[urls.str.startswith(("http://", "https://"))]
    urls = list(pd.unique(urls))

    return urls


# =========================
# 生成视觉图片集合
# =========================
def generate_visual_image_set(dataframe):
    urls = get_valid_image_urls(dataframe)

    if not urls:
        return {
            "page_bg": None,
            "hero_bg": None,
            "menu_buttons": {},
            "background_button": None
        }

    urls = urls.copy()
    random.shuffle(urls)

    menu_names = [
        "首页概览",
        "全球地图",
        "摄影画廊",
        "上传归档",
        "排行趋势"
    ]

    def pick_image(index):
        return urls[index % len(urls)]

    page_bg = pick_image(0)
    hero_bg = pick_image(1)

    menu_buttons = {}
    start_index = 2

    for i, menu_name in enumerate(menu_names):
        menu_buttons[menu_name] = pick_image(start_index + i)

    background_button = pick_image(start_index + len(menu_names))

    return {
        "page_bg": page_bg,
        "hero_bg": hero_bg,
        "menu_buttons": menu_buttons,
        "background_button": background_button
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

# ✨ 优化一：默认关闭背景图，优先进入“纯净模式”
if "bg_enabled" not in st.session_state:
    st.session_state.bg_enabled = False


# =========================
# 获取当前背景状态下的 URL 变量
# =========================
if st.session_state.bg_enabled:
    page_background_image_url = st.session_state.visual_images.get("page_bg")
    hero_background_image_url = st.session_state.visual_images.get("hero_bg")
    menu_button_images = st.session_state.visual_images.get("menu_buttons", {})
    background_button_image_url = st.session_state.visual_images.get("background_button")
else:
    # 纯净模式
    page_background_image_url = None
    hero_background_image_url = None
    menu_button_images = {}
    background_button_image_url = None


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

page_icons = {
    "home": "🏠",
    "map": "🗺️",
    "gallery": "🎞️",
    "upload": "📦",
    "rank": "📈"
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
        background: linear-gradient(135deg, #f8fafc 0%, #f1f5f9 50%, #e2e8f0 100%);
    }
    """


# =========================
# 动态 CSS：顶部主横幅与基础文字适配
# =========================
if hero_background_image_url:
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
            url("{hero_background_image_url}");
        background-size: cover;
        background-position: center right;
        background-repeat: no-repeat;
        overflow: hidden;
    }}
    h1, h2, h3 {{
        color: #ffffff !important;
        text-shadow: 0 2px 8px rgba(15, 23, 42, 0.45) !important;
    }}
    .footer-text {{
        color: rgba(255, 255, 255, 0.82) !important;
        text-shadow: 0 2px 8px rgba(15, 23, 42, 0.55);
    }}
    """
else:
    hero_card_css = """
    .hero-card {
        padding: 34px 38px;
        border-radius: 24px;
        background: linear-gradient(135deg, #1e3a8a 0%, #3b82f6 100%);
        color: white;
        box-shadow: 0 10px 30px rgba(30, 58, 138, 0.15);
        margin-bottom: 24px;
    }
    h1, h2, h3 {
        color: #0f172a !important;
        text-shadow: none !important;
    }
    .footer-text {
        color: #64748b !important;
        text-shadow: none !important;
    }
    """


# =========================
# 动态 CSS：每个左侧菜单按钮单独背景
# =========================
def build_menu_button_css(menu_images):
    menu_class_map = {
        "首页概览": "menu-home",
        "全球地图": "menu-map",
        "摄影画廊": "menu-gallery",
        "上传归档": "menu-upload",
        "排行趋势": "menu-rank"
    }

    css = ""

    for menu_name, class_name in menu_class_map.items():
        image_url = menu_images.get(menu_name)

        if image_url:
            css += f"""
            .{class_name} {{
                background-image:
                    linear-gradient(
                        90deg,
                        rgba(37, 99, 235, 0.98) 0%,
                        rgba(59, 130, 246, 0.95) 34%,
                        rgba(79, 70, 229, 0.82) 54%,
                        rgba(99, 102, 241, 0.50) 72%,
                        rgba(124, 58, 237, 0.16) 100%
                    ),
                    url("{image_url}");
                background-size: cover;
                background-position: center right;
                background-repeat: no-repeat;
            }}
            """
        else:
            css += f"""
            .{class_name} {{
                background: linear-gradient(135deg, #3b82f6, #1d4ed8);
            }}
            """

    return css


menu_button_css = build_menu_button_css(menu_button_images)


# =========================
# 动态 CSS：更换背景按钮/开关背景按钮样式
# =========================
if background_button_image_url:
    background_button_css = f"""
    section[data-testid="stSidebar"] .stButton > button {{
        width: 100%;
        min-height: 48px;
        border-radius: 12px;
        margin-bottom: 8px;
        font-size: 14px;
        font-weight: 700;
        color: white;
        border: none;
        box-shadow: 0 6px 14px rgba(37, 99, 235, 0.15);
        background-image:
            linear-gradient(
                90deg,
                rgba(37, 99, 235, 0.95) 0%,
                rgba(59, 130, 246, 0.90) 50%,
                rgba(124, 58, 237, 0.20) 100%
            ),
            url("{background_button_image_url}");
        background-size: cover;
        background-position: center right;
        background-repeat: no-repeat;
    }}
    """
else:
    background_button_css = """
    section[data-testid="stSidebar"] .stButton > button {
        width: 100%;
        min-height: 48px;
        border-radius: 12px;
        margin-bottom: 8px;
        font-size: 14px;
        font-weight: 700;
        color: white;
        border: none;
        box-shadow: 0 6px 14px rgba(37, 99, 235, 0.1);
        background: linear-gradient(135deg, #475569, #334155);
    }
    """


# =========================
# 总体 CSS 注入
# =========================
st.markdown(
    f"""
    <style>
    {page_background_css}
    {hero_card_css}
    {menu_button_css}
    {background_button_css}

    .hero-title {{
        font-size: 34px;
        font-weight: 800;
        margin-bottom: 8px;
        letter-spacing: 0.5px;
    }}

    .hero-subtitle {{
        font-size: 15px;
        color: rgba(255, 255, 255, 0.90);
        line-height: 1.6;
    }}

    .section-card {{
        background: rgba(255, 255, 255, 0.95);
        padding: 22px 24px;
        border-radius: 16px;
        border: 1px solid rgba(226, 232, 240, 0.8);
        box-shadow: 0 10px 25px rgba(15, 23, 42, 0.08);
        margin-bottom: 20px;
        backdrop-filter: blur(12px);
    }}

    .title-card {{
        background: rgba(255, 255, 255, 0.98);
        padding: 16px 22px;
        border-radius: 14px;
        border: 1px solid rgba(226, 232, 240, 0.9);
        box-shadow: 0 8px 22px rgba(15, 23, 42, 0.08);
        backdrop-filter: blur(12px);
        margin-top: 16px;
        margin-bottom: 16px;
    }}

    .title-card h2 {{
        color: #0f172a !important;
        text-shadow: none !important;
        margin: 0;
        font-size: 24px;
        font-weight: 800;
    }}

    .title-card p {{
        color: #64748b !important;
        margin-top: 6px;
        margin-bottom: 0;
        font-size: 13px;
        line-height: 1.6;
    }}

    .block-title {{
        font-size: 20px;
        font-weight: 800;
        color: #0f172a;
        margin-bottom: 6px;
    }}

    .block-caption {{
        font-size: 13px;
        color: #64748b;
        line-height: 1.6;
        margin-bottom: 14px;
    }}

    .photo-card {{
        background: rgba(255, 255, 255, 0.96);
        border-radius: 14px;
        padding: 10px;
        border: 1px solid rgba(229, 231, 235, 0.8);
        box-shadow: 0 6px 18px rgba(15, 23, 42, 0.08);
        margin-bottom: 14px;
        backdrop-filter: blur(10px);
    }}

    .feature-card {{
        background: rgba(255, 255, 255, 0.96);
        border-radius: 14px;
        padding: 20px 22px;
        border: 1px solid rgba(229, 231, 235, 0.8);
        box-shadow: 0 6px 18px rgba(15, 23, 42, 0.06);
        min-height: 140px;
        backdrop-filter: blur(10px);
    }}

    .feature-title {{
        font-size: 16px;
        font-weight: 800;
        color: #1e3a8a;
        margin-bottom: 6px;
    }}

    .feature-text {{
        font-size: 13px;
        color: #64748b;
        line-height: 1.6;
    }}

    div[data-testid="stMetric"] {{
        background: rgba(255, 255, 255, 0.96);
        padding: 16px;
        border-radius: 14px;
        border: 1px solid rgba(229, 231, 235, 0.8);
        box-shadow: 0 6px 16px rgba(15, 23, 42, 0.06);
        backdrop-filter: blur(10px);
    }}

    section[data-testid="stSidebar"] {{
        background: rgba(255, 255, 255, 0.96);
        border-right: 1px solid rgba(226, 232, 240, 0.8);
        backdrop-filter: blur(14px);
    }}

    .menu-link {{
        display: flex;
        align-items: center;
        justify-content: center;
        width: 100%;
        min-height: 64px;
        border-radius: 14px;
        margin-bottom: 12px;
        color: white !important;
        text-decoration: none !important;
        font-size: 18px;
        font-weight: 800;
        box-shadow: 0 8px 20px rgba(37, 99, 235, 0.15);
        transition: all 0.15s ease;
        overflow: hidden;
    }}

    .menu-link:hover {{
        transform: translateY(-2px);
        box-shadow: 0 12px 26px rgba(37, 99, 235, 0.25);
        color: white !important;
    }}

    .menu-link-active {{
        outline: 3px solid #3b82f6;
        box-shadow: 0 12px 26px rgba(37, 99, 235, 0.3);
    }}

    .menu-label {{
        background: rgba(15, 23, 42, 0.15);
        padding: 4px 12px;
        border-radius: 999px;
    }}

    [data-testid="stDataFrame"] {{
        border-radius: 12px;
        overflow: hidden;
        border: 1px solid rgba(229, 231, 235, 0.8);
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
                基于云计算架构的摄影大数据实时 analysis 系统，聚合全球摄影点位、热门目的地、
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
# 统计分析数据载入
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
    ("home", "首页概览", "🏠", "menu-home"),
    ("map", "全球地图", "🗺️", "menu-map"),
    ("gallery", "摄影画廊", "🎞️", "menu-gallery"),
    ("upload", "上传归档", "📦", "menu-upload"),
    ("rank", "排行趋势", "📈", "menu-rank")
]

for key, name, icon, css_class in menu_items:
    active_class = "menu-link-active" if current_page_key == key else ""
    st.sidebar.markdown(
        f"""
        <a href="?page={key}" target="_self" class="menu-link {css_class} {active_class}">
            <span class="menu-label">{icon} {name}</span>
        </a>
        """,
        unsafe_allow_html=True
    )


# =========================
# 🎨 侧边栏：背景控制中心
# =========================
st.sidebar.markdown("---")
st.sidebar.markdown("## 🎨 视觉氛围控制")

bg_toggle = st.sidebar.toggle("启用摄影图片背景", value=st.session_state.bg_enabled)

if bg_toggle != st.session_state.bg_enabled:
    st.session_state.bg_enabled = bg_toggle
    st.rerun()

if st.session_state.bg_enabled:
    if st.sidebar.button("🔄 更换下一张背景", use_container_width=True):
        st.session_state.visual_images = generate_visual_image_set(df)
        st.rerun()
    st.sidebar.caption("💡 提示：当前卡片与全局大背景来自摄影数据库中随机抓取的视觉影像。")
else:
    st.sidebar.info("🍃 已切换至纯净清爽背景模式。")


# =========================
# 侧边栏：全局数据过滤
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

st.sidebar.caption(f"全局筛选：{selected_month[0]} 月 - {selected_month[1]} 月")


# =========================
# 侧边栏：图片上传
# =========================
st.sidebar.markdown("---")
st.sidebar.markdown("## 🖼️ 摄影作品上传")

uploaded_file = st.sidebar.file_uploader(
    "上传摄影作品（限制 2MB）",
    type=["jpg", "jpeg", "png"],
    accept_multiple_files=False
)

if uploaded_file is not None:
    file_size_mb = uploaded_file.size / (1024 * 1024)

    if file_size_mb > 2:
        st.sidebar.error("图片不能超过 2MB ❌")
    else:
        if uploaded_file.name not in st.session_state.uploaded_photo_names:
            st.session_state.uploaded_photos.append(
                {
                    "name": uploaded_file.name,
                    "data": uploaded_file
                }
            )
            st.session_state.uploaded_photo_names.add(uploaded_file.name)
            st.sidebar.success("上传成功 ✅")
        else:
            st.sidebar.info("该图片已上传过。")


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
# ✨ 模块二：全球地图（核心重构 - 柱体高度微调版）
# =========================
def render_map():
    render_header()

    render_title_card(
        "🗺️ 全球摄影足迹地图",
        "使用 3D 六边形聚合层直接展示各区域摄影热度。剔除繁杂散点，选中柱体即可查看详情。"
    )

    if filtered_df.empty:
        st.info("筛选月份范围内暂无数据。")
        return

    # 🛠️ 引入地图页专属的时间分布查看与时间轴无缝联动
    st.markdown('<div class="section-card">', unsafe_allow_html=True)
    st.markdown('<div class="block-title">⏱️ 地图时间轴深度过滤</div>', unsafe_allow_html=True)
    
    # 统计当前全局过滤后，各个月份的分布数据作为时间轴参照
    timeline_stats = filtered_df.groupby("month").size().reindex(range(1, 13), fill_value=0)
    
    # 用简单的进度条/小迷你图表通知用户当前时间轴上分布状态
    st.caption("📅 当前已选月份范围内的拍摄热度分布简图：")
    st.bar_chart(timeline_stats, height=80)

    # 专属精细度滑块控制
    map_months = st.slider(
        "滑动微调地图专属展示月份（可缩减至单一月份查看动态演变）：",
        min_value=int(selected_month[0]),
        max_value=int(selected_month[1]),
        value=(int(selected_month[0]), int(selected_month[1])),
        key="map_exclusive_slider"
    )
    st.markdown('</div>', unsafe_allow_html=True)

    # 最终用于渲染地图的数据集
    map_df = filtered_df[
        (filtered_df["month"] >= map_months[0]) &
        (filtered_df["month"] <= map_months[1])
    ]

    if map_df.empty:
        st.warning("⏱️ 当前选定单月暂无拍摄记录，请拉大时间轴。")
        return

    # 🛠️ 纯 3D 柱体聚合层配置（高度已大幅优化，调矮观感更精致）
    hex_layer = pdk.Layer(
        "HexagonLayer",
        map_df,
        get_position=["longitude", "latitude"],
        radius=40000,           # 聚合半径(米)，更紧凑不易重叠覆盖
        elevation_scale=250,    # 💎 【核心修改点】从 1500 调矮到 250，让 3D 柱体高度平缓、高低错落更有沙盘质感
        elevation_range=[0, 1000], # 限制最高高度，防止极个别超高热点爆表
        pickable=True,          # 允许选中柱子
        extruded=True,          # 开启 3D 立体
        coverage=0.9,           # 柱体间隙美化
        color_range=[
            [243, 244, 246],
            [191, 219, 254],
            [96, 165, 250],
            [37, 99, 235],
            [29, 78, 216],
            [30, 58, 138]
        ]
    )

    # 精准定制柱体的悬停详情，多条同点位数据会在 points 里自动排列
    tooltip = {
        "html": """
        <div style="
            background: rgba(15,23,42,0.96);
            color: white;
            padding: 12px 14px;
            border-radius: 12px;
            width: 280px;
            font-family: Arial;
            box-shadow: 0 10px 20px rgba(0,0,0,0.3);
        ">
            <div style="font-size: 15px; font-weight: 700; margin-bottom: 6px; color:#3b82f6;">
                📊 区域聚合摄影热点
            </div>
            <div style="font-size: 13px; line-height: 1.7;">
                • 采集热度指数：<b>{elevationValue} 条记录</b><br/>
                • 核心参考点位：经度 {centroid.0} / 纬度 {centroid.1}
            </div>
            <div style="font-size: 11px; margin-top:8px; color:#94a3b8; border-top:1px solid #334155; padding-top:4px;">
                💡 旋转/倾斜地图：按住右键/Ctrl滑动鼠标
            </div>
        </div>
        """
    }

    view_state = pdk.ViewState(
        latitude=30.0,
        longitude=100.0,   # 初始视角聚焦亚太至全球过渡带
        zoom=2.5,
        pitch=45,          # 略微放平倾斜角度（从50度调到45度），配合矮柱体视觉效果极佳
        bearing=0
    )

    try:
        st.pydeck_chart(
            pdk.Deck(
                layers=[hex_layer],
                initial_view_state=view_state,
                tooltip=tooltip,
                map_style='dark'
                # map_style="mapbox://styles/mapbox/streets-v11" # 💎 【核心修改点】更换为内置免费路网底图，解决白屏显示不出来的问题
            ),
            use_container_width=True
        )
    except Exception as e:
        st.error("地图加载失败，请检查经纬度数据或 pydeck 配置。")
        st.exception(e)

    st.markdown("---")
    render_title_card("📍 3D 立体柱状地图交互说明")
    st.markdown(
        """
        <div class="section-card">
            为了杜绝散点被柱体无情掩盖、导致画面杂乱的问题，本版地图已进化为<b>全自动空间六边形聚合网络</b>。<br/>
            • <b>柱体高度与颜色</b>：颜色越深、柱体越高，代表该区域在指定月份段内生成的摄影作品数量越多。当前高度已优化，提供更舒适的宏观视觉比例。<br/>
            • <b>悬浮探测</b>：将鼠标移至任意 3D 柱体上，即可在云端浮窗中直接捕获该区块的核心热度指数及空间几何坐标。
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

            if pd.notna(row["image_url"]) and image_url.startswith(("http://", "https://")):
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
    
    tab1, tab2, tab3 = st.tabs(["📤 表单数据同步入库", "🗑️ 云端数据管理（删除）", "🖼️ 临时本地缓存查看"])
    
    # TAB 1: 写入云端数据库
    with tab1:
        render_title_card(
            "📝 提交全新摄影点位", 
            "在这里输入摄影作品的各项结构化元数据（包含网络图片URL），直接通过后端安全写入 Railway PostgreSQL 云端。"
        )
        
        with st.form("upload_meta_form", clear_on_submit=False):
            col1, col2 = st.columns(2)
            with col1:
                in_loc_name = st.text_input("📍 拍摄地点名称（例如：上海陆家嘴）", max_chars=100)
                in_photographer = st.text_input("👤 摄影师署名", max_chars=50)
                in_time = st.date_input("📅 拍摄日期")
            with col2:
                in_lon = st.number_input("🌐 经度 (Longitude)", min_value=-180.0, max_value=180.0, value=121.47, format="%.6f")
                in_lat = st.number_input("🌐 纬度 (Latitude)", min_value=-90.0, max_value=90.0, value=31.23, format="%.6f")
                in_url = st.text_input("🔗 图片 URL 链接（请右键复制网上的有效图片地址，需以 http/https 开头）")
            
            submit_btn = st.form_submit_button("🚀 安全写入云数据库")
            
            if submit_btn:
                if not in_loc_name or not in_photographer or not in_url:
                    st.error("请完整填写地点名称、摄影师以及图片链接！")
                elif not in_url.startswith(("http://", "https://")):
                    st.error("图片 URL 格式不合法，必须以 http:// 或 https:// 开头！")
                else:
                    with st.spinner("正在通过 SQLAlchemy 与云端数据库握手..."):
                        success, msg = analytics.insert_photo_to_db(
                            capture_time=in_time,
                            longitude=in_lon,
                            latitude=in_lat,
                            location_name=in_loc_name,
                            photographer=in_photographer,
                            image_url=in_url
                        )
                    if success:
                        st.success(msg)
                        st.cache_data.clear()
                        st.rerun()
                    else:
                        st.error(msg)

    # TAB 2: 从云端数据库删除
    with tab2:
        render_title_card("🚨 云端数据库清理面板", "警告：此操作直接对 PostgreSQL 云数据库执行 DELETE，删除后数据不可逆恢复。")
        
        admin_password = st.text_input("🔒 输入管理员管理凭证以解锁删除权限", type="password")
        
        if admin_password == "admin123":
            if df.empty:
                st.info("当前云端数据为空。")
            else:
                st.caption("为了演示方便，系统在此列出当前最新的 20 条摄影点位记录：")
                
                # 特别适配：兼容新旧 photo_id / id 的动态降级选择
                pk_col = "photo_id" if "photo_id" in df.columns else ("id" if "id" in df.columns else None)
                
                if not pk_col:
                    st.warning("⚠️ 数据库当前返回的 DataFrame 中没有包含识别主键字段，无法唯一定位删除！")
                else:
                    df_manage = df.head(20).copy()
                    df_manage["display_text"] = df_manage.apply(
                        lambda r: f"ID: {r[pk_col]} | 【{r['location_name']}】 - 摄影师: {r['photographer']} ({pd.to_datetime(r['capture_time']).strftime('%Y-%m')})", 
                        axis=1
                    )
                    
                    selected_record = st.selectbox("🎯 选择你想销毁的摄影点位记录：", options=df_manage["display_text"].tolist())
                    
                    if selected_record:
                        selected_id = selected_record.split(" | ")[0].split(": ")[1]
                        
                        if st.button("❌ 确认物理清除（不可逆转）", type="primary"):
                            with st.spinner("正在从 Railway 云端抹除该条目..."):
                                success, msg = analytics.delete_photo_from_db(selected_id)
                            if success:
                                st.success(msg)
                                st.cache_data.clear()
                                st.rerun()
                            else:
                                st.error(msg)
        else:
            if admin_password:
                st.error("🔒 密码错误，拒绝开启云端删除权限。")
            else:
                st.info("💡 请输入管理员密码以展示云端删除控制台（在 app.py 中预设）。")

    # TAB 3: 本地会话图片
    with tab3:
        render_title_card(
            "🖼️ 本地临时上传归档",
            "这里仅展示你从左侧边栏 file_uploader 临时上传的本地照片，它们仅保存在当前网页的 SessionState 会话缓存中，刷新网页就会消失。"
        )

        if not st.session_state.uploaded_photos:
            st.info("当前会话还没有上传本地图片。你可以通过左侧边栏尝试上传。")
            return

        st.success(f"当前会话已临时缓存在线 {len(st.session_state.uploaded_photos)} 张图片。")

        cols = st.columns(4)
        for idx, photo in enumerate(st.session_state.uploaded_photos):
            with cols[idx % 4]:
                st.markdown('<div class="photo-card">', unsafe_allow_html=True)
                st.image(photo["data"], caption=photo["name"], use_container_width=True)
                st.markdown('</div>', unsafe_allow_html=True)

        st.markdown("---")
        if st.button("🧹 清空本地上传归档"):
            st.session_state.uploaded_photos = []
            st.session_state.uploaded_photo_names = set()
            st.rerun()


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
        st.info("当前筛选月份范围内暂无数据. ")
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
st.sidebar.markdown("---")
st.markdown(
    """
    <div class="footer-text" style="
        text-align: center;
        font-size: 13px;
        padding: 18px 0 8px 0;
    ">
        全球摄影热点与视觉趋势云分析平台 · Cloud Photography Analytics Dashboard
    </div>
    """,
    unsafe_allow_html=True
)