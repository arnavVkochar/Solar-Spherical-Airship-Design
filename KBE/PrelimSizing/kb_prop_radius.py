from __future__ import annotations
import math
import numpy as np
import os


def _thrust_at_max_rpm(
    radius: float,
    blade_data_file: str,
    num_blades: int,
    hub_to_tip: float,
    design_airspeed: float,
    max_rpm: float,
    c_tip_fraction: float,
    env_basepath: str,
):
    import jpype
    import jpype.imports
    from components.horizontal_propulsion import _read_blade_table
    from math import pi

    D = 2.0 * radius
    R = radius
    V = design_airspeed
    rho = 1.225
    kv = 1.5e-5
    sos = 340.0
    c_tip = c_tip_fraction * radius
    spinner_dia = hub_to_tip * D

    if not jpype.isJVMStarted():
        jpype.startJVM(
            jpype.getDefaultJVMPath(),
            classpath=[
                os.path.join(env_basepath, 'JavaProp.jar'),
                os.path.join(env_basepath, 'MHClasses.jar'),
            ],
        )

    from MH.JavaProp import Propeller
    from MH.AeroTools.Airfoils import Airfoil

    def make_airfoil(n):
        af = Airfoil()
        af.Init(n)
        return af

    blade_sections = 40
    prop = Propeller(blade_sections)
    prop.Name = 'KB-PrelimSizing'

    prop.Density = rho
    prop.KinematicViscosity = kv
    prop.SpeedOfSound = sos

    prop.removeAirfoils()
    prop.addAirfoil(jpype.JDouble(0.000), make_airfoil(13))
    prop.addAirfoil(jpype.JDouble(0.333), make_airfoil(13))
    prop.addAirfoil(jpype.JDouble(2 / 3), make_airfoil(12))
    prop.addAirfoil(jpype.JDouble(1.000), make_airfoil(10))

    prop.addAlfa(jpype.JDouble(0.00), jpype.JDouble(3.0))
    prop.addAlfa(jpype.JDouble(0.25), jpype.JDouble(3.0))
    prop.addAlfa(jpype.JDouble(0.50), jpype.JDouble(3.0))
    prop.addAlfa(jpype.JDouble(0.75), jpype.JDouble(3.0))
    prop.addAlfa(jpype.JDouble(1.00), jpype.JDouble(3.0))

    prop.BladeCount = num_blades
    prop.rRSpinner = jpype.JDouble(spinner_dia / D)
    prop.removeShroud()
    prop.hasSquareTips = 0

    prop.incrementBladeAngle(jpype.JDouble(0.0))
    prop.multiplyBladeAngle(jpype.JDouble(1.0))
    prop.incrementChord(jpype.JDouble(0.0))
    prop.multiplyChord(jpype.JDouble(1.0))
    prop.taperChord(jpype.JDouble(1.0))


    rpm_design = 3000.0
    Omega_design = 2.0 * pi * (rpm_design / 60.0)
    prop.performPropellerDesign(
        jpype.JDouble(V),
        jpype.JDouble(Omega_design),
        jpype.JDouble(R),
        jpype.JDouble(0.0),
        jpype.JDouble(100.0)
    )


    table = _read_blade_table(blade_data_file)
    r_R_arr = np.array([row[0] for row in table])
    c_R_arr = np.array([(row[1] * c_tip) / R for row in table])
    beta_arr = np.array([row[2] for row in table])
    n_pts = len(table)

    JDoubleArray = jpype.JArray(jpype.JDouble)
    rR_java = JDoubleArray(n_pts)
    cR_java = JDoubleArray(n_pts)
    beta_java = JDoubleArray(n_pts)
    for i in range(n_pts):
        rR_java[i] = jpype.JDouble(r_R_arr[i])
        cR_java[i] = jpype.JDouble(c_R_arr[i])
        beta_java[i] = jpype.JDouble(beta_arr[i])

    prop.interpolateGeometry(rR_java, cR_java, beta_java, jpype.JInt(n_pts))


    rpm_arr = list(np.arange(100, max_rpm + 100, 100, dtype=float))
    thrust = 0.0
    eta = 0.0
    for rpm in rpm_arr:
        n_rps = rpm / 60.0
        Omega = 2.0 * pi * n_rps
        prop.performAnalysis(
            jpype.JDouble(V), jpype.JDouble(Omega), jpype.JDouble(R),
            jpype.JDouble(rho), jpype.JDouble(kv), jpype.JDouble(sos)
        )
        if rpm >= max_rpm:
            thrust = max(0.0, float(prop.getThrust()))
            eta = max(0.0, min(1.0, float(prop.Eta)))
            break

    print(f'max rpm: {max_rpm}  thrust: {thrust:.2f} N  eta: {eta:.4f}  radius: {radius:.4f}')
    return thrust, eta


def size_prop_radius(
    thrust_required_N: float,
    blade_data_file: str,
    env_basepath: str,
    *,
    num_blades: int = 3,
    hub_to_tip: float = 0.2,
    design_airspeed: float = 15.0,
    max_rpm: float = 5000.0,
    c_tip_fraction: float = 0.08,
    r_min: float = 0.3,
    r_max: float = 5.0,
    thrust_tol: float = 0.5,
    radius_tol: float = 1e-5,
):
    def evaluate(r):
        return _thrust_at_max_rpm(
            r, blade_data_file, num_blades, hub_to_tip,
            design_airspeed, max_rpm, c_tip_fraction, env_basepath,
        )

    t_lo, _ = evaluate(r_min)
    t_hi, _ = evaluate(r_max)

    if t_hi < thrust_required_N:
        raise ValueError(
            f"Even at r_max={r_max:.3f} m, thrust={t_hi:.1f} N "
            f"is below the required {thrust_required_N:.1f} N."
        )

    if t_lo >= thrust_required_N:
        t, eta = evaluate(r_min)
        return {
            "prop_radius_m": r_min,
            "thrust_at_max_rpm_N": t,
            "eta_at_max_rpm": eta,
            "thrust_required_N": thrust_required_N,
            "thrust_margin_N": t - thrust_required_N,
        }

    lo, hi = r_min, r_max
    while True:
        mid = 0.5 * (lo + hi)
        thrust, eta = evaluate(mid)
        error = thrust - thrust_required_N
        if abs(error) <= thrust_tol:
            r_solved, t_solved, eta_solved = mid, thrust, eta
            break
        if error < 0:
            lo = mid
        else:
            hi = mid
        if (hi - lo) <= radius_tol:
            r_solved, t_solved, eta_solved = mid, thrust, eta
            break

    return {
        "prop_radius_m": r_solved,
        "thrust_at_max_rpm_N": t_solved,
        "eta_at_max_rpm": eta_solved,
        "thrust_required_N": thrust_required_N,
        "thrust_margin_N": t_solved - thrust_required_N,
    }


if __name__ == "__main__":
    import env_Arnesh as env

    BLADE_FILE = os.path.join(os.path.dirname(__file__), "..", "blade_data_output2.xlsx")
    result = size_prop_radius(
        thrust_required_N=288.5,
        blade_data_file=BLADE_FILE,
        env_basepath=env.basepath,
        num_blades=3,
        hub_to_tip=0.2,
        design_airspeed=8.75,
        max_rpm=7000.0,
    )
    print("=" * 50)
    print("  PROP RADIUS SIZING RESULT")
    print("=" * 50)
    for k, v in result.items():
        print(f"  {k:<26}: {v:.4f}")