"""
find maximum airspeed- critical mission leg depending on average ground speed assumption and wind speed
"""

from __future__ import annotations
import sys
import importlib
from typing import Any


def _load(name: str):
    if name in sys.modules:
        return importlib.reload(sys.modules[name])
    return importlib.import_module(name)

def find_max_airspeed(
    mission_plan_path: str,
    start_year:int,
    start_month:int,
    start_date:int,
    start_hour:int,
    start_minute:int,
    timestep_s:float = 1200.0,
):
    GS_mod = _load("ground_speed")
    gs_out =GS_mod.run_model({})
    ground_speed_ms = float(gs_out["ground_speed_ms"])
    traj_mod = _load("airship_trajectory")
    traj_out = traj_mod.run_model({
        "excel_path":mission_plan_path,
        "sheet_name":"Waypoints",
        "avg_speed_ms":ground_speed_ms,
        "start_year":start_year,
        "start_month":start_month,
        "start_day":start_date,
        "start_hour":start_hour,
        "start_minute":start_minute,
        "timestep_minutes": timestep_s / 60.0,
    })

    latitudes = list(traj_out["latitudes"])
    longitudes= list(traj_out["longitudes"])
    n_points= int(traj_out["n_points"])

    wind_mod   = _load("wind_data")
    wvect_mod  = _load("Wind_Vector_Module")
    import math
    def _bearing(lat1_deg, lon1_deg, lat2_deg, lon2_deg):
        lat1 = math.radians(lat1_deg)
        lat2= math.radians(lat2_deg)
        dlon =math.radians(lon2_deg - lon1_deg)
        x = math.sin(dlon) * math.cos(lat2)
        y = (math.cos(lat1) * math.sin(lat2)- math.sin(lat1) * math.cos(lat2) * math.cos(dlon))
        bearing = math.degrees(math.atan2(x, y))
        return (bearing + 360.0) % 360.0

    airspeeds:list[float] = []
    wind_speeds:list[float] = []
    wind_dirs:list[float] = []
    headings:list[float] = []

    for i in range(n_points - 1):
        lat0, lon0 = latitudes[i],     longitudes[i]
        lat1, lon1 = latitudes[i + 1], longitudes[i + 1]
        heading = _bearing(lat0, lon0, lat1, lon1)
        headings.append(heading)
        wind_out = wind_mod.run_model({
            "latitude":  lat0,
            "longitude": lon0,
        })
        ws= float(wind_out["wind_speed_mps"])
        wd= float(wind_out["wind_direction_deg"])
        wind_speeds.append(ws)
        wind_dirs.append(wd)
        va_out = wvect_mod.run_model({
            "wind_speed":ws,
            "wind_direction": wd,
            "ground_speed":ground_speed_ms,
            "heading":heading,
        })
        airspeed = float(va_out["airspeed"])
        airspeeds.append(airspeed)

    if not airspeeds:
        raise ValueError("No legs found in trajectory — check mission_plan_path.")

    worst_idx= int(max(range(len(airspeeds)), key=lambda i: airspeeds[i]))
    max_airspeed = airspeeds[worst_idx]

    return {
    "max_airspeed_ms":max_airspeed,
    "worst_leg_index":worst_idx,
    "worst_heading_deg":headings[worst_idx],
    "worst_wind_speed":wind_speeds[worst_idx],
    "worst_wind_dir":wind_dirs[worst_idx],
    "ground_speed_ms":ground_speed_ms,
    "airspeeds_ms":airspeeds,
    "n_legs":len(airspeeds),
    "worst_leg_start_lat":latitudes[worst_idx],
    "worst_leg_start_lon":longitudes[worst_idx],
    "worst_leg_end_lat":latitudes[worst_idx + 1],
    "worst_leg_end_lon":longitudes[worst_idx + 1],
}

if __name__ == "__main__":
    import os

    MISSION_PLAN = os.path.join(
        os.path.dirname(__file__), "..", "mission_plan.xlsx"
    )
    result = find_max_airspeed(
        mission_plan_path=MISSION_PLAN,
        start_year=2024,
        start_month=6,
        start_date=15,
        start_hour=8,
        start_minute=0,
    )

    print("=" * 50)
    print("  MAX AIRSPEED SIZING RESULT")
    print("=" * 50)
    print(f"Ground speed : {result['ground_speed_ms']:.2f} m/s")
    print(f"Number of legs: {result['n_legs']}")
    print(f"Max airspeed: {result['max_airspeed_ms']:.2f} m/s")
    print(f" Worst leg index: {result['worst_leg_index']}")
    print(f"Heading at worst leg: {result['worst_heading_deg']:.1f} deg")
    print(f"Wind speed (worst): {result['worst_wind_speed']:.2f} m/s")
    print(f"Wind direction (worst): {result['worst_wind_dir']:.1f} deg")
    print()
    print(" All leg airspeeds [m/s]:")
    for i, v in enumerate(result["airspeeds_ms"]):
        marker = " ← MAX" if i == result["worst_leg_index"] else ""
        print(f"leg {i:3d}: {v:.3f}{marker}")