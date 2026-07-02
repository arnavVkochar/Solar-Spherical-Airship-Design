
import math
from ambiance import Atmosphere


def _cd_from_reynolds(Re):

    if Re <= 0:
        raise ValueError(f"Reynolds number must be positive, got {Re:.4g}")

    W = math.log10(Re)

    if Re <= 0.01:
        return 3.0/16.0 + 24.0/Re,                                          "Re <= 0.01"
    elif Re <= 20:
        return (24.0/Re) * (1.0 + 0.1315 * Re**(0.82 - 0.05*W)),           "0.01 < Re <= 20"
    elif Re <= 260:
        return (24.0/Re) * (1.0 + 0.1935 * Re**0.6305),                    "20 < Re <= 260"
    elif Re <= 1.5e3:
        return 10**(1.6435 - 1.1242*W + 0.1558*W**2),                      "260 <= Re <= 1500"
    elif Re <= 1.2e4:
        return 10**(-2.4571 + 2.5558*W - 0.9295*W**2 + 0.1049*W**3),      "1500 < Re <= 1.2e4"
    elif Re <= 4.4e4:
        return 10**(-1.9181 + 0.6370*W - 0.0636*W**2),                     "1.2e4 < Re <= 4.4e4"
    elif Re <= 3.38e5:
        return 10**(-4.3390 + 1.5809*W - 0.1546*W**2),                     "4.4e4 < Re <= 3.38e5"
    elif Re <= 4.0e5:
        return 29.78 - 5.3*W,                                               "3.38e5 < Re <= 4.0e5 (drag-crisis)"
    elif Re <= 1.0e6:
        return 0.1*W - 0.49,                                                "4.0e5 < Re <= 1e6 (post-crisis)"
    else:
        return 0.19 - (8.0e4 / Re),                                         "Re > 1e6 (fully turbulent)"



def run_model(inputs: dict) -> dict:

    envelope_radius = float(inputs["envelope_radius"])
    airspeed        = float(inputs["airspeed"])
    cruise_altitude = float(inputs["cruise_altitude"])


    if envelope_radius <= 0:
        raise ValueError(f"envelope_radius must be > 0, got {envelope_radius}")
    if airspeed < 0:
        raise ValueError(f"airspeed must be >= 0, got {airspeed}")
    if cruise_altitude < 0:
        raise ValueError(f"cruise_altitude must be >= 0, got {cruise_altitude}")


    atm = Atmosphere(cruise_altitude)
    rho = float(atm.density[0])              
    mu  = float(atm.dynamic_viscosity[0])     


    D     = 2.0 * envelope_radius             
    A_ref = math.pi * envelope_radius**2      
    q     = 0.5 * rho * airspeed**2          


    if airspeed == 0.0:
        return {
            "drag_force_N":           0.0,
            "cd":                     0.0,
            "reynolds":               0.0,
            "dynamic_pressure_Pa":    0.0,
            "frontal_area_m2":        A_ref,
            "air_density_kg_m3":      rho,
            "dynamic_viscosity_Pa_s": mu,
        }


    Re          = rho * airspeed * D / mu
    cd, _regime = _cd_from_reynolds(Re)


    drag_force_N = cd * A_ref * q


    return {
        "drag_force_N":           drag_force_N,
        "cd":                     cd,
        "reynolds":               Re,
        "dynamic_pressure_Pa":    q,
        "frontal_area_m2":        A_ref,
        "air_density_kg_m3":      rho,
        "dynamic_viscosity_Pa_s": mu,
    }




if __name__ == "__main__":
    import sys

    R   = 8.71
    V   = 8.747
    alt = 11000

    test_input = {
        "envelope_radius": R,
        "airspeed":        V,
        "cruise_altitude": alt,
    }

    print(f"\nTest inputs: {test_input}")
    result = run_model(test_input)
    print("\nOutputs:")
    for k, v in result.items():
        print(f"  {k:<26} = {v:.6g}")