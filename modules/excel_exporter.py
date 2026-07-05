"""Экспорт данных в XLSX с несколькими листами."""

import io

import pandas as pd

from config import QUESTIONS, BLOCK_NAMES

NO_ANSWER = "(нет ответа)"


def _clean(series: pd.Series) -> pd.Series:
    """Убирает пропуски и '(нет ответа)' из серии."""
    return series[series.notna() & (series.astype(str) != NO_ANSWER)]


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

        grouping_df = _build_grouping_tables(df_clean)
        if not grouping_df.empty:
            grouping_df.to_excel(writer, sheet_name="Группировка", index=False)

    buf.seek(0)
    return buf.read()


def _build_stats_table(df: pd.DataFrame) -> pd.DataFrame:
    """Сводная статистика по всем колонкам."""
    rows = []
    for col, cfg in QUESTIONS.items():
        if col not in df.columns:
            continue
        row = {"Вопрос": cfg["question"], "Тип": cfg["type"], "Блок": cfg["block"], "Всего ответов": _clean(df[col]).count()}

        if cfg["type"] == "numeric":
            s = _clean(df[col]).dropna()
            row["Среднее"] = round(s.mean(), 1) if len(s) else ""
            row["Медиана"] = round(s.median(), 1) if len(s) else ""
            row["Мин"] = round(s.min(), 1) if len(s) else ""
            row["Макс"] = round(s.max(), 1) if len(s) else ""
        elif cfg["type"] == "scale_1_5":
            s = pd.to_numeric(_clean(df[col]), errors="coerce").dropna()
            row["Среднее"] = round(s.mean(), 2) if len(s) else ""
        else:
            top = _clean(df[col]).value_counts().head(1)
            row["Топ-1 ответ"] = top.index[0] if len(top) else ""
            row["Топ-1 %"] = f"{top.values[0] / _clean(df[col]).count() * 100:.1f}%" if len(top) else ""

        rows.append(row)

    return pd.DataFrame(rows)


def _build_grouping_tables(df: pd.DataFrame) -> pd.DataFrame:
    """Группировка по ключевым категориальным колонкам с подсчётом."""
    group_cols = ["Ваш пол", "На каком курсе вы учитесь?", "Где вы проживаете?"]
    rows = []
    for col in group_cols:
        if col not in df.columns:
            continue
        vc = _clean(df[col]).value_counts()
        total = vc.sum()
        for val, count in vc.items():
            rows.append({
                "Параметр": QUESTIONS.get(col, {}).get("question", col),
                "Значение": val,
                "Количество": count,
                "Доля (%)": round(count / total * 100, 1) if total else 0,
            })
    return pd.DataFrame(rows)
