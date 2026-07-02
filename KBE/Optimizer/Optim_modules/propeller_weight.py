
import math
import os
from typing import Optional


MATERIAL_DENSITY_KG_M3: float = 1550.0   # kg/m^3


AIRFOIL_AREA_FACTOR: float = 0.68


_AIRFOIL_TC_BY_STATION = [
    (0.000, 0.333, 0.098),   
    (0.333, 0.667, 0.130),   
    (0.667, 1.001, 0.098),   
]


def _t_over_c(r_R: float) -> float:

    for r_lo, r_hi, tc in _AIRFOIL_TC_BY_STATION:
        if r_lo <= r_R < r_hi:
            return tc
    return _AIRFOIL_TC_BY_STATION[-1][2]   



def _read_blade_table(excel_path: str):

    try:
        import openpyxl
    except ImportError:
        raise ImportError(
            "openpyxl is required: pip install openpyxl"
        )

    wb = openpyxl.load_workbook(excel_path, read_only=True, data_only=True)
    ws = wb.worksheets[0]

    rows = list(ws.iter_rows(values_only=True))
    if not rows:
        raise ValueError(f"No data found in {excel_path} sheet 'blade_data'")

    # First row is the header
    header = [str(h).strip().lower() for h in rows[0]]
    try:
        i_rR= header.index("r_r")
        i_ccmax= header.index("c_cmax")
        i_twist= header.index("twist_deg")
    except ValueError as e:
        raise ValueError(f"Expected columns r_R, c_cmax, twist_deg in {excel_path}. Got: {header}") from e

    data = []
    for row in rows[1:]:
        try:
            r_R= float(row[i_rR])
            c_cmax = float(row[i_ccmax])
            twist= float(row[i_twist])
            data.append({"r_R": r_R, "c_cmax": c_cmax, "twist_deg": twist})
        except (TypeError, ValueError):
            continue  

    if len(data) < 2:
        return []  

    data.sort(key=lambda d: d["r_R"])
    return data


def _blade_volume_m3(
    stations: list,
    prop_radius_m: float,
    hub_to_tip: float,
    max_chord_m: float,
) -> float:
    
    R = prop_radius_m
    r_hub = hub_to_tip   

    total_volume = 0.0

    for k in range(len(stations) - 1):
        s0 = stations[k]
        s1 = stations[k + 1]

        #Skip stations entirely inside the spinner
        if s1["r_R"] <= r_hub:
            continue

        rR_lo = max(s0["r_R"], r_hub)
        rR_hi = s1["r_R"]

        if rR_hi <= rR_lo:
            continue

        frac = (rR_lo - s0["r_R"]) / (s1["r_R"] - s0["r_R"] + 1e-12)
        ccmax_lo = s0["c_cmax"] + frac * (s1["c_cmax"] - s0["c_cmax"])
        ccmax_hi = s1["c_cmax"]

        c_lo = ccmax_lo * max_chord_m
        c_hi = ccmax_hi * max_chord_m

        tc_lo = _t_over_c(rR_lo)
        tc_hi = _t_over_c(rR_hi)

        A_lo = AIRFOIL_AREA_FACTOR * tc_lo * c_lo ** 2
        A_hi = AIRFOIL_AREA_FACTOR * tc_hi * c_hi ** 2

        dr = (rR_hi - rR_lo) * R
        total_volume += 0.5 * (A_lo + A_hi) * dr

    return total_volume




def _estimate_max_chord(stations: list, prop_radius_m: float) -> float:
    
    return 0.15 * prop_radius_m




def run_model(inputs: dict) -> dict:
    

    excel_path= str(inputs["excel_path"])
    prop_radius_m = float(inputs["prop_radius_m"])
    blade_count= int(round(float(inputs["blade_count"])))
    hub_to_tip= float(inputs["hub_to_tip"])

    material_density = float(inputs.get("material_density_kg_m3", MATERIAL_DENSITY_KG_M3))


    if "max_chord_m" in inputs and inputs["max_chord_m"]:
        max_chord_m = float(inputs["max_chord_m"])
    else:
        max_chord_m = None   # will be estimated below

    if not os.path.isfile(excel_path):
        raise FileNotFoundError(f"Blade geometry file not found: {excel_path}")
    if prop_radius_m <= 0:
        raise ValueError(f"prop_radius_m must be > 0, got {prop_radius_m}")
    if blade_count < 1:
        raise ValueError(f"blade_count must be >= 1, got {blade_count}")
    if not (0 < hub_to_tip < 1):
        raise ValueError(f"hub_to_tip must be in (0, 1), got {hub_to_tip}")


    stations = _read_blade_table(excel_path)


    if len(stations) < 2:
        penalty = 1e6
        return {
            "weight_per_blade_kg":penalty,
            "total_assembly_weight_kg": penalty * blade_count,
            "blade_volume_m3":0.0,
            "max_chord_m_used":0.0,
            "n_stations":len(stations),
        }

   
    if max_chord_m is None:
        max_chord_m = _estimate_max_chord(stations, prop_radius_m)


    blade_vol_m3 = _blade_volume_m3(stations, prop_radius_m, hub_to_tip, max_chord_m)

    weight_per_blade_kg= material_density * blade_vol_m3
    total_assembly_weight_kg = weight_per_blade_kg * blade_count


    return {
        "weight_per_blade_kg":weight_per_blade_kg,
        "total_assembly_weight_kg": total_assembly_weight_kg,
        "blade_volume_m3":blade_vol_m3,
        "max_chord_m_used":max_chord_m,
        "n_stations":len(stations),
    }



if __name__ == "__main__":
    import sys

    excel   = sys.argv[1] if len(sys.argv) > 1 else r"C:\Users\Arnav\Desktop\Career\MSc Aerospace\KBE\parapy_tutorial\ProjectUpdated\KBE\blade_data_output2.xlsx"
    R       = float(sys.argv[2]) if len(sys.argv) > 2 else 1.5
    blades  = int(sys.argv[3])   if len(sys.argv) > 3 else 3
    h2t     = float(sys.argv[4]) if len(sys.argv) > 4 else 0.2

    result = run_model({
        "excel_path":    excel,
        "prop_radius_m": R,
        "blade_count":   blades,
        "hub_to_tip":    h2t,
    })

    print("\nOutputs:")
    for k, v in result.items():
        print(f"  {k:<30} = {v}")