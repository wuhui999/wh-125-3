import pandas as pd
import numpy as np
from typing import List, Dict
from datetime import timedelta


ANOMALY_TYPES = {
    "idle_high_power": {
        "name": "停机高耗电",
        "severity": "高",
        "description": "设备已停机但仍消耗大量电力",
        "suggestions": [
            "检查设备是否完全断电",
            "排查待机设备是否未关闭",
            "检查辅助设备（空压机、空调等）",
            "核实设备状态传感器是否正常",
        ],
    },
    "low_output_high_power": {
        "name": "低产高耗电",
        "severity": "中",
        "description": "产量极低但电耗异常高",
        "suggestions": [
            "检查班组操作规范",
            "排查设备故障导致效率下降",
            "核实产量统计是否准确",
            "检查是否存在空载运行时间过长",
        ],
    },
    "power_fluctuation": {
        "name": "电耗同比波动",
        "severity": "中",
        "description": "电耗较同期显著异常",
        "suggestions": [
            "对比同期生产计划差异",
            "检查设备维护保养记录",
            "核实工艺参数是否变更",
            "分析班组人员配置差异",
        ],
    },
    "missing_data": {
        "name": "数据缺失",
        "severity": "低",
        "description": "电表数据存在缺失记录",
        "suggestions": [
            "检查电表通信是否正常",
            "核实数据采集系统运行状态",
            "排查网络连接问题",
            "联系IT部门检查数据存储",
        ],
    },
    "high_idle_ratio": {
        "name": "空载耗电过高",
        "severity": "中",
        "description": "空载电耗占比超过阈值",
        "suggestions": [
            "优化生产计划，减少待机时间",
            "实施设备停机时的断电管理",
            "建立设备待机能耗标准",
            "加强班组节电意识培训",
        ],
    },
    "peak_usage_abnormal": {
        "name": "峰段用电异常",
        "severity": "中",
        "description": "高峰时段用电占比过高",
        "suggestions": [
            "优化生产排班，错峰用电",
            "将可调整工序转移至谷段",
            "检查是否存在非必要峰段用电",
            "评估储能设备配置需求",
        ],
    },
    "uec_abnormal": {
        "name": "单位能耗异常",
        "severity": "高",
        "description": "单位产量能耗显著偏离基准",
        "suggestions": [
            "检查班组操作流程规范性",
            "排查设备运行状态",
            "核实原材料质量波动",
            "分析工艺参数稳定性",
            "与优秀班组开展对标学习",
        ],
    },
}


def detect_idle_high_power(meter_df: pd.DataFrame, threshold_ratio: float = 0.5) -> List[Dict]:
    anomalies = []
    df = meter_df.copy()
    df = df[df["is_running"] == 0]

    base_loads = df.groupby("production_line")["power_kw"].quantile(0.05)

    for line in base_loads.index:
        base_load = base_loads[line]
        threshold = base_load * threshold_ratio

        line_df = df[(df["production_line"] == line) & (df["power_kw"] > threshold)]

        for _, row in line_df.iterrows():
            if pd.isna(row["power_kw"]):
                continue
            anomalies.append({
                "anomaly_type": "idle_high_power",
                "anomaly_name": ANOMALY_TYPES["idle_high_power"]["name"],
                "severity": ANOMALY_TYPES["idle_high_power"]["severity"],
                "timestamp": row["timestamp"],
                "production_line": line,
                "team": row["team"],
                "shift": row["shift"],
                "evidence": f"设备停机时功率 {row['power_kw']:.2f} kW，超过基准值 {base_load:.2f} kW的 {threshold_ratio*100:.0f}%",
                "power_kw": row["power_kw"],
                "baseline": base_load,
                "deviation_ratio": (row["power_kw"] - base_load) / base_load * 100 if base_load > 0 else 0,
                "suggestions": ANOMALY_TYPES["idle_high_power"]["suggestions"],
                "description": ANOMALY_TYPES["idle_high_power"]["description"],
            })

    return anomalies


def detect_low_output_high_power(production_df: pd.DataFrame, cv_threshold: float = 50) -> List[Dict]:
    anomalies = []
    df = production_df.copy()
    df = df[df["output_quantity"] > 0]

    for line in df["production_line"].unique():
        line_df = df[df["production_line"] == line]
        uec_mean = line_df["unit_energy_consumption"].mean()
        uec_std = line_df["unit_energy_consumption"].std()
        threshold = uec_mean + 2 * uec_std

        high_uec = line_df[line_df["unit_energy_consumption"] > threshold]

        for _, row in high_uec.iterrows():
            anomalies.append({
                "anomaly_type": "low_output_high_power",
                "anomaly_name": ANOMALY_TYPES["low_output_high_power"]["name"],
                "severity": ANOMALY_TYPES["low_output_high_power"]["severity"],
                "timestamp": pd.Timestamp(row["date"]),
                "production_line": line,
                "team": row["team"],
                "shift": row["shift"],
                "evidence": f"产量 {row['output_quantity']:.1f}，单位能耗 {row['unit_energy_consumption']:.4f} kWh/单位，超过基准值 {uec_mean:.4f} 的2σ阈值",
                "unit_ec": row["unit_energy_consumption"],
                "baseline": uec_mean,
                "output_quantity": row["output_quantity"],
                "power_consumption": row["power_consumption_kwh"],
                "deviation_ratio": (row["unit_energy_consumption"] - uec_mean) / uec_mean * 100 if uec_mean > 0 else 0,
                "suggestions": ANOMALY_TYPES["low_output_high_power"]["suggestions"],
                "description": ANOMALY_TYPES["low_output_high_power"]["description"],
            })

    return anomalies


def detect_power_fluctuation(meter_df: pd.DataFrame, threshold: float = 30) -> List[Dict]:
    anomalies = []
    df = meter_df.copy()
    df["date"] = df["timestamp"].dt.date
    df["hour"] = df["timestamp"].dt.hour
    df["power_kwh"] = df["power_kw"] * 0.25

    daily_hourly = df.groupby(["production_line", "date", "hour"])["power_kwh"].sum().reset_index()

    for line in daily_hourly["production_line"].unique():
        line_df = daily_hourly[daily_hourly["production_line"] == line]

        for hour in range(24):
            hour_df = line_df[line_df["hour"] == hour].sort_values("date")
            if len(hour_df) < 3:
                continue

            for i in range(1, len(hour_df)):
                current = hour_df.iloc[i]
                prev_values = hour_df.iloc[max(0, i-7):i]["power_kwh"]
                prev_mean = prev_values.mean()

                if prev_mean == 0 or pd.isna(current["power_kwh"]):
                    continue

                deviation = abs(current["power_kwh"] - prev_mean) / prev_mean * 100

                if deviation > threshold:
                    row_data = df[(df["production_line"] == line) &
                                  (df["date"] == current["date"]) &
                                  (df["hour"] == hour)].iloc[0]

                    anomalies.append({
                        "anomaly_type": "power_fluctuation",
                        "anomaly_name": ANOMALY_TYPES["power_fluctuation"]["name"],
                        "severity": ANOMALY_TYPES["power_fluctuation"]["severity"],
                        "timestamp": pd.Timestamp(current["date"]) + pd.Timedelta(hours=hour),
                        "production_line": line,
                        "team": row_data["team"],
                        "shift": row_data["shift"],
                        "evidence": f"时段电耗 {current['power_kwh']:.2f} kWh，较近7日均值 {prev_mean:.2f} kWh 波动 {deviation:.1f}%，超过阈值 {threshold}%",
                        "current_power": current["power_kwh"],
                        "baseline": prev_mean,
                        "deviation_ratio": deviation,
                        "suggestions": ANOMALY_TYPES["power_fluctuation"]["suggestions"],
                        "description": ANOMALY_TYPES["power_fluctuation"]["description"],
                    })

    return anomalies


def detect_missing_data(meter_df: pd.DataFrame) -> List[Dict]:
    anomalies = []
    df = meter_df.copy()

    missing_mask = df["power_kw"].isna()
    missing_rows = df[missing_mask]

    for _, row in missing_rows.iterrows():
        anomalies.append({
            "anomaly_type": "missing_data",
            "anomaly_name": ANOMALY_TYPES["missing_data"]["name"],
            "severity": ANOMALY_TYPES["missing_data"]["severity"],
            "timestamp": row["timestamp"],
            "production_line": row["production_line"],
            "team": row["team"],
            "shift": row["shift"],
            "evidence": f"该时间点电表数据缺失",
            "suggestions": ANOMALY_TYPES["missing_data"]["suggestions"],
            "description": ANOMALY_TYPES["missing_data"]["description"],
        })

    return anomalies


def detect_high_idle_ratio(meter_df: pd.DataFrame, threshold: float = 10) -> List[Dict]:
    anomalies = []
    df = meter_df.copy()
    df["date"] = df["timestamp"].dt.date
    df["power_kwh"] = df["power_kw"] * 0.25
    df["idle_power_kwh"] = np.where(
        (df["is_running"] == 0) & (df["power_kw"] > 0),
        df["power_kwh"],
        0
    )

    daily = df.groupby(["date", "production_line"]).agg(
        total_power=("power_kwh", "sum"),
        idle_power=("idle_power_kwh", "sum"),
    ).reset_index()

    daily["idle_ratio"] = np.where(
        daily["total_power"] > 0,
        daily["idle_power"] / daily["total_power"] * 100,
        0
    )

    high_idle = daily[daily["idle_ratio"] > threshold]

    for _, row in high_idle.iterrows():
        row_data = df[(df["production_line"] == row["production_line"]) & (df["date"] == row["date"])].iloc[0]
        anomalies.append({
            "anomaly_type": "high_idle_ratio",
            "anomaly_name": ANOMALY_TYPES["high_idle_ratio"]["name"],
            "severity": ANOMALY_TYPES["high_idle_ratio"]["severity"],
            "timestamp": pd.Timestamp(row["date"]),
            "production_line": row["production_line"],
            "team": row_data["team"],
            "shift": row_data["shift"],
            "evidence": f"空载电耗 {row['idle_power']:.2f} kWh，占比 {row['idle_ratio']:.1f}%，超过阈值 {threshold}%",
            "idle_power": row["idle_power"],
            "total_power": row["total_power"],
            "idle_ratio": row["idle_ratio"],
            "deviation_ratio": row["idle_ratio"] - threshold,
            "suggestions": ANOMALY_TYPES["high_idle_ratio"]["suggestions"],
            "description": ANOMALY_TYPES["high_idle_ratio"]["description"],
        })

    return anomalies


def detect_uec_abnormal(production_df: pd.DataFrame) -> List[Dict]:
    anomalies = []
    df = production_df.copy()
    df = df[df["output_quantity"] > 0]

    for line in df["production_line"].unique():
        line_df = df[df["production_line"] == line]

        for team in line_df["team"].unique():
            team_df = line_df[line_df["team"] == team]
            other_teams_df = line_df[line_df["team"] != team]

            if len(team_df) < 3 or len(other_teams_df) < 3:
                continue

            team_uec_mean = team_df["unit_energy_consumption"].mean()
            other_uec_mean = other_teams_df["unit_energy_consumption"].mean()

            if other_uec_mean == 0:
                continue

            diff_ratio = (team_uec_mean - other_uec_mean) / other_uec_mean * 100

            if diff_ratio > 15:
                latest_record = team_df.iloc[-1]
                anomalies.append({
                    "anomaly_type": "uec_abnormal",
                    "anomaly_name": ANOMALY_TYPES["uec_abnormal"]["name"],
                    "severity": ANOMALY_TYPES["uec_abnormal"]["severity"],
                    "timestamp": pd.Timestamp(latest_record["date"]),
                    "production_line": line,
                    "team": team,
                    "shift": latest_record["shift"],
                    "evidence": f"{team}单位能耗均值 {team_uec_mean:.4f} kWh/单位，较其他班组均值 {other_uec_mean:.4f} 高出 {diff_ratio:.1f}%",
                    "team_uec": team_uec_mean,
                    "baseline_uec": other_uec_mean,
                    "deviation_ratio": diff_ratio,
                    "suggestions": ANOMALY_TYPES["uec_abnormal"]["suggestions"],
                    "description": ANOMALY_TYPES["uec_abnormal"]["description"],
                })

    return anomalies


def detect_peak_usage_abnormal(meter_df: pd.DataFrame, threshold_ratio: float = 0.5) -> List[Dict]:
    anomalies = []
    df = meter_df.copy()
    df["date"] = df["timestamp"].dt.date
    df["power_kwh"] = df["power_kw"] * 0.25

    daily = df.groupby(["date", "production_line"]).agg(
        total_power=("power_kwh", "sum"),
        peak_power=("power_kwh", lambda x: x[df.loc[x.index, "is_peak"] == 1].sum()),
    ).reset_index()

    daily["peak_ratio"] = np.where(
        daily["total_power"] > 0,
        daily["peak_power"] / daily["total_power"],
        0
    )

    high_peak = daily[daily["peak_ratio"] > threshold_ratio]

    for _, row in high_peak.iterrows():
        row_data = df[(df["production_line"] == row["production_line"]) & (df["date"] == row["date"])].iloc[0]
        anomalies.append({
            "anomaly_type": "peak_usage_abnormal",
            "anomaly_name": ANOMALY_TYPES["peak_usage_abnormal"]["name"],
            "severity": ANOMALY_TYPES["peak_usage_abnormal"]["severity"],
            "timestamp": pd.Timestamp(row["date"]),
            "production_line": row["production_line"],
            "team": row_data["team"],
            "shift": row_data["shift"],
            "evidence": f"峰段用电 {row['peak_power']:.2f} kWh，占比 {row['peak_ratio']*100:.1f}%，超过阈值 {threshold_ratio*100:.0f}%",
            "peak_power": row["peak_power"],
            "total_power": row["total_power"],
            "peak_ratio": row["peak_ratio"] * 100,
            "deviation_ratio": (row["peak_ratio"] - threshold_ratio) * 100,
            "suggestions": ANOMALY_TYPES["peak_usage_abnormal"]["suggestions"],
            "description": ANOMALY_TYPES["peak_usage_abnormal"]["description"],
        })

    return anomalies


def detect_all_anomalies(meter_df: pd.DataFrame, production_df: pd.DataFrame) -> pd.DataFrame:
    all_anomalies = []

    all_anomalies.extend(detect_idle_high_power(meter_df))
    all_anomalies.extend(detect_low_output_high_power(production_df))
    all_anomalies.extend(detect_power_fluctuation(meter_df))
    all_anomalies.extend(detect_missing_data(meter_df))
    all_anomalies.extend(detect_high_idle_ratio(meter_df))
    all_anomalies.extend(detect_uec_abnormal(production_df))
    all_anomalies.extend(detect_peak_usage_abnormal(meter_df))

    if not all_anomalies:
        return pd.DataFrame()

    df = pd.DataFrame(all_anomalies)

    severity_order = {"高": 0, "中": 1, "低": 2}
    df["severity_order"] = df["severity"].map(severity_order)
    df = df.sort_values(["severity_order", "timestamp"], ascending=[True, False])
    df = df.drop(columns=["severity_order"])
    df = df.reset_index(drop=True)

    return df


def summarize_anomalies(anomaly_df: pd.DataFrame) -> Dict:
    if anomaly_df.empty:
        return {
            "total_count": 0,
            "by_type": {},
            "by_severity": {"高": 0, "中": 0, "低": 0},
            "by_line": {},
            "by_team": {},
        }

    return {
        "total_count": len(anomaly_df),
        "by_type": anomaly_df.groupby("anomaly_name").size().to_dict(),
        "by_severity": anomaly_df.groupby("severity").size().to_dict(),
        "by_line": anomaly_df.groupby("production_line").size().to_dict(),
        "by_team": anomaly_df.groupby("team").size().to_dict(),
    }
