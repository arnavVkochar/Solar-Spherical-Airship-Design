import math
import env_Arnesh as env
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import List, Tuple

import pandas as pd
from geographiclib.geodesic import Geodesic

_GEOD = Geodesic.WGS84

DEFAULT_TIMESTEP_MINUTES: int = 5


@dataclass
class Waypoint:
    index:     int
    latitude:  float
    longitude: float


@dataclass
class TrajectoryPoint:
    datetime:          datetime
    lat:               float
    lon:               float
    leg_index:         int
    dist_from_start_m: float
    elapsed_s:         float



def geodesic_distance_m(lat1: float, lon1: float,
                        lat2: float, lon2: float) -> float:
    return _GEOD.Inverse(lat1, lon1, lat2, lon2)['s12']


def geodesic_interpolate(lat1: float, lon1: float,
                         lat2: float, lon2: float,
                         t: float) -> Tuple[float, float]:
    line = _GEOD.InverseLine(lat1, lon1, lat2, lon2)
    pos  = line.Position(t * line.s13)
    return pos['lat2'], pos['lon2']



def load_waypoints(coords: List[Tuple[float, float]]) -> List[Waypoint]:
    if len(coords) < 2:
        raise ValueError("At least 2 waypoints are required.")
    return [Waypoint(index=i, latitude=lat, longitude=lon)
            for i, (lat, lon) in enumerate(coords)]


def build_trajectory(waypoints:        List[Waypoint],
                     avg_speed_ms:     float,
                     start_time:       datetime,
                     timestep_minutes: int = DEFAULT_TIMESTEP_MINUTES,
                     ) -> List[TrajectoryPoint]:
    if avg_speed_ms <= 0:
        raise ValueError("avg_speed_ms must be positive.")
    if len(waypoints) < 2:
        raise ValueError("Need at least 2 waypoints.")

    leg_distances_m: List[float] = []
    for i in range(len(waypoints) - 1):
        wp_a, wp_b = waypoints[i], waypoints[i + 1]
        leg_distances_m.append(
            geodesic_distance_m(wp_a.latitude, wp_a.longitude,
                                wp_b.latitude, wp_b.longitude))

    total_distance_m = sum(leg_distances_m)
    total_duration_s = total_distance_m / avg_speed_ms

    cum_dist_at_leg_start: List[float] = [0.0]
    for d in leg_distances_m[:-1]:
        cum_dist_at_leg_start.append(cum_dist_at_leg_start[-1] + d)

    step_s  = timestep_minutes * 60.0
    n_steps = math.ceil(total_duration_s / step_s)

    eval_seconds: List[float] = [i * step_s for i in range(n_steps + 1)]
    if eval_seconds[-1] > total_duration_s:
        eval_seconds[-1] = total_duration_s
    elif eval_seconds[-1] < total_duration_s:
        eval_seconds.append(total_duration_s)

    trajectory: List[TrajectoryPoint] = []

    for elapsed_s in eval_seconds:
        dist_covered = avg_speed_ms * elapsed_s

        leg_idx = 0
        for k in range(len(leg_distances_m) - 1):
            if dist_covered >= cum_dist_at_leg_start[k + 1]:
                leg_idx = k + 1
            else:
                break

        leg_idx       = min(leg_idx, len(leg_distances_m) - 1)
        leg_len       = leg_distances_m[leg_idx]
        dist_into_leg = dist_covered - cum_dist_at_leg_start[leg_idx]
        t_frac        = max(0.0, min(1.0, (dist_into_leg / leg_len) if leg_len > 0 else 1.0))

        wp_a, wp_b = waypoints[leg_idx], waypoints[leg_idx + 1]
        lat, lon   = geodesic_interpolate(wp_a.latitude, wp_a.longitude,
                                          wp_b.latitude, wp_b.longitude, t_frac)

        trajectory.append(TrajectoryPoint(
            datetime          = start_time + timedelta(seconds=elapsed_s),
            lat               = lat,
            lon               = lon,
            leg_index         = leg_idx,
            dist_from_start_m = dist_covered,
            elapsed_s         = elapsed_s,
        ))

    return trajectory



def run_model(inputs: dict) -> dict:
    
    excel_path       = str(inputs["excel_path"])
    sheet_name       = str(inputs["sheet_name"])
    avg_speed_ms     = float(inputs["avg_speed_ms"])
    start_year       = int(inputs["start_year"])
    start_month      = int(inputs["start_month"])
    start_day        = int(inputs["start_day"])
    start_hour       = int(inputs["start_hour"])
    start_minute     = int(inputs["start_minute"])
    timestep_minutes = int(inputs.get("timestep_minutes", DEFAULT_TIMESTEP_MINUTES))


    df        = pd.read_excel(excel_path, sheet_name=sheet_name)
    waypoints = load_waypoints(list(zip(df["Latitude"], df["Longitude"])))


    start_time = datetime(start_year, start_month, start_day,
                          start_hour, start_minute, tzinfo=timezone.utc)


    points = build_trajectory(
        waypoints        = waypoints,
        avg_speed_ms     = avg_speed_ms,
        start_time       = start_time,
        timestep_minutes = timestep_minutes,
    )

    total_distance_m = sum(
        geodesic_distance_m(waypoints[i].latitude,  waypoints[i].longitude,
                            waypoints[i+1].latitude, waypoints[i+1].longitude)
        for i in range(len(waypoints) - 1)
    )

    latitudes      = [p.lat               for p in points]
    longitudes     = [p.lon               for p in points]
    elapsed_s_list = [p.elapsed_s         for p in points]
    dist_m_list    = [p.dist_from_start_m for p in points]
    leg_idx_list   = [float(p.leg_index)  for p in points]   # float so MATLAB double() works
    timestamps     = [p.datetime.strftime("%Y-%m-%d %H:%M:%S") for p in points]

    return {
        # Per-sample arrays
        "n_points":           len(points),
        "latitudes":          latitudes,
        "longitudes":         longitudes,
        "elapsed_s":          elapsed_s_list,
        "dist_m":             dist_m_list,
        "leg_indices":        leg_idx_list,
        "timestamps_utc":     timestamps,
        # Summary scalars
        "total_distance_km":  total_distance_m / 1000.0,
        "total_duration_min": points[-1].elapsed_s / 60.0,
        "n_waypoints":        len(waypoints),
        "n_legs":             len(waypoints) - 1,
    }



if __name__ == "__main__":
    import sys

    test_input = {
        "excel_path":       env.mission_plan_file_path,
        "sheet_name":       "Waypoints",
        "avg_speed_ms":     30.0,
        "start_year":       2026,
        "start_month":      5,
        "start_day":        5,
        "start_hour":       9,
        "start_minute":     0,
        "timestep_minutes": 5,
    }

    result = run_model(test_input)

    print(f"\nRoute:    {result['n_waypoints']} waypoints, {result['n_legs']} leg(s)")
    print(f"Distance: {result['total_distance_km']:.1f} km")
    print(f"Duration: {result['total_duration_min']:.1f} min")
    print(f"Samples:  {result['n_points']}")
    print()
    print(f"{'#':<5} {'Time (UTC)':<22} {'Latitude':>10} {'Longitude':>11} "
          f"{'Leg':>4} {'Dist (km)':>10}")
    print("─" * 67)

    lats  = result["latitudes"]
    lons  = result["longitudes"]
    times = result["timestamps_utc"]
    dists = result["dist_m"]
    legs  = result["leg_indices"]

    for i in range(result["n_points"]):
        print(f"{i:<5} {times[i]:<22} {lats[i]:>10.5f} {lons[i]:>11.5f} "
              f"{int(legs[i]):>4}   {dists[i]/1000:>8.2f}")