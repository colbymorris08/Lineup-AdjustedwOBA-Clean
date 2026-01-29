from pybaseball import statcast
import pandas as pd
from time import sleep
from datetime import datetime, timedelta

# Parameters
start_date = datetime(2024, 3, 28)
end_date = datetime(2024, 10, 3)
delta = timedelta(days=10)

# Loop in 10-day chunks
current = start_date
while current <= end_date:
    chunk_start = current
    chunk_end = min(current + delta - timedelta(days=1), end_date)

    label = chunk_start.strftime("%Y_%m_%d") + "_to_" + chunk_end.strftime("%Y_%m_%d")
    print(f"📥 Downloading Statcast data: {chunk_start.date()} to {chunk_end.date()}")

    try:
        df = statcast(start_dt=str(chunk_start.date()), end_dt=str(chunk_end.date()))
        filename = f"statcast_{label}.csv"
        df.to_csv(filename, index=False)
        print(f"✅ Saved to {filename} | Rows: {len(df)}")
    except Exception as e:
        print(f"❌ Error for {label}: {e}")

    current += delta
    sleep(10)  # Respect rate limits

print("✅ All chunks downloaded.")
