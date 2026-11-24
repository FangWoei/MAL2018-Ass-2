"""Create the CW2 database objects by running every file in /sql in order."""
import glob
import os
import re
import sys
import time

import pyodbc
from dotenv import load_dotenv

load_dotenv()

HOST = os.getenv("DB_HOST", "localhost")
PORT = os.getenv("DB_PORT", "1434")
PASSWORD = os.getenv("DB_SA_PASSWORD")
SQL_DIR = os.getenv(
    "SQL_DIR",
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "sql"),
)

CONN_STR = (
    "DRIVER={ODBC Driver 18 for SQL Server};"
    f"SERVER={HOST},{PORT};DATABASE=master;UID=sa;PWD={{{PASSWORD}}};"
    "TrustServerCertificate=yes;"
)


def connect(retries=60, delay=2):
    """SQL Server needs a while to start, so retry instead of failing at once."""
    for attempt in range(1, retries + 1):
        try:
            # autocommit is required because CREATE DATABASE cannot run in a transaction
            return pyodbc.connect(CONN_STR, autocommit=True, timeout=5)
        except pyodbc.Error:
            print(f"Waiting for the database ({attempt}/{retries})...")
            time.sleep(delay)
    sys.exit("The database did not become ready in time.")


def split_batches(script):
    """Split a script into batches at lines that contain only GO."""
    parts = re.split(r"^\s*GO\s*$", script, flags=re.IGNORECASE | re.MULTILINE)
    return [part.strip() for part in parts if part.strip()]


def run_file(cursor, path):
    with open(path, encoding="utf-8-sig") as handle:  # utf-8-sig copes with a BOM
        script = handle.read()
    for batch in split_batches(script):
        cursor.execute(batch)
        while cursor.nextset():  # makes pyodbc raise errors from later statements
            pass


def main():
    if not PASSWORD:
        sys.exit("DB_SA_PASSWORD is not set (see .env.example).")

    connection = connect()
    cursor = connection.cursor()
    for path in sorted(glob.glob(os.path.join(SQL_DIR, "*.sql"))):
        print("Running", os.path.basename(path))
        run_file(cursor, path)
    print("Database ready.")
    connection.close()


if __name__ == "__main__":
    main()