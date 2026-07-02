
import re
from dataclasses import dataclass
from typing import List, Tuple

import pandas as pd
from geographiclib.geodesic import Geodesic

import env_Arnesh as env

_GEOD = Geodesic.WGS84


@dataclass
class _Waypoint:
    index:     int
    latitude:  float
    longitude: float


def _geodesic_distance_m(lat1: float, lon1: float,
                         lat2: float, lon2: float) -> float:
    """Geodesic distance [m] between two WGS-84 points."""
    return _GEOD.Inverse(lat1, lon1, lat2, lon2)["s12"]


def _load_waypoints(coords: List[Tuple[float, float]]) -> List[_Waypoint]:
    if len(coords) < 2:
        raise ValueError("At least 2 waypoints are required.")
    return [
        _Waypoint(index=i, latitude=float(lat), longitude=float(lon))
        for i, (lat, lon) in enumerate(coords)
    ]



def run_model(inputs: dict) -> dict:

    df_kbe  = pd.read_excel(env.excel_file_path,       sheet_name="KBE_Input", header=None)
    df_wpts = pd.read_excel(env.mission_plan_file_path, sheet_name="Waypoints")


    data_kbe = {
        str(row[0]).strip(): row[1]
        for _, row in df_kbe.iterrows()
        if pd.notna(row[1])
    }
    raw = data_kbe.get("Mission Duration")
    if raw is None:
        raise KeyError("'Mission Duration' not found in KBE_Input sheet.")
    mission_duration = float(re.sub(r"[^\d.]", "", str(raw)))   # hours

    if mission_duration <= 0:
        raise ValueError(f"mission_duration must be > 0 hours, got {mission_duration}")


    waypoints = _load_waypoints(list(zip(df_wpts["Latitude"], df_wpts["Longitude"])))


    total_distance_m = sum(
        _geodesic_distance_m(
            waypoints[i].latitude,  waypoints[i].longitude,
            waypoints[i + 1].latitude, waypoints[i + 1].longitude,
        )
        for i in range(len(waypoints) - 1)
    )


    mission_duration_s = mission_duration * 3600.0         
    ground_speed_ms    = total_distance_m / mission_duration_s
    ground_speed_kmh   = (total_distance_m / 1000.0) / mission_duration


    return {
        "total_distance_m":  total_distance_m,
        "total_distance_km": total_distance_m / 1000.0,
        "ground_speed_ms":   ground_speed_ms,
        "ground_speed_kmh":  ground_speed_kmh,
        "num_waypoints":     len(waypoints),
    }



if __name__ == "__main__":
    result = run_model({})
    print("\nOutputs:")
    for k, v in result.items():
        print(f"  {k:<22} = {v:.6g}")