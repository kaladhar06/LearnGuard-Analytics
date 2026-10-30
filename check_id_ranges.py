
from src.db_connection import get_connection

connection = get_connection(database="learnguard_staging")
cursor = connection.cursor()

try:
    cursor.execute("SELECT DATABASE()")
    print("Connected database:", cursor.fetchone()[0])

    for table, column in [
        ("Learner", "learner_id"),
        ("Course", "course_id"),
        ("Enrollment", "enrollment_id"),
    ]:
        cursor.execute(
            f"SELECT MIN({column}), MAX({column}), COUNT(*) FROM {table}"
        )
        minimum, maximum, count = cursor.fetchone()
        print(f"\n{table}: count={count}, min={minimum}, max={maximum}")
finally:
    cursor.close()
    connection.close()
