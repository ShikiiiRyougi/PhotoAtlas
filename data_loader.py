import datetime
import random
import psycopg2
import streamlit as st

def generate_mock_photo_data(num_records=300):
    hotspots = [
        # 欧洲
        {"name": "巴黎埃菲尔铁塔", "lat": 48.8584, "lon": 2.2945},
        {"name": "伦敦大本钟", "lat": 51.5007, "lon": -0.1246},
        {"name": "罗马斗兽场", "lat": 41.8902, "lon": 12.4922},
        {"name": "威尼斯水城", "lat": 45.4408, "lon": 12.3155},

        # 日本
        {"name": "东京涩谷十字路口", "lat": 35.6595, "lon": 139.7005},
        {"name": "东京新宿", "lat": 35.6938, "lon": 139.7034},
        {"name": "京都清水寺", "lat": 34.9948, "lon": 135.7850},
        {"name": "奈良公园", "lat": 34.6851, "lon": 135.8050},
        {"name": "富士山", "lat": 35.3606, "lon": 138.7274},

        # 中国
        {"name": "上海外滩", "lat": 31.2304, "lon": 121.4737},
        {"name": "北京故宫", "lat": 39.9163, "lon": 116.3971},
        {"name": "杭州西湖", "lat": 30.2431, "lon": 120.1500},
        {"name": "张家界国家森林公园", "lat": 29.3167, "lon": 110.4833},
        {"name": "黄山", "lat": 30.1319, "lon": 118.1667},
        {"name": "稻城亚丁", "lat": 28.3768, "lon": 100.2981},
        {"name": "喀纳斯", "lat": 48.7120, "lon": 87.0400},
        {"name": "茶卡盐湖", "lat": 36.7078, "lon": 99.0790},
        {"name": "青海湖", "lat": 36.8933, "lon": 100.1386},
        {"name": "元阳梯田", "lat": 23.1346, "lon": 102.7312},
        {"name": "新疆赛里木湖", "lat": 44.6000, "lon": 81.2000},
        
        # 北美
        {"name": "纽约时代广场", "lat": 40.7580, "lon": -73.9855},
        {"name": "大峡谷国家公园", "lat": 36.1069, "lon": -112.1129},
        {"name": "优胜美地国家公园", "lat": 37.8651, "lon": -119.5383},
        {"name": "羚羊谷", "lat": 36.8619, "lon": -111.3743},
        {"name": "纪念碑谷", "lat": 36.9980, "lon": -110.0986},
        {"name": "死亡谷", "lat": 36.5054, "lon": -117.0794},
        {"name": "黄石国家公园", "lat": 44.4280, "lon": -110.5885},
        {"name": "拱门国家公园", "lat": 38.7331, "lon": -109.5925},
        
        # 加拿大
        {"name": "班夫国家公园", "lat": 51.4968, "lon": -115.9281},
        {"name": "露易丝湖", "lat": 51.4254, "lon": -116.1773},
        {"name": "梦莲湖", "lat": 51.3215, "lon": -116.1860},
        
        # 新西兰
        {"name": "米尔福德峡湾", "lat": -44.6717, "lon": 167.9250},
        {"name": "库克山", "lat": -43.5950, "lon": 170.1418},
        {"name": "瓦纳卡孤独之树", "lat": -44.6964, "lon": 169.1365},

        # 澳大利亚
        {"name": "大洋路十二门徒", "lat": -38.6655, "lon": 143.1050},
        {"name": "乌鲁鲁巨石", "lat": -25.3444, "lon": 131.0369},

        # 东南亚
        {"name": "巴厘岛佩尼达岛", "lat": -8.7278, "lon": 115.5444},
        {"name": "吴哥窟", "lat": 13.4125, "lon": 103.8670},
        {"name": "下龙湾", "lat": 20.9101, "lon": 107.1839},

        # 南美
        {"name": "马丘比丘", "lat": -13.1631, "lon": -72.5450},
        {"name": "乌尤尼盐沼", "lat": -20.1338, "lon": -67.4891},
        {"name": "巴塔哥尼亚", "lat": -50.9423, "lon": -73.4068},

        # 非洲
        {"name": "塞伦盖蒂国家公园", "lat": -2.3333, "lon": 34.8333},
        {"name": "乞力马扎罗山", "lat": -3.0674, "lon": 37.3556},
        {"name": "纳米布沙漠", "lat": -24.7270, "lon": 15.2960},

        # 冰岛
        {"name": "冰岛黄金瀑布", "lat": 64.3271, "lon": -20.1199},
        {"name": "塞里雅兰瀑布", "lat": 63.6156, "lon": -19.9921},

        # 挪威
        {"name": "罗弗敦群岛", "lat": 68.2075, "lon": 13.5665},
        {"name": "布道石", "lat": 58.9861, "lon": 6.1903},
        {"name": "特罗尔之舌", "lat": 60.1240, "lon": 6.7400},

        # 瑞士
        {"name": "少女峰", "lat": 46.5475, "lon": 7.9850},
        {"name": "马特洪峰", "lat": 45.9763, "lon": 7.6586},  # 🛠️ 已修正原先 46.01d 的语法错误
        {"name": "劳特布龙嫩", "lat": 46.5935, "lon": 7.9091},
        
        # 朝圣
        {"name": "法罗群岛", "lat": 62.0000, "lon": -6.8000},
        {"name": "格陵兰岛伊卢利萨特", "lat": 69.2196, "lon": -51.0986},
        {"name": "阿尔卑斯多洛米蒂", "lat": 46.4333, "lon": 11.8500},
        {"name": "挪威盖朗厄尔峡湾", "lat": 62.1015, "lon": 7.2057},
        {"name": "苏格兰天空岛", "lat": 57.2736, "lon": -6.2150},
        {"name": "美国马蹄湾", "lat": 36.8790, "lon": -111.5100},
        {"name": "加拿大贾斯珀国家公园", "lat": 52.8737, "lon": -117.9543},
        {"name": "冰岛维克镇", "lat": 63.4186, "lon": -19.0060},
    ]

    photos = []
    for i in range(num_records):
        spot = random.choice(hotspots)
        lat = spot["lat"] + random.uniform(-0.01, 0.01)
        lon = spot["lon"] + random.uniform(-0.01, 0.01)

        days_ago = random.randint(0, 365)
        capture_time = datetime.datetime.now() - datetime.timedelta(days=days_ago)
        capture_time = capture_time.strftime("%Y-%m-%d %H:%M:%S")

        # 🎯 严格对应的字段顺序，完美衔接云端表结构
        photos.append((
            f"p_{10000 + i}",
            f"User_{random.randint(1,50)}",
            spot["name"],
            lat,
            lon,
            capture_time,
            random.randint(10, 2000),
            f"https://picsum.photos/400/300?random={random.randint(1,1000)}"
        ))

    return photos

def save_to_cloud_db(photos):
    # 优先从 streamlit secrets 载入连接串，避免硬编码泄露风险
    try:
        DB_URL = st.secrets["DB_URL"]
    except Exception:
        DB_URL = "postgresql://postgres:zIFYleROpDgIanqJqBAkoVponqVDugtr@acela.proxy.rlwy.net:36131/railway"
        
    conn = psycopg2.connect(DB_URL)
    cursor = conn.cursor()

    # 🏢 权威唯一种型（Schema）定义：确保字段与前文完全对齐
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS photos (
        photo_id TEXT PRIMARY KEY,
        photographer TEXT NOT NULL,
        location_name TEXT,
        latitude NUMERIC(9,6),
        longitude NUMERIC(9,6),
        capture_time TIMESTAMP,
        likes INT DEFAULT 0,
        image_url VARCHAR(500),
        created_at TIMESTAMP DEFAULT now()
    );
    """)

    insert_query = """
    INSERT INTO photos (photo_id, photographer, location_name, latitude, longitude, capture_time, likes, image_url)
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
    ON CONFLICT (photo_id) DO NOTHING;
    """

    cursor.executemany(insert_query, photos)
    conn.commit()
    cursor.close()
    conn.close()

    print(f"✔ 成功插入 {len(photos)} 条数据！")

if __name__ == "__main__":
    # 建议第一次清洗时先生成 300 条或 2000 条进行测试
    data = generate_mock_photo_data(300)
    save_to_cloud_db(data)