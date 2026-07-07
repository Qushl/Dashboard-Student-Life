"""Генерация PDF-отчёта через fpdf2 + matplotlib."""

import io
import tempfile
from datetime import datetime
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
from fpdf import FPDF

from config import QUESTIONS, BLOCK_NAMES
from modules.analytics import compute_kpi, compute_all_stats
from modules.conclusions import generate_conclusions

FONT_DIR = Path(__file__).resolve().parent.parent / "static" / "fonts"
COLORS = ["#6366f1", "#22c55e", "#f97316", "#ef4444", "#eab308", "#8b5cf6", "#06b6d4", "#ec4899"]
SCALE_COLORS = ["#ef4444", "#f97316", "#eab308", "#22c55e", "#6366f1"]

NO_ANSWER = "(нет ответа)"


def _clean(series: pd.Series) -> pd.Series:
    """Убирает пропуски и '(нет ответа)' из серии."""
    return series[series.notna() & (series.astype(str) != NO_ANSWER)]


def _fig_to_png_bytes(fig) -> bytes:
    """Конвертирует matplotlib figure в PNG."""
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=100, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    buf.seek(0)
    return buf.read()


def _make_pie(series: pd.Series, title: str) -> bytes:
    vc = _clean(series).value_counts()
    fig, ax = plt.subplots(figsize=(5, 3.5))
    ax.pie(vc.values, labels=vc.index, autopct="%1.0f%%", colors=COLORS[:len(vc)], startangle=90, textprops={"fontsize": 8})
    ax.set_title(title, fontsize=10, fontweight="bold")
    return _fig_to_png_bytes(fig)


def _make_bar(series: pd.Series, title: str) -> bytes:
    vc = _clean(series).value_counts()
    fig, ax = plt.subplots(figsize=(5, 3))
    ax.barh(vc.index[::-1], vc.values[::-1], color=COLORS[:len(vc)])
    ax.set_xlabel("Количество", fontsize=8)
    ax.set_title(title, fontsize=10, fontweight="bold")
    ax.tick_params(axis="y", labelsize=7)
    for i, v in enumerate(vc.values[::-1]):
        ax.text(v + 0.1, i, str(v), va="center", fontsize=7)
    fig.tight_layout()
    return _fig_to_png_bytes(fig)


def _make_histogram(series: pd.Series, title: str) -> bytes:
    s = _clean(series).dropna()
    vals = [int(v) for v in s if pd.notna(v)]
    vc = pd.Series(vals).value_counts().sort_index()
    fig, ax = plt.subplots(figsize=(5, 3))
    ax.bar(vc.index.astype(str), vc.values, color="#6366f1")
    ax.set_xlabel("Значение", fontsize=8)
    ax.set_ylabel("Количество", fontsize=8)
    ax.set_title(title, fontsize=10, fontweight="bold")
    for i, v in enumerate(vc.values):
        ax.text(i, v + 0.1, str(v), ha="center", fontsize=7)
    fig.tight_layout()
    return _fig_to_png_bytes(fig)


def _make_scale(series: pd.Series, title: str) -> bytes:
    s = pd.to_numeric(_clean(series), errors="coerce").dropna().astype(int)
    vc = s.value_counts().sort_index()
    fig, ax = plt.subplots(figsize=(5, 3))
    ax.bar([str(v) for v in vc.index], vc.values, color=SCALE_COLORS[:len(vc)])
    ax.set_xlabel("Оценка", fontsize=8)
    ax.set_ylabel("Количество", fontsize=8)
    ax.set_title(f"{title} (среднее: {s.mean():.2f})", fontsize=10, fontweight="bold")
    for i, v in enumerate(vc.values):
        ax.text(i, v + 0.1, str(v), ha="center", fontsize=7)
    fig.tight_layout()
    return _fig_to_png_bytes(fig)


def _make_multi_choice(series: pd.Series, title: str) -> bytes:
    expanded = _clean(series).astype(str).str.split(r",\s*", expand=True).stack().dropna().astype(str).str.strip()
    vc = expanded.value_counts().head(10)
    fig, ax = plt.subplots(figsize=(5, 3))
    ax.barh(vc.index[::-1], vc.values[::-1], color="#22c55e")
    ax.set_xlabel("Количество упоминаний", fontsize=8)
    ax.set_title(title, fontsize=10, fontweight="bold")
    ax.tick_params(axis="y", labelsize=7)
    for i, v in enumerate(vc.values[::-1]):
        ax.text(v + 0.1, i, str(v), va="center", fontsize=7)
    fig.tight_layout()
    return _fig_to_png_bytes(fig)

def _render_chart_for_pdf(df: pd.DataFrame, col: str, cfg: dict) -> bytes | None:
    """Выбирает и рендерит подходящий тип графика."""
    col_type = cfg.get("type", "")
    title = cfg.get("question", col)

    if col_type == "categorical":
        vc = _clean(df[col]).value_counts()
        return _make_pie(df[col], title) if len(vc) <= 5 else _make_bar(df[col], title)
    if col_type == "numeric":
        return _make_histogram(df[col], title)
    if col_type == "scale_1_5":
        return _make_scale(df[col], title)
    if col_type == "multiple_choice":
        return _make_multi_choice(df[col], title)
    if col_type == "text":
        return None
    return None


class StudentReportPDF(FPDF):
    def __init__(self):
        super().__init__()
        self._setup_fonts()
        self.set_auto_page_break(auto=True, margin=20)

    def _setup_fonts(self):
        font_path = self._find_font()
        if font_path:
            self.add_font("DejaVu", "", str(font_path), uni=True)
            self.add_font("DejaVu", "B", str(font_path), uni=True)
            self._font_family = "DejaVu"
        else:
            self._font_family = "Helvetica"

    def _find_font(self) -> Path | None:
        for p in [FONT_DIR / "DejaVuSans.ttf", Path("C:/Windows/Fonts/arial.ttf")]:
            if p.exists():
                return p
        return None

    def header(self):
        self.set_font(self._font_family, "B", 12)
        self.cell(0, 8, "Отчёт: Анализ студенческой жизни", align="C", new_x="LMARGIN", new_y="NEXT")
        self.ln(4)

    def footer(self):
        self.set_y(-15)
        self.set_font(self._font_family, "", 8)
        self.cell(0, 10, f"Стр. {self.page_no()}/{{nb}}", align="C")

    def add_title_page(self, total: int):
        self.add_page()
        self.ln(30)
        self.set_font(self._font_family, "B", 22)
        self.cell(0, 15, "Анализ результатов анкетирования", align="C", new_x="LMARGIN", new_y="NEXT")
        self.cell(0, 15, "Студенческая жизнь", align="C", new_x="LMARGIN", new_y="NEXT")
        self.ln(10)
        self.set_font(self._font_family, "", 12)
        today = datetime.now().strftime("%d.%m.%Y")
        self.cell(0, 8, f"Дата формирования: {today}", align="C", new_x="LMARGIN", new_y="NEXT")
        self.cell(0, 8, f"Обработано анкет: {total}", align="C", new_x="LMARGIN", new_y="NEXT")

    def add_kpi_section(self, kpi: dict):
        self.add_page()
        self.set_font(self._font_family, "B", 14)
        self.cell(0, 10, "Ключевые показатели (KPI)", new_x="LMARGIN", new_y="NEXT")
        self.ln(4)
        self.set_font(self._font_family, "", 11)
        for label, value in kpi.items():
            self.cell(0, 8, f"  {label}: {value}", new_x="LMARGIN", new_y="NEXT")

    def add_block_section(self, block_num: int, block_name: str, block_stats: dict, df: pd.DataFrame):
        self.add_page()
        self.set_font(self._font_family, "B", 14)
        self.cell(0, 10, f"Блок {block_num}. {block_name}", new_x="LMARGIN", new_y="NEXT")
        self.ln(4)

        self.set_font(self._font_family, "", 10)
        for col, data in block_stats.items():
            cfg = QUESTIONS.get(col, {})
            q = cfg.get("question", col)
            text = _format_stat_line(q, cfg, data)
            if text:
                if self.get_y() + 10 > self.h - 20:
                    self.add_page()
                self.set_x(10)
                self.multi_cell(190, 6, f"  {text}")
        self.ln(4)

        for col, cfg in QUESTIONS.items():
            if cfg["block"] != block_num or col not in df.columns:
                continue
            png = _render_chart_for_pdf(df, col, cfg)
            if png is None:
                continue
            with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
                tmp.write(png)
                tmp_path = tmp.name
            if self.get_y() + 70 > self.h - 20:
                self.add_page()
            self.image(tmp_path, x=15, w=170)
            self.ln(3)
            Path(tmp_path).unlink(missing_ok=True)

    def add_block_conclusions(self, block_num: int, block_name: str, items: list[str]):
        """Добавляет аналитические выводы по блоку."""
        self.add_page()
        self.set_font(self._font_family, "B", 14)
        self.cell(0, 10, f"Выводы: Блок {block_num}. {block_name}", new_x="LMARGIN", new_y="NEXT")
        self.ln(4)
        self.set_font(self._font_family, "", 10)
        for item in items:
            if self.get_y() + 10 > self.h - 20:
                self.add_page()
            self.set_x(10)
            self.multi_cell(190, 6, f"  — {item}")
            self.ln(2)

    def add_conclusion(self, total: int):
        self.add_page()
        self.set_font(self._font_family, "B", 14)
        self.cell(0, 10, "Итоговое заключение", new_x="LMARGIN", new_y="NEXT")
        self.ln(4)
        self.set_font(self._font_family, "", 11)
        self.multi_cell(0, 8, (
            f"Проведён анализ {total} анкет студентов. "
            "Результаты охватывают 7 тематических блоков: демографию, географию, "
            "логистику, финансы, увлечения, расписание и дополнительную информацию. "
            "Подробные данные доступны в прилагаемом XLSX-отчёте."
        ))


def export_to_pdf(df: pd.DataFrame) -> bytes:
    """Генерирует PDF-отчёт с графиками."""
    kpi = compute_kpi(df)
    stats = compute_all_stats(df)
    conclusions = generate_conclusions(df)

    pdf = StudentReportPDF()
    pdf.alias_nb_pages()
    pdf.add_title_page(len(df))
    pdf.add_kpi_section(kpi)

    for block_num, block_name in BLOCK_NAMES.items():
        block_stats = stats.get(block_num, {})
        pdf.add_block_section(block_num, block_name, block_stats, df)

        block_conclusions = conclusions.get(block_num, [])
        if block_conclusions:
            pdf.add_block_conclusions(block_num, block_name, block_conclusions)

    pdf.add_conclusion(len(df))
    return bytes(pdf.output())


def _format_stat_line(question: str, cfg: dict, data: dict) -> str:
    col_type = cfg.get("type", "")
    if col_type == "numeric":
        return f"{question}: среднее = {data.get('mean', '?')}, медиана = {data.get('median', '?')}"
    if col_type == "scale_1_5":
        return f"{question}: среднее = {data.get('mean', '?')}"
    if col_type in ("categorical", "multiple_choice"):
        pcts = data.get("percentages", {})
        filtered = {k: v for k, v in pcts.items() if k != NO_ANSWER}
        if filtered:
            top = max(filtered, key=filtered.get)
            return f"{question}: самый частый ответ — «{top}» ({filtered[top]}%)"
    return ""
