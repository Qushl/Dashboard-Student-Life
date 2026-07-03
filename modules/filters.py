"""Фильтрация данных по параметрам анкеты."""

import pandas as pd
import streamlit as st

from config import QUESTIONS


def render_sidebar(df: pd.DataFrame) -> dict:
    """Отрисовывает сайдбар с фильтрами."""
    st.sidebar.header("Фильтры данных")
    filters = {}

    if "Ваш пол" in df.columns:
        options = sorted(df["Ваш пол"].dropna().unique())
        filters["Ваш пол"] = st.sidebar.multiselect("Пол", options)

    if "Ваш возраст" in df.columns:
        vals = df["Ваш возраст"].dropna()
        age_min = int(vals.min()) if len(vals) else 16
        age_max = int(vals.max()) if len(vals) else 30
        filters["Ваш возраст"] = st.sidebar.slider("Возраст", age_min, age_max, (age_min, age_max))

    if "На каком курсе вы учитесь?" in df.columns:
        options = sorted(df["На каком курсе вы учитесь?"].dropna().unique())
        filters["На каком курсе вы учитесь?"] = st.sidebar.multiselect("Курс", options)

    if "Где вы проживаете?" in df.columns:
        options = sorted(df["Где вы проживаете?"].dropna().unique())
        filters["Где вы проживаете?"] = st.sidebar.multiselect("Место проживания", options)

    if "Ваш родной город" in df.columns:
        city_input = st.sidebar.text_input("Родной город (введите)")
        if city_input:
            filters["Ваш родной город"] = city_input.strip().lower()

    if "Есть ли у вас подработка?" in df.columns:
        options = sorted(df["Есть ли у вас подработка?"].dropna().unique())
        filters["Есть ли у вас подработка?"] = st.sidebar.multiselect("Подработка", options)

    fin_col = "В целом, как вы оцениваете свою финансовую ситуацию?"
    if fin_col in df.columns:
        vals = df[fin_col].dropna()
        fin_min = int(vals.min()) if len(vals) else 1
        fin_max = int(vals.max()) if len(vals) else 5
        filters[fin_col] = st.sidebar.slider("Финансовое положение", fin_min, fin_max, (fin_min, fin_max))

    return filters


def apply_filters(df: pd.DataFrame, filters: dict) -> pd.DataFrame:
    """Применяет фильтры к DataFrame."""
    result = df.copy()

    for col, value in filters.items():
        if col not in result.columns:
            continue

        cfg = QUESTIONS.get(col, {})
        col_type = cfg.get("type", "categorical")

        if isinstance(value, list) and len(value) > 0:
            if col_type == "multiple_choice":
                mask = result[col].apply(
                    lambda x: any(v in str(x) for v in value) if pd.notna(x) else False
                )
            else:
                mask = result[col].isin(value)
            result = result[mask]

        elif isinstance(value, tuple) and col_type in ("numeric", "scale_1_5"):
            lo, hi = value
            result = result[(result[col] >= lo) & (result[col] <= hi)]

        elif isinstance(value, str) and value:
            mask = result[col].astype(str).str.lower().str.contains(value, na=False)
            result = result[mask]

    return result
