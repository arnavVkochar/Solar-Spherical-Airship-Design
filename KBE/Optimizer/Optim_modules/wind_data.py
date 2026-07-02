

import pandas as pd
from pathlib import Path
import env_Arnesh as env

EXCEL_PATH = env.mission_plan_file_path
SHEET_NAME = "Wind Data"

_wind_df: pd.DataFrame | None = None



def _load_data(excel_path: str = EXCEL_PATH, sheet_name: str = SHEET_NAME) -> pd.DataFrame:

    global _wind_df
    if _wind_df is None:
        path = Path(excel_path)
        if not path.exists():
            raise FileNotFoundError(f"Excel file not found: {path}")
        _wind_df = pd.read_excel(path, sheet_name=sheet_name)
        required = {"GridSize_deg", "SW_Lat", "SW_Lon", "Speed_mps", "Direction_deg"}
        missing = required - set(_wind_df.columns)
        if missing:
            raise ValueError(f"Missing columns in sheet '{sheet_name}': {missing}")
    return _wind_df



def _lookup_wind(latitude: float, longitude: float) -> tuple[float, float]:

    df = _load_data()

    mask = (
        (df["SW_Lat"] <= latitude)  & (latitude  < df["SW_Lat"] + df["GridSize_deg"]) &
        (df["SW_Lon"] <= longitude) & (longitude < df["SW_Lon"] + df["GridSize_deg"])
    )

    matches = df[mask]

    if matches.empty:
        raise ValueError(
            f"No wind grid cell found for lat={latitude:.5f}, lon={longitude:.5f}. "
            "Point may be outside the covered area."
        )

    if len(matches) > 1:
        matches = matches.sort_values("GridSize_deg")  # prefer smallest/most precise cell

    row = matches.iloc[0]
    return float(row["Speed_mps"]), float(row["Direction_deg"])




def run_model(inputs: dict) -> dict:

    latitude  = float(inputs["latitude"])
    longitude = float(inputs["longitude"])


    if not (-90.0 <= latitude <= 90.0):
        raise ValueError(f"latitude must be in [-90, 90], got {latitude}")
    if not (-180.0 <= longitude <= 180.0):
        raise ValueError(f"longitude must be in [-180, 180], got {longitude}")


    speed_mps, direction_deg = _lookup_wind(latitude, longitude)


    return {
        "wind_speed_mps":     speed_mps,
        "wind_direction_deg": direction_deg,
    }


def reload_data() -> None:
    """Force a fresh read from Excel on the next call to run_model()."""
    global _wind_df
    _wind_df = None



if __name__ == "__main__":
    import sys

    lat = float(sys.argv[1]) if len(sys.argv) > 1 else 52.1419
    lon = float(sys.argv[2]) if len(sys.argv) > 2 else 5.1292

    test_input = {"latitude": lat, "longitude": lon}
    print(f"\nTest inputs: {test_input}")

    result = run_model(test_input)
    print("\nOutputs:")
    for k, v in result.items():
        print(f"  {k:<26} = {v:.6g}")