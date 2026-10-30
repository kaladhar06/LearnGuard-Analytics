
import csv
import hashlib
import shutil
from pathlib import Path

source = Path("data/generated_activity_preview.csv")
backup = Path.home() / "OneDrive" / "Desktop" / "generated_activity_2million.csv"

if not source.exists():
    raise FileNotFoundError(source)

sha256 = hashlib.sha256()
row_count = 0

with source.open("rb") as f:
    for chunk in iter(lambda: f.read(1024 * 1024), b""):
        sha256.update(chunk)

with source.open("r", newline="", encoding="utf-8") as f:
    reader = csv.reader(f)
    header = next(reader)
    for _ in reader:
        row_count += 1

print("CSV rows:", row_count)
print("Columns:", len(header))
print("Header:", header)
print("File size:", source.stat().st_size)
print("SHA256:", sha256.hexdigest())

if row_count != 2_000_000 or len(header) != 11:
    raise RuntimeError("CSV verification failed.")

backup.parent.mkdir(parents=True, exist_ok=True)
shutil.copy2(source, backup)

print("Backup created:", backup)
print("Backup size:", backup.stat().st_size)
print("\nCSV verification successful.")
