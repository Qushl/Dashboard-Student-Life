"""Экспорт данных в XLSX с несколькими листами."""

import io

import pandas as pd

from config import QUESTIONS, BLOCK_NAMES


def export_to_excel(df_raw: pd.DataFrame, df_clean: pd.DataFrame) -> bytes:
    """Формирует XLSX-файл и возвращает bytes."""
    buf = io.BytesIO()

    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        df_raw.to_excel(writer, sheet_name="Исходные данные", index=False)
        df_clean.to_excel(writer, sheet_name="Очищенные данные", index=False)

        stats_df = _build_stats_table(df_clean)
        stats_df.to_excel(writer, sheet_name="Статистика", index=False)

        for block_num, block_name in BLOCK_NAMES.items():
            block_cols = [
                col for col, cfg in QUESTIONS.items()
                if cfg["block"] == block_num and col in df_clean.columns
            ]
            if block_cols:
                df_clean[block_cols].to_excel(writer, sheet_name=f"Блок {block_num}", index=False)

    buf.seek(0)
    return buf.read()


def _build_stats_table(df: pd.DataFrame) -> pd.DataFrame:
    """Сводная статистика по всем колонкам."""
    rows = []
    for col, cfg in QUESTIONS.items():
        if col not in df.columns:
            continue
        row = {"Вопрос": cfg["question"], "Тип": cfg["type"], "Блок": cfg["block"], "Всего ответов": df[col].count()}

        if cfg["type"] == "numeric":
            s = df[col].dropna()
            row["Среднее"] = round(s.mean(), 1) if len(s) else ""
            row["Медиана"] = round(s.median(), 1) if len(s) else ""
            row["Мин"] = round(s.min(), 1) if len(s) else ""
            row["Макс"] = round(s.max(), 1) if len(s) else ""
        elif cfg["type"] == "scale_1_5":
            row["Среднее"] = round(df[col].mean(), 2) if df[col].count() else ""
        else:
            top = df[col].value_counts().head(1)
            row["Топ-1 ответ"] = top.index[0] if len(top) else ""
            row["Топ-1 %"] = f"{top.values[0] / len(df) * 100:.1f}%" if len(top) and len(df) else ""

        rows.append(row)

    return pd.DataFrame(rows)
