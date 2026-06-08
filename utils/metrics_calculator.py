import pandas as pd
import numpy as np
from typing import Dict, Tuple


def calculate_unit_energy_consumption(production_df: pd.DataFrame) -> pd.DataFrame:
    df = production_df.copy()
    df["unit_energy_consumption"] = np.where(
        df["output_quantity"] > 0,
        df["power_consumption_kwh"] / df["output_quantity"],
        np.nan
    )
    return df


def calculate_idle_power_consumption(meter_df: pd.DataFrame) -> pd.DataFrame:
    df = meter_df.copy()
    df["is_idle"] = (df["is_running"] == 0) & (df["power_kw"] > 0)
    df["idle_power_kw"] = np.where(df["is_idle"], df["power_kw"], 0)
    return df


def calculate_peak_valley_ratio(meter_df: pd.DataFrame) -> Tuple[pd.DataFrame, Dict]:
    df = meter_df.copy()

    df["power_kwh"] = df["power_kw"] * 0.25

    peak_power = df[df["is_peak"] == 1]["power_kwh"].sum()
    valley_power = df[df["is_valley"] == 1]["power_kwh"].sum()
    flat_power = df[df["is_flat"] == 1]["power_kwh"].sum()
    total_power = peak_power + valley_power + flat_power

    if total_power > 0:
        peak_ratio = peak_power / total_power * 100
        valley_ratio = valley_power / total_power * 100
        flat_ratio = flat_power / total_power * 100
    else:
        peak_ratio = valley_ratio = flat_ratio = 0

    ratios = {
        "peak_power_kwh": round(peak_power, 2),
        "valley_power_kwh": round(valley_power, 2),
        "flat_power_kwh": round(flat_power, 2),
        "total_power_kwh": round(total_power, 2),
        "peak_ratio": round(peak_ratio, 2),
        "valley_ratio": round(valley_ratio, 2),
        "flat_ratio": round(flat_ratio, 2),
    }

    return df, ratios


def calculate_daily_metrics(meter_df: pd.DataFrame) -> pd.DataFrame:
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
        running_hours=("is_running", lambda x: (x.sum() * 0.25)),
        idle_power=("idle_power_kwh", "sum"),
        peak_power=("power_kwh", lambda x: x[df.loc[x.index, "is_peak"] == 1].sum()),
        valley_power=("power_kwh", lambda x: x[df.loc[x.index, "is_valley"] == 1].sum()),
    ).reset_index()

    daily["idle_ratio"] = np.where(
        daily["total_power"] > 0,
        daily["idle_power"] / daily["total_power"] * 100,
        0
    )

    return daily


def calculate_team_metrics(production_df: pd.DataFrame) -> pd.DataFrame:
    team_metrics = production_df.groupby(["production_line", "team"]).agg(
        total_power=("power_consumption_kwh", "sum"),
        total_output=("output_quantity", "sum"),
        total_running_hours=("running_hours", "sum"),
        record_count=("date", "count"),
    ).reset_index()

    team_metrics["avg_unit_ec"] = np.where(
        team_metrics["total_output"] > 0,
        team_metrics["total_power"] / team_metrics["total_output"],
        np.nan
    )

    line_baselines = team_metrics.groupby("production_line")["avg_unit_ec"].transform("mean")
    team_metrics["efficiency_vs_baseline"] = np.where(
        line_baselines > 0,
        (line_baselines - team_metrics["avg_unit_ec"]) / line_baselines * 100,
        0
    )
    team_metrics["efficiency_vs_baseline"] = team_metrics["efficiency_vs_baseline"].round(2)

    return team_metrics


def calculate_hourly_distribution(meter_df: pd.DataFrame) -> pd.DataFrame:
    df = meter_df.copy()
    df["power_kwh"] = df["power_kw"] * 0.25
    df["date"] = df["timestamp"].dt.date

    hourly = df.groupby(["production_line", "hour"]).agg(
        avg_power_kw=("power_kw", "mean"),
        total_power_kwh=("power_kwh", "sum"),
        running_rate=("is_running", "mean"),
    ).reset_index()

    hourly["running_rate"] = (hourly["running_rate"] * 100).round(2)
    hourly["avg_power_kw"] = hourly["avg_power_kw"].round(2)
    hourly["total_power_kwh"] = hourly["total_power_kwh"].round(2)

    return hourly


def calculate_overall_kpis(meter_df: pd.DataFrame, production_df: pd.DataFrame) -> Dict:
    meter_df["power_kwh"] = meter_df["power_kw"] * 0.25
    total_power = meter_df["power_kwh"].sum()

    total_output = production_df["output_quantity"].sum()
    unit_ec = total_power / total_output if total_output > 0 else 0

    idle_mask = (meter_df["is_running"] == 0) & (meter_df["power_kw"] > 0)
    idle_power = (meter_df.loc[idle_mask, "power_kw"] * 0.25).sum()
    idle_ratio = idle_power / total_power * 100 if total_power > 0 else 0

    peak_power = meter_df[meter_df["is_peak"] == 1]["power_kwh"].sum()
    valley_power = meter_df[meter_df["is_valley"] == 1]["power_kwh"].sum()
    peak_valley_ratio = peak_power / valley_power * 100 if valley_power > 0 else 0

    missing_count = meter_df["power_kw"].isna().sum()
    data_completeness = (1 - missing_count / len(meter_df)) * 100 if len(meter_df) > 0 else 100

    avg_running_rate = meter_df["is_running"].mean() * 100

    return {
        "total_power_kwh": round(total_power, 2),
        "total_output": round(total_output, 2),
        "unit_ec_kwh_per_unit": round(unit_ec, 4),
        "idle_power_kwh": round(idle_power, 2),
        "idle_ratio": round(idle_ratio, 2),
        "peak_power_kwh": round(peak_power, 2),
        "valley_power_kwh": round(valley_power, 2),
        "peak_valley_ratio": round(peak_valley_ratio, 2),
        "data_completeness": round(data_completeness, 2),
        "avg_running_rate": round(avg_running_rate, 2),
        "meter_records": len(meter_df),
        "production_records": len(production_df),
    }


def calculate_production_correlation(production_df: pd.DataFrame) -> pd.DataFrame:
    df = production_df.copy()
    df = df[df["output_quantity"] > 0]

    corr_data = []
    for line in df["production_line"].unique():
        line_df = df[df["production_line"] == line]
        correlation = line_df["power_consumption_kwh"].corr(line_df["output_quantity"])
        avg_uec = line_df["unit_energy_consumption"].mean()
        std_uec = line_df["unit_energy_consumption"].std()

        corr_data.append({
            "production_line": line,
            "power_output_correlation": round(correlation, 4),
            "avg_unit_ec": round(avg_uec, 4),
            "std_unit_ec": round(std_uec, 4),
            "cv_unit_ec": round(std_uec / avg_uec * 100, 2) if avg_uec > 0 else 0,
        })

    return pd.DataFrame(corr_data)
