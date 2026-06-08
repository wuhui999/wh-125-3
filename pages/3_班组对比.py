import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils import (
    load_session_data,
    check_data_loaded,
    format_number,
    calculate_team_metrics,
    calculate_overall_kpis,
    TEAMS,
    PRODUCTION_LINES,
)

st.set_page_config(
    page_title="班组对比 - 能耗分析看板",
    page_icon="👥",
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

st.title("👥 班组对比")
st.markdown("---")

if not check_data_loaded(st):
    st.stop()

data = load_session_data(st)
meter_df = data["meter"]
production_df = data["production"]

with st.spinner("正在计算班组指标..."):
    team_metrics = calculate_team_metrics(production_df)
    kpis = calculate_overall_kpis(meter_df, production_df)

st.markdown("### 🎯 班组效率总览")

team_summary = team_metrics.groupby("team").agg(
    total_power=("total_power", "sum"),
    total_output=("total_output", "sum"),
    total_running_hours=("total_running_hours", "sum"),
    record_count=("record_count", "sum"),
).reset_index()

team_summary["avg_unit_ec"] = np.where(
    team_summary["total_output"] > 0,
    team_summary["total_power"] / team_summary["total_output"],
    np.nan
)

overall_avg_uec = team_summary["avg_unit_ec"].mean()
team_summary["efficiency_vs_avg"] = np.where(
    overall_avg_uec > 0,
    (overall_avg_uec - team_summary["avg_unit_ec"]) / overall_avg_uec * 100,
    0
)
team_summary["rank"] = team_summary["avg_unit_ec"].rank().astype(int)
team_summary = team_summary.sort_values("rank")

col1, col2, col3, col4 = st.columns(4)
for i, (_, row) in enumerate(team_summary.iterrows()):
    with [col1, col2, col3, col4][i]:
        delta_color = "normal" if row["efficiency_vs_avg"] > 0 else "inverse"
        st.metric(
            label=f"🏆 第{row['rank']}名 - {row['team']}",
            value=f"{row['avg_unit_ec']:.4f} kWh/单位",
            delta=f"{row['efficiency_vs_avg']:+.1f}% 均值对比",
            delta_color=delta_color,
        )

st.markdown("---")

col1, col2 = st.columns([1, 1])

with col1:
    st.markdown("### 📊 班组单位能耗对比")

    team_bar = team_metrics.copy()
    team_bar["efficiency_vs_baseline"] = -team_bar["efficiency_vs_baseline"]

    fig_bar = px.bar(
        team_bar,
        x="production_line",
        y="avg_unit_ec",
        color="team",
        barmode="group",
        color_discrete_sequence=px.colors.qualitative.Set2,
        text_auto=".4f",
        labels={
            "production_line": "产线",
            "avg_unit_ec": "平均单位能耗 (kWh/单位)",
            "team": "班组",
        },
    )
    fig_bar.update_layout(
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        margin=dict(l=0, r=0, t=30, b=0),
        height=400,
    )
    st.plotly_chart(fig_bar, use_container_width=True)

with col2:
    st.markdown("### 📈 效率对比基准线")

    team_metrics["efficiency_label"] = team_metrics["efficiency_vs_baseline"].apply(
        lambda x: f"优 {x:.1f}%" if x > 0 else f"差 {abs(x):.1f}%"
    )

    fig_scatter = px.scatter(
        team_metrics,
        x="production_line",
        y="efficiency_vs_baseline",
        color="team",
        size="total_power",
        size_max=60,
        text="efficiency_label",
        color_discrete_sequence=px.colors.qualitative.Set2,
        labels={
            "production_line": "产线",
            "efficiency_vs_baseline": "相对产线基准线 (%)",
            "team": "班组",
        },
    )
    fig_scatter.add_hline(
        y=0,
        line_dash="dash",
        line_color="gray",
        annotation_text="产线基准线",
    )
    fig_scatter.update_traces(textposition="top center")
    fig_scatter.update_layout(
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        margin=dict(l=0, r=0, t=30, b=0),
        height=400,
    )
    st.plotly_chart(fig_scatter, use_container_width=True)

st.markdown("---")

st.markdown("### 🔥 班组×产线 能耗热力图")

heatmap_data = team_metrics.pivot_table(
    index="team",
    columns="production_line",
    values="avg_unit_ec",
    aggfunc="mean",
)

heatmap_normalized = (heatmap_data - heatmap_data.min()) / (heatmap_data.max() - heatmap_data.min())

fig_heatmap = px.imshow(
    heatmap_normalized.values,
    x=heatmap_data.columns,
    y=heatmap_data.index,
    labels=dict(x="产线", y="班组", color="归一化能耗"),
    color_continuous_scale="RdYlGn_r",
    text_auto=".4f",
    aspect="auto",
)

for i in range(len(heatmap_data.index)):
    for j in range(len(heatmap_data.columns)):
        fig_heatmap.add_annotation(
            x=j,
            y=i,
            text=f"{heatmap_data.values[i][j]:.4f}",
            showarrow=False,
            font=dict(color="black", size=12),
        )

fig_heatmap.update_layout(
    height=350,
    margin=dict(l=0, r=0, t=30, b=0),
)
st.plotly_chart(fig_heatmap, use_container_width=True)

st.markdown("---")

col1, col2 = st.columns([1, 1])

with col1:
    st.markdown("### 🏆 班组综合排名")

    team_ranking = team_metrics.groupby("team").agg(
        avg_uec=("avg_unit_ec", "mean"),
        avg_efficiency=("efficiency_vs_baseline", "mean"),
        total_power=("total_power", "sum"),
        total_output=("total_output", "sum"),
        record_count=("record_count", "sum"),
    ).reset_index()

    team_ranking = team_ranking.sort_values("avg_efficiency", ascending=False)
    team_ranking["rank"] = range(1, len(team_ranking) + 1)
    team_ranking["medal"] = team_ranking["rank"].map({1: "🥇", 2: "🥈", 3: "🥉", 4: "🏅"})

    ranking_display = team_ranking[["rank", "medal", "team", "avg_uec", "avg_efficiency", "total_power", "total_output"]].rename(
        columns={
            "rank": "排名",
            "medal": "",
            "team": "班组",
            "avg_uec": "平均单位能耗",
            "avg_efficiency": "相对效率 (%)",
            "total_power": "总电耗 (kWh)",
            "total_output": "总产量",
        }
    )

    st.dataframe(
        ranking_display.style
        .format({
            "平均单位能耗": "{:.4f}",
            "相对效率 (%)": "{:+.1f}",
            "总电耗 (kWh)": "{:,.2f}",
            "总产量": "{:,.2f}",
        })
        .background_gradient(subset=["相对效率 (%)"], cmap="RdYlGn"),
        use_container_width=True,
        hide_index=True,
        height=250,
    )

with col2:
    st.markdown("### 📋 班组详细指标")

    team_metrics_display = team_metrics[[
        "production_line", "team", "avg_unit_ec", "efficiency_vs_baseline",
        "total_power", "total_output", "total_running_hours", "record_count"
    ]].rename(columns={
        "production_line": "产线",
        "team": "班组",
        "avg_unit_ec": "单位能耗",
        "efficiency_vs_baseline": "相对效率 (%)",
        "total_power": "总电耗 (kWh)",
        "total_output": "总产量",
        "total_running_hours": "运行时长 (h)",
        "record_count": "记录数",
    })

    st.dataframe(
        team_metrics_display.style
        .format({
            "单位能耗": "{:.4f}",
            "相对效率 (%)": "{:+.1f}",
            "总电耗 (kWh)": "{:,.2f}",
            "总产量": "{:,.2f}",
            "运行时长 (h)": "{:.1f}",
        })
        .background_gradient(subset=["相对效率 (%)"], cmap="RdYlGn"),
        use_container_width=True,
        height=250,
    )

st.markdown("---")

st.markdown("### 📈 班组日单位能耗趋势")

selected_team = st.selectbox("选择班组查看趋势", options=TEAMS, index=0)

team_prod = production_df[production_df["team"] == selected_team].copy()
team_prod["date"] = pd.to_datetime(team_prod["date"])
team_prod = team_prod.sort_values("date")

fig = go.Figure()

line_colors = ["#1f77b4", "#ff7f0e", "#2ca02c", "#d62728"]
for i, line in enumerate(PRODUCTION_LINES):
    line_data = team_prod[team_prod["production_line"] == line]
    if len(line_data) > 0:
        fig.add_trace(go.Scatter(
            x=line_data["date"],
            y=line_data["unit_energy_consumption"],
            mode="lines+markers",
            name=line,
            line=dict(color=line_colors[i], width=2),
            marker=dict(size=6),
        ))

line_baseline = team_metrics.groupby("production_line")["avg_unit_ec"].mean()
for i, line in enumerate(PRODUCTION_LINES):
    if line in line_baseline.index:
        fig.add_hline(
            y=line_baseline[line],
            line_dash="dash",
            line_color=line_colors[i],
            opacity=0.5,
            annotation_text=f"{line}基准",
        )

fig.update_layout(
    xaxis_title="日期",
    yaxis_title="单位能耗 (kWh/单位)",
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    margin=dict(l=0, r=0, t=30, b=0),
    height=350,
    hovermode="x unified",
)
st.plotly_chart(fig, use_container_width=True)

st.markdown("---")
st.markdown("### 💡 班组归因分析")

attribution_cols = st.columns(4)

for idx, team in enumerate(TEAMS):
    team_data = team_ranking[team_ranking["team"] == team].iloc[0]
    efficiency = team_data["avg_efficiency"]

    if efficiency > 5:
        status = "🌟 优秀"
        color = "#2ecc71"
        insights = [
            "操作规范执行到位",
            "设备维护保养良好",
            "节能意识强",
            "班组协作效率高",
        ]
    elif efficiency > 0:
        status = "✅ 良好"
        color = "#3498db"
        insights = [
            "整体表现稳定",
            "可向优秀班组对标学习",
            "关注空载用电优化",
        ]
    elif efficiency > -5:
        status = "⚠️ 待改进"
        color = "#ffaa00"
        insights = [
            "需要加强操作规范",
            "开展节能培训",
            "分析空载原因",
            "与优秀班组结对学习",
        ]
    else:
        status = "🔴 需重点关注"
        color = "#ff4b4b"
        insights = [
            "排查设备运行状态",
            "检查工艺参数设置",
            "加强班组长管理",
            "制定专项改进计划",
        ]

    with attribution_cols[idx]:
        st.markdown(f"#### {team}")
        st.markdown(f"<h3 style='text-align: center; color: {color};'>{status}</h3>", unsafe_allow_html=True)
        st.metric(
            label="相对效率",
            value=f"{efficiency:+.1f}%",
            delta=f"排名 第{team_data['rank']}名",
        )
        st.markdown("**归因分析:**")
        for insight in insights:
            st.markdown(f"- {insight}")
