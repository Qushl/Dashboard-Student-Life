"""Расчёт статистических показателей и KPI."""

import pandas as pd

from config import QUESTIONS, BLOCK_NAMES


NO_ANSWER = "(нет ответа)"


def _clean(series: pd.Series) -> pd.Series:
    """Убирает пропуски и '(нет ответа)' из серии."""
    return series[series.notna() & (series.astype(str) != NO_ANSWER)]


def compute_all_stats(df: pd.DataFrame) -> dict:
    """Вычисляет показатели по всем блокам."""
    return {block: _compute_block(df, block) for block in BLOCK_NAMES}


def compute_kpi(df: pd.DataFrame) -> dict:
    """Ключевые показатели для st.metric."""
    total = len(df)
    avg_age = df["Ваш возраст"].mean() if "Ваш возраст" in df else 0

    pct_local = 0
    if "Является ли город, где вы учитесь, вашим родным?" in df:
        local_mask = df["Является ли город, где вы учитесь, вашим родным?"].str.contains("Да", na=False)
        pct_local = local_mask.sum() / total * 100 if total else 0

    pct_working = 0
    if "Есть ли у вас подработка?" in df:
        work_mask = ~df["Есть ли у вас подработка?"].str.contains("Нет", na=False)
        pct_working = work_mask.sum() / total * 100 if total else 0

    logist_col = "Как вы оцениваете удобство логистики (дорога + транспорт)?"
    avg_logistics = 0
    if logist_col in df:
        s = pd.to_numeric(df[logist_col], errors="coerce").dropna()
        avg_logistics = s.mean() if len(s) else 0

    return {
        "Всего респондентов": total,
        "Средний возраст": round(avg_age, 1),
        "Местные студенты (%)": round(pct_local, 1),
        "С подработкой (%)": round(pct_working, 1),
        "Удобство логистики (1-5)": round(avg_logistics, 2),
    }


def _compute_block(df: pd.DataFrame, block: int) -> dict:
    """Показатели для одного блока."""
    result = {}
    for col, cfg in QUESTIONS.items():
        if cfg["block"] != block or col not in df.columns:
            continue
        result[col] = _compute_column(df, col, cfg)
    return result


def _compute_column(df: pd.DataFrame, col: str, cfg: dict) -> dict:
    """Показатели для одного столбца."""
    col_type = cfg["type"]

    if col_type == "categorical":
        vc = _clean(df[col]).value_counts()
        total = vc.sum()
        return {
            "counts": vc.to_dict(),
            "percentages": (vc / total * 100).round(1).to_dict() if total else {},
        }

    if col_type == "numeric":
        s = df[col].dropna()
        return {
            "mean": round(s.mean(), 1) if len(s) else 0,
            "median": round(s.median(), 1) if len(s) else 0,
            "min": round(s.min(), 1) if len(s) else 0,
            "max": round(s.max(), 1) if len(s) else 0,
            "std": round(s.std(), 1) if len(s) else 0,
        }

    if col_type == "scale_1_5":
        s = pd.to_numeric(df[col], errors="coerce").dropna()
        vc = s.value_counts().sort_index()
        total = vc.sum()
        return {
            "counts": vc.to_dict(),
            "percentages": (vc / total * 100).round(1).to_dict() if total else {},
            "mean": round(s.mean(), 2) if total else 0,
        }

    if col_type == "multiple_choice":
        expanded = _expand_multiple(_clean(df[col]))
        vc = expanded.sum().sort_values(ascending=False)
        total = len(df)
        return {
            "counts": vc.to_dict(),
            "percentages": (vc / total * 100).round(1).to_dict() if total else {},
        }

    if col_type == "text":
        return {
            "sample": _clean(df[col]).head(10).tolist(),
        }

    return {}


def _expand_multiple(series: pd.Series) -> pd.DataFrame:
    """Разворачивает множественный выбор в one-hot."""
    exploded = series.str.split(r",\s*", expand=True).stack()
    exploded = exploded.str.strip()
    return pd.get_dummies(exploded).groupby(level=0).max()


def get_full_answers(series: pd.Series) -> list[str]:
    """Список уникальных полных ответов."""
    answers = []
    for val in series.dropna():
        s = str(val).strip()
        if not s or s in (".", "-", "—", "(нет ответа)"):
            continue
        if len(s) < 3:
            continue
        answers.append(s)
    return answers


# ── Категоризация текстовых ответов ──

def _match_category(text_lower: str, categories: dict) -> str | None:
    """Находит первую подходящую категорию для текста."""
    for category, keywords in categories.items():
        for kw in keywords:
            if kw in text_lower:
                return category
    return None


def categorize_text_responses(series: pd.Series, categories: dict) -> dict:
    """
    Категоризирует текстовые ответы по словарю ключевых слов.
    Возвращает: {категория: [список_ответов]}.
    """
    from collections import defaultdict

    _JUNK = {"(нет ответа)", ".", "-", "—", "нет", "норм", "хз", "лол", "ок", "кек"}

    results: dict[str, list[str]] = defaultdict(list)

    for text in series.dropna():
        if not isinstance(text, str) or len(text.strip()) < 3:
            continue

        text_lower = text.lower().strip()
        if text_lower in _JUNK:
            continue

        cat = _match_category(text_lower, categories)
        results[cat or "Другое"].append(text.strip())

    # Сортируем по убыванию количества, «Другое» в конце
    sorted_items = sorted(
        results.items(),
        key=lambda x: (x[0] == "Другое", -len(x[1])),
    )
    return dict(sorted_items)


def get_category_summary(series: pd.Series, categories: dict) -> pd.DataFrame:
    """
    Возвращает DataFrame: Категория | Количество | Доля (%) | Примеры.
    """
    categorized = categorize_text_responses(series, categories)
    total = sum(len(v) for v in categorized.values())

    rows = []
    for cat, answers in categorized.items():
        pct = round(len(answers) / total * 100, 1) if total else 0
        examples = answers[:3]  # первые 3 примера
        rows.append({
            "Категория": cat,
            "Ответов": len(answers),
            "Доля (%)": pct,
            "Примеры": ", ".join(examples),
        })

    return pd.DataFrame(rows)
