
def run_model(inputs: dict) -> dict:

    P_shaft   = float(inputs["power_shaft_per_thruster_W"])
    eta_motor = float(inputs["motor_efficiency"])
    dt        = float(inputs["timestep_s"])

    if P_shaft < 0:
        raise ValueError(f"power_shaft_per_thruster_W must be >= 0, got {P_shaft:.4g}")
    if not (0.0 < eta_motor <= 1.0):
        raise ValueError(f"motor_efficiency must be in (0, 1], got {eta_motor}")
    if dt <= 0:
        raise ValueError(f"timestep_s must be > 0, got {dt}")


    P_elec_per_thruster = P_shaft / eta_motor       # [W]

    P_elec_total = 2.0 * P_elec_per_thruster        # [W]


    E_per_thruster = P_elec_per_thruster * dt        # [J]
    E_total        = P_elec_total * dt               # [J]

    return {
        "power_elec_per_thruster_W" : P_elec_per_thruster,
        "power_elec_total_W"        : P_elec_total,
        "energy_per_thruster_J"     : E_per_thruster,
        "energy_total_J"            : E_total,
    }


if __name__ == "__main__":
    test_input = {
        "power_shaft_per_thruster_W" : 500.0,   # e.g. from AnalyzeProp
        "motor_efficiency"           : 0.85,
        "timestep_s"                 : 60.0,
    }
    r = run_model(test_input)
    print("\nHorizontal Thruster Module — self-test")
    print("=" * 48)
    print(f"  Shaft power per thruster : {test_input['power_shaft_per_thruster_W']:.2f} W")
    print(f"  Motor efficiency         : {test_input['motor_efficiency']:.2f}")
    print(f"  Timestep                 : {test_input['timestep_s']:.0f} s")
    print("-" * 48)
    print(f"  Elec power per thruster  : {r['power_elec_per_thruster_W']:.2f} W")
    print(f"  Elec power total         : {r['power_elec_total_W']:.2f} W")
    print(f"  Energy per thruster      : {r['energy_per_thruster_J']:.2f} J")
    print(f"  Energy total (both)      : {r['energy_total_J']:.2f} J")
    print("=" * 48)