"""Приложение Streamlit — Анализ студенческой жизни."""

import streamlit as st
import pandas as pd
import plotly.express as px

from modules.data_loader import load_data
from modules.preprocessor import preprocess
from modules.analytics import (
    compute_kpi, compute_all_stats, get_full_answers,
    get_category_summary, categorize_text_responses,
)
from modules.charts import (
    render_block_charts, render_chart,
    render_pie, render_table, _cycle_colors,
)
from modules.filters import render_sidebar, apply_filters
from modules.excel_exporter import export_to_excel
from modules.pdf_exporter import export_to_pdf
from modules.conclusions import generate_conclusions
from modules.logger import get_recent_logs
from config import BLOCK_NAMES, QUESTIONS, TEXT_CATEGORIES_CHANGE, TEXT_CATEGORIES_OKNA

st.set_page_config(
    page_title="Студенческая жизнь",
    page_icon="🎓",
    layout="wide",
)

st.title("Анализ результатов анкетирования «Студенческая жизнь»")

# Загрузка данных (несколько файлов)
uploaded_files = st.file_uploader(
    "Загрузите файлы с результатами анкетирования (CSV или XLSX)",
    type=["csv", "xlsx"],
    accept_multiple_files=True,
)

if not uploaded_files:
    st.info("Загрузите CSV или XLSX файл(ы) для начала анализа.")
    st.stop()

# Загружаем и объединяем все файлы
frames = []
for f in uploaded_files:
    df_part = load_data(f)
    if df_part is not None:
        frames.append(df_part)

if not frames:
    st.error("Не удалось загрузить ни один файл.")
    st.stop()

df_raw = pd.concat(frames, ignore_index=True)
df = preprocess(df_raw)
st.success(f"Загружено файлов: {len(frames)} | Записей после обработки: {len(df)}")

# Сайдбар: фильтры
filters = render_sidebar(df)
df_filtered = apply_filters(df, filters)

st.sidebar.write(f"Записей после фильтрации: **{len(df_filtered)}**")

# Журнал ошибок в сайдбаре
with st.sidebar.expander("Журнал событий"):
    logs = get_recent_logs(15)
    if logs:
        for line in logs:
            st.code(line, language=None)
    else:
        st.caption("Журнал пуст")

# KPI
st.subheader("Ключевые показатели")
kpi = compute_kpi(df_filtered)
cols = st.columns(len(kpi))
for i, (label, value) in enumerate(kpi.items()):
    cols[i].metric(label, value)

# Экспорт
st.subheader("Экспорт отчётов")

if "pdf_ready" not in st.session_state:
    st.session_state.pdf_ready = False
if "xlsx_ready" not in st.session_state:
    st.session_state.xlsx_ready = False

exp_col1, exp_col2 = st.columns(2)
with exp_col1:
    if st.button("Подготовить отчёт (PDF)"):
        with st.spinner("Генерация PDF..."):
            st.session_state.pdf_bytes = export_to_pdf(df_filtered)
        st.session_state.pdf_ready = True
    if st.session_state.pdf_ready:
        st.download_button("Скачать PDF", st.session_state.pdf_bytes, "report.pdf", "application/pdf", key="dl_pdf")

with exp_col2:
    if st.button("Подготовить отчёт (XLSX)"):
        st.session_state.xlsx_bytes = export_to_excel(df_raw, df_filtered)
        st.session_state.xlsx_ready = True
    if st.session_state.xlsx_ready:
        st.download_button("Скачать XLSX", st.session_state.xlsx_bytes, "report.xlsx",
                           "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", key="dl_xlsx")

# Глобальный выбор типа графиков
global_chart_type = st.radio(
    "Тип графиков",
    ["Столбчатая", "Круговая", "Таблица"],
    horizontal=True,
    key="global_chart_type",
)

st.divider()

# Аналитические выводы
conclusions = generate_conclusions(df_filtered)
if conclusions:
    st.subheader("Аналитические выводы")
    for block_num, items in conclusions.items():
        block_name = BLOCK_NAMES.get(block_num, "")
        with st.expander(f"Выводы: Блок {block_num}. {block_name}"):
            for item in items:
                st.markdown(f"- {item}")

st.divider()

# Графики по блокам
for block_num, block_name in BLOCK_NAMES.items():
    with st.expander(f"Блок {block_num}. {block_name}", expanded=(block_num == 1)):
        for col, cfg in QUESTIONS.items():
            if cfg["block"] != block_num or col not in df_filtered.columns:
                continue
            if cfg["type"] == "text":
                continue

            chart_title = cfg["question"]

            if global_chart_type == "Столбчатая":
                fig = render_chart(df_filtered, col, cfg)
                if fig is not None:
                    st.plotly_chart(fig, width='stretch', key=f"b{block_num}_{col}")
            elif global_chart_type == "Круговая":
                fig = render_pie(df_filtered, col, cfg["question"])
                if fig is not None:
                    st.plotly_chart(fig, width='stretch', key=f"pie_{block_num}_{col}")
            elif global_chart_type == "Таблица":
                table = render_table(df_filtered, col, cfg["question"])
                if table is not None:
                    st.dataframe(table, width='stretch', hide_index=True)

        # Текстовые колонки — категоризация + топ слов + ответы
        for col, cfg in QUESTIONS.items():
            if cfg["block"] != block_num or cfg["type"] != "text":
                continue
            if col not in df_filtered.columns:
                continue

            # Выбираем словарь категорий в зависимости от вопроса
            if "хотели изменить" in col:
                categories = TEXT_CATEGORIES_CHANGE
            elif "окнах" in col:
                categories = TEXT_CATEGORIES_OKNA
            else:
                categories = TEXT_CATEGORIES_CHANGE

            st.markdown(f"### {cfg['question']}")

            # Таблица категорий
            cat_df = get_category_summary(df_filtered[col], categories)
            if not cat_df.empty:
                st.dataframe(cat_df, width='stretch', hide_index=True)

                # График
                fig = px.bar(
                    cat_df[cat_df["Категория"] != "Другое"],
                    x="Категория",
                    y="Ответов",
                    text="Доля (%)",
                    color="Категория",
                    color_discrete_sequence=_cycle_colors(len(cat_df) - 1),
                )
                fig.update_traces(textposition="outside")
                fig.update_layout(showlegend=False, xaxis_title="", yaxis_title="Количество ответов")
                st.plotly_chart(fig, width='stretch', key=f"cat_{block_num}_{col}")

            # «Другое» — раскрывающийся список неопознанных ответов
            categorized = categorize_text_responses(df_filtered[col], categories)
            other_answers = categorized.get("Другое", [])
            if other_answers:
                with st.expander(f"Неопознанные ответы ({len(other_answers)} шт.)"):
                    for a in other_answers:
                        st.markdown(f"- {a}")

            # Все ответы
            answers = get_full_answers(df_filtered[col])
            if answers:
                with st.expander(f"Все ответы ({len(answers)} шт.)"):
                    for a in answers:
                        st.markdown(f"- {a}")
