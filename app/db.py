"""Database access. Every query uses parameters, so input is never pasted into SQL."""
import os
from datetime import date, datetime

import pyodbc


def _connection_string():
    host = os.getenv("DB_HOST", "localhost")
    port = os.getenv("DB_PORT", "1434")
    user = os.getenv("DB_USER", "sa")
    password = os.getenv("DB_PASSWORD") or os.getenv("DB_SA_PASSWORD")
    return (
        "DRIVER={ODBC Driver 18 for SQL Server};"
        f"SERVER={host},{port};DATABASE=MAL2018_Profile;"
        f"UID={user};PWD={{{password}}};TrustServerCertificate=yes;"
    )


def query(sql, params=()):
    """Run one statement and return the rows as a list of dictionaries."""
    connection = pyodbc.connect(_connection_string(), timeout=5)
    try:
        cursor = connection.cursor()
        cursor.execute(sql, params)
        rows = []
        if cursor.description:
            columns = [column[0] for column in cursor.description]
            for record in cursor.fetchall():
                row = {}
                for name, value in zip(columns, record):
                    row[name] = value.isoformat() if isinstance(value, (date, datetime)) else value
                rows.append(row)
        connection.commit()
        return rows
    finally:
        connection.close()


def has_error(exc, code):
    """True if a pyodbc error came from THROW <code> in a stored procedure."""
    return f"({code})" in str(exc)