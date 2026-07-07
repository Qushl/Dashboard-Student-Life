"""Визуализация данных с помощью plotly."""

import plotly.express as px
import plotly.graph_objects as go
import pandas as pd

from config import QUESTIONS

COLORS = px.colors.qualitative.Set2
SCALE_COLOR = ["#ef4444", "#f97316", "#eab308", "#22c55e", "#3b82f6"]


def _cycle_colors(n: int) -> list[str]:
    """Возвращает n цветов, зацикливая основную палитру."""
    return [COLORS[i % len(COLORS)] for i in range(n)]

NO_ANSWER = "(нет ответа)"


def _clean(series: pd.Series) -> pd.Series:
    """Убирает пропуски и '(нет ответа)' из серии."""
    return series[series.notna() & (series.astype(str) != NO_ANSWER)]


def render_block_charts(df: pd.DataFrame, block: int) -> list[go.Figure]:
    """Список графиков для одного тематического блока."""
    charts = []
    for col, cfg in QUESTIONS.items():
        if cfg["block"] != block or col not in df.columns:
            continue
        fig = render_chart(df, col, cfg)
        if fig is not None:
            charts.append((cfg["question"], fig))
    return charts


def render_chart(df: pd.DataFrame, col: str, cfg: dict) -> go.Figure | None:
    """Строит подходящий график для одной колонки."""
    col_type = cfg["type"]
    title = cfg["question"]

    if col_type == "categorical":
        return _bar_chart(df, col, title)
    if col_type == "numeric":
        return _histogram(df, col, title)
    if col_type == "scale_1_5":
        return _scale_chart(df, col, title)
    if col_type == "multiple_choice":
        return _multi_choice_chart(df, col, title)
    if col_type == "text":
        return _text_wordcloud_chart(df, col, title)
    return None


def _wrap_label(text: str, max_len: int = 20) -> str:
    """Переносит длинный текст на две строки."""
    if len(text) <= max_len:
        return text
    words = text.split()
    lines, current = [], ""
    for w in words:
        if current and len(current) + 1 + len(w) > max_len:
            lines.append(current)
            current = w
        else:
            current = f"{current} {w}".strip() if current else w
    if current:
        lines.append(current)
    return "<br>".join(lines)


def _bar_chart(df: pd.DataFrame, col: str, title: str) -> go.Figure | None:
    """Столбчатая диаграмма."""
    vc = _clean(df[col]).value_counts()
    if vc.empty:
        return None
    labels = [_wrap_label(str(v)) for v in vc.index]
    fig = go.Figure(go.Bar(
        x=labels, y=vc.values, text=vc.values,
        textposition="outside", marker_color=_cycle_colors(len(vc)),
    ))
    fig.update_layout(
        title=title, xaxis_title="", yaxis_title="Количество",
        showlegend=False,
        xaxis=dict(tickangle=0, type="category", categoryorder="array", categoryarray=labels),
    )
    return fig


def _histogram(df: pd.DataFrame, col: str, title: str) -> go.Figure | None:
    """Гистограмма для числовых данных."""
    vc = pd.to_numeric(_clean(df[col]), errors="coerce").dropna().value_counts().sort_index()
    if vc.empty:
        return None
    labels = [str(v) for v in vc.index]
    fig = go.Figure(go.Bar(
        x=labels, y=vc.values, text=vc.values,
        textposition="outside", marker_color="#6366f1",
    ))
    fig.update_layout(
        title=title, xaxis_title="", yaxis_title="Количество",
        showlegend=False,
        xaxis=dict(type="category", categoryorder="array", categoryarray=labels),
    )
    return fig


def _scale_chart(df: pd.DataFrame, col: str, title: str) -> go.Figure | None:
    """Диаграмма для шкалы 1-5."""
    s = pd.to_numeric(_clean(df[col]), errors="coerce").dropna().astype(int)
    vc = s.value_counts().sort_index()
    if vc.empty:
        return None
    x_labels = [str(v) for v in vc.index]
    fig = go.Figure(go.Bar(
        x=x_labels, y=vc.values, text=vc.values,
        textposition="outside", marker_color=SCALE_COLOR[:len(vc)],
    ))
    fig.update_layout(
        title=f"{title} (среднее: {s.mean():.2f})",
        xaxis_title="Оценка", yaxis_title="Количество",
        showlegend=False,
        xaxis=dict(type="category", categoryorder="array", categoryarray=["1", "2", "3", "4", "5"]),
    )
    return fig


def _multi_choice_chart(df: pd.DataFrame, col: str, title: str) -> go.Figure | None:
    """Диаграмма для множественного выбора."""
    expanded = _clean(df[col]).astype(str).str.split(r",\s*", expand=True).stack().dropna().astype(str).str.strip()
    vc = expanded.value_counts()
    if vc.empty:
        return None
    labels = [_wrap_label(str(v)) for v in vc.index]
    fig = go.Figure(go.Bar(
        x=labels, y=vc.values, text=vc.values,
        textposition="outside", marker_color=_cycle_colors(len(vc)),
    ))
    fig.update_layout(
        title=title, xaxis_title="", yaxis_title="Количество",
        showlegend=False,
        xaxis=dict(tickangle=0, type="category", categoryorder="array", categoryarray=labels),
    )
    return fig


def _text_wordcloud_chart(df: pd.DataFrame, col: str, title: str) -> go.Figure:
    """Топ слов для текстовых колонок — заглушка (категоризация в app.py)."""
    return None


def render_pie(df: pd.DataFrame, col: str, title: str) -> go.Figure | None:
    """Круговая диаграмма."""
    cfg = QUESTIONS.get(col, {})
    col_type = cfg.get("type", "")

    if col_type == "categorical":
        vc = _clean(df[col]).value_counts()
    elif col_type == "scale_1_5":
        s = pd.to_numeric(_clean(df[col]), errors="coerce").dropna().astype(int)
        vc = s.value_counts().sort_index()
        vc.index = [str(v) for v in vc.index]
    elif col_type == "multiple_choice":
        expanded = _clean(df[col]).astype(str).str.split(r",\s*", expand=True).stack().dropna().astype(str).str.strip()
        vc = expanded.value_counts()
    elif col_type == "numeric":
        vc = pd.to_numeric(_clean(df[col]), errors="coerce").dropna().value_counts().sort_index()
        vc.index = [str(v) for v in vc.index]
    else:
        return None

    if vc.empty:
        return None

    fig = go.Figure(go.Pie(
        labels=vc.index.astype(str), values=vc.values, hole=0.3,
        marker=dict(colors=_cycle_colors(len(vc))),
        textinfo="label+percent", textposition="outside",
    ))
    fig.update_layout(title=title, showlegend=False)
    return fig


def render_table(df: pd.DataFrame, col: str, title: str) -> pd.DataFrame | None:
    """Таблица со статистикой по колонке."""
    cfg = QUESTIONS.get(col, {})
    col_type = cfg.get("type", "")

    if col_type == "categorical":
        vc = _clean(df[col]).value_counts()
        if vc.empty:
            return None
        total = vc.sum()
        return pd.DataFrame({
            "Ответ": vc.index, "Количество": vc.values,
            "Доля (%)": (vc.values / total * 100).round(1),
        })
    if col_type == "scale_1_5":
        s = pd.to_numeric(_clean(df[col]), errors="coerce").dropna().astype(int)
        vc = s.value_counts().sort_index()
        if vc.empty:
            return None
        total = vc.sum()
        return pd.DataFrame({
            "Оценка": vc.index.astype(str), "Количество": vc.values,
            "Доля (%)": (vc.values / total * 100).round(1),
        })
    if col_type == "multiple_choice":
        expanded = _clean(df[col]).astype(str).str.split(r",\s*", expand=True).stack().dropna().astype(str).str.strip()
        vc = expanded.value_counts()
        total = len(df)
        return pd.DataFrame({
            "Вариант": vc.index, "Количество": vc.values,
            "Доля (%)": (vc.values / total * 100).round(1),
        })
    if col_type == "numeric":
        s = _clean(df[col]).dropna()
        return pd.DataFrame({
            "Показатель": ["Среднее", "Медиана", "Мин", "Макс", "Стд. отклонение"],
            "Значение": [
                round(s.mean(), 1) if len(s) else 0,
                round(s.median(), 1) if len(s) else 0,
                round(s.min(), 1) if len(s) else 0,
                round(s.max(), 1) if len(s) else 0,
                round(s.std(), 1) if len(s) else 0,
            ],
        })
    return None
