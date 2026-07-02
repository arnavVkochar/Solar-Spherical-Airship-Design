from dataclasses import dataclass
from datetime import datetime, timezone
import math



@dataclass
class TimeStamp:
    dt: datetime

    @classmethod
    def from_parts(cls, year: int, month: int, day: int,
                   hour: int, minute: int, second: int = 0) -> "TimeStamp":
        return cls(datetime(year, month, day, hour, minute, second, tzinfo=timezone.utc))

    @property
    def hour(self) -> int:   return self.dt.hour
    @property
    def minute(self) -> int: return self.dt.minute
    def __str__(self) -> str:
        return self.dt.strftime("%Y-%m-%d  %H:%M UTC")


@dataclass
class AirshipState:
    latitude:  float   # degrees  (+ve North)
    longitude: float   # degrees  (+ve East)
    altitude:  float   # metres above sea level
    heading:   float   # degrees clockwise from North (0 = North, 90 = East)

@dataclass
class PanelPosition:

    x: float
    y: float
    z: float

    @property
    def outward_normal(self) -> tuple[float, float, float]:
        """Unit vector pointing away from sphere centre — the panel's facing direction."""
        mag = math.sqrt(self.x**2 + self.y**2 + self.z**2)
        if mag == 0:
            raise ValueError("Panel is at the sphere centre — normal undefined.")
        return (self.x / mag, self.y / mag, self.z / mag)


# ── Sun-position helper (uses pysolar) ────────────────────────────────────────

def _sun_direction_enu(airship: AirshipState, ts: TimeStamp) -> tuple[float, float, float]:
    from pysolar.solar import get_altitude, get_azimuth

    el_deg = get_altitude(airship.latitude, airship.longitude, ts.dt,
                          elevation=airship.altitude)
    az_deg = get_azimuth(airship.latitude, airship.longitude, ts.dt,
                         elevation=airship.altitude)

    # pysolar azimuth is already clockwise from North — no offset needed
    az_from_north = az_deg  # ← was wrongly (az_deg + 180) % 360

    el = math.radians(el_deg)
    az = math.radians(az_from_north)

    east  = math.cos(el) * math.sin(az)
    north = math.cos(el) * math.cos(az)
    up    = math.sin(el)
    return (east, north, up)


def _enu_to_body(sun_enu: tuple, heading_deg: float) -> tuple[float, float, float]:

    h = math.radians(heading_deg)

    # Forward unit vector in ENU
    fwd_e, fwd_n =  math.sin(h),  math.cos(h)
    # Left unit vector in ENU  (rotate forward 90° CCW in horizontal plane)
    lft_e, lft_n = -math.cos(h),  math.sin(h)

    east, north, up = sun_enu
    body_x = east * fwd_e + north * fwd_n   # component along forward
    body_y = east * lft_e + north * lft_n   # component along left
    body_z = up                              # z is the same in both frames
    return (body_x, body_y, body_z)


# ── Main calculation ───────────────────────────────────────────────────────────

def solar_incidence(airship: AirshipState,
                    panel: PanelPosition,
                    ts: TimeStamp) -> dict:

    sun_enu  = _sun_direction_enu(airship, ts)
    sun_body = _enu_to_body(sun_enu, airship.heading)
    normal   = panel.outward_normal

    dot = sum(a * b for a, b in zip(sun_body, normal))
    dot = max(-1.0, min(1.0, dot))          # clamp for floating-point safety
    angle_deg = math.degrees(math.acos(dot))

    sun_elevation = math.degrees(math.asin(sun_enu[2]))

    return {
        "incidence_angle_deg": round(angle_deg, 2), #0 deg is best, 90 panel edge, >90 zero power
        "panel_illuminated":   angle_deg < 90.0,
        "sun_elevation_deg":   round(sun_elevation, 2),
        "sun_body_vector":     tuple(round(v, 4) for v in sun_body),
        "panel_normal":        tuple(round(v, 4) for v in normal),
    }


# ── Example usage ─────────────────────────────────────────────────────────────

airship = AirshipState(latitude=52, longitude=4.3, altitude=1000, heading=90)
panel   = PanelPosition(x=0, y=0, z=10) # direction from centre to panel
ts      = TimeStamp.from_parts(year=2026, month=5, day=5, hour=9, minute=0)

print(ts)
result = solar_incidence(airship, panel, ts)
for k, v in result.items():
    print(f"  {k}: {v}")

