
import math

def _ring_layout(envelope_radius: float,
                 num_panels: int,
                 side: float,
                 min_ring_fraction: float,
                 ring_spacing_factor: float,
                 azimuth_spacing_factor: float) -> list:

    R = envelope_radius
    rings = []
    panels_remaining = num_panels

    # Top cap — one panel at the very top (polar = 0 deg)
    rings.append({
        'ring_radius':     0.0,
        'z_height':        R,
        'count':           1,
        'polar_angle_deg': 0.0,
    })
    panels_remaining -= 1

    if panels_remaining <= 0:
        return rings

    min_r         = R * min_ring_fraction
    current_polar = math.asin(min_r / R)          # starting polar angle [rad]
    arc_step      = (side * ring_spacing_factor) / R  # polar step [rad]

    while panels_remaining > 0:
        current_radius = R * math.sin(current_polar)
        z              = R * math.cos(current_polar)
        polar_deg      = math.degrees(current_polar)

        if current_polar >= math.pi / 2:
            # Past equator — dump remaining panels here (constraint violated)
            current_radius = R
            z              = 0.0
            polar_deg      = 90.0
            capacity       = panels_remaining
        else:
            circumference = 2 * math.pi * current_radius
            capacity      = max(1, math.floor(
                circumference / (side * azimuth_spacing_factor)
            ))

        count = min(capacity, panels_remaining)
        rings.append({
            'ring_radius':     current_radius,
            'z_height':        z,
            'count':           count,
            'polar_angle_deg': polar_deg,
        })
        panels_remaining -= count
        current_polar    += arc_step

    return rings


def _all_panels_above_equator(rings: list) -> bool:
    """True if every ring sits strictly above the equator (polar < 90 deg)."""
    return all(r['polar_angle_deg'] < 90.0 for r in rings)



def _find_min_radius(num_panels: int,
                     side: float,
                     min_ring_fraction: float,
                     ring_spacing_factor: float,
                     azimuth_spacing_factor: float,
                     r_lo: float = 0.5,
                     r_hi: float = 200.0,
                     tol: float = 1e-4,
                     max_iter: int = 200) -> tuple:


    rings_hi = _ring_layout(r_hi, num_panels, side,
                            min_ring_fraction, ring_spacing_factor,
                            azimuth_spacing_factor)
    if not _all_panels_above_equator(rings_hi):
        raise ValueError(
            f"Even at r={r_hi} m all panels cannot fit above the equator "
            f"with {num_panels} panels of side {side:.4f} m. "
            "Increase r_hi or reduce num_panels."
        )

    best_r     = r_hi
    best_rings = rings_hi

    for _ in range(max_iter):
        r_mid  = 0.5 * (r_lo + r_hi)
        rings  = _ring_layout(r_mid, num_panels, side,
                              min_ring_fraction, ring_spacing_factor,
                              azimuth_spacing_factor)

        if _all_panels_above_equator(rings):
            best_r     = r_mid
            best_rings = rings
            r_hi       = r_mid          # feasible → try smaller
        else:
            r_lo       = r_mid          # infeasible → need larger

        if (r_hi - r_lo) < tol:
            break

    return best_r, best_rings


def run_model(inputs: dict) -> dict:
    
    req_area               = float(inputs["req_area"])
    area_per_panel         = float(inputs["area_per_panel"])
    min_ring_fraction      = float(inputs.get("min_ring_fraction",      0.15))
    ring_spacing_factor    = float(inputs.get("ring_spacing_factor",    1.0))
    azimuth_spacing_factor = float(inputs.get("azimuth_spacing_factor", 1.1))
    r_lo                   = float(inputs.get("r_lo",                   0.5))
    r_hi                   = float(inputs.get("r_hi",                   200.0))
    tol                    = float(inputs.get("tol",                    1e-4))

    if req_area <= 0:
        raise ValueError(f"req_area must be > 0, got {req_area}")
    if area_per_panel <= 0:
        raise ValueError(f"area_per_panel must be > 0, got {area_per_panel}")

    num_panels = math.ceil(req_area / area_per_panel)
    side       = math.sqrt(area_per_panel)

    #print(f"\n=== solar_panel_min_radius ===")
    #print(f"  req_area       = {req_area} m²")
    #print(f"  area_per_panel = {area_per_panel} m²  →  panel side = {side:.4f} m")
    #print(f"  num_panels     = {num_panels}")
    #print(f"  Searching radius in [{r_lo}, {r_hi}] m  (tol={tol} m) …")

    min_r, rings = _find_min_radius(
        num_panels, side,
        min_ring_fraction, ring_spacing_factor, azimuth_spacing_factor,
        r_lo=r_lo, r_hi=r_hi, tol=tol,
    )

    last_polar = rings[-1]['polar_angle_deg']
    num_rings  = len(rings)

    #print(f"\n  ✓  Minimum radius   = {min_r:.4f} m")
    #print(f"     Rings used        = {num_rings}")
    #print(f"     Last ring polar   = {last_polar:.2f} deg  (must be < 90)")
    #print(f"\n  Ring breakdown:")
    #for i, r in enumerate(rings):
    #    print(f"    Ring {i:2d}: r={r['ring_radius']:7.4f} m  "
    #          f"z={r['z_height']:7.4f} m  "
    #          f"n={r['count']:3d}  polar={r['polar_angle_deg']:6.2f} deg")
    #print("=" * 33)

    return {
        "min_radius_m":         round(min_r, 6),
        "num_panels":           num_panels,
        "num_rings":            num_rings,
        "last_ring_polar_deg":  round(last_polar, 4),
        "panel_side_m":         round(side, 6),
    }



if __name__ == "__main__":
    test_cases = [
        {"req_area": 50.0,  "area_per_panel": 0.5},
        {"req_area": 120.0, "area_per_panel": 0.5},
        {"req_area": 251.0, "area_per_panel": 1.0},
    ]
    for tc in test_cases:
        print()
        result = run_model(tc)
        print(f"  → min_radius_m = {result['min_radius_m']:.4f} m  "
              f"({result['num_panels']} panels, {result['num_rings']} rings, "
              f"last polar {result['last_ring_polar_deg']:.2f} deg)")