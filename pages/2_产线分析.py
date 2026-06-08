import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils import (
    load_session_data,
    check_data_loaded,
    format_number,
    calculate_daily_metrics,
    calculate_hourly_distribution,
    calculate_production_correlation,
    calculate_overall_kpis,
    PRODUCTION_LINES,
)

st.set_page_config(
    page_title="产线分析 - 能耗分析看板",
    page_icon="🏭",
    layout="wide",
)

with st.sidebar:
    st.title("⚡ 能耗分析看板")
    st.markdown("---")
    st.page_link("app.py", label="📊 总览页", icon="📊")
    st.page_link("pages/1_数据导入.py", label="📤 数据导入", icon="📤")
    st.page_link("pages/2_产线分析.py", label="🏭 产线分析", icon="🏭")
    st.page_link("pages/3_班组对比.py", label="👥 班组对比", icon="👥")
    st.page_link("pages/4_异常清单.py", label="⚠️ 异常清单", icon="⚠️")

st.title("🏭 产线分析")
st.markdown("---")

if not check_data_loaded(st):
    st.stop()

data = load_session_data(st)
meter_df = data["meter"]
production_df = data["production"]

with st.spinner("正在计算产线指标..."):
    daily_metrics = calculate_daily_metrics(meter_df)
    hourly_dist = calculate_hourly_distribution(meter_df)
    corr_df = calculate_production_correlation(production_df)
    kpis = calculate_overall_kpis(meter_df, production_df)

st.markdown("### 🎛️ 选择产线")
selected_line = st.selectbox("选择分析产线", options=PRODUCTION_LINES, index=0)

line_daily = daily_metrics[daily_metrics["production_line"] == selected_line]
line_hourly = hourly_dist[hourly_dist["production_line"] == selected_line]
line_corr = corr_df[corr_df["production_line"] == selected_line].iloc[0]
line_prod = production_df[production_df["production_line"] == selected_line]

st.markdown("---")
st.markdown(f"### 📊 {selected_line} 关键指标")

col1, col2, col3, col4 = st.columns(4)

line_total_power = line_daily["total_power"].sum()
line_avg_uec = line_corr["avg_unit_ec"]
line_correlation = line_corr["power_output_correlation"]
line_idle_ratio = line_daily["idle_ratio"].mean()

with col1:
    st.metric(
        label="总用电量",
        value=f"{format_number(line_total_power)} kWh",
        delta=f"占比 {line_total_power/kpis['total_power_kwh']*100:.1f}%",
        delta_color="off",
    )

with col2:
    st.metric(
        label="平均单位能耗",
        value=f"{format_number(line_avg_uec, 4)} kWh/单位",
        delta=f"变异系数 {line_corr['cv_unit_ec']:.1f}%",
        delta_color="off",
    )

with col3:
    st.metric(
        label="电耗-产量相关系数",
        value=f"{line_correlation:.4f}",
        delta="正相关越强越好" if line_correlation > 0.7 else "相关性较弱，需关注",
        delta_color="normal" if line_correlation > 0.7 else "inverse",
    )

with col4:
    st.metric(
        label="平均空载占比",
        value=f"{line_idle_ratio:.1f}%",
        delta=f"空载电耗 {format_number(line_daily['idle_power'].sum())} kWh",
        delta_color="inverse",
    )

st.markdown("---")

col1, col2 = st.columns([3, 2])

with col1:
    st.markdown("### 📈 用电趋势分析")

    fig = make_subplots(rows=2, cols=1, shared_xaxis=True,
                        subplot_titles=("日用电量趋势", "空载电耗占比"),
                        vertical_spacing=0.1)

    fig.add_trace(
        go.Scatter(
            x=line_daily["date"],
            y=line_daily["total_power"],
            mode="lines+markers",
            name="总用电量",
            line=dict(color="#1f77b4", width=2),
            marker=dict(size=6),
        ),
        row=1, col=1
    )

    fig.add_trace(
        go.Scatter(
            x=line_daily["date"],
            y=line_daily["running_hours"],
            mode="lines+markers",
            name="运行时长",
            line=dict(color="#2ca02c", width=2),
            marker=dict(size=6),
            yaxis="y2",
        ),
        row=1, col=1
    )

    fig.update_layout(
        yaxis2=dict(
            title="运行时长 (小时)",
            overlaying="y",
            side="right",
            showgrid=False,
        ),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )

    fig.add_trace(
        go.Bar(
            x=line_daily["date"],
            y=line_daily["idle_ratio"],
            name="空载占比",
            marker_color="#ff7f0e",
            opacity=0.7,
        ),
        row=2, col=1
    )

    fig.add_hline(
        y=10,
        line_dash="dash",
        line_color="red",
        annotation_text="阈值 10%",
        row=2, col=1
    )

    fig.update_layout(
        height=500,
        margin=dict(l=0, r=0, t=30, b=0),
        hovermode="x unified",
    )
    fig.update_xaxes(title_text="日期", row=2, col=1)
    fig.update_yaxes(title_text="用电量 (kWh)", row=1, col=1)
    fig.update_yaxes(title_text="空载占比 (%)", row=2, col=1)

    st.plotly_chart(fig, use_container_width=True)

with col2:
    st.markdown("### ⏰ 小时用电视图")

    hourly_pivot = line_hourly.pivot_table(
        index="hour",
        values="avg_power_kw",
        aggfunc="mean"
    ).reset_index()

    fig_hourly = go.Figure()
    fig_hourly.add_trace(go.Bar(
        x=hourly_pivot["hour"],
        y=hourly_pivot["avg_power_kw"],
        marker_color=[
            "#ff4b4b" if h in [8, 9, 10, 11, 17, 18, 19, 20]
            else "#2ecc71" if h in [0, 1, 2, 3, 4, 5]
            else "#3498db"
            for h in hourly_pivot["hour"]
        ],
    ))

    fig_hourly.update_layout(
        xaxis=dict(tickmode="linear", tick0=0, dtick=1, title="小时"),
        yaxis_title="平均功率 (kW)",
        height=300,
        margin=dict(l=0, r=0, t=30, b=0),
    )
    st.plotly_chart(fig_hourly, use_container_width=True)

    st.markdown("### 🏃 设备运行率")
    fig_run = go.Figure(go.Bar(
        x=line_hourly["hour"],
        y=line_hourly["running_rate"],
        marker_color="#2ca02c",
    ))
    fig_run.update_layout(
        xaxis=dict(tickmode="linear", tick0=0, dtick=1, title="小时"),
        yaxis_title="运行率 (%)",
        yaxis_range=[0, 100],
        height=200,
        margin=dict(l=0, r=0, t=30, b=0),
    )
    st.plotly_chart(fig_run, use_container_width=True)

st.markdown("---")

col1, col2 = st.columns([1, 1])

with col1:
    st.markdown("### 🔄 产量 vs 电耗 散点图")

    fig_scatter = px.scatter(
        line_prod,
        x="output_quantity",
        y="power_consumption_kwh",
        color="team",
        size="running_hours",
        hover_data=["date", "shift", "unit_energy_consumption"],
        trendline="ols",
        color_discrete_sequence=px.colors.qualitative.Set2,
    )
    fig_scatter.update_layout(
        xaxis_title="产量",
        yaxis_title="耗电量 (kWh)",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        height=400,
        margin=dict(l=0, r=0, t=30, b=0),
    )
    st.plotly_chart(fig_scatter, use_container_width=True)

with col2:
    st.markdown("### 📊 单位能耗分布")

    fig_box = px.box(
        line_prod,
        x="team",
        y="unit_energy_consumption",
        color="team",
        points="all",
        color_discrete_sequence=px.colors.qualitative.Set2,
    )
    fig_box.update_layout(
        xaxis_title="班组",
        yaxis_title="单位能耗 (kWh/单位)",
        showlegend=False,
        height=400,
        margin=dict(l=0, r=0, t=30, b=0),
    )
    st.plotly_chart(fig_box, use_container_width=True)

st.markdown("---")
st.markdown("### 📋 产线对比汇总")

line_summary = daily_metrics.groupby("production_line").agg(
    total_power=("total_power", "sum"),
    avg_running_hours=("running_hours", "mean"),
    avg_idle_ratio=("idle_ratio", "mean"),
    total_idle_power=("idle_power", "sum"),
).reset_index()

line_summary = line_summary.merge(corr_df, on="production_line", how="left")
line_summary["power_rank"] = line_summary["total_power"].rank(ascending=False).astype(int)
line_summary["efficiency_rank"] = line_summary["avg_unit_ec"].rank().astype(int)

display_cols = [
    "production_line", "power_rank", "total_power", "avg_unit_ec",
    "avg_running_hours", "avg_idle_ratio", "power_output_correlation", "cv_unit_ec"
]
display_names = {
    "production_line": "产线",
    "power_rank": "用电排名",
    "total_power": "总用电量 (kWh)",
    "avg_unit_ec": "平均单位能耗",
    "avg_running_hours": "平均日运行时长",
    "avg_idle_ratio": "平均空载占比 (%)",
    "power_output_correlation": "电耗-产量相关系数",
    "cv_unit_ec": "单位能耗变异系数 (%)",
}

line_summary_display = line_summary[display_cols].rename(columns=display_names)

def highlight_rows(row):
    if row["产线"] == selected_line:
        return ["background-color: rgba(31, 119, 180, 0.2)"] * len(row)
    return [""] * len(row)

st.dataframe(
    line_summary_display.style
    .apply(highlight_rows, axis=1)
    .format({
        "总用电量 (kWh)": "{:,.2f}",
        "平均单位能耗": "{:.4f}",
        "平均日运行时长": "{:.1f}",
        "平均空载占比 (%)": "{:.1f}",
        "电耗-产量相关系数": "{:.4f}",
        "单位能耗变异系数 (%)": "{:.1f}",
    }),
    use_container_width=True,
    height=200,
)

st.markdown("---")
st.markdown("### 🔥 用电热力图（按小时×星期）")

meter_df["weekday"] = meter_df["timestamp"].dt.weekday
meter_df["hour"] = meter_df["timestamp"].dt.hour
line_meter = meter_df[meter_df["production_line"] == selected_line]

heatmap_data = line_meter.groupby(["weekday", "hour"])["power_kw"].mean().unstack()
weekday_names = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
heatmap_data.index = weekday_names

fig_heatmap = px.imshow(
    heatmap_data.values,
    x=heatmap_data.columns,
    y=heatmap_data.index,
    labels=dict(x="小时", y="星期", color="平均功率 (kW)"),
    color_continuous_scale="Reds",
    aspect="auto",
)
fig_heatmap.update_layout(
    xaxis=dict(tickmode="linear", tick0=0, dtick=2),
    height=350,
    margin=dict(l=0, r=0, t=30, b=0),
)
st.plotly_chart(fig_heatmap, use_container_width=True)
