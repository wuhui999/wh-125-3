import pandas as pd
import numpy as np
import io
from typing import Dict, Optional


def set_plotly_chinese_font(fig):
    chinese_font = (
        "Microsoft YaHei, SimHei, PingFang SC, "
        "Noto Sans CJK SC, WenQuanYi Micro Hei, sans-serif"
    )
    font_dict = {"family": chinese_font}

    fig.update_layout(
        font={**font_dict, "size": 12},
        title_font=font_dict,
        legend_font=font_dict,
        hoverlabel={"font": font_dict},
    )

    fig.update_xaxes(title_font=font_dict, tickfont=font_dict)
    fig.update_yaxes(title_font=font_dict, tickfont=font_dict)
    fig.update_annotations(font=font_dict)

    try:
        fig.update_coloraxes(
            colorbar=dict(title_font=font_dict, tickfont=font_dict),
        )
    except (ValueError, AttributeError):
        pass

    for trace in fig.data:
        try:
            if getattr(trace, "textfont", None) is not None:
                trace.update(textfont=font_dict)
        except (AttributeError, TypeError, ValueError):
            continue

    return fig


def load_session_data(st) -> Dict:
    if "data" not in st.session_state:
        return None
    return st.session_state["data"]


def save_session_data(st, data: Dict):
    st.session_state["data"] = data


def check_data_loaded(st) -> bool:
    if "data" not in st.session_state or st.session_state["data"] is None:
        st.warning("⚠️ 请先在【数据导入】页上传或生成数据")
        return False
    return True


def format_number(num: float, decimals: int = 2) -> str:
    if pd.isna(num) or num is None:
        return "-"
    return f"{num:,.{decimals}f}"


def get_severity_color(severity: str) -> str:
    colors = {
        "高": "#ff4b4b",
        "中": "#ffaa00",
        "低": "#2ecc71",
    }
    return colors.get(severity, "#999999")


def get_severity_emoji(severity: str) -> str:
    emojis = {
        "高": "🔴",
        "中": "🟡",
        "低": "🟢",
    }
    return emojis.get(severity, "⚪")


def export_to_excel(data_frames: Dict[str, pd.DataFrame]) -> bytes:
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        for sheet_name, df in data_frames.items():
            df.to_excel(writer, sheet_name=sheet_name, index=False)
    output.seek(0)
    return output.getvalue()


def generate_energy_saving_report(anomaly_df: pd.DataFrame, kpis: Dict) -> str:
    report = []
    report.append("=" * 60)
    report.append("                工厂能耗分析异常报告")
    report.append("=" * 60)
    report.append("")

    report.append("一、关键指标概览")
    report.append("-" * 40)
    report.append(f"  总耗电量:       {format_number(kpis['total_power_kwh'])} kWh")
    report.append(f"  总产量:         {format_number(kpis['total_output'])} 单位")
    report.append(f"  单位产量能耗:   {format_number(kpis['unit_ec_kwh_per_unit'], 4)} kWh/单位")
    report.append(f"  空载电耗:       {format_number(kpis['idle_power_kwh'])} kWh ({kpis['idle_ratio']:.2f}%)")
    report.append(f"  平均开机率:     {kpis['avg_running_rate']:.2f}%")
    report.append(f"  数据完整率:     {kpis['data_completeness']:.2f}%")
    report.append("")

    report.append("二、异常检测汇总")
    report.append("-" * 40)

    if anomaly_df.empty:
        report.append("  ✅ 未检测到异常")
    else:
        report.append(f"  异常总数: {len(anomaly_df)} 项")
        report.append("")

        severity_counts = anomaly_df.groupby("severity").size()
        report.append("  按严重程度:")
        for sev in ["高", "中", "低"]:
            count = severity_counts.get(sev, 0)
            report.append(f"    {get_severity_emoji(sev)} {sev}度异常: {count} 项")
        report.append("")

        type_counts = anomaly_df.groupby("anomaly_name").size().sort_values(ascending=False)
        report.append("  按异常类型:")
        for type_name, count in type_counts.items():
            report.append(f"    • {type_name}: {count} 项")
        report.append("")

        team_counts = anomaly_df.groupby("team").size().sort_values(ascending=False)
        report.append("  按班组分布:")
        for team, count in team_counts.items():
            report.append(f"    • {team}: {count} 项")
        report.append("")

        report.append("三、异常明细")
        report.append("-" * 40)

        for idx, row in anomaly_df.head(20).iterrows():
            report.append(f"  {get_severity_emoji(row['severity'])} [{row['severity']}] {row['anomaly_name']}")
            report.append(f"      时间: {row['timestamp']}")
            report.append(f"      产线: {row['production_line']} | 班组: {row['team']} | 班次: {row['shift']}")
            report.append(f"      证据: {row['evidence']}")
            report.append(f"      归因: {row['description']}")
            report.append("")

        if len(anomaly_df) > 20:
            report.append(f"  ... 还有 {len(anomaly_df) - 20} 条异常记录请查看完整清单")
            report.append("")

    report.append("四、节能建议汇总")
    report.append("-" * 40)

    suggestions = set()
    if not anomaly_df.empty:
        for _, row in anomaly_df.iterrows():
            if isinstance(row["suggestions"], list):
                for s in row["suggestions"]:
                    suggestions.add(s)

    suggestions.add("建立定期能耗分析会议机制，持续追踪改进效果")
    suggestions.add("开展班组能耗绩效考核，激励节能行为")
    suggestions.add("引入实时能耗监控预警系统，及时发现异常")

    for i, s in enumerate(sorted(suggestions), 1):
        report.append(f"  {i}. {s}")

    report.append("")
    report.append("=" * 60)
    report.append(f"                      报告生成时间: {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report.append("=" * 60)

    return "\n".join(report)


def parse_uploaded_file(uploaded_file) -> Optional[pd.DataFrame]:
    try:
        if uploaded_file.name.endswith(".csv"):
            df = pd.read_csv(uploaded_file)
        elif uploaded_file.name.endswith(".xlsx") or uploaded_file.name.endswith(".xls"):
            df = pd.read_excel(uploaded_file)
        else:
            return None

        if "timestamp" in df.columns:
            df["timestamp"] = pd.to_datetime(df["timestamp"])
        if "date" in df.columns:
            df["date"] = pd.to_datetime(df["date"]).dt.date

        return df
    except Exception as e:
        return None


def validate_data(data: Dict) -> Dict:
    issues = []

    if "meter" not in data or data["meter"].empty:
        issues.append("电表数据为空")
    else:
        meter = data["meter"]
        required_cols = ["timestamp", "production_line", "power_kw", "is_running"]
        for col in required_cols:
            if col not in meter.columns:
                issues.append(f"电表数据缺少必需列: {col}")

        if "power_kw" in meter.columns:
            missing_pct = meter["power_kw"].isna().mean() * 100
            if missing_pct > 10:
                issues.append(f"电表数据缺失率过高: {missing_pct:.1f}%")

    if "production" not in data or data["production"].empty:
        issues.append("产量数据为空")
    else:
        prod = data["production"]
        required_cols = ["date", "production_line", "power_consumption_kwh", "output_quantity"]
        for col in required_cols:
            if col not in prod.columns:
                issues.append(f"产量数据缺少必需列: {col}")

    return {
        "is_valid": len(issues) == 0,
        "issues": issues,
    }
