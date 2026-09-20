import math
import pandas as pd

EARTH_RADIUS_KM = 6371.0


def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    if not (-90 <= lat1 <= 90):
        raise ValueError('Invalid latitude %r: latitude must be in range [-90, 90]' % (lat1,))
    if not (-90 <= lat2 <= 90):
        raise ValueError('Invalid latitude %r: latitude must be in range [-90, 90]' % (lat2,))
    if not (-180 <= lon1 <= 180):
        raise ValueError('Invalid longitude %r: longitude must be in range [-180, 180]' % (lon1,))
    if not (-180 <= lon2 <= 180):
        raise ValueError('Invalid longitude %r: longitude must be in range [-180, 180]' % (lon2,))

    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)

    a = math.sin(dlat / 2) ** 2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2
    c = 2 * math.asin(math.sqrt(a))

    return EARTH_RADIUS_KM * c


def calculate_distances(
    df: pd.DataFrame, user_lat: float, user_lon: float
) -> pd.DataFrame:
    df_copy = df.copy()
    lat_series = pd.to_numeric(df_copy['latitude'], errors='coerce')
    lon_series = pd.to_numeric(df_copy['longitude'], errors='coerce')
    distances = []
    for i in range(len(df_copy)):
        lat = lat_series.iloc[i]
        lon = lon_series.iloc[i]
        if pd.isna(lat) or pd.isna(lon):
            distances.append(None)
        else:
            try:
                d = haversine_distance(float(lat), float(lon), user_lat, user_lon)
                distances.append(d)
            except ValueError:
                distances.append(None)
    df_copy['distance_km'] = distances
    return df_copy
