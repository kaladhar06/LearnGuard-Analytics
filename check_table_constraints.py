
from src.db_connection import get_connection

conn = get_connection(database="learnguard_staging")
cur = conn.cursor()

try:
    for table in ["ContentItem", "Assessment", "CompletionRule"]:
        print("\n" + "=" * 60)
        print("TABLE:", table)

        cur.execute(f"SHOW CREATE TABLE `{table}`")
        print(cur.fetchone()[1])

        cur.execute(f"SHOW INDEX FROM `{table}`")
        for row in cur.fetchall():
            print("INDEX:", row)

finally:
    cur.close()
    conn.close()
