import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils import (
    load_session_data,
    check_data_loaded,
    format_number,
    get_severity_color,
    get_severity_emoji,
    detect_all_anomalies,
    summarize_anomalies,
    calculate_overall_kpis,
    generate_energy_saving_report,
    export_to_excel,
    set_plotly_chinese_font,
    ANOMALY_TYPES,
    PRODUCTION_LINES,
    TEAMS,
)

st.set_page_config(
    page_title="异常清单 - 能耗分析看板",
    page_icon="⚠️",
    layout="wide",
)

with st.sidebar:
    st.title("⚡ 能耗分析看板")
    st.markdown("---")
    st.page_link("app.py", label="📊 总览页")
    st.page_link("pages/1_数据导入.py", label="📤 数据导入")
    st.page_link("pages/2_产线分析.py", label="🏭 产线分析")
    st.page_link("pages/3_班组对比.py", label="👥 班组对比")
    st.page_link("pages/4_异常清单.py", label="⚠️ 异常清单")

st.title("⚠️ 异常清单")
st.markdown("---")

if not check_data_loaded(st):
    st.stop()

data = load_session_data(st)
meter_df = data["meter"]
production_df = data["production"]

with st.spinner("正在检测异常..."):
    anomaly_df = detect_all_anomalies(meter_df, production_df)
    anomaly_summary = summarize_anomalies(anomaly_df)
    kpis = calculate_overall_kpis(meter_df, production_df)

st.markdown("### 📊 异常总览")

col1, col2, col3, col4 = st.columns(4)

total_count = anomaly_summary["total_count"]
high_count = anomaly_summary["by_severity"].get("高", 0)
medium_count = anomaly_summary["by_severity"].get("中", 0)
low_count = anomaly_summary["by_severity"].get("低", 0)

with col1:
    st.metric(
        label="🔴 高度异常",
        value=f"{high_count} 项",
        delta=f"占比 {high_count/total_count*100:.1f}%" if total_count > 0 else "0%",
        delta_color="inverse",
    )

with col2:
    st.metric(
        label="🟡 中度异常",
        value=f"{medium_count} 项",
        delta=f"占比 {medium_count/total_count*100:.1f}%" if total_count > 0 else "0%",
        delta_color="off",
    )

with col3:
    st.metric(
        label="🟢 低度异常",
        value=f"{low_count} 项",
        delta=f"占比 {low_count/total_count*100:.1f}%" if total_count > 0 else "0%",
        delta_color="normal",
    )

with col4:
    st.metric(
        label="📋 异常总数",
        value=f"{total_count} 项",
        delta=f"涉及 {len(anomaly_summary['by_team'])} 个班组" if anomaly_summary['by_team'] else "0 个班组",
        delta_color="off",
    )

st.markdown("---")

col1, col2 = st.columns([1, 1])

with col1:
    st.markdown("### 📈 异常类型分布")
    if anomaly_df.empty:
        st.info("✅ 未检测到异常")
    else:
        type_counts = anomaly_df.groupby("anomaly_name").size().reset_index(name="count")
        type_counts = type_counts.sort_values("count", ascending=True)

        fig_type = px.bar(
            type_counts,
            y="anomaly_name",
            x="count",
            color="count",
            orientation="h",
            color_continuous_scale="Reds",
            text_auto=True,
            labels={"anomaly_name": "异常类型", "count": "异常次数"},
        )
        fig_type.update_layout(
            height=350,
            margin=dict(l=0, r=0, t=30, b=0),
            showlegend=False,
        )
        st.plotly_chart(set_plotly_chinese_font(fig_type), use_container_width=True)

with col2:
    st.markdown("### 🏭 异常产线分布")
    if anomaly_df.empty:
        st.info("✅ 未检测到异常")
    else:
        line_counts = anomaly_df.groupby("production_line").size().reset_index(name="count")
        line_counts = line_counts.sort_values("count", ascending=False)

        fig_line = px.pie(
            line_counts,
            values="count",
            names="production_line",
            color="production_line",
            color_discrete_sequence=px.colors.qualitative.Set2,
            hole=0.4,
        )
        fig_line.update_traces(textposition="inside", textinfo="percent+label")
        fig_line.update_layout(
            height=350,
            margin=dict(l=0, r=0, t=30, b=0),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        )
        st.plotly_chart(set_plotly_chinese_font(fig_line), use_container_width=True)

st.markdown("---")

st.markdown("### 👥 班组异常排名")
if anomaly_df.empty:
    st.info("✅ 未检测到异常")
else:
    team_counts = anomaly_df.groupby(["team", "severity"]).size().unstack(fill_value=0)
    team_counts["total"] = team_counts.sum(axis=1)
    team_counts = team_counts.sort_values("total", ascending=False)

    for col in ["高", "中", "低"]:
        if col not in team_counts.columns:
            team_counts[col] = 0

    team_counts = team_counts[["高", "中", "低", "total"]].reset_index()
    team_counts.columns = ["班组", "高度", "中度", "低度", "合计"]

    fig_team = go.Figure()
    fig_team.add_trace(go.Bar(
        x=team_counts["班组"],
        y=team_counts["高度"],
        name="高度",
        marker_color="#ff4b4b",
    ))
    fig_team.add_trace(go.Bar(
        x=team_counts["班组"],
        y=team_counts["中度"],
        name="中度",
        marker_color="#ffaa00",
    ))
    fig_team.add_trace(go.Bar(
        x=team_counts["班组"],
        y=team_counts["低度"],
        name="低度",
        marker_color="#2ecc71",
    ))
    fig_team.update_layout(
        barmode="stack",
        xaxis_title="班组",
        yaxis_title="异常次数",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        height=300,
        margin=dict(l=0, r=0, t=30, b=0),
    )
    st.plotly_chart(set_plotly_chinese_font(fig_team), use_container_width=True)

st.markdown("---")

st.markdown("### 🔍 异常筛选")

if anomaly_df.empty:
    st.info("✅ 未检测到异常，无需筛选")
else:
    filter_cols = st.columns(4)

    with filter_cols[0]:
        severity_filter = st.multiselect(
            "严重程度",
            options=["高", "中", "低"],
            default=["高", "中", "低"],
        )

    with filter_cols[1]:
        type_filter = st.multiselect(
            "异常类型",
            options=list(anomaly_df["anomaly_name"].unique()),
            default=list(anomaly_df["anomaly_name"].unique()),
        )

    with filter_cols[2]:
        line_filter = st.multiselect(
            "产线",
            options=PRODUCTION_LINES,
            default=PRODUCTION_LINES,
        )

    with filter_cols[3]:
        team_filter = st.multiselect(
            "班组",
            options=TEAMS,
            default=TEAMS,
        )

    filtered_df = anomaly_df[
        (anomaly_df["severity"].isin(severity_filter)) &
        (anomaly_df["anomaly_name"].isin(type_filter)) &
        (anomaly_df["production_line"].isin(line_filter)) &
        (anomaly_df["team"].isin(team_filter))
    ].copy()

    st.markdown(f"**筛选结果：** 共 {len(filtered_df)} 条异常记录")

st.markdown("---")
st.markdown("### 📋 异常明细")

if anomaly_df.empty:
    st.success("🎉 太棒了！当前数据未检测到任何异常，生产能耗状况良好。")
else:
    display_df = filtered_df[[
        "severity", "anomaly_name", "timestamp", "production_line",
        "team", "shift", "evidence", "deviation_ratio"
    ]].copy()

    display_df.columns = [
        "严重程度", "异常类型", "时间", "产线",
        "班组", "班次", "证据数据", "偏离程度 (%)"
    ]

    display_df["严重程度"] = display_df["严重程度"].apply(
        lambda x: f"{get_severity_emoji(x)} {x}"
    )

    def style_severity(val):
        sev = val.split()[-1] if " " in val else val
        color = get_severity_color(sev)
        return f"color: {color}; font-weight: bold;"

    st.dataframe(
        display_df.style
        .map(style_severity, subset=["严重程度"])
        .format({
            "偏离程度 (%)": "{:+.1f}",
        }),
        use_container_width=True,
        height=400,
        hide_index=True,
    )

    st.markdown("---")
    st.markdown("### 🔎 异常详情与归因建议")

    if len(filtered_df) > 0:
        selected_idx = st.selectbox(
            "选择异常记录查看详情",
            options=range(len(filtered_df)),
            format_func=lambda x: f"#{x+1} {filtered_df.iloc[x]['anomaly_name']} - {filtered_df.iloc[x]['timestamp']}",
        )

        selected = filtered_df.iloc[selected_idx]

        detail_cols = st.columns([2, 1])

        with detail_cols[0]:
            st.markdown(f"#### {get_severity_emoji(selected['severity'])} [{selected['severity']}] {selected['anomaly_name']}")
            st.markdown(f"**时间：** {selected['timestamp']}")
            st.markdown(f"**产线：** {selected['production_line']}")
            st.markdown(f"**班组：** {selected['team']} | **班次：** {selected['shift']}")
            st.markdown("---")
            st.markdown("**📝 证据数据：**")
            st.info(selected["evidence"])
            st.markdown("**🔍 归因分析：**")
            st.warning(selected["description"])

        with detail_cols[1]:
            st.markdown("**📊 偏离程度：**")
            deviation = selected.get("deviation_ratio", 0)
            fig_gauge = go.Figure(go.Indicator(
                mode="gauge+number",
                value=abs(deviation),
                domain={"x": [0, 1], "y": [0, 1]},
                title={"text": "偏离程度 (%)"},
                gauge={
                    "axis": {"range": [None, max(100, abs(deviation) * 1.2)]},
                    "bar": {"color": get_severity_color(selected["severity"])},
                    "steps": [
                        {"range": [0, 15], "color": "#2ecc71"},
                        {"range": [15, 30], "color": "#ffaa00"},
                        {"range": [30, 100], "color": "#ff4b4b"},
                    ],
                },
            ))
            fig_gauge.update_layout(height=250, margin=dict(l=0, r=0, t=0, b=0))
            st.plotly_chart(set_plotly_chinese_font(fig_gauge), use_container_width=True)

            if "baseline" in selected and not pd.isna(selected["baseline"]):
                st.metric(
                    label="基准值",
                    value=f"{selected['baseline']:.4f}",
                )

        st.markdown("---")
        st.markdown("### 💡 归因建议")

        suggestions = selected.get("suggestions", [])
        for i, suggestion in enumerate(suggestions, 1):
            st.markdown(f"**{i}.** {suggestion}")

st.markdown("---")
st.markdown("### 📤 导出报告")

report_cols = st.columns(2)

with report_cols[0]:
    st.markdown("#### 📄 异常报告 (文本)")
    report_text = generate_energy_saving_report(anomaly_df, kpis)
    st.download_button(
        label="📥 下载异常报告",
        data=report_text,
        file_name=f"能耗异常报告_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.txt",
        mime="text/plain",
        use_container_width=True,
    )

    with st.expander("📖 预览报告"):
        st.text(report_text)

with report_cols[1]:
    st.markdown("#### 📊 异常数据 (Excel)")
    if not anomaly_df.empty:
        export_df = anomaly_df.copy()
        export_df["timestamp"] = export_df["timestamp"].astype(str)
        if "suggestions" in export_df.columns:
            export_df["suggestions"] = export_df["suggestions"].apply(
                lambda x: "\n".join(x) if isinstance(x, list) else str(x)
            )

        excel_data = export_to_excel({"异常清单": export_df})
        st.download_button(
            label="📥 下载异常清单 (Excel)",
            data=excel_data,
            file_name=f"异常清单_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
        )
    else:
        st.info("暂无异常数据可导出")

st.markdown("---")
st.markdown("### 📚 异常类型说明")

with st.expander("🔍 查看所有异常类型定义"):
    for key, info in ANOMALY_TYPES.items():
        st.markdown(f"#### {get_severity_emoji(info['severity'])} [{info['severity']}] {info['name']}")
        st.markdown(f"**描述：** {info['description']}")
        st.markdown("**常见建议：**")
        for s in info["suggestions"]:
            st.markdown(f"- {s}")
        st.markdown("---")
