import os
import sqlite3
from datetime import datetime


# ============================================================
# PATHS
# ============================================================

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

DATA_DIR = os.path.join(BASE_DIR, "data")

DB_PATH = os.path.join(DATA_DIR, "printing.db")


# ============================================================
# DATABASE CONNECTION
# ============================================================

def get_connection():
    """
    Create and return a connection to the SQLite database.
    """

    os.makedirs(DATA_DIR, exist_ok=True)

    connection = sqlite3.connect(DB_PATH)

    connection.row_factory = sqlite3.Row

    return connection


# ============================================================
# DATABASE HELPERS
# ============================================================

def _get_columns(cursor, table):
    """
    Get all column names from a table.
    """

    cursor.execute(f"PRAGMA table_info({table})")

    return {
        row["name"]
        for row in cursor.fetchall()
    }


def _add_column_if_missing(cursor, table, column, definition):
    """
    Add a column if it does not already exist.
    """

    columns = _get_columns(cursor, table)

    if column not in columns:

        cursor.execute(
            f"ALTER TABLE {table} ADD COLUMN {column} {definition}"
        )


# ============================================================
# INITIALIZE DATABASE
# ============================================================

def init_db():

    connection = get_connection()

    cursor = connection.cursor()

    # --------------------------------------------------------
    # PRINT JOBS TABLE
    # --------------------------------------------------------

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS print_jobs (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            file_path TEXT NOT NULL,

            printer TEXT NOT NULL,

            copies INTEGER DEFAULT 1,

            trigger_type TEXT NOT NULL,

            status TEXT NOT NULL,

            error TEXT,

            paper_size TEXT DEFAULT 'A4',

            orientation TEXT DEFAULT 'Portrait',

            color_mode TEXT DEFAULT 'Color',

            duplex INTEGER DEFAULT 0,

            timestamp TEXT NOT NULL,

            created_at TEXT

        )
    """)

    # --------------------------------------------------------
    # SCHEDULES TABLE
    # --------------------------------------------------------

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS schedules (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            file_path TEXT NOT NULL,

            printer TEXT NOT NULL,

            print_time TEXT NOT NULL,

            time TEXT NOT NULL,

            days TEXT NOT NULL,

            copies INTEGER DEFAULT 1,

            paper_size TEXT DEFAULT 'A4',

            orientation TEXT DEFAULT 'Portrait',

            color_mode TEXT DEFAULT 'Color',

            duplex INTEGER DEFAULT 0,

            enabled INTEGER DEFAULT 1,

            timestamp TEXT NOT NULL,

            created_at TEXT

        )
    """)

    # ========================================================
    # PRINT JOBS MIGRATION
    # ========================================================

    _add_column_if_missing(
        cursor,
        "print_jobs",
        "file_path",
        "TEXT"
    )

    _add_column_if_missing(
        cursor,
        "print_jobs",
        "printer",
        "TEXT"
    )

    _add_column_if_missing(
        cursor,
        "print_jobs",
        "copies",
        "INTEGER DEFAULT 1"
    )

    _add_column_if_missing(
        cursor,
        "print_jobs",
        "trigger_type",
        "TEXT"
    )

    _add_column_if_missing(
        cursor,
        "print_jobs",
        "status",
        "TEXT"
    )

    _add_column_if_missing(
        cursor,
        "print_jobs",
        "error",
        "TEXT"
    )

    _add_column_if_missing(
        cursor,
        "print_jobs",
        "paper_size",
        "TEXT DEFAULT 'A4'"
    )

    _add_column_if_missing(
        cursor,
        "print_jobs",
        "orientation",
        "TEXT DEFAULT 'Portrait'"
    )

    _add_column_if_missing(
        cursor,
        "print_jobs",
        "color_mode",
        "TEXT DEFAULT 'Color'"
    )

    _add_column_if_missing(
        cursor,
        "print_jobs",
        "duplex",
        "INTEGER DEFAULT 0"
    )

    _add_column_if_missing(
        cursor,
        "print_jobs",
        "timestamp",
        "TEXT NOT NULL DEFAULT ''"
    )

    _add_column_if_missing(
        cursor,
        "print_jobs",
        "created_at",
        "TEXT"
    )

    # ========================================================
    # SCHEDULES MIGRATION
    # ========================================================

    _add_column_if_missing(
        cursor,
        "schedules",
        "file_path",
        "TEXT"
    )

    _add_column_if_missing(
        cursor,
        "schedules",
        "printer",
        "TEXT"
    )

    _add_column_if_missing(
        cursor,
        "schedules",
        "print_time",
        "TEXT"
    )

    # IMPORTANT:
    # Older database uses a required "time" column.
    # Keep it and fill it whenever a schedule is created.

    _add_column_if_missing(
        cursor,
        "schedules",
        "time",
        "TEXT NOT NULL DEFAULT ''"
    )

    _add_column_if_missing(
        cursor,
        "schedules",
        "days",
        "TEXT DEFAULT 'Every day'"
    )

    _add_column_if_missing(
        cursor,
        "schedules",
        "copies",
        "INTEGER DEFAULT 1"
    )

    _add_column_if_missing(
        cursor,
        "schedules",
        "paper_size",
        "TEXT DEFAULT 'A4'"
    )

    _add_column_if_missing(
        cursor,
        "schedules",
        "orientation",
        "TEXT DEFAULT 'Portrait'"
    )

    _add_column_if_missing(
        cursor,
        "schedules",
        "color_mode",
        "TEXT DEFAULT 'Color'"
    )

    _add_column_if_missing(
        cursor,
        "schedules",
        "duplex",
        "INTEGER DEFAULT 0"
    )

    _add_column_if_missing(
        cursor,
        "schedules",
        "enabled",
        "INTEGER DEFAULT 1"
    )

    _add_column_if_missing(
        cursor,
        "schedules",
        "timestamp",
        "TEXT NOT NULL DEFAULT ''"
    )

    _add_column_if_missing(
        cursor,
        "schedules",
        "created_at",
        "TEXT"
    )

    # --------------------------------------------------------
    # SAVE CHANGES
    # --------------------------------------------------------

    connection.commit()

    connection.close()


# ============================================================
# ADD PRINT JOB
# ============================================================

def add_job(
    file_path,
    printer,
    copies,
    trigger_type,
    status,
    error=None,
    paper_size="A4",
    orientation="Portrait",
    color_mode="Color",
    duplex=False
):

    connection = get_connection()

    cursor = connection.cursor()

    now = datetime.now().isoformat(
        timespec="seconds"
    )

    cursor.execute("""
        INSERT INTO print_jobs
        (
            file_path,
            printer,
            copies,
            trigger_type,
            status,
            error,
            paper_size,
            orientation,
            color_mode,
            duplex,
            timestamp,
            created_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        file_path,
        printer,
        copies,
        trigger_type,
        status,
        error,
        paper_size,
        orientation,
        color_mode,
        1 if duplex else 0,
        now,
        now
    ))

    connection.commit()

    connection.close()


# ============================================================
# GET RECENT PRINT JOBS
# ============================================================

def recent_jobs(limit=50):

    connection = get_connection()

    rows = connection.execute("""
        SELECT
            id,
            file_path,
            printer,
            copies,
            trigger_type,
            status,
            error,
            paper_size,
            orientation,
            color_mode,
            duplex,
            timestamp,
            created_at

        FROM print_jobs

        ORDER BY id DESC

        LIMIT ?
    """, (limit,)).fetchall()

    connection.close()

    jobs = []

    for row in rows:

        item = dict(row)

        # Older records may not have created_at.
        # Use timestamp instead.

        if not item.get("created_at"):

            item["created_at"] = item.get("timestamp")

        jobs.append(item)

    return jobs


# ============================================================
# ADD SCHEDULE
# ============================================================

def add_schedule(
    file_path,
    printer,
    print_time,
    days,
    copies=1,
    paper_size="A4",
    orientation="Portrait",
    color_mode="Color",
    duplex=False
):

    connection = get_connection()

    cursor = connection.cursor()

    now = datetime.now().isoformat(
        timespec="seconds"
    )

    # IMPORTANT:
    # Both "print_time" and the older "time" column
    # receive the same schedule time.

    cursor.execute("""
        INSERT INTO schedules
        (
            file_path,
            printer,
            print_time,
            time,
            days,
            copies,
            paper_size,
            orientation,
            color_mode,
            duplex,
            enabled,
            timestamp,
            created_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1, ?, ?)
    """, (
        file_path,
        printer,
        print_time,
        print_time,
        days,
        copies,
        paper_size,
        orientation,
        color_mode,
        1 if duplex else 0,
        now,
        now
    ))

    schedule_id = cursor.lastrowid

    connection.commit()

    connection.close()

    return schedule_id


# ============================================================
# LIST SCHEDULES
# ============================================================

def list_schedules():

    connection = get_connection()

    rows = connection.execute("""
        SELECT
            id,
            file_path,
            printer,
            print_time,
            time,
            days,
            copies,
            paper_size,
            orientation,
            color_mode,
            duplex,
            enabled,
            timestamp,
            created_at

        FROM schedules

        ORDER BY print_time ASC, id ASC
    """).fetchall()

    connection.close()

    schedules = []

    for row in rows:

        item = dict(row)

        # If print_time is empty for an older record,
        # use the old "time" field.

        if not item.get("print_time"):

            item["print_time"] = item.get("time")

        # Older records may not have created_at.

        if not item.get("created_at"):

            item["created_at"] = item.get("timestamp")

        schedules.append(item)

    return schedules


# ============================================================
# TOGGLE SCHEDULE
# ============================================================

def toggle_schedule(schedule_id):

    connection = get_connection()

    connection.execute("""
        UPDATE schedules

        SET enabled =
            CASE
                WHEN enabled = 1 THEN 0
                ELSE 1
            END

        WHERE id = ?
    """, (schedule_id,))

    connection.commit()

    connection.close()


# ============================================================
# DELETE SCHEDULE
# ============================================================

def delete_schedule(schedule_id):

    connection = get_connection()

    connection.execute("""
        DELETE FROM schedules

        WHERE id = ?
    """, (schedule_id,))

    connection.commit()

    connection.close()