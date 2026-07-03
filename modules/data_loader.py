"""Загрузка данных из CSV / XLSX с валидацией."""

import pandas as pd
import streamlit as st

from config import REQUIRED_COLUMNS, SKIP_COLUMNS
from modules.logger import log_info, log_error, log_warning


def load_data(uploaded_file) -> pd.DataFrame | None:
    """Загружает файл и возвращает DataFrame."""
    try:
        name = uploaded_file.name.lower()
        log_info("data_loader", f"Загрузка файла: {uploaded_file.name}")

        if name.endswith(".csv"):
            df = pd.read_csv(uploaded_file)
        elif name.endswith(".xlsx") or name.endswith(".xls"):
            df = pd.read_excel(uploaded_file)
        else:
            st.error("Поддерживаются только форматы CSV и XLSX.")
            log_warning("data_loader", f"Неподдерживаемый формат: {name}")
            return None

        log_info("data_loader", f"Прочитано строк: {len(df)}, колонок: {len(df.columns)}")
    except Exception as e:
        st.error(f"Ошибка чтения файла: {e}")
        log_error("data_loader", e)
        return None

    df = _normalize_columns(df)
    df = _drop_unneeded(df)
    missing = _validate_columns(df)
    if missing:
        st.warning(
            "В файле отсутствуют ожидаемые колонки:\n"
            + "\n".join(f"  — {c}" for c in missing)
        )
        log_warning("data_loader", f"Отсутствуют колонки: {missing}")

    log_info("data_loader", f"Итого записей после обработки: {len(df)}")
    return df


def _normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Убирает лишние пробелы по краям названий колонок."""
    df.columns = df.columns.str.strip()
    return df


def _drop_unneeded(df: pd.DataFrame) -> pd.DataFrame:
    """Удаляет служебные и полностью пустые колонки."""
    cols_to_drop = [c for c in df.columns if c in SKIP_COLUMNS]
    df = df.drop(columns=cols_to_drop, errors="ignore")
    df = df.dropna(axis=1, how="all")
    return df


def _validate_columns(df: pd.DataFrame) -> list[str]:
    """Проверяет наличие обязательных колонок."""
    present = set(df.columns)
    return [col for col in REQUIRED_COLUMNS if col not in present]
