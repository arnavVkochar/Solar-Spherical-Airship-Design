"""
Preliminary envelope radius sizing based on estimates for weights using typical weights observed.

Aim -Given mission parameters (cruise altitude, dry-mass estimate) and constants,
compute the minimum envelope radius that lets the airship achieve neutral buoyancy at cruise altitude.
"""

from __future__ import annotations
import math
from ambiance import Atmosphere


def _atm(h: float) -> Atmosphere:
    return Atmosphere(max(0.0, min(float(h), 81_020.0)))

def rho_air(h: float) -> float:
    """Air density [kg/m³] at a given altitude h [m]."""
    return _atm(h).density[0]

def rho_gas(h: float, rho_gas_sl: float) -> float:
    a   = _atm(h);   a0  = _atm(0.0)
    return rho_gas_sl * (a.pressure[0] / a0.pressure[0]) * (a0.temperature[0] / a.temperature[0])

def size_envelope_radius(
    cruise_altitude_m: float,
    dry_mass_kg:float,
    *, #keyword only to separate optional from needed parameters. can be removed
    gas_density_sl:float = 0.1786,
    envelope_mass_per_m2:float = 0.35,
    envelope_thickness:float = 4e-4,
    ballonet_mass_per_m2:float = 0.25,
    ballonet_thickness:float = 3e-4,
    ballonet_volume_fraction_sl: float = 0.30,
    r_min:float = 1.0,
    r_max:float = 60.0,
    tol:float = 0.01,
    gravity: float = 9.81,
):
    """ Description -
    Goal of this block is to find the smallest sphere radius [m] for neutral buoyancy at cruise altitude. Main
    brain of the prelim sizing of envelope radius which holds some assumptions that need to be altered if needed.

    The envelope and ballonet skin masses are computed internally (same as
    the buoyancy module, Eq. 10-11), so ``dry_mass_kg`` must NOT include them.

    Parameters:
    cruise_altitude_m- Target cruise altitude [m].
    dry_mass_kg- Everything except envelope + ballonet skins:
    gas_density_sl- Lifting-gas density at sea level [kg/m³].
    envelope_mass_per_m2- Envelope fabric density [kg/m²].
    envelope_thickness-Envelope wall thickness [m].
    ballonet_mass_per_m2-Ballonet fabric areal density [kg/m²].
    ballonet_thickness-Ballonet wall thickness [m].
    ballonet_volume_fraction_sl-Fraction of interior volume filled by ballonet at sea level
    r_min / r_max- Search bracket [m].
    tol- Convergence tolerance [m].
    """

    h = cruise_altitude_m
    rho_a = rho_air(h)
    rho_a_sl = rho_air(0.0)
    rho_g_h= rho_gas(h, gas_density_sl)
    rho_g_sl = gas_density_sl

    def _net_lift(r: float):
        V_total= (4.0 / 3.0) * math.pi * r**3
        A_env= 4.0 * math.pi * r**2
        V_shell_e = A_env * envelope_thickness
        V_int= V_total - V_shell_e

        V_bal_max = ballonet_volume_fraction_sl *V_int
        A_bal= (36.0 * math.pi* V_bal_max**2) **(1.0 / 3.0)
        V_shell_b = A_bal* ballonet_thickness
        V_usable = V_int - V_shell_b

        V_gas_sl= V_usable - V_bal_max
        if V_gas_sl <= 0.0:
            return -1.0  #infeasible so negative lift used to inflict penalty

        gas_mass  = rho_g_sl * V_gas_sl
        m_env= envelope_mass_per_m2 * A_env
        m_bal= ballonet_mass_per_m2 * A_bal
        m_struc = dry_mass_kg + m_env + m_bal
        V_gas_h = min(gas_mass / rho_g_h, V_usable)
        V_bal_h = max(0.0, V_usable - V_gas_h)
        m_tot_h = m_struc + gas_mass + rho_a * V_bal_h
        return (rho_a * V_total - m_tot_h) * gravity

    lift_min = _net_lift(r_min)
    lift_max = _net_lift(r_max)

    if lift_max < 0.0:
        raise ValueError(
            f"Even at r_max={r_max} m the airship cannot reach {h/1000:.1f} km. "
            "Increase r_max, reduce dry_mass, or choose a lower cruise altitude."
        )
    if lift_min > 0.0:
        #Already buoyant at r_min
        r_min_new = 0.1
        if _net_lift(r_min_new) > 0.0:
            raise ValueError(
                f"Airship is buoyant even at r={r_min_new} m. "
                "Dry mass might be too low. Increase payload or identift issue."
            )
        r_min = r_min_new

    #Checks complete - perform bisection to locate feasible envelope
    lo, hi = r_min, r_max

    if _net_lift(lo) > 0.0:
        lo, hi = hi, lo

    while (hi - lo) > tol:
        mid = 0.5 * (lo + hi)
        if _net_lift(mid) < 0.0:
            lo = mid
        else:
            hi = mid

    r_solved = 0.5 * (lo + hi)
    V_total= (4.0 / 3.0) * math.pi * r_solved**3
    A_env= 4.0 * math.pi * r_solved**2
    V_shell_e = A_env * envelope_thickness
    V_int= V_total - V_shell_e
    V_bal_max = ballonet_volume_fraction_sl * V_int
    A_bal= (36.0 * math.pi * V_bal_max**2) ** (1.0 / 3.0)
    V_shell_b = A_bal * ballonet_thickness
    V_usable= V_int - V_shell_b
    V_gas_sl = V_usable - V_bal_max
    gas_mass= rho_g_sl * V_gas_sl
    m_env= envelope_mass_per_m2 * A_env
    m_bal= ballonet_mass_per_m2 * A_bal
    m_struc= dry_mass_kg + m_env + m_bal
    V_gas_h= min(gas_mass / rho_g_h, V_usable)
    V_bal_h= max(0.0, V_usable - V_gas_h)
    m_tot_h= m_struc + gas_mass + rho_a * V_bal_h
    net_lift= (rho_a * V_total - m_tot_h) * gravity

    #find pressure ceiling where ballonet is completely pressed
    rho_target = gas_mass / V_usable
    h_pc: float | None = None
    if rho_gas(0.0, gas_density_sl) > rho_target:
        lo_pc, hi_pc = 0.0, 81_020.0
        while (hi_pc - lo_pc) > 1.0:
            mid = 0.5 * (lo_pc + hi_pc)
            if rho_gas(mid, gas_density_sl) > rho_target:
                lo_pc = mid
            else:
                hi_pc = mid
        h_pc = 0.5 * (lo_pc + hi_pc)

    return {
        "radius_m":r_solved,
        "volume_total_m3":V_total,
        "gas_mass_kg":gas_mass,
        "envelope_mass_kg":m_env,
        "ballonet_mass_kg":m_bal,
        "structural_mass_kg":m_struc,
        "net_lift_N":net_lift,
        "buoyancy_margin_kg":net_lift / gravity,
        "pressure_ceiling_m":h_pc if h_pc is not None else float("nan"),
        "gas_volume_sl_m3":V_gas_sl,
        "ballonet_volume_sl_m3": V_bal_max,
        "usable_volume_m3":V_usable,
    }

def estimate_dry_mass(
    payload_kg:float,
    n_batteries:int = 4,
    battery_mass_kg:float = 3.0,
    n_solar_panels:int = 6,
    solar_panel_mass_kg: float = 0.9,
    n_horiz_props:int = 2,
    horiz_prop_mass_kg:float = 3.0,
    n_vert_props:int= 4,
    vert_prop_mass_kg:float = 1.0,
    avionics_mass_kg:float = 5.0,
    gondola_mass_kg:float = 8.0,
):
    return (
        payload_kg
        +n_batteries* battery_mass_kg
        +n_solar_panels* solar_panel_mass_kg
        +n_horiz_props* horiz_prop_mass_kg
        +n_vert_props* vert_prop_mass_kg
        + avionics_mass_kg
        +gondola_mass_kg
    )

if __name__ == "__main__":

    print("=" * 58)
    print("  SCENARIO 1 — known dry mass, cruise at 10 km")
    print("=" * 58)
    result = size_envelope_radius(
        cruise_altitude_m=10_000.0,
        dry_mass_kg=70.0,
    )
    for k, v in result.items():
        print(f"  {k:<30s}: {v:.4f}")

    print()
    print("=" * 58)
    print("  SCENARIO 2 — estimate dry mass, cruise at 5 km")
    print("=" * 58)
    dm = estimate_dry_mass(
        payload_kg=15.0,
        n_batteries=4,  battery_mass_kg=3.5,
        n_solar_panels=8, solar_panel_mass_kg=1.0,
        gondola_mass_kg=10.0,
    )
    print(f"  Estimated dry mass : {dm:.1f} kg")
    result2 = size_envelope_radius(
        cruise_altitude_m=5_000.0,
        dry_mass_kg=dm,
    )
    for k, v in result2.items():
        print(f"  {k:<30s}: {v:.4f}")

    print()
    print("=" * 58)
    print("  SCENARIO 3 — H₂ gas, cruise at 15 km")
    print("=" * 58)
    result3 = size_envelope_radius(
        cruise_altitude_m=15_000.0,
        dry_mass_kg=120.0,
        gas_density_sl=0.0899,   # H₂
    )
    for k, v in result3.items():
        print(f"  {k:<30s}: {v:.4f}")