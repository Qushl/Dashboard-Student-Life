"""Генерация аналитических выводов по блокам."""

import pandas as pd

from config import QUESTIONS, BLOCK_NAMES

NO_ANSWER = "(нет ответа)"


def generate_conclusions(df: pd.DataFrame) -> dict[int, list[str]]:
    """Текстовые выводы по каждому тематическому блоку."""
    conclusions = {}
    for block_num in BLOCK_NAMES:
        items = _conclusions_for_block(df, block_num)
        if items:
            conclusions[block_num] = items
    return conclusions


def _conclusions_for_block(df: pd.DataFrame, block: int) -> list[str]:
    """Выводы для одного блока."""
    result = []

    for col, cfg in QUESTIONS.items():
        if cfg["block"] != block or col not in df.columns:
            continue

        col_type = cfg["type"]
        q = cfg["question"]

        if col_type == "categorical":
            vc = df[col][df[col].astype(str) != NO_ANSWER].value_counts()
            total = vc.sum()
            if len(vc) == 0 or total == 0:
                continue
            top = vc.index[0]
            top_pct = round(vc.values[0] / total * 100)
            result.append(f"**{q}**: наиболее частый ответ — «{top}» ({top_pct}% респондентов).")

        elif col_type == "numeric":
            s = pd.to_numeric(df[col], errors="coerce").dropna()
            s = s[s.astype(str) != NO_ANSWER]
            if len(s) == 0:
                continue
            result.append(f"**{q}**: среднее = {round(s.mean(), 1)}, медиана = {round(s.median(), 1)}.")

        elif col_type == "scale_1_5":
            raw = df[col][df[col].astype(str) != NO_ANSWER]
            s = pd.to_numeric(raw, errors="coerce").dropna()
            if len(s) == 0:
                continue
            mean = round(s.mean(), 2)
            if mean >= 4:
                level = "высокий уровень удовлетворённости"
            elif mean >= 3:
                level = "средний уровень удовлетворённости"
            else:
                level = "низкий уровень удовлетворённости"
            result.append(f"**{q}**: средняя оценка {mean} из 5 — {level}.")

        elif col_type == "multiple_choice":
            raw = df[col][df[col].astype(str) != NO_ANSWER]
            expanded = raw.str.split(r",\s*", expand=True).stack().str.strip()
            vc = expanded.value_counts()
            total = len(df)
            if len(vc) == 0 or total == 0:
                continue
            top = vc.index[0]
            top_pct = round(vc.values[0] / total * 100)
            result.append(f"**{q}**: самый популярный вариант — «{top}» ({top_pct}% респондентов).")

    return result
