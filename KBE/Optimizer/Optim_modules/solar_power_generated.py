

import math
import zoneinfo
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import List, Tuple

#import pvlib
import pandas as pd
from pysolar.solar import get_altitude, get_azimuth


@dataclass
class _TimeStamp:
    """UTC datetime wrapper."""
    dt: datetime

    @classmethod
    def from_parts(cls, year: int, month: int, day: int,
                   hour: int, minute: int, second: int = 0) -> "_TimeStamp":
        return cls(datetime(year, month, day, hour, minute, second,
                            tzinfo=timezone.utc))


@dataclass
class _AirshipState:
    latitude:  float   # deg N
    longitude: float   # deg E
    altitude:  float   # m ASL
    heading:   float   # deg clockwise from North


@dataclass
class _PanelPosition:
    """
    Panel position on the sphere surface (origin = sphere centre).
      x = forward, y = left (port), z = up
    Panel outward normal = unit vector (x, y, z).
    """
    x: float
    y: float
    z: float

    @property
    def outward_normal(self) -> Tuple[float, float, float]:
        mag = math.sqrt(self.x**2 + self.y**2 + self.z**2)
        if mag == 0:
            raise ValueError("Panel at sphere centre — normal undefined.")
        return (self.x / mag, self.y / mag, self.z / mag)


def _sun_direction_enu(airship: _AirshipState,
                       ts: _TimeStamp) -> Tuple[float, float, float]:
    """Sun direction vector in East-North-Up frame."""
    el_deg = get_altitude(airship.latitude, airship.longitude, ts.dt,
                          elevation=airship.altitude)
    az_deg = get_azimuth(airship.latitude, airship.longitude, ts.dt,
                         elevation=airship.altitude)
    # pysolar azimuth is clockwise from North — no offset needed
    el = math.radians(el_deg)
    az = math.radians(az_deg)
    east  = math.cos(el) * math.sin(az)
    north = math.cos(el) * math.cos(az)
    up    = math.sin(el)
    return (east, north, up)


def _enu_to_body(sun_enu: Tuple[float, float, float],
                 heading_deg: float) -> Tuple[float, float, float]:
    """
    Rotate ENU sun vector into airship body frame.
      body-x = forward (heading), body-y = left, body-z = up
    """
    h     = math.radians(heading_deg)
    fwd_e, fwd_n =  math.sin(h),  math.cos(h)
    lft_e, lft_n = -math.cos(h),  math.sin(h)
    east, north, up = sun_enu
    return (
        east * fwd_e + north * fwd_n,   # body x (forward)
        east * lft_e + north * lft_n,   # body y (left)
        up,                              # body z (up, unchanged)
    )


def _solar_incidence(airship: _AirshipState,
                     panel:   _PanelPosition,
                     ts:      _TimeStamp) -> dict:
    """
    Incidence angle between sunlight and panel outward normal.
      0 deg  = sun shines straight into panel (optimal)
      0-90   = panel illuminated
      >=90   = panel facing away from sun → zero power
    """
    sun_enu  = _sun_direction_enu(airship, ts)
    sun_body = _enu_to_body(sun_enu, airship.heading)
    normal   = panel.outward_normal
    dot      = max(-1.0, min(1.0, sum(a * b for a, b in zip(sun_body, normal))))
    angle_deg     = math.degrees(math.acos(dot))
    sun_elevation = math.degrees(math.asin(sun_enu[2]))
    return {
        "incidence_angle_deg": angle_deg,
        "panel_illuminated":   angle_deg < 90.0,
        "sun_elevation_deg":   sun_elevation,
    }



def _calculate_direct_irradiance(latitude: float,
                                 longitude: float,
                                 altitude_m: float,
                                 dt: datetime,
                                 sun_elevation_deg: float = None) -> float:

    # If sun is below horizon → no direct irradiance
    if sun_elevation_deg is None:
        return 0.0

    if sun_elevation_deg <= 0:
        return 0.0

    # Convert elevation to radians
    el = math.radians(sun_elevation_deg)


    airmass = 1.0 / max(math.sin(el), 0.05)


    dni = 730.0 * math.exp(-0.15 * (airmass - 1.0))
    #950
    return max(0.0, dni)


def _generate_ring_layout(num_panels:             int,
                          sp_area:                float,
                          outer_radius:           float,
                          min_ring_fraction:      float,
                          ring_spacing_factor:    float,
                          azimuth_spacing_factor: float) -> List[dict]:

    R    = outer_radius
    side = math.sqrt(sp_area)   # square panel side length

    rings: List[dict] = []
    remaining = num_panels

    # Top cap — one panel at the very top
    rings.append({'ring_radius': 0.0, 'z_height': R, 'count': 1})
    remaining -= 1

    if remaining <= 0:
        return rings

    min_r         = R * min_ring_fraction
    current_polar = math.asin(min_r / R)
    arc_step      = (side * ring_spacing_factor) / R

    while remaining > 0:
        current_radius = R * math.sin(current_polar)
        z              = R * math.cos(current_polar)

        if current_polar >= math.pi / 2:
            current_radius = R
            z              = 0.0
            capacity       = remaining
        else:
            circumference = 2 * math.pi * current_radius
            capacity      = max(1, math.floor(
                circumference / (side * azimuth_spacing_factor)
            ))

        count = min(capacity, remaining)
        rings.append({'ring_radius': current_radius, 'z_height': z, 'count': count})
        remaining     -= count
        current_polar += arc_step

    return rings


def _rings_to_panels(rings: List[dict]) -> List[_PanelPosition]:
    """Convert ring layout to flat list of _PanelPosition objects."""
    panels = []
    for ring in rings:
        r, z, n = ring['ring_radius'], ring['z_height'], ring['count']
        for i in range(n):
            az = (2 * math.pi * i / n) if n > 1 else 0.0
            panels.append(_PanelPosition(
                x = r * math.cos(az),
                y = r * math.sin(az),
                z = z,
            ))
    return panels


def _compute_instantaneous_power(airship, panels, ts, sp_area, sp_efficiency):

    total_power = 0.0
    sun_el = None

    for panel in panels:
        result = _solar_incidence(airship, panel, ts)

        if sun_el is None:
            sun_el = result['sun_elevation_deg']

        irradiance = _calculate_direct_irradiance(
            airship.latitude,
            airship.longitude,
            airship.altitude,
            ts.dt,
            sun_el
        )

        if result['panel_illuminated'] and sun_el > 0.0:
            cos_theta = max(
                0.0,
                math.cos(math.radians(result['incidence_angle_deg']))
            )

            total_power += irradiance * sp_area * sp_efficiency * cos_theta

    return total_power, (sun_el if sun_el is not None else 0.0)


def _calculate_mission_energy(start_lat:   float, start_lon:  float,
                              dest_lat:    float, dest_lon:   float,
                              start_dt:    datetime,
                              duration_hours: float,
                              heading:     float,
                              altitude:    float,
                              sp_area:     float,
                              sp_efficiency: float,
                              num_panels:  int,
                              outer_radius: float,
                              min_ring_fraction:      float,
                              ring_spacing_factor:    float,
                              azimuth_spacing_factor: float,
                              timestep_minutes: int) -> dict:

    # Build layout
    rings  = _generate_ring_layout(num_panels, sp_area, outer_radius,
                                   min_ring_fraction, ring_spacing_factor,
                                   azimuth_spacing_factor)
    panels = _rings_to_panels(rings)

    # Print ring layout summary — mirrors solar_energy_mission.py output exactly
    req_area_implied = num_panels * sp_area   # reconstruct for display only
    #print(f"Panel array: {len(panels)} panels (req_area~{req_area_implied:.2f} m\u00b2 / "
    #      f"sp_area={sp_area} m\u00b2 \u2192 num={num_panels}) across {len(rings)} ring(s).")
    #for i, r in enumerate(rings):
    #    print(f"  Ring {i:2d}: r={r['ring_radius']:6.3f} m  "
    #          f"z={r['z_height']:6.3f} m  n={r['count']}")

    # Build evaluation time steps
    if duration_hours <= 0:
        raise ValueError("duration_hours must be > 0.")
    total_seconds = duration_hours * 3600.0
    end_dt        = start_dt + timedelta(seconds=total_seconds)

    step_s     = timestep_minutes * 60.0
    eval_times = []
    t = start_dt
    while t <= end_dt + timedelta(seconds=1):
        eval_times.append(t)
        t += timedelta(seconds=step_s)
    if eval_times[-1] > end_dt:
        eval_times[-1] = end_dt

    # Print per-timestep table header
    cet = zoneinfo.ZoneInfo('Europe/Amsterdam')

    #print(f"\n{'Time (CET)':<22} {'Lat':>8} {'Lon':>9} "
    #      f"{'Sun El':>8} {'Power (W)':>12}")
    #print("\u2500" * 65)

    # Evaluate power at each step
    timeline = []
    for dt in eval_times:
        frac    = (dt - start_dt).total_seconds() / total_seconds
        lat     = start_lat + frac * (dest_lat  - start_lat)
        lon     = start_lon + frac * (dest_lon  - start_lon)
        airship = _AirshipState(latitude=lat, longitude=lon,
                                altitude=altitude, heading=heading)
        ts      = _TimeStamp(dt)
        power_w, sun_el = _compute_instantaneous_power(
            airship, panels, ts, sp_area, sp_efficiency)
        timeline.append({'dt': dt, 'power_w': power_w, 'sun_el': sun_el,
                         'lat': lat, 'lon': lon})

        dt_cet   = dt.astimezone(cet)
        sun_flag = "  [night]" if sun_el <= 0 else ""
        #print(f"  {dt_cet.strftime('%Y-%m-%d %H:%M CET'):<20}  "
        #      f"{lat:>7.4f}  {lon:>8.4f}  "
        #      f"{sun_el:>6.2f}\u00b0  {power_w:>10.1f} W{sun_flag}")

    # Trapezoidal integration → Wh
    total_energy_wh = 0.0
    for i in range(len(timeline) - 1):
        p0   = timeline[i]['power_w']
        p1   = timeline[i + 1]['power_w']
        dt_h = (timeline[i + 1]['dt'] - timeline[i]['dt']).total_seconds() / 3600.0
        total_energy_wh += 0.5 * (p0 + p1) * dt_h

    mission_duration_h = total_seconds / 3600.0
    all_powers         = [s['power_w'] for s in timeline]
    peak_power_w       = max(all_powers) if all_powers else 0.0
    avg_power_w        = (total_energy_wh / mission_duration_h
                          if mission_duration_h > 0 else 0.0)

    # Print mission summary
    #print(f"\n\u2550\u2550 Mission Energy Summary \u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550")
    #print(f"  Panels              {len(panels)}  across {len(rings)} ring(s)")
    #print(f"  Mission duration    {round(mission_duration_h, 4):.2f} h")
    #print(f"  Peak power          {round(peak_power_w, 2):.1f} W")
    #print(f"  Average power       {round(avg_power_w, 2):.1f} W")
    #print(f"  Total energy        {round(total_energy_wh, 3):.2f} Wh"
    #      f"  ({round(total_energy_wh / 1000.0, 6):.4f} kWh)")
    #print("\u2550" * 63)

    return {
        'total_energy_wh':    round(total_energy_wh,    3),
        'total_energy_kwh':   round(total_energy_wh / 1000.0, 6),
        'total_energy_J':     round(total_energy_wh * 3600.0, 2),
        'peak_power_w':       round(peak_power_w,       2),
        'avg_power_w':        round(avg_power_w,        2),
        'mission_duration_h': round(mission_duration_h, 4),
        'num_panels':         len(panels),
        'num_rings':          len(rings),
    }



def run_model(inputs: dict) -> dict:

    start_lat  = float(inputs["start_latitude"])
    start_lon  = float(inputs["start_longitude"])
    dest_lat   = float(inputs["destination_latitude"])
    dest_lon   = float(inputs["destination_longitude"])

    sy  = int(float(inputs["start_year"]))
    smo = int(float(inputs["start_month"]))
    sd  = int(float(inputs["start_day"]))
    sh  = int(float(inputs["start_hour"]))
    smi = int(float(inputs["start_minute"]))
    duration_hours   = float(inputs["duration_hours"])

    heading          = float(inputs["heading"])
    cruise_altitude  = float(inputs["cruise_altitude"])
    sp_area          = float(inputs["sp_area"])
    sp_efficiency    = float(inputs["sp_efficiency"])
    req_area         = float(inputs["req_area"])
    outer_radius     = float(inputs["outer_envelope_radius"])
    timestep_minutes = int(float(inputs["timestep_minutes"]))

    min_ring_fraction      = float(inputs.get("min_ring_fraction",      0.15))
    ring_spacing_factor    = float(inputs.get("ring_spacing_factor",    1.0))
    azimuth_spacing_factor = float(inputs.get("azimuth_spacing_factor", 1.1))

    # Validate
    if duration_hours <= 0:
        raise ValueError(f"duration_hours must be > 0, got {duration_hours}")
    if sp_area <= 0:
        raise ValueError(f"sp_area must be > 0, got {sp_area}")
    if not (0.0 < sp_efficiency <= 1.0):
        raise ValueError(f"sp_efficiency must be in (0,1], got {sp_efficiency}")
    if req_area <= 0:
        raise ValueError(f"req_area must be > 0, got {req_area}")
    if outer_radius <= 0:
        raise ValueError(f"outer_envelope_radius must be > 0, got {outer_radius}")

    num_panels = math.ceil(req_area / sp_area)

    # Input hours are CET — convert to UTC for internal calculations
    cet      = zoneinfo.ZoneInfo('Europe/Amsterdam')
    start_dt = datetime(sy, smo, sd, sh, smi,
                        tzinfo=cet).astimezone(timezone.utc)

    return _calculate_mission_energy(
        start_lat, start_lon, dest_lat, dest_lon,
        start_dt, duration_hours,
        heading, cruise_altitude,
        sp_area, sp_efficiency, num_panels, outer_radius,
        min_ring_fraction, ring_spacing_factor, azimuth_spacing_factor,
        timestep_minutes,
    )


if __name__ == "__main__":
    test_input = {
        "start_latitude":        52.01,  "start_longitude":        4.36,
        "destination_latitude":  52.37,  "destination_longitude":  4.90,
        "start_year": 2026, "start_month": 5, "start_day": 5,
        "start_hour": 9,    "start_minute": 0,
        "duration_hours": 10.0,
        "heading":           45.0,
        "cruise_altitude": 1000.0,
        "sp_area":            0.5,
        "sp_efficiency":     0.22,
        "req_area":          15.0,
        "outer_envelope_radius": 10.0,
        "timestep_minutes":   5,
    }

    print("\nSolar Panel Module — self-test")
    print("=" * 50)
    result = run_model(test_input)
    print(f"  total_energy_wh    = {result['total_energy_wh']:.3f} Wh")
    print(f"  total_energy_kwh   = {result['total_energy_kwh']:.6f} kWh")
    print(f"  total_energy_J     = {result['total_energy_J']:.1f} J")
    print(f"  peak_power_w       = {result['peak_power_w']:.2f} W")
    print(f"  avg_power_w        = {result['avg_power_w']:.2f} W")
    print(f"  mission_duration_h = {result['mission_duration_h']:.4f} h")
    print(f"  num_panels         = {result['num_panels']}")
    print(f"  num_rings          = {result['num_rings']}")
    print("=" * 50)