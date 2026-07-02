
from datetime import datetime, timedelta



def run_model(inputs: dict) -> dict:

    start_year      = int(float(inputs["start_year"]))
    start_month     = int(float(inputs["start_month"]))
    start_day       = int(float(inputs["start_day"]))
    start_hour      = int(float(inputs["start_hour"]))
    start_minute    = int(float(inputs["start_minute"]))
    elapsed_seconds = float(inputs["elapsed_seconds"])

    if not (1 <= start_month <= 12):
        raise ValueError(f"start_month must be 1-12, got {start_month}")
    if not (0 <= start_hour <= 23):
        raise ValueError(f"start_hour must be 0-23, got {start_hour}")
    if not (0 <= start_minute <= 59):
        raise ValueError(f"start_minute must be 0-59, got {start_minute}")
    if elapsed_seconds < 0:
        raise ValueError(f"elapsed_seconds must be >= 0, got {elapsed_seconds}")


    elapsed_minutes = int(elapsed_seconds // 60)


    start_dt = datetime(start_year, start_month, start_day,
                        start_hour, start_minute, 0)


    new_dt = start_dt + timedelta(minutes=elapsed_minutes)

    return {
        "new_year":         new_dt.year,
        "new_month":        new_dt.month,
        "new_day":          new_dt.day,
        "new_hour":         new_dt.hour,
        "new_minute":       new_dt.minute,
        "new_datetime_str": new_dt.strftime("%Y-%m-%d %H:%M"),
        "elapsed_minutes":  elapsed_minutes,
    }



if __name__ == "__main__":
    import sys

    test_input = {
        "start_year":      int(sys.argv[1])   if len(sys.argv) > 1 else 2025,
        "start_month":     int(sys.argv[2])   if len(sys.argv) > 2 else 6,
        "start_day":       int(sys.argv[3])   if len(sys.argv) > 3 else 15,
        "start_hour":      int(sys.argv[4])   if len(sys.argv) > 4 else 8,
        "start_minute":    int(sys.argv[5])   if len(sys.argv) > 5 else 30,
        "elapsed_seconds": float(sys.argv[6]) if len(sys.argv) > 6 else 13500.0,
    }

    print(f"\nTest inputs:  {test_input}")
    result = run_model(test_input)
    print("\nOutputs:")
    for k, v in result.items():
        print(f"  {k:<22} = {v}")