
import os
import mysql.connector
from dotenv import load_dotenv

load_dotenv()


def get_connection(database=None):
    """Connect to the explicitly requested database, if provided."""
    db_name = database or os.getenv(
        "DB_NAME",
        "learnguard_analytics"
    )

    return mysql.connector.connect(
        host=os.getenv("DB_HOST", "127.0.0.1"),
        port=int(os.getenv("DB_PORT", "3306")),
        user=os.getenv("DB_USER", "root"),
        password=os.getenv("DB_PASSWORD", ""),
        database=db_name,
    )
