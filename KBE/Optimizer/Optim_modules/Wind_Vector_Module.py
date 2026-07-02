

import math


def run_model(inputs: dict) -> dict:
    
    wind_speed    = float(inputs["wind_speed"])
    wind_dir_deg  = float(inputs["wind_direction"])
    ground_speed  = float(inputs["ground_speed"])
    heading_deg   = float(inputs["heading"])

    if wind_speed < 0:
        raise ValueError(f"wind_speed must be >= 0, got {wind_speed}")
    if ground_speed < 0:
        raise ValueError(f"ground_speed must be >= 0, got {ground_speed}")

    # --- Convert to radians ------------------------------------------------
    wind_dir_rad = math.radians(wind_dir_deg)
    heading_rad  = math.radians(heading_deg)

    # --- Ground velocity components ----------------------------------------
    # V_ground points along the airship heading at ground_speed magnitude.
    #   N-component = ground_speed * cos(heading)
    #   E-component = ground_speed * sin(heading)
    V_ground_N = ground_speed * math.cos(heading_rad)
    V_ground_E = ground_speed * math.sin(heading_rad)

    # --- Wind velocity components ------------------------------------------
    # Wind blows in the direction wind_dir_deg (going TO, not coming FROM).
    #   N-component = wind_speed * cos(wind_dir)
    #   E-component = wind_speed * sin(wind_dir)
    V_wind_N = wind_speed * math.cos(wind_dir_rad)
    V_wind_E = wind_speed * math.sin(wind_dir_rad)

    # --- Airspeed vector ---------------------------------------------------
    # The airship moves through the air at Va = V_ground - V_wind.
    # This is the velocity the propulsors must sustain and the envelope
    # experiences aerodynamic drag against.
    #
    #   Va_N = V_ground_N - V_wind_N
    #   Va_E = V_ground_E - V_wind_E
    Va_N = V_ground_N - V_wind_N
    Va_E = V_ground_E - V_wind_E

    # --- Airspeed magnitude ------------------------------------------------
    airspeed = math.sqrt(Va_N**2 + Va_E**2)

    # --- Thrust bearing (compass direction of Va vector) -------------------
    # atan2 in NE frame: bearing = atan2(East, North)
    if airspeed > 0.0:
        thrust_bearing_rad = math.atan2(Va_E, Va_N)
        thrust_bearing_deg = math.degrees(thrust_bearing_rad) % 360.0

        # Crab angle = signed difference between thrust bearing and heading
        # Normalise to [-180, +180]
        crab_angle_deg = thrust_bearing_deg - heading_deg
        if crab_angle_deg > 180.0:
            crab_angle_deg -= 360.0
        elif crab_angle_deg < -180.0:
            crab_angle_deg += 360.0
    else:
        thrust_bearing_deg = heading_deg   # undefined; return heading as fallback
        crab_angle_deg     = 0.0

    # --- Return ------------------------------------------------------------
    return {
        "Va_N":               Va_N,
        "Va_E":               Va_E,
        "airspeed":           airspeed,
        "V_ground_N":         V_ground_N,
        "V_ground_E":         V_ground_E,
        "V_wind_N":           V_wind_N,
        "V_wind_E":           V_wind_E,
        "crab_angle_deg":     crab_angle_deg,
        "thrust_bearing_deg": thrust_bearing_deg,
    }



if __name__ == "__main__":
    import sys

    ws  = float(sys.argv[1]) if len(sys.argv) > 1 else 8.0    # m/s
    wd  = float(sys.argv[2]) if len(sys.argv) > 2 else 90.0   # deg (blowing East)
    gs  = float(sys.argv[3]) if len(sys.argv) > 3 else 15.0   # m/s
    hdg = float(sys.argv[4]) if len(sys.argv) > 4 else 0.0    # deg (heading North)

    inp = {
        "wind_speed":     ws,
        "wind_direction": wd,
        "ground_speed":   gs,
        "heading":        hdg,
    }

    r = run_model(inp)

    print(f"\nWind Vector Module — self-test")
    print(f"=" * 52)
    print(f"  Wind speed          : {ws} m/s  @ {wd} deg")
    print(f"  Ground speed        : {gs} m/s  heading {hdg} deg")
    print(f"-" * 52)
    print(f"  V_ground (N, E)     : ({r['V_ground_N']:.3f}, {r['V_ground_E']:.3f}) m/s")
    print(f"  V_wind   (N, E)     : ({r['V_wind_N']:.3f},  {r['V_wind_E']:.3f}) m/s")
    print(f"  Va       (N, E)     : ({r['Va_N']:.3f}, {r['Va_E']:.3f}) m/s")
    print(f"  Airspeed |Va|       : {r['airspeed']:.4f} m/s")
    print(f"  Thrust bearing      : {r['thrust_bearing_deg']:.2f} deg from North")
    print(f"  Crab angle          : {r['crab_angle_deg']:.2f} deg")
    print(f"=" * 52)


    scenarios = [
        ("Pure headwind",      15.0,   0.0,  15.0,  0.0),
        ("Pure tailwind",      10.0, 180.0,  15.0,  0.0),
        ("Right crosswind",     8.0,  90.0,  15.0,  0.0),
        ("Left crosswind",      8.0, 270.0,  15.0,  0.0),
        ("Quartering headwind", 8.0,  45.0,  15.0,  0.0),
        ("Wind == ground spd",  15.0, 90.0,  15.0,  0.0),
    ]
    print(f"\n{'Scenario':<25} {'|Va| m/s':>10} {'Crab deg':>10} {'Bearing deg':>12}")
    print("-" * 62)
    for name, ws_, wd_, gs_, hdg_ in scenarios:
        out = run_model({"wind_speed":ws_,"wind_direction":wd_,"ground_speed":gs_,"heading":hdg_})
        print(f"  {name:<23} {out['airspeed']:>10.3f} {out['crab_angle_deg']:>10.2f} {out['thrust_bearing_deg']:>12.2f}")
    print()