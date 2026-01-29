import pandas as pd

# Load large CSV in chunks
chunk_size = 100_000  # Adjust based on row size
chunks = pd.read_csv("statcast_2024_full.csv", chunksize=chunk_size)

# Write chunks into separate files
for i, chunk in enumerate(chunks):
    chunk.to_csv(f"statcast_2024_part{i+1}.csv", index=False)
