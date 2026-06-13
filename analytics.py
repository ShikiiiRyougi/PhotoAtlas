import pandas as pd


def fetch_data_from_db():
    data = [
        {
            "location_name": "Paris",
            "photographer": "Alice",
            "likes": 1200,
            "capture_time": "2024-01-15",
            "latitude": 48.8566,
            "longitude": 2.3522,
            "image_url": "https://images.unsplash.com/photo-1502602898657-3e91760cbb34"
        },
        {
            "location_name": "Tokyo",
            "photographer": "Ken",
            "likes": 980,
            "capture_time": "2024-03-20",
            "latitude": 35.6762,
            "longitude": 139.6503,
            "image_url": "https://images.unsplash.com/photo-1540959733332-eab4deabeeaf"
        },
        {
            "location_name": "New York",
            "photographer": "Emma",
            "likes": 1350,
            "capture_time": "2024-06-05",
            "latitude": 40.7128,
            "longitude": -74.0060,
            "image_url": "https://images.unsplash.com/photo-1534430480872-3498386e7856"
        },
        {
            "location_name": "Singapore",
            "photographer": "Leo",
            "likes": 760,
            "capture_time": "2024-09-10",
            "latitude": 1.3521,
            "longitude": 103.8198,
            "image_url": "https://images.unsplash.com/photo-1525625293386-3f8f99389edd"
        },
    ]

    return pd.DataFrame(data)


def process_analytics(df):
    top_loc = (
        df.groupby("location_name", as_index=False)
        .agg(
            total_likes=("likes", "sum"),
            photo_count=("location_name", "count")
        )
        .sort_values(by="total_likes", ascending=False)
    )

    monthly_trend = (
        df.assign(month=pd.to_datetime(df["capture_time"]).dt.month)
        .groupby("month", as_index=False)
        .agg(photo_count=("month", "count"))
        .sort_values("month")
    )

    return top_loc, monthly_trend
