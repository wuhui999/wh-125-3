import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from utils import (
    load_session_data,
    check_data_loaded,
    format_number,
    get_severity_color,
    get_severity_emoji,
    calculate_overall_kpis,
    calculate_peak_valley_ratio,
    calculate_daily_metrics,
    detect_all_anomalies,
    summarize_anomalies,
    PRODUCTION_LINES,
)

st.set_page_config(
    page_title="工厂能耗数据分析看板",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)

if "data" not in st.session_state:
    st.session_state["data"] = None

with st.sidebar:
    st.title("⚡ 能耗分析看板")
    st.markdown("---")
    st.page_link("app.py", label="📊 总览页", icon="📊")
    st.page_link("pages/1_数据导入.py", label="📤 数据导入", icon="📤")
    st.page_link("pages/2_产线分析.py", label="🏭 产线分析", icon="🏭")
    st.page_link("pages/3_班组对比.py", label="👥 班组对比", icon="👥")
    st.page_link("pages/4_异常清单.py", label="⚠️ 异常清单", icon="⚠️")
    st.markdown("---")
    st.caption("帮助能源管理员发现产线电耗异常")

st.title("📊 能耗总览")
st.markdown("---")

if not check_data_loaded(st):
    st.stop()

data = load_session_data(st)
meter_df = data["meter"]
production_df = data["production"]

with st.spinner("正在计算指标..."):
    kpis = calculate_overall_kpis(meter_df, production_df)
    _, peak_valley_ratios = calculate_peak_valley_ratio(meter_df)
    daily_metrics = calculate_daily_metrics(meter_df)
    anomaly_df = detect_all_anomalies(meter_df, production_df)
    anomaly_summary = summarize_anomalies(anomaly_df)

st.markdown("### 🔑 关键指标")
col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric(
        label="总耗电量",
        value=f"{format_number(kpis['total_power_kwh'])} kWh",
        delta=f"数据完整率 {kpis['data_completeness']}%",
        delta_color="off",
    )

with col2:
    st.metric(
        label="单位产量能耗",
        value=f"{format_number(kpis['unit_ec_kwh_per_unit'], 4)} kWh/单位",
        delta=f"总产量 {format_number(kpis['total_output'])}",
        delta_color="off",
    )

with col3:
    anomaly_count = anomaly_summary["total_count"]
    high_count = anomaly_summary["by_severity"].get("高", 0)
    st.metric(
        label="异常次数",
        value=f"{anomaly_count} 次",
        delta=f"🔴 高度异常 {high_count} 次",
        delta_color="inverse",
    )

with col4:
    st.metric(
        label="峰谷用电比",
        value=f"{kpis['peak_valley_ratio']:.1f}%",
        delta=f"峰段 {peak_valley_ratios['peak_ratio']:.1f}% / 谷段 {peak_valley_ratios['valley_ratio']:.1f}%",
        delta_color="off",
    )

st.markdown("---")

col1, col2 = st.columns([2, 1])

with col1:
    st.markdown("### 📈 用电趋势")
    daily_total = daily_metrics.groupby("date").agg(
        total_power=("total_power", "sum"),
        idle_power=("idle_power", "sum"),
    ).reset_index()

    fig_trend = go.Figure()
    fig_trend.add_trace(go.Bar(
        x=daily_total["date"],
        y=daily_total["total_power"] - daily_total["idle_power"],
        name="生产用电",
        marker_color="#1f77b4",
    ))
    fig_trend.add_trace(go.Bar(
        x=daily_total["date"],
        y=daily_total["idle_power"],
        name="空载用电",
        marker_color="#ff7f0e",
    ))
    fig_trend.update_layout(
        barmode="stack",
        xaxis_title="日期",
        yaxis_title="用电量 (kWh)",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        margin=dict(l=0, r=0, t=30, b=0),
        height=350,
    )
    st.plotly_chart(fig_trend, use_container_width=True)

with col2:
    st.markdown("### ⚡ 峰谷用电比例")
    pie_data = pd.DataFrame({
        "类型": ["峰段", "谷段", "平段"],
        "用电量 (kWh)": [
            peak_valley_ratios["peak_power_kwh"],
            peak_valley_ratios["valley_power_kwh"],
            peak_valley_ratios["flat_power_kwh"],
        ],
        "占比 (%)": [
            peak_valley_ratios["peak_ratio"],
            peak_valley_ratios["valley_ratio"],
            peak_valley_ratios["flat_ratio"],
        ],
    })
    colors = ["#ff4b4b", "#2ecc71", "#3498db"]
    fig_pie = px.pie(
        pie_data,
        values="用电量 (kWh)",
        names="类型",
        color="类型",
        color_discrete_map={"峰段": "#ff4b4b", "谷段": "#2ecc71", "平段": "#3498db"},
        hole=0.5,
    )
    fig_pie.update_traces(textposition="inside", textinfo="percent+label")
    fig_pie.update_layout(
        margin=dict(l=0, r=0, t=30, b=0),
        height=350,
        showlegend=False,
    )
    st.plotly_chart(fig_pie, use_container_width=True)

st.markdown("---")

col1, col2 = st.columns([1, 1])

with col1:
    st.markdown("### 🏭 各产线能耗对比")
    line_power = daily_metrics.groupby("production_line")["total_power"].sum().reset_index()
    line_power = line_power.sort_values("total_power", ascending=False)

    fig_line = px.bar(
        line_power,
        x="production_line",
        y="total_power",
        color="production_line",
        color_discrete_sequence=px.colors.qualitative.Set2,
        text_auto=".2s",
    )
    fig_line.update_layout(
        xaxis_title="产线",
        yaxis_title="总用电量 (kWh)",
        showlegend=False,
        margin=dict(l=0, r=0, t=30, b=0),
        height=350,
    )
    st.plotly_chart(fig_line, use_container_width=True)

with col2:
    st.markdown("### ⚠️ 异常类型分布")
    if anomaly_df.empty:
        st.info("✅ 未检测到异常")
    else:
        type_counts = anomaly_df.groupby(["anomaly_name", "severity"]).size().reset_index(name="count")
        type_counts = type_counts.sort_values("count", ascending=True)
        type_counts["color"] = type_counts["severity"].apply(get_severity_color)

        fig_anomaly = px.barh(
            type_counts,
            y="anomaly_name",
            x="count",
            color="severity",
            color_discrete_map={"高": "#ff4b4b", "中": "#ffaa00", "低": "#2ecc71"},
            text_auto=True,
        )
        fig_anomaly.update_layout(
            xaxis_title="异常次数",
            yaxis_title="",
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            margin=dict(l=0, r=0, t=30, b=0),
            height=350,
        )
        st.plotly_chart(fig_anomaly, use_container_width=True)

st.markdown("---")

st.markdown("### 📋 核心指标详情")
metric_cols = st.columns(6)
metrics_data = [
    ("平均开机率", f"{kpis['avg_running_rate']:.1f}%", "⚙️"),
    ("空载电耗", f"{format_number(kpis['idle_power_kwh'])} kWh", "🔌"),
    ("空载占比", f"{kpis['idle_ratio']:.1f}%", "📉"),
    ("峰段用电", f"{format_number(peak_valley_ratios['peak_power_kwh'])} kWh", "🔴"),
    ("谷段用电", f"{format_number(peak_valley_ratios['valley_power_kwh'])} kWh", "🟢"),
    ("平段用电", f"{format_number(peak_valley_ratios['flat_power_kwh'])} kWh", "🔵"),
]

for col, (label, value, emoji) in zip(metric_cols, metrics_data):
    with col:
        st.markdown(f"**{emoji} {label}**")
        st.markdown(f"<h3 style='text-align: center; color: #1f77b4;'>{value}</h3>", unsafe_allow_html=True)

st.markdown("---")
st.markdown("### 🏭 各产线日用电趋势")
line_colors = ["#1f77b4", "#ff7f0e", "#2ca02c", "#d62728"]
fig = go.Figure()

for i, line in enumerate(PRODUCTION_LINES):
    line_data = daily_metrics[daily_metrics["production_line"] == line]
    fig.add_trace(go.Scatter(
        x=line_data["date"],
        y=line_data["total_power"],
        mode="lines+markers",
        name=line,
        line=dict(color=line_colors[i], width=2),
        marker=dict(size=6),
    ))

fig.update_layout(
    xaxis_title="日期",
    yaxis_title="日用电量 (kWh)",
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    margin=dict(l=0, r=0, t=30, b=0),
    height=300,
    hovermode="x unified",
)
st.plotly_chart(fig, use_container_width=True)
