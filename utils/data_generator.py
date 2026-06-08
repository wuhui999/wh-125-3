import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta

PRODUCTION_LINES = ["产线A", "产线B", "产线C", "产线D"]
TEAMS = ["甲班", "乙班", "丙班", "丁班"]
SHIFTS = ["早班(08:00-16:00)", "中班(16:00-24:00)", "晚班(00:00-08:00)"]

TEAM_EFFICIENCY = {
    "甲班": 0.95,
    "乙班": 1.0,
    "丙班": 1.08,
    "丁班": 1.15,
}

EQUIPMENT_BASE_LOAD = {
    "产线A": 80,
    "产线B": 120,
    "产线C": 90,
    "产线D": 150,
}

PEAK_HOURS = list(range(8, 12)) + list(range(17, 21))
VALLEY_HOURS = list(range(0, 6))
FLAT_HOURS = [h for h in range(24) if h not in PEAK_HOURS and h not in VALLEY_HOURS]


def generate_date_range(days: int = 30, freq: str = "15min") -> pd.DatetimeIndex:
    end_date = datetime.now().replace(minute=0, second=0, microsecond=0)
    start_date = end_date - timedelta(days=days)
    return pd.date_range(start=start_date, end=end_date, freq=freq)


def generate_meter_data(days: int = 30, freq: str = "15min") -> pd.DataFrame:
    timestamps = generate_date_range(days, freq)
    data = []

    for ts in timestamps:
        hour = ts.hour
        is_weekend = ts.weekday() >= 5

        for line in PRODUCTION_LINES:
            base_load = EQUIPMENT_BASE_LOAD[line]
            team_idx = (ts.dayofyear + (hour // 8)) % len(TEAMS)
            team = TEAMS[team_idx]
            efficiency = TEAM_EFFICIENCY[team]

            if is_weekend and hour not in [8, 9, 10, 11, 12, 13, 14, 15, 16, 17]:
                power = base_load * 0.1 * np.random.uniform(0.9, 1.1)
                running = 0
            else:
                running = 1
                production_factor = 1.0
                if hour in PEAK_HOURS:
                    production_factor *= 1.1
                elif hour in VALLEY_HOURS:
                    production_factor *= 0.85

                power = base_load * efficiency * production_factor * np.random.uniform(0.92, 1.08)

            if np.random.random() < 0.02:
                power = base_load * 0.05
                running = 0

            if np.random.random() < 0.015:
                power = base_load * 1.8
                running = 0

            if np.random.random() < 0.01:
                power = base_load * 1.5 * efficiency
                running = 1

            data.append({
                "timestamp": ts,
                "production_line": line,
                "team": team,
                "shift": SHIFTS[hour // 8],
                "power_kw": round(power, 2),
                "is_running": running,
                "hour": hour,
                "is_peak": 1 if hour in PEAK_HOURS else 0,
                "is_valley": 1 if hour in VALLEY_HOURS else 0,
                "is_flat": 1 if hour in FLAT_HOURS else 0,
            })

    df = pd.DataFrame(data)

    missing_idx = np.random.choice(len(df), size=int(len(df) * 0.005), replace=False)
    df.loc[missing_idx, "power_kw"] = np.nan

    return df


def generate_production_data(meter_df: pd.DataFrame) -> pd.DataFrame:
    daily_data = meter_df.copy()
    daily_data["date"] = daily_data["timestamp"].dt.date

    grouped = daily_data.groupby(["date", "production_line", "team", "shift"]).agg(
        total_power=("power_kw", lambda x: (x.sum() * 0.25)),
        running_hours=("is_running", lambda x: (x.sum() * 0.25)),
    ).reset_index()

    production_records = []
    for _, row in grouped.iterrows():
        line = row["production_line"]
        base_yield = {
            "产线A": 500,
            "产线B": 800,
            "产线C": 600,
            "产线D": 1000,
        }[line]

        efficiency = TEAM_EFFICIENCY[row["team"]]
        running_factor = min(row["running_hours"] / 8, 1.0) if row["running_hours"] > 0 else 0

        expected_yield = base_yield * efficiency * running_factor
        actual_yield = expected_yield * np.random.uniform(0.85, 1.15)

        if np.random.random() < 0.03:
            actual_yield = expected_yield * 0.3

        production_records.append({
            "date": row["date"],
            "production_line": line,
            "team": row["team"],
            "shift": row["shift"],
            "running_hours": round(row["running_hours"], 2),
            "power_consumption_kwh": round(row["total_power"], 2),
            "output_quantity": round(actual_yield, 1),
            "unit_energy_consumption": round(row["total_power"] / actual_yield, 4) if actual_yield > 0 else np.nan,
        })

    return pd.DataFrame(production_records)


def generate_team_schedule(days: int = 30) -> pd.DataFrame:
    end_date = datetime.now().date()
    start_date = end_date - timedelta(days=days)
    date_range = pd.date_range(start=start_date, end=end_date, freq="D")

    schedule = []
    for d in date_range:
        for shift_idx, shift in enumerate(SHIFTS):
            teams_for_shift = np.roll(TEAMS, shift_idx + d.dayofyear)
            for i, line in enumerate(PRODUCTION_LINES):
                schedule.append({
                    "date": d.date(),
                    "production_line": line,
                    "shift": shift,
                    "team": teams_for_shift[i % len(TEAMS)],
                    "team_leader": f"{teams_for_shift[i % len(TEAMS)]}组长{np.random.randint(1, 4)}",
                    "operators_count": np.random.randint(4, 8),
                })

    return pd.DataFrame(schedule)


def generate_equipment_status(meter_df: pd.DataFrame) -> pd.DataFrame:
    status_changes = []
    for line in PRODUCTION_LINES:
        line_data = meter_df[meter_df["production_line"] == line].sort_values("timestamp")

        current_status = None
        for _, row in line_data.iterrows():
            status = "运行" if row["is_running"] == 1 else "停机"
            if status != current_status:
                status_changes.append({
                    "timestamp": row["timestamp"],
                    "production_line": line,
                    "status": status,
                    "power_kw": row["power_kw"],
                    "team": row["team"],
                    "shift": row["shift"],
                })
                current_status = status

    return pd.DataFrame(status_changes)


def generate_all_data(days: int = 30, freq: str = "15min") -> dict:
    meter_df = generate_meter_data(days=days, freq=freq)
    production_df = generate_production_data(meter_df)
    schedule_df = generate_team_schedule(days=days)
    equipment_df = generate_equipment_status(meter_df)

    return {
        "meter": meter_df,
        "production": production_df,
        "schedule": schedule_df,
        "equipment": equipment_df,
    }


if __name__ == "__main__":
    data = generate_all_data(days=7)
    for k, v in data.items():
        print(f"\n{k}:")
        print(v.head())
        print(f"Shape: {v.shape}")
