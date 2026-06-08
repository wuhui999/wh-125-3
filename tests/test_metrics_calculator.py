import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
import numpy as np
import pytest
from datetime import datetime, timedelta
from utils.metrics_calculator import calculate_overall_kpis, calculate_peak_valley_ratio


def create_mock_meter_data():
    timestamps = pd.date_range(start='2024-01-01 00:00:00', periods=96, freq='15min')
    data = []
    for i, ts in enumerate(timestamps):
        hour = ts.hour
        is_peak = 1 if (8 <= hour < 12 or 17 <= hour < 21) else 0
        is_valley = 1 if 0 <= hour < 6 else 0
        is_flat = 1 if not is_peak and not is_valley else 0
        is_running = 1 if (6 <= hour < 22) else 0
        power_kw = 100 if is_running else 10

        data.append({
            "timestamp": ts,
            "production_line": "产线A",
            "team": "甲班",
            "shift": "早班(08:00-16:00)" if 8 <= hour < 16 else "中班(16:00-24:00)" if 16 <= hour < 24 else "晚班(00:00-08:00)",
            "power_kw": power_kw,
            "is_running": is_running,
            "hour": hour,
            "is_peak": is_peak,
            "is_valley": is_valley,
            "is_flat": is_flat,
        })
    return pd.DataFrame(data)


def create_mock_production_data():
    dates = pd.date_range(start='2024-01-01', periods=4, freq='D')
    data = []
    for date in dates:
        data.append({
            "date": date,
            "production_line": "产线A",
            "team": "甲班",
            "shift": "早班(08:00-16:00)",
            "output_quantity": 1000,
            "power_consumption_kwh": 500,
            "running_hours": 8,
        })
    return pd.DataFrame(data)


class TestCalculateOverallKpis:

    def test_normal_data_kpi_calculation(self):
        meter_df = create_mock_meter_data()
        production_df = create_mock_production_data()

        result = calculate_overall_kpis(meter_df, production_df)

        expected_power_kwh = (meter_df["power_kw"] * 0.25).sum()
        assert result["total_power_kwh"] == pytest.approx(round(expected_power_kwh, 2))
        assert result["total_output"] == 4000
        assert result["unit_ec_kwh_per_unit"] == pytest.approx(round(expected_power_kwh / 4000, 4))

        idle_mask = (meter_df["is_running"] == 0) & (meter_df["power_kw"] > 0)
        expected_idle_power = (meter_df.loc[idle_mask, "power_kw"] * 0.25).sum()
        assert result["idle_power_kwh"] == pytest.approx(round(expected_idle_power, 2))

        expected_idle_ratio = expected_idle_power / expected_power_kwh * 100 if expected_power_kwh > 0 else 0
        assert result["idle_ratio"] == pytest.approx(round(expected_idle_ratio, 2))

        peak_power = meter_df[meter_df["is_peak"] == 1]["power_kw"].sum() * 0.25
        valley_power = meter_df[meter_df["is_valley"] == 1]["power_kw"].sum() * 0.25
        expected_pv_ratio = peak_power / valley_power * 100 if valley_power > 0 else 0
        assert result["peak_valley_ratio"] == pytest.approx(round(expected_pv_ratio, 2))

        expected_completeness = 100.0
        assert result["data_completeness"] == pytest.approx(expected_completeness)

        expected_running_rate = meter_df["is_running"].mean() * 100
        assert result["avg_running_rate"] == pytest.approx(round(expected_running_rate, 2))

        assert result["meter_records"] == len(meter_df)
        assert result["production_records"] == len(production_df)

    def test_output_quantity_all_zero_unit_ec_handling(self):
        meter_df = create_mock_meter_data()
        production_df = create_mock_production_data()
        production_df["output_quantity"] = 0

        result = calculate_overall_kpis(meter_df, production_df)

        assert result["total_output"] == 0
        assert result["unit_ec_kwh_per_unit"] == 0

    def test_power_kw_missing_values_data_completeness(self):
        meter_df = create_mock_meter_data()
        production_df = create_mock_production_data()

        missing_count = 10
        meter_df.loc[:missing_count - 1, "power_kw"] = np.nan

        result = calculate_overall_kpis(meter_df, production_df)

        expected_completeness = (1 - missing_count / len(meter_df)) * 100
        assert result["data_completeness"] == pytest.approx(round(expected_completeness, 2))

    def test_all_power_kw_missing(self):
        meter_df = create_mock_meter_data()
        production_df = create_mock_production_data()
        meter_df["power_kw"] = np.nan

        result = calculate_overall_kpis(meter_df, production_df)

        assert result["data_completeness"] == pytest.approx(0.0)
        assert result["total_power_kwh"] == 0
        assert result["idle_power_kwh"] == 0
        assert result["peak_power_kwh"] == 0
        assert result["valley_power_kwh"] == 0

    def test_empty_meter_data(self):
        meter_df = pd.DataFrame(columns=[
            "timestamp", "production_line", "team", "shift",
            "power_kw", "is_running", "hour", "is_peak", "is_valley", "is_flat"
        ])
        production_df = create_mock_production_data()

        result = calculate_overall_kpis(meter_df, production_df)

        assert result["data_completeness"] == 100
        assert result["meter_records"] == 0
        assert result["total_power_kwh"] == 0
        assert result["avg_running_rate"] == pytest.approx(0.0)


class TestCalculatePeakValleyRatio:

    def test_normal_data_ratio_calculation(self):
        meter_df = create_mock_meter_data()

        df, ratios = calculate_peak_valley_ratio(meter_df)

        assert "power_kwh" in df.columns

        peak_power = df[df["is_peak"] == 1]["power_kwh"].sum()
        valley_power = df[df["is_valley"] == 1]["power_kwh"].sum()
        flat_power = df[df["is_flat"] == 1]["power_kwh"].sum()
        total_power = peak_power + valley_power + flat_power

        assert ratios["peak_power_kwh"] == pytest.approx(round(peak_power, 2))
        assert ratios["valley_power_kwh"] == pytest.approx(round(valley_power, 2))
        assert ratios["flat_power_kwh"] == pytest.approx(round(flat_power, 2))
        assert ratios["total_power_kwh"] == pytest.approx(round(total_power, 2))

        expected_peak_ratio = peak_power / total_power * 100
        expected_valley_ratio = valley_power / total_power * 100
        expected_flat_ratio = flat_power / total_power * 100

        assert ratios["peak_ratio"] == pytest.approx(round(expected_peak_ratio, 2))
        assert ratios["valley_ratio"] == pytest.approx(round(expected_valley_ratio, 2))
        assert ratios["flat_ratio"] == pytest.approx(round(expected_flat_ratio, 2))

    def test_ratio_sum_to_100_percent(self):
        meter_df = create_mock_meter_data()

        _, ratios = calculate_peak_valley_ratio(meter_df)

        ratio_sum = ratios["peak_ratio"] + ratios["valley_ratio"] + ratios["flat_ratio"]
        assert ratio_sum == pytest.approx(100.0, abs=0.01)

    def test_zero_total_power_ratios(self):
        meter_df = create_mock_meter_data()
        meter_df["power_kw"] = 0

        _, ratios = calculate_peak_valley_ratio(meter_df)

        assert ratios["total_power_kwh"] == 0
        assert ratios["peak_ratio"] == 0
        assert ratios["valley_ratio"] == 0
        assert ratios["flat_ratio"] == 0
        assert ratios["peak_power_kwh"] == 0
        assert ratios["valley_power_kwh"] == 0
        assert ratios["flat_power_kwh"] == 0

    def test_ratio_sum_to_100_with_missing_values(self):
        meter_df = create_mock_meter_data()
        meter_df.loc[:5, "power_kw"] = np.nan

        _, ratios = calculate_peak_valley_ratio(meter_df)

        ratio_sum = ratios["peak_ratio"] + ratios["valley_ratio"] + ratios["flat_ratio"]
        assert ratio_sum == pytest.approx(100.0, abs=0.01)

    def test_single_period_all_types(self):
        data = []
        base_time = datetime(2024, 1, 1, 0, 0, 0)
        for i in range(24):
            ts = base_time + timedelta(hours=i)
            hour = ts.hour
            is_peak = 1 if (8 <= hour < 12 or 17 <= hour < 21) else 0
            is_valley = 1 if 0 <= hour < 6 else 0
            is_flat = 1 if not is_peak and not is_valley else 0

            data.append({
                "timestamp": ts,
                "production_line": "产线A",
                "team": "甲班",
                "shift": "早班(08:00-16:00)",
                "power_kw": 100,
                "is_running": 1,
                "hour": hour,
                "is_peak": is_peak,
                "is_valley": is_valley,
                "is_flat": is_flat,
            })
        meter_df = pd.DataFrame(data)

        _, ratios = calculate_peak_valley_ratio(meter_df)

        ratio_sum = ratios["peak_ratio"] + ratios["valley_ratio"] + ratios["flat_ratio"]
        assert ratio_sum == pytest.approx(100.0, abs=0.01)

        expected_peak_hours = 8
        expected_valley_hours = 6
        expected_flat_hours = 10

        assert ratios["peak_ratio"] == pytest.approx(expected_peak_hours / 24 * 100, abs=0.01)
        assert ratios["valley_ratio"] == pytest.approx(expected_valley_hours / 24 * 100, abs=0.01)
        assert ratios["flat_ratio"] == pytest.approx(expected_flat_hours / 24 * 100, abs=0.01)
