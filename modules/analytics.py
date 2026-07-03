"""Расчёт статистических показателей и KPI."""

import pandas as pd

from config import QUESTIONS, BLOCK_NAMES

# Стоп-слова для анализа текста
_STOP_RU = {
    "и", "в", "во", "не", "что", "он", "на", "я", "с", "со", "как", "а", "то",
    "все", "она", "так", "его", "но", "да", "ты", "к", "у", "же", "вы", "за",
    "бы", "по", "только", "ее", "мне", "было", "вот", "от", "меня", "еще",
    "нет", "о", "из", "ему", "теперь", "когда", "даже", "ну", "вдруг", "ли",
    "если", "уже", "или", "ни", "был", "него", "до", "вас", "нибудь",
    "опять", "уж", "вам", "ведь", "там", "потом", "себя", "ничего", "ей",
    "может", "они", "тут", "где", "есть", "надо", "ней", "для", "мы", "тебя",
    "их", "чем", "была", "сам", "чтоб", "без", "будто", "чего", "раз", "тоже",
    "себе", "под", "будет", "ж", "тогда", "кто", "этот", "того", "потому",
    "этого", "какой", "совсем", "ним", "здесь", "этом", "один", "почти", "мой",
    "тем", "чтобы", "нее", "сейчас", "были", "куда", "зачем", "всех", "можно",
    "при", "наконец", "два", "об", "другой", "хоть", "после", "над", "больше",
    "тот", "через", "эти", "нас", "про", "всего", "них", "какая", "много",
    "разве", "три", "эту", "моя", "впрочем", "хорошо", "свою", "этой",
    "перед", "иногда", "лучше", "чуть", "том", "нельзя", "такой", "им",
    "более", "всегда", "хотя", "конечно", "всю", "между",
    "этого", "этих", "этим", "этими", "себе", "свои", "своих", "своей",
    "своего", "своё", "своим", "мной", "тобой", "ними", "нему", "них", "её",
    "который", "которая", "которое", "которые", "которого", "которой",
    "такой", "такая", "такие", "такого", "весь", "вся", "всё", "все",
    "каждый", "каждая", "каждое",
    "то", "это", "вот", "ещё", "еще", "уже", "просто", "также", "тоже",
    "самый", "самая", "самое", "самые", "очень", "довольно", "примерно",
    "почему", "поэтому", "нужно", "нужна", "нужны", "нужен",
    "сидеть", "сиджу", "сидел", "сидела",
    "ходить", "хожу", "пошел", "пошла",
    "идти", "иду", "шел", "шла",
    "стоять", "стою", "лежать", "лежу",
    "ждать", "жду",
    "делать", "сделать", "заниматься", "заняться",
    "проводить", "провести", "провел", "провела",
    "тратить", "потратить", "использовать",
    "получать", "получить", "хотеть", "захотеть",
    "мочь", "смочь", "быть", "стать",
    "сказать", "взять", "дать", "понять", "видеть", "знать", "думать",
    "ответ", "норма", "нормальный", "нормально",
    "целое", "закрыть", "вернуть", "повлиять", "сфера",
    "семестр", "год", "месяц", "неделя", "день", "время", "времена", "период",
    "весь", "вся", "все", "всё", "всего",
    "сейчас", "теперь", "тогда", "потом",
    "часто", "редко", "иногда", "постоянно",
    "маленький", "большой", "либо", "стоить", "уточнить", "некоторый",
}

# Словарь сленга
_SLANG_MAP = {
    "стипух": "стипендия", "стипуха": "стипендия", "стипухи": "стипендия",
    "препод": "преподаватель", "преподы": "преподаватель", "преподов": "преподаватель",
    "хата": "домой", "хату": "домой",
    "нвк": "общежитие нвк",
    "тусоваться": "тусоваться с друзьями", "тусуюсь": "тусоваться с друзьями",
    "тусил": "тусоваться с друзьями",
    "сиджу": "сидеть", "сижу": "сидеть",
    "хожу": "ходить",
    "перечитываю": "перечитывать", "рисую": "рисовать",
}


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
        work_mask = df["Есть ли у вас подработка?"].str.contains("Да|Полноценно|работаю", na=False, regex=True)
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
        vc = df[col].value_counts()
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
        expanded = _expand_multiple(df[col])
        vc = expanded.sum().sort_values(ascending=False)
        total = len(df)
        return {
            "counts": vc.to_dict(),
            "percentages": (vc / total * 100).round(1).to_dict() if total else {},
        }

    if col_type == "text":
        top_words = _top_words(df[col])
        return {
            "sample": df[col].dropna().head(10).tolist(),
            "top_words": top_words,
        }

    return {}


def _expand_multiple(series: pd.Series) -> pd.DataFrame:
    """Разворачивает множественный выбор в one-hot."""
    exploded = series.str.split(r",\s*", expand=True).stack()
    exploded = exploded.str.strip()
    return pd.get_dummies(exploded).groupby(level=0).max()


def _top_words(series: pd.Series, n: int = 15, min_freq: int = 2) -> dict:
    """Топ-N слов с лемматизацией и сленгом."""
    from collections import Counter
    import re

    try:
        import pymorphy3
        morph = pymorphy3.MorphAnalyzer()
        use_lemma = True
    except ImportError:
        use_lemma = False

    words = []
    for val in series.dropna():
        tokens = re.findall(r"[а-яёa-z]+", str(val).lower())
        for t in tokens:
            if len(t) < 3:
                continue
            if t in _SLANG_MAP:
                mapped = _SLANG_MAP[t]
                if mapped not in _STOP_RU:
                    words.append(mapped)
                continue
            if use_lemma:
                lemma = morph.parse(t)[0].normal_form
                if lemma in _STOP_RU or len(lemma) < 3:
                    continue
                words.append(lemma)
            else:
                if t not in _STOP_RU:
                    words.append(t)

    counter = Counter(words)
    return {w: c for w, c in counter.most_common(n) if c >= min_freq}


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
