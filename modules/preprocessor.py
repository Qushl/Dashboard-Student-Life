"""Предобработка данных: дубли, пропуски, нормализация."""

import re

import pandas as pd

from config import QUESTIONS
from modules.logger import log_info

TIME_TEXT_COL = "Сколько минут вы тратите на дорогу от дома до учебного корпуса (в одну сторону)?"


def preprocess(df: pd.DataFrame) -> pd.DataFrame:
    """Полный цикл предобработки."""
    df = df.copy()
    before = len(df)
    df = remove_duplicates(df)
    removed = before - len(df)
    if removed:
        log_info("preprocessor", f"Удалено дублей: {removed}")
    df = parse_time_column(df)
    df = normalize_text(df)
    df = handle_missing(df)
    df = validate_numeric(df)
    df = round_scales(df)
    log_info("preprocessor", f"Предобработка завершена: {len(df)} записей")
    return df


def remove_duplicates(df: pd.DataFrame) -> pd.DataFrame:
    """Удаляет полностью дублирующиеся строки."""
    return df.drop_duplicates().reset_index(drop=True)


def parse_time_column(df: pd.DataFrame) -> pd.DataFrame:
    """Парсит текстовые значения времени в минуты."""
    if TIME_TEXT_COL not in df.columns:
        return df

    def _parse_time(val):
        if pd.isna(val):
            return None
        s = str(val).strip().lower()
        if s.isdigit():
            return int(s)
        if "полтора" in s:
            return 90
        if "час" in s and "часа" not in s:
            return 60
        m = re.search(r"(\d+)", s)
        if m:
            n = int(m.group(1))
            if "час" in s:
                return n * 60
            return n
        return None

    df[TIME_TEXT_COL] = df[TIME_TEXT_COL].apply(_parse_time)
    return df


def handle_missing(df: pd.DataFrame) -> pd.DataFrame:
    """Заполняет пропуски: медианой для чисел, (нет ответа) для остальных."""
    for col in df.columns:
        cfg = QUESTIONS.get(col)
        if cfg is None:
            continue
        if cfg["type"] in ("numeric", "scale_1_5"):
            df[col] = df[col].fillna(df[col].median())
        else:
            df[col] = df[col].fillna("(нет ответа)")
    return df


def normalize_text(df: pd.DataFrame) -> pd.DataFrame:
    """Нормализует строковые значения."""
    for col in df.columns:
        cfg = QUESTIONS.get(col)
        if cfg is None:
            continue
        if cfg["type"] in ("categorical", "multiple_choice"):
            df[col] = df[col].astype(str).str.strip()
        elif cfg["type"] == "text":
            df[col] = df[col].astype(str).str.strip().str.lower()
    return df


def validate_numeric(df: pd.DataFrame) -> pd.DataFrame:
    """Приводит числовые колонки к целым."""
    for col in df.columns:
        cfg = QUESTIONS.get(col)
        if cfg and cfg["type"] == "numeric":
            df[col] = pd.to_numeric(df[col], errors="coerce").round().astype("Int64")
    return df


def round_scales(df: pd.DataFrame) -> pd.DataFrame:
    """Округляет значения шкалы 1-5 до целых."""
    for col in df.columns:
        cfg = QUESTIONS.get(col)
        if cfg and cfg["type"] == "scale_1_5":
            df[col] = pd.to_numeric(df[col], errors="coerce").round().astype("Int64")
    return df
