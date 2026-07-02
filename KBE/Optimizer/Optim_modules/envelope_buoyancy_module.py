import math
from ambiance import Atmosphere


def _atm(altitude_m: float) -> Atmosphere:
    """Clamp to valid ISA range and return Atmosphere object."""
    return Atmosphere(max(0.0, min(float(altitude_m), 81020.0)))


def air_density_at_altitude(altitude_m: float) -> float:
    """ρ_air(h) [kg/m³] from ISA."""
    return _atm(altitude_m).density[0]


def gas_density_at_altitude(altitude_m: float, gas_density_sl: float) -> float:
    """
    ρ_gas(h) [kg/m³]  — ideal-gas isobaric scaling  (Eq. 1).
    Valid for H₂, He, and other non-reactive ideal lifting gases.
    """
    atm    = _atm(altitude_m)
    atm_sl = _atm(0.0)
    return (gas_density_sl
            * (atm.pressure[0]       / atm_sl.pressure[0])
            * (atm_sl.temperature[0] / atm.temperature[0]))



def _find_pressure_ceiling(gas_mass: float, gas_density_sl: float,
                            V_usable: float,
                            max_altitude: float = 50000.0,
                            tol: float = 0.1) -> float | None:
    rho_target = gas_mass / V_usable
    if gas_density_at_altitude(max_altitude, gas_density_sl) > rho_target:
        return None
    lo, hi = 0.0, max_altitude
    while (hi - lo) > tol:
        mid = 0.5 * (lo + hi)
        if gas_density_at_altitude(mid, gas_density_sl) > rho_target:
            lo = mid
        else:
            hi = mid
    return 0.5 * (lo + hi)


def _find_achievable_altitude(m_structural: float, gas_mass: float,
                               gas_density_sl: float,
                               V_total: float, V_usable: float,
                               gravity: float,
                               max_altitude: float = 50000.0,
                               tol: float = 0.1) -> float:

    def net_lift(h):
        rho_air = air_density_at_altitude(h)
        rho_gas = gas_density_at_altitude(h, gas_density_sl)
        V_gas   = min(gas_mass / rho_gas, V_usable)          # Eq. 13
        V_bal   = max(0.0, V_usable - V_gas)                 # Eq. 14
        m_tot   = m_structural + gas_mass + rho_air * V_bal  # Eq. 15
        return (rho_air * V_total - m_tot) * gravity          # Eq. 16

    if net_lift(0.0) < 0.0:
        return 0.0
    if net_lift(max_altitude) > 0.0:
        return max_altitude

    lo, hi = 0.0, max_altitude
    while (hi - lo) > tol:
        mid = 0.5 * (lo + hi)
        if net_lift(mid) > 0.0:
            lo = mid
        else:
            hi = mid
    return 0.5 * (lo + hi)



def _overpressure_and_stress(gas_mass: float, gas_density_sl: float,
                              V_usable: float, eval_altitude: float,
                              radius: float, envelope_thickness: float,
                              h_pc: float) -> dict:

    atm_pc    = _atm(h_pc)
    atm_eval  = _atm(eval_altitude)
    P_ceiling = atm_pc.pressure[0]
    T_ceiling = atm_pc.temperature[0]
    T_eval    = atm_eval.temperature[0]
    P_ambient = atm_eval.pressure[0]

    P_gas_inside = P_ceiling * (T_eval / T_ceiling)
    delta_P      = max(0.0, P_gas_inside - P_ambient)
    hoop = (delta_P * radius / (2.0 * envelope_thickness)
            if envelope_thickness > 0.0 else float('inf'))

    return {
        "overpressure_Pa":  delta_P,
        "overpressure_kPa": delta_P / 1e3,
        "hoop_stress_Pa":   hoop,
        "hoop_stress_MPa":  hoop / 1e6,
    }



def _evaluate(radius: float, ballonet_volume_fraction_sl: float,
              gas_density_sl: float, dry_mass: float,
              envelope_mass_per_m2: float, envelope_thickness: float,
              ballonet_mass_per_m2: float, ballonet_thickness: float,
              ceiling_tolerance_m: float, cruise_altitude_m: float,
              gravity: float = 9.81) -> dict:

    V_total     = (4.0 / 3.0) * math.pi * radius**3          # Eq. 2
    A_env       = 4.0 * math.pi * radius**2
    V_shell_env = A_env * envelope_thickness                  # Eq. 3
    V_int       = V_total - V_shell_env                       # Eq. 4

    V_bal_max   = ballonet_volume_fraction_sl * V_int         # Eq. 5
    A_bal       = (36.0 * math.pi * V_bal_max**2) ** (1.0 / 3.0)  # Eq. 6
    V_shell_bal = A_bal * ballonet_thickness                  # Eq. 7
    V_usable    = V_int - V_shell_bal                         # Eq. 8


    V_gas_sl = V_usable - V_bal_max                           # Eq. 9
    if V_gas_sl <= 0.0:
        raise ValueError(
            f"ballonet_volume_fraction_sl ({ballonet_volume_fraction_sl:.3f}) is too "
            "large: no space left for lifting gas at sea level.  "
            "Reduce f_bal_sl or increase radius."
        )
    gas_mass = gas_density_sl * V_gas_sl                      # Eq. 9


    m_env        = envelope_mass_per_m2 * A_env               # Eq. 10
    m_bal        = ballonet_mass_per_m2 * A_bal               # Eq. 10
    m_structural = dry_mass + m_env + m_bal                   # Eq. 11
    print("Empty weight:", m_structural)

    rho_sl       = air_density_at_altitude(0.0)
    k            = rho_sl / gas_density_sl
    gas_mass_min = m_structural / (k - 1.0)
    

    h_achievable = _find_achievable_altitude(
        m_structural, gas_mass, gas_density_sl,
        V_total, V_usable, gravity,
    )

    rho_air_h  = air_density_at_altitude(h_achievable)
    rho_gas_h  = gas_density_at_altitude(h_achievable, gas_density_sl)
    V_gas_h    = min(gas_mass / rho_gas_h, V_usable)          # Eq. 13
    V_bal_h    = max(0.0, V_usable - V_gas_h)                 # Eq. 14
    m_total_h  = m_structural + gas_mass + rho_air_h * V_bal_h
    net_lift_h = (rho_air_h * V_total - m_total_h) * gravity  # Eq. 16
    print("Net lift:", net_lift_h)

    h_pc = _find_pressure_ceiling(gas_mass, gas_density_sl, V_usable)
    gap  = (max(0.0, h_achievable - h_pc) if h_pc is not None else 0.0)

    if h_pc is not None and h_achievable > h_pc:
        op = _overpressure_and_stress(
            gas_mass, gas_density_sl, V_usable,
            h_achievable, radius, envelope_thickness, h_pc,
        )
    else:
        op = {"overpressure_Pa": 0.0, "overpressure_kPa": 0.0,
              "hoop_stress_Pa":  0.0, "hoop_stress_MPa":  0.0}


    m_air_bal_sl = rho_sl * V_bal_max
    m_total_sl   = m_structural + gas_mass + m_air_bal_sl
    net_lift_sl  = (rho_sl * V_total - m_total_sl) * gravity
    print("Net lift:", net_lift_sl)

    altitude_residual = h_achievable - cruise_altitude_m

    return {

        "altitude_residual_m":           altitude_residual,
        # Achievable altitude
        "achievable_altitude_m":         h_achievable,
        "achievable_altitude_km":        h_achievable / 1000.0,
        # Pressure ceiling gap (use in inequality c(1))
        "gap_to_ceiling_m":              gap,
        "pressure_ceiling_m":            h_pc if h_pc is not None else float('nan'),
        # Gas (derived)
        "gas_mass_kg":                   gas_mass,
        "gas_mass_min_kg":               gas_mass_min,
        # Masses
        "envelope_mass_kg":              m_env,
        "ballonet_mass_kg":              m_bal,
        "structural_mass_kg":            m_structural,
        # Volumes
        "envelope_volume_m3":            V_total,
        "interior_volume_m3":            V_int,
        "gas_volume_sl_m3":              V_gas_sl,
        "gas_volume_at_altitude_m3":     V_gas_h,
        "ballonet_volume_at_altitude_m3": V_bal_h,
        "ballonet_volume_fraction_sl":   ballonet_volume_fraction_sl,
        # Lift
        "net_lift_at_altitude_N":        net_lift_h,
        "sea_level_net_lift_N":          net_lift_sl,
        # Structural
        "overpressure_Pa":               op["overpressure_Pa"],
        "overpressure_kPa":              op["overpressure_kPa"],
        "envelope_hoop_stress_Pa":       op["hoop_stress_Pa"],
        "envelope_hoop_stress_MPa":      op["hoop_stress_MPa"],
    }



def run_model(inputs: dict) -> dict:
    
    mode = str(inputs.get("mode", "constraint"))
    if mode != "constraint":
        raise ValueError(
            f"Unknown mode '{mode}'. This module only supports mode='constraint'."
        )

    radius                      = float(inputs["radius"])
    ballonet_volume_fraction_sl = float(inputs["ballonet_volume_fraction_sl"])
    gas_density_sl              = float(inputs["gas_density_sl"])
    dry_mass                    = float(inputs["dry_mass"])
    envelope_mass_per_m2        = float(inputs["envelope_mass_per_m2"])
    envelope_thickness          = float(inputs["envelope_thickness"])
    ballonet_mass_per_m2        = float(inputs["ballonet_mass_per_m2"])
    ballonet_thickness          = float(inputs["ballonet_thickness"])
    ceiling_tolerance_m         = float(inputs["ceiling_tolerance_m"])
    cruise_altitude_m           = float(inputs["cruise_altitude_m"])
    gravity                     = float(inputs.get("gravity", 9.81))

    if radius <= 0.0:
        raise ValueError(f"radius must be positive, got {radius}")
    if not (0.0 < ballonet_volume_fraction_sl < 1.0):
        raise ValueError(
            f"ballonet_volume_fraction_sl must be in (0, 1), "
            f"got {ballonet_volume_fraction_sl}"
        )
    if cruise_altitude_m < 0.0:
        raise ValueError(f"cruise_altitude_m must be >= 0, got {cruise_altitude_m}")

    return _evaluate(
        radius=radius,
        ballonet_volume_fraction_sl=ballonet_volume_fraction_sl,
        gas_density_sl=gas_density_sl,
        dry_mass=dry_mass,
        envelope_mass_per_m2=envelope_mass_per_m2,
        envelope_thickness=envelope_thickness,
        ballonet_mass_per_m2=ballonet_mass_per_m2,
        ballonet_thickness=ballonet_thickness,
        ceiling_tolerance_m=ceiling_tolerance_m,
        cruise_altitude_m=cruise_altitude_m,
        gravity=gravity,
    )



if __name__ == "__main__":

    BASE = {
        "mode":                         "constraint",
        "cruise_altitude_m":            10000.0,
        "radius":                       8.0,
        "ballonet_volume_fraction_sl":  0.30,
        "gas_density_sl":               0.1786,    # He
        "dry_mass":                     40.0,
        "envelope_mass_per_m2":         0.35,
        "envelope_thickness":           4e-4,
        "ballonet_mass_per_m2":         0.25,
        "ballonet_thickness":           3e-4,
        "ceiling_tolerance_m":          500.0,
    }

    print("=" * 62)
    print("  CONSTRAINT MODE — self test")
    print("=" * 62)
    out = run_model(BASE)
    for k, v in out.items():
        print(f"  {k:46s}: {v:.4f}")

    print()
    print(f"  Gas mass (derived, not input) : {out['gas_mass_kg']:.1f} kg")
    print(f"  Achievable altitude           : {out['achievable_altitude_km']:.2f} km")
    print(f"  Cruise altitude (target)      : {BASE['cruise_altitude_m']/1000:.2f} km")
    print(f"  Residual (ceq × h_cruise)     : {out['altitude_residual_m']:.1f} m")
    print()
    print("  fmincon drives 'altitude_residual_m' → 0.")