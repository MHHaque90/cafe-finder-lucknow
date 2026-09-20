"""Deterministic cafe ranking and explainable recommendations for Lucknow Cafe Finder."""

import pandas as pd

MAX_DISTANCE_SCORE = 40
MAX_CUISINE_SCORE = 30
MAX_OPENING_HOURS_SCORE = 15
MAX_WEBSITE_SCORE = 10
MAX_PHONE_SCORE = 5
MAX_TOTAL_SCORE = 100


def calculate_distance_score(distance_km) -> int:
    """
    Calculate distance score based on distance bands.

    Args:
        distance_km: Distance in kilometers (float, int, or None)

    Returns:
        Score from 0 to 40
    """
    if distance_km is None:
        return 0
    try:
        d = float(distance_km)
    except (TypeError, ValueError):
        return 0

    if d <= 1:
        return 40
    if d <= 2:
        return 30
    if d <= 3:
        return 20
    if d <= 5:
        return 10
    return 0


def calculate_cuisine_score(cuisine_str, requested_cuisine) -> int:
    """
    Calculate cuisine score based on exact tag matching.

    Args:
        cuisine_str: Semicolon-separated cuisine tags from dataset
        requested_cuisine: Cuisine tag to match (string)

    Returns:
        Score: 30 if exact tag match, 0 otherwise
    """
    if not requested_cuisine or not requested_cuisine.strip():
        return 0

    if not isinstance(cuisine_str, str) or not cuisine_str.strip():
        return 0

    tag = requested_cuisine.strip().lower()
    tags = [t.strip().lower() for t in cuisine_str.split(";") if t.strip()]

    if tag in tags:
        return 30
    return 0


def calculate_opening_hours_score(opening_hours) -> int:
    """
    Calculate opening hours score based on presence in dataset.

    Args:
        opening_hours: Opening hours string from dataset

    Returns:
        Score: 15 if present, 0 if missing
    """
    if pd.isna(opening_hours):
        return 0
    if isinstance(opening_hours, str) and opening_hours.strip() == "":
        return 0
    return 15


def calculate_website_score(website) -> int:
    """
    Calculate website score based on presence in dataset.

    Args:
        website: Website URL from dataset

    Returns:
        Score: 10 if present, 0 if missing
    """
    if pd.isna(website):
        return 0
    if isinstance(website, str) and website.strip() == "":
        return 0
    return 10


def calculate_phone_score(phone) -> int:
    """
    Calculate phone score based on presence in dataset.

    Args:
        phone: Phone number from dataset

    Returns:
        Score: 5 if present, 0 if missing
    """
    if pd.isna(phone):
        return 0
    if isinstance(phone, str) and phone.strip() == "":
        return 0
    return 5


def score_cafe(row, requested_cuisine) -> dict:
    """
    Calculate all score components for a single cafe row.

    Args:
        row: DataFrame row (pd.Series)
        requested_cuisine: Cuisine tag to match (string or None)

    Returns:
        Dict with score components and reasons
    """
    distance_km = row.get("distance_km")
    cuisine_str = row.get("cuisine")
    opening_hours = row.get("opening_hours")
    website = row.get("website")
    phone = row.get("phone")

    score_distance = calculate_distance_score(distance_km)
    score_cuisine = calculate_cuisine_score(cuisine_str, requested_cuisine)
    score_opening_hours = calculate_opening_hours_score(opening_hours)
    score_website = calculate_website_score(website)
    score_phone = calculate_phone_score(phone)

    score_total = (
        score_distance
        + score_cuisine
        + score_opening_hours
        + score_website
        + score_phone
    )
    score_total = max(0, min(score_total, MAX_TOTAL_SCORE))

    reasons = []

    if distance_km is not None:
        try:
            d = float(distance_km)
            reasons.append(f"Distance: {d:.1f} km → {score_distance} points")
        except (TypeError, ValueError):
            reasons.append("Distance could not be determined from dataset → 0 points")
    else:
        reasons.append("Distance could not be determined from dataset → 0 points")

    if score_cuisine > 0:
        reasons.append(f"Cuisine match: {requested_cuisine.strip().lower()} → {score_cuisine} points")
    else:
        reasons.append("Cuisine unavailable in dataset or no match → 0 points")

    if score_opening_hours > 0:
        reasons.append("Opening hours available in dataset → 15 points")
    else:
        reasons.append("Opening hours unavailable in dataset → 0 points")

    if score_website > 0:
        reasons.append("Website available in dataset → 10 points")
    else:
        reasons.append("Website unavailable in dataset → 0 points")

    if score_phone > 0:
        reasons.append("Phone available in dataset → 5 points")
    else:
        reasons.append("Phone unavailable in dataset → 0 points")

    return {
        "score_distance": score_distance,
        "score_cuisine": score_cuisine,
        "score_opening_hours": score_opening_hours,
        "score_website": score_website,
        "score_phone": score_phone,
        "score_total": score_total,
        "reasons": reasons,
    }


def rank_cafes(df: pd.DataFrame, requested_cuisine) -> pd.DataFrame:
    """
    Calculate ranking scores for all cafes in the DataFrame.

    Args:
        df: DataFrame with cafe data
        requested_cuisine: Cuisine tag to match (string or None)

    Returns:
        New DataFrame with score columns added (original not modified)
    """
    if df.empty:
        result = df.copy()
        score_cols = [
            "score_total",
            "score_distance",
            "score_cuisine",
            "score_opening_hours",
            "score_website",
            "score_phone",
        ]
        for col in score_cols:
            result[col] = pd.Series(dtype="int")
        result["score_reasons"] = pd.Series(dtype="object")
        return result

    result = df.copy()
    scores = []

    for _, row in result.iterrows():
        score_info = score_cafe(row, requested_cuisine)
        scores.append(score_info)

    result["score_distance"] = [s["score_distance"] for s in scores]
    result["score_cuisine"] = [s["score_cuisine"] for s in scores]
    result["score_opening_hours"] = [s["score_opening_hours"] for s in scores]
    result["score_website"] = [s["score_website"] for s in scores]
    result["score_phone"] = [s["score_phone"] for s in scores]
    result["score_total"] = [s["score_total"] for s in scores]
    result["score_reasons"] = [s["reasons"] for s in scores]

    return result