"""Shared core: configuration, the TiDB storage layer and the helpers every feature module uses."""
from flask import Flask, render_template, request, redirect, url_for, jsonify, session, send_from_directory


import csv, os, shutil, tempfile, uuid


from collections import Counter


from email.message import EmailMessage


from werkzeug.security import generate_password_hash, check_password_hash


from werkzeug.utils import secure_filename


from functools import wraps


import json


import re


import smtplib


import ssl


import threading


import time


from datetime import datetime, timedelta


from urllib import parse, request as urllib_request, error as urllib_error


try:
    from backend.taskvise_admin import admin_manager as taskvise_admin_manager
except Exception:
    taskvise_admin_manager = None


BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # repository root


try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass


IS_VERCEL = os.environ.get("VERCEL") == "1" or bool(os.environ.get("VERCEL_ENV"))


SOURCE_DATA_DIR = os.path.join(BASE_DIR, "data")


SOURCE_STATIC_DIR = os.path.join(BASE_DIR, "static")


STORAGE_ROOT = os.environ.get(
    "TASKVISE_STORAGE_DIR",
    os.path.join(tempfile.gettempdir(), "taskvise") if IS_VERCEL else BASE_DIR
)


TASKVISE_ADMIN_URL = os.environ.get('TASKVISE_ADMIN_URL', 'http://127.0.0.1:5051').rstrip('/')


DATA_DIR = os.path.join(STORAGE_ROOT, "data")


USERS_CSV = os.path.join(DATA_DIR, "users.csv")


EMP_CSV = os.path.join(DATA_DIR, "employees.csv")


TASKS_CSV = os.path.join(DATA_DIR, "tasks.csv")


PROJECTS_CSV = os.path.join(DATA_DIR, "projects.csv")


PROJECT_MEMBERS_CSV = os.path.join(DATA_DIR, "project_members.csv")


LEAVE_CSV = os.path.join(DATA_DIR, "leave.csv")


NOTES_CSV = os.path.join(DATA_DIR, "team_notes.csv")


WORK_CSV = os.path.join(DATA_DIR, "work.csv")


NOTIF_CSV = os.path.join(DATA_DIR, "notifications.csv")


SETTINGS_CSV = os.path.join(DATA_DIR, "settings.csv")


HELP_REQUESTS_CSV = os.path.join(DATA_DIR, "help_requests.csv")


CREDENTIALS_EXPORT_TXT = os.path.join(DATA_DIR, "login_credentials.txt")


TEAMS_CSV = os.path.join(DATA_DIR, "teams.csv")


PAYMENTS_CSV = os.path.join(DATA_DIR, "payments.csv")


ADMIN_DATA_DIR = os.path.join(DATA_DIR, "admin")


AVATAR_UPLOAD_DIR = os.path.join(STORAGE_ROOT, "static", "uploads", "avatars")


TASK_SUBMISSIONS_CSV = os.path.join(DATA_DIR, "task_submissions.csv")


TASK_SUBMISSION_UPLOAD_DIR = os.path.join(STORAGE_ROOT, "static", "uploads", "task_submissions")


def _ensure_runtime_storage():
    os.makedirs(DATA_DIR, exist_ok=True)
    if os.path.abspath(DATA_DIR) != os.path.abspath(SOURCE_DATA_DIR) and os.path.isdir(SOURCE_DATA_DIR):
        for name in os.listdir(SOURCE_DATA_DIR):
            source_path = os.path.join(SOURCE_DATA_DIR, name)
            target_path = os.path.join(DATA_DIR, name)
            if os.path.isdir(source_path):
                if not os.path.exists(target_path):
                    shutil.copytree(source_path, target_path)
            elif not os.path.exists(target_path):
                shutil.copy2(source_path, target_path)
    os.makedirs(ADMIN_DATA_DIR, exist_ok=True)
    os.makedirs(AVATAR_UPLOAD_DIR, exist_ok=True)
    os.makedirs(TASK_SUBMISSION_UPLOAD_DIR, exist_ok=True)


_ensure_runtime_storage()


try:
    import mysql.connector
except Exception:
    mysql = None


try:
    from pymongo import MongoClient
except Exception:
    MongoClient = None


DB_BACKEND = "mysql"


MONGO_REQUIRED = False


MIRROR_MONGODB = False


CSV_SHADOW_SYNC = False


MONGO_URI = ""


MONGO_DATABASE = "taskvise"


MYSQL_HOST = os.environ.get("MYSQL_HOST", "").strip()


MYSQL_PORT = int(os.environ.get("MYSQL_PORT", "4000"))


MYSQL_USER = os.environ.get("MYSQL_USER", "").strip()


MYSQL_PASSWORD = os.environ.get("MYSQL_PASSWORD", "")


MYSQL_DATABASE = os.environ.get("MYSQL_DATABASE", "taskvise").strip() or "taskvise"


MIRROR_MYSQL = False


if not (MYSQL_HOST and MYSQL_USER and MYSQL_PASSWORD):
    raise RuntimeError("Database is not configured. Set MYSQL_HOST, MYSQL_USER and MYSQL_PASSWORD (TiDB Cloud) before starting TaskVise.")


EMAIL_NOTIFICATIONS_ENABLED = os.environ.get(
    "TASKVISE_EMAIL_NOTIFICATIONS",
    "true"
).strip().lower() in {"1", "true", "yes", "on"}


SMTP_HOST = os.environ.get("SMTP_HOST", "").strip()


SMTP_PORT = int(os.environ.get("SMTP_PORT", "587"))


SMTP_USER = os.environ.get("SMTP_USER", "").strip()


SMTP_PASSWORD = os.environ.get("SMTP_PASSWORD", "")


SMTP_FROM = os.environ.get("SMTP_FROM", SMTP_USER).strip()


SMTP_USE_TLS = os.environ.get(
    "SMTP_USE_TLS",
    "true"
).strip().lower() in {"1", "true", "yes", "on"}


SYSTEM_SETTINGS_USER_ID = "__system__"


DEFAULT_COMPANY_NAME = "TaskVise HyperScale Operations Consortium"


PLATFORM_FOUNDER_EMAIL = os.environ.get("TASKVISE_FOUNDER_EMAIL", "").strip()


PLATFORM_FOUNDER_PASSWORD = os.environ.get("TASKVISE_FOUNDER_PASSWORD", "")


SEED_DEMO = os.environ.get("TASKVISE_SEED_DEMO", "").strip().lower() in {"1", "true", "yes", "on"} and not os.environ.get("VERCEL")


_DEMO_PASSWORD = os.environ.get("TASKVISE_DEMO_PASSWORD", "")


ROLE_DEFAULT_PASSWORDS = {role: _DEMO_PASSWORD for role in ("platform_admin", "admin", "manager", "hr", "teamlead", "employee")}


WORKFORCE_ID_PREFIX = "EMP"


WORKFORCE_ID_WIDTH = 3


PROJECT_ID_PREFIX = "PRJ"


PROJECT_ID_WIDTH = 4


TASK_ID_PREFIX = "TSK"


TASK_ID_WIDTH = 5


PROJECT_MEMBER_ID_PREFIX = "PMB"


PROJECT_MEMBER_ID_WIDTH = 5


TEAM_BLUEPRINTS = [
    {
        "id": "TEAM001",
        "name": "Code Comets",
        "department": "Engineering",
        "manager_id": "EMP004",
        "teamlead_id": "EMP010",
        "member_ids": ["EMP016", "EMP018", "EMP019", "EMP021", "EMP042"],
        "tagline": "Debug fast, ship faster.",
        "focus_area": "Core engineering, platforms, and delivery acceleration",
    },
    {
        "id": "TEAM002",
        "name": "Feature Falcons",
        "department": "Product",
        "manager_id": "EMP005",
        "teamlead_id": "EMP013",
        "member_ids": ["EMP017", "EMP020", "EMP023", "EMP024", "EMP041"],
        "tagline": "Turning roadmap chaos into launch-day magic.",
        "focus_area": "Product planning, discovery, design, and feature launches",
    },
    {
        "id": "TEAM003",
        "name": "Audit Avengers",
        "department": "Finance",
        "manager_id": "EMP006",
        "teamlead_id": "EMP012",
        "member_ids": ["EMP022", "EMP030", "EMP031", "EMP034", "EMP035"],
        "tagline": "Clean books, calm systems, zero drama.",
        "focus_area": "Finance operations, systems control, and compliance readiness",
    },
    {
        "id": "TEAM004",
        "name": "Pixel Pulse",
        "department": "Marketing",
        "manager_id": "EMP007",
        "teamlead_id": "EMP011",
        "member_ids": ["EMP025", "EMP026", "EMP027", "EMP038", "EMP043"],
        "tagline": "Brand sparkle with measurable pipeline juice.",
        "focus_area": "Creative production, campaigns, and customer storytelling",
    },
    {
        "id": "TEAM005",
        "name": "Quota Crushers",
        "department": "Sales",
        "manager_id": "EMP008",
        "teamlead_id": "EMP014",
        "member_ids": ["EMP028", "EMP029", "EMP037", "EMP039", "EMP045"],
        "tagline": "Closing deals before the coffee gets cold.",
        "focus_area": "Revenue operations, enablement, and deal execution",
    },
    {
        "id": "TEAM006",
        "name": "Ops Oddballs",
        "department": "Operations",
        "manager_id": "EMP009",
        "teamlead_id": "EMP015",
        "member_ids": ["EMP032", "EMP033", "EMP036", "EMP040", "EMP044"],
        "tagline": "Chaos managed. Somehow stylishly.",
        "focus_area": "Operational excellence, support flow, and people enablement",
    },
]


ROLE_PAY_BANDS = {
    "platform_admin": 320000,
    "admin": 250000,
    "hr": 145000,
    "manager": 195000,
    "teamlead": 158000,
    "employee": 92000,
}


_ORG_STRUCTURE_BOOTSTRAPPED = False


STORAGE_TABLE_MAP = {
    USERS_CSV: "users",
    EMP_CSV: "employees",
    TASKS_CSV: "tasks",
    PROJECTS_CSV: "projects",
    PROJECT_MEMBERS_CSV: "project_members",
    LEAVE_CSV: "leave_requests",
    NOTES_CSV: "team_notes",
    WORK_CSV: "work_logs",
    NOTIF_CSV: "notifications",
    SETTINGS_CSV: "user_settings",
    TEAMS_CSV: "teams",
    PAYMENTS_CSV: "payments",
    TASK_SUBMISSIONS_CSV: "task_submissions",
    HELP_REQUESTS_CSV: "help_requests",
}


MYSQL_DEFAULT_COLUMNS = {
    "help_requests": ["id", "requester_id", "requester_name", "task_id", "task_title", "message", "urgency", "status", "recipient_type", "recipient_id", "recipient_name", "request_type", "created_at", "updated_at"],
    "users": ["id", "username", "password_hash", "full_name", "role", "created_at", "is_active"],
    "employees": ["id", "name", "email", "position", "department", "company", "join_date", "phone", "skills", "location", "last_login", "password_last_changed", "avatar_url", "status", "productivity"],
    "tasks": ["id", "title", "description", "project_id", "assignee_id", "assignee_name", "status", "priority", "created_at", "due_date", "estimated_hours", "actual_hours", "progress"],
    "projects": ["id", "name", "description", "owner_id", "start_date", "end_date", "status", "team_members", "company", "progress"],
    "project_members": ["id", "project_id", "employee_id"],
    "leave_requests": ["id", "employee_id", "start_date", "end_date", "reason", "type", "status", "applied_at"],
    "team_notes": ["id", "title", "content", "author", "author_id", "priority", "is_pinned", "created_at", "updated_at", "visible_to"],
    "work_logs": ["id", "employee_id", "task_id", "start_time", "end_time", "duration_minutes", "notes"],
    "notifications": ["id", "user_id", "title", "message", "type", "is_read", "created_at"],
    "teams": [
        "id", "name", "department", "manager_id", "manager_name", "teamlead_id", "teamlead_name",
        "member_ids", "tagline", "focus_area", "created_at", "updated_at"
    ],
    "payments": [
        "id", "employee_id", "employee_name", "role", "team_id", "team_name", "department",
        "base_salary", "bonus", "currency", "payment_status", "last_paid_date", "next_pay_date",
        "pay_cycle", "updated_at"
    ],
    "task_submissions": [
        "id", "task_id", "project_id", "employee_id", "employee_name", "manager_id", "teamlead_id",
        "recipient_ids", "original_filename", "stored_filename", "file_path", "file_size",
        "status", "notes", "created_at", "updated_at"
    ],
    "user_settings": [
        "id", "user_id", "email_notifications", "push_notifications", "task_reminders", "deadline_alerts",
        "theme", "language", "timezone", "updated_at", "company_name", "date_format", "session_timeout",
        "password_policy", "notify_task_assignments", "notify_project_updates", "notify_system_alerts",
        "desktop_notifications", "sound_alerts", "auto_backup", "data_retention", "api_access", "webhook_url"
    ],
}


_MYSQL_ENABLED = mysql is not None


_MONGO_ENABLED = MongoClient is not None


_MYSQL_BOOTSTRAPPED = False


if DB_BACKEND == "mysql" and mysql is None:
    if IS_VERCEL:
        raise RuntimeError("mysql-connector-python is not installed; CSV storage is not allowed in production.")
    print("mysql-connector-python is not installed. Falling back to CSV storage.")


if DB_BACKEND == "mongodb" and MongoClient is None:
    print("pymongo is not installed. Falling back to CSV storage.")


def _mongo_client():
    if not _MONGO_ENABLED:
        raise RuntimeError("MongoDB is not enabled or pymongo is not installed")
    return MongoClient(MONGO_URI)


def _mongo_collection(collection_name):
    client = _mongo_client()
    db = client[MONGO_DATABASE]
    return db[collection_name]


def _mongo_read_rows(path):
    collection_name = STORAGE_TABLE_MAP.get(path)
    if not collection_name:
        return []
    try:
        coll = _mongo_collection(collection_name)
        rows = []
        for doc in coll.find():
            row = {k: (str(v) if k == '_id' else v) for k,v in doc.items() if k != '_id'}
            rows.append(row)
        return rows
    except Exception as exc:
        if MONGO_REQUIRED and DB_BACKEND == "mongodb":
            raise RuntimeError(f"MongoDB read failed for {path}: {exc}") from exc
        print(f"MongoDB read error for {path}: {exc}. Falling back to CSV.")
        return _read_csv_file(path)


def _mongo_write_rows(path, rows, fieldnames):
    collection_name = STORAGE_TABLE_MAP.get(path)
    if not collection_name:
        return
    try:
        coll = _mongo_collection(collection_name)
        coll.delete_many({})
        if rows:
            coll.insert_many([{k: v for k, v in row.items()} for row in rows])
    except Exception as exc:
        if MONGO_REQUIRED and DB_BACKEND == "mongodb":
            raise RuntimeError(f"MongoDB write failed for {path}: {exc}") from exc
        print(f"MongoDB write error for {path}: {exc}. Falling back to CSV.")
        _write_csv_file(path, rows, fieldnames)


def _read_csv_file(path):
    if not os.path.exists(path):
        return []
    with open(path, newline='', encoding='utf-8') as f:
        return list(csv.DictReader(f))


def _write_csv_file(path, rows, fieldnames):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def _mongo_append_row(path, row, fieldnames):
    collection_name = STORAGE_TABLE_MAP.get(path)
    if not collection_name:
        return

    try:
        coll = _mongo_collection(collection_name)
        coll.insert_one({k: v for k, v in row.items()})
    except Exception as exc:
        if MONGO_REQUIRED and DB_BACKEND == "mongodb":
            raise RuntimeError(f"MongoDB append failed for {path}: {exc}") from exc
        print(f"MongoDB append error for {path}: {exc}. Falling back to CSV.")
        if fieldnames is None:
            fieldnames = list(row.keys())
        _write_csv_file(path, _read_csv_file(path) + [row], fieldnames)


def _mongo_update_by_id(path, id, updates):
    """Direct MongoDB update by ID"""
    collection_name = STORAGE_TABLE_MAP.get(path)
    if not collection_name:
        return False

    try:
        coll = _mongo_collection(collection_name)
        result = coll.update_one({'id': id}, {'$set': updates})
        return result.matched_count > 0
    except Exception as exc:
        print(f"MongoDB update error for {path}: {exc}")
        return False


def _mongo_delete_by_id(path, id):
    """Direct MongoDB delete by ID"""
    collection_name = STORAGE_TABLE_MAP.get(path)
    if not collection_name:
        return False

    try:
        coll = _mongo_collection(collection_name)
        result = coll.delete_one({'id': id})
        return result.deleted_count > 0
    except Exception as exc:
        print(f"MongoDB delete error for {path}: {exc}")
        return False


def _mongo_bootstrap():
    if not _MONGO_ENABLED:
        return False
    try:
        for path in STORAGE_TABLE_MAP:
            collection_name = STORAGE_TABLE_MAP[path]
            coll = _mongo_collection(collection_name)
            coll.find_one()
        return True
    except Exception as exc:
        if MONGO_REQUIRED and DB_BACKEND == "mongodb":
            raise RuntimeError(f"MongoDB unavailable: {exc}") from exc
        print(f"MongoDB unavailable ({exc}). Falling back to CSV storage.")
        return False


def _use_mongo(path):
    return DB_BACKEND == 'mongodb' and _mongo_bootstrap()


def _collect_fieldnames(rows, preferred_fieldnames=None):
    names = []
    for name in preferred_fieldnames or []:
        if name and name not in names:
            names.append(name)
    for row in rows or []:
        for key in row.keys():
            if key and key not in names:
                names.append(key)
    return names


def _escape_identifier(name):
    return f"`{str(name).replace('`', '``')}`"


def _mysql_column_type(column_name):
    col = str(column_name or "").lower()
    if col == "id":
        return "VARCHAR(64)"
    if col in {"description", "reason", "notes", "content", "skills", "team_members"}:
        return "TEXT"
    if col in {"is_active", "is_pinned"}:
        return "VARCHAR(16)"
    if col in {"duration_minutes", "estimated_hours", "actual_hours"}:
        return "VARCHAR(32)"
    return "VARCHAR(255)"


class _PooledConnection:
    """One live connection per thread. close() keeps it open and only rolls back if something was written but not committed.

    Reads use READ COMMITTED, so a connection that stays open still sees other writers' data without a round trip."""

    _WRITE = re.compile(r"\s*(INSERT|UPDATE|DELETE|REPLACE|ALTER|CREATE|DROP|TRUNCATE)", re.I)

    def __init__(self, raw):
        self._raw = raw
        self._dirty = False
        self._last_used = time.time()

    def _is_write(self, sql):
        if isinstance(sql, (bytes, bytearray)):
            sql = sql.decode("utf-8", "ignore")
        return bool(self._WRITE.match(sql))

    def cursor(self, *args, **kwargs):
        cur = self._raw.cursor(*args, **kwargs)
        execute, executemany = cur.execute, cur.executemany

        def run(sql, *a, **k):
            if self._is_write(sql):
                self._dirty = True
            return execute(sql, *a, **k)

        def run_many(sql, *a, **k):
            if self._is_write(sql):
                self._dirty = True
            return executemany(sql, *a, **k)

        cur.execute, cur.executemany = run, run_many
        return cur

    def commit(self):
        self._raw.commit()
        self._dirty = False

    def rollback(self):
        self._raw.rollback()
        self._dirty = False

    def close(self):
        self._last_used = time.time()
        if self._dirty:
            try:
                self.rollback()
            except Exception:
                pass

    def __getattr__(self, name):
        return getattr(self._raw, name)


_mysql_local = threading.local()


def _mysql_connect(include_database=True):
    if mysql is None:
        raise RuntimeError("mysql-connector-python is not available")
    config = {
        "host": MYSQL_HOST,
        "port": MYSQL_PORT,
        "user": MYSQL_USER,
        "password": MYSQL_PASSWORD,
        "connection_timeout": int(os.environ.get("MYSQL_CONNECTION_TIMEOUT", "3")),
    }
    if not include_database:
        return mysql.connector.connect(**config)
    config["database"] = MYSQL_DATABASE
    # Reuse one connection per thread: opening a TLS connection per query made every page take many seconds.
    pooled = getattr(_mysql_local, "conn", None)
    if pooled is not None:
        try:
            if time.time() - pooled._last_used > 20:  # only check a connection that has been idle a while
                pooled._raw.ping(reconnect=True, attempts=2, delay=0)
            return pooled
        except Exception:
            _mysql_local.conn = None
    raw = mysql.connector.connect(**config)
    try:
        cur = raw.cursor()
        cur.execute("SET SESSION TRANSACTION ISOLATION LEVEL READ COMMITTED")
        cur.close()
    except Exception:
        pass  # a server that refuses it still works, just with snapshot reads
    _mysql_local.conn = _PooledConnection(raw)
    return _mysql_local.conn


def _mysql_ensure_database():
    conn = _mysql_connect(include_database=False)
    try:
        cur = conn.cursor()
        cur.execute(
            f"CREATE DATABASE IF NOT EXISTS {_escape_identifier(MYSQL_DATABASE)} "
            "CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
        )
        conn.commit()
    finally:
        conn.close()


def _mysql_existing_columns(table_name):
    conn = _mysql_connect(include_database=True)
    try:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT COLUMN_NAME
            FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_SCHEMA = %s AND TABLE_NAME = %s
            ORDER BY ORDINAL_POSITION
            """,
            (MYSQL_DATABASE, table_name),
        )
        return [row[0] for row in cur.fetchall()]
    finally:
        conn.close()


def _mysql_ensure_table(table_name, columns):
    cols = _collect_fieldnames([], columns) or ["id"]
    definitions = []
    has_id = False
    for col in cols:
        if col == "id":
            has_id = True
            definitions.append(f"{_escape_identifier(col)} {_mysql_column_type(col)} NOT NULL")
        else:
            definitions.append(f"{_escape_identifier(col)} {_mysql_column_type(col)} NULL")
    if not has_id:
        definitions.insert(0, "`id` VARCHAR(64) NOT NULL")
        has_id = True
    if has_id:
        definitions.append("PRIMARY KEY (`id`)")

    conn = _mysql_connect(include_database=True)
    try:
        cur = conn.cursor()
        cur.execute(
            f"CREATE TABLE IF NOT EXISTS {_escape_identifier(table_name)} "
            f"({', '.join(definitions)}) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4"
        )
        conn.commit()
    finally:
        conn.close()


def _mysql_ensure_columns(table_name, columns):
    missing = []
    existing = set(_mysql_existing_columns(table_name))
    for col in _collect_fieldnames([], columns):
        if col and col not in existing:
            missing.append(col)
    if not missing:
        return

    conn = _mysql_connect(include_database=True)
    try:
        cur = conn.cursor()
        for col in missing:
            cur.execute(
                f"ALTER TABLE {_escape_identifier(table_name)} "
                f"ADD COLUMN {_escape_identifier(col)} {_mysql_column_type(col)} NULL"
            )
        conn.commit()
    finally:
        conn.close()


def _mysql_schema_complete():
    try:
        conn = _mysql_connect(include_database=True)
        try:
            cur = conn.cursor()
            cur.execute("SELECT table_name, column_name FROM information_schema.columns WHERE table_schema = %s", (MYSQL_DATABASE,))
            have = {}
            for table, column in cur.fetchall():
                have.setdefault(str(table).lower(), set()).add(str(column).lower())
            cur.close()
        finally:
            conn.close()
        for table_name, columns in MYSQL_DEFAULT_COLUMNS.items():
            needed = {c.lower() for c in (_collect_fieldnames([], columns) or ["id"])} | {"id"}
            if not needed <= have.get(table_name.lower(), set()):
                return False
        return True
    except Exception:
        return False


def _mysql_bootstrap():
    global _MYSQL_BOOTSTRAPPED, _MYSQL_ENABLED
    if not _MYSQL_ENABLED:
        return False
    if _MYSQL_BOOTSTRAPPED:
        return True

    try:
        # Fast path: one query tells us whether every table and column already exists (the usual case after the
        # first run), so a restart does not repeat a dozen CREATE/ALTER round trips.
        if _mysql_schema_complete():
            _MYSQL_BOOTSTRAPPED = True
            return True
        _mysql_ensure_database()
        for table_name, columns in MYSQL_DEFAULT_COLUMNS.items():
            _mysql_ensure_table(table_name, columns)
        _MYSQL_BOOTSTRAPPED = True
        return True
    except Exception as exc:
        if IS_VERCEL:
            raise RuntimeError(f"MySQL/TiDB is unavailable in production: {exc}") from exc
        print(f"MySQL unavailable ({exc}). Falling back to CSV storage (local development only).")
        _MYSQL_ENABLED = False
        return False


def _use_database(path):
    if path not in STORAGE_TABLE_MAP:
        return False
    if DB_BACKEND == 'mysql':
        return _mysql_bootstrap()
    if DB_BACKEND == 'mongodb':
        return _mongo_bootstrap()
    return False


def _mysql_value(value):
    if value is None:
        return None
    if isinstance(value, str):
        return value if value.strip() else None
    if isinstance(value, (dict, list)):
        return json.dumps(value)
    return str(value)


def _mysql_read_rows(path):
    table_name = STORAGE_TABLE_MAP.get(path)
    if not table_name:
        return []
    conn = _mysql_connect(include_database=True)
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute(f"SELECT * FROM {_escape_identifier(table_name)}")
        rows = cur.fetchall() or []
        normalized = []
        for row in rows:
            normalized.append({
                key: "" if value is None else str(value)
                for key, value in row.items()
            })
        return normalized
    finally:
        conn.close()


def _mysql_write_rows(path, rows, fieldnames):
    table_name = STORAGE_TABLE_MAP.get(path)
    if not table_name:
        return

    incoming_fields = _collect_fieldnames(rows, fieldnames) or MYSQL_DEFAULT_COLUMNS.get(table_name, ["id"])
    _mysql_ensure_columns(table_name, incoming_fields)
    table_columns = _mysql_existing_columns(table_name)

    conn = _mysql_connect(include_database=True)
    try:
        cur = conn.cursor()
        cur.execute(f"DELETE FROM {_escape_identifier(table_name)}")
        if rows:
            col_sql = ", ".join(_escape_identifier(col) for col in table_columns)
            placeholders = ", ".join(["%s"] * len(table_columns))
            sql = f"INSERT INTO {_escape_identifier(table_name)} ({col_sql}) VALUES ({placeholders})"
            payload = []
            for row in rows:
                payload.append(tuple(_mysql_value(row.get(col, "")) for col in table_columns))
            cur.executemany(sql, payload)
        conn.commit()
    finally:
        conn.close()


def _mysql_append_row(path, row, fieldnames):
    table_name = STORAGE_TABLE_MAP.get(path)
    if not table_name:
        return

    incoming_fields = _collect_fieldnames([row], fieldnames) or MYSQL_DEFAULT_COLUMNS.get(table_name, ["id"])
    _mysql_ensure_columns(table_name, incoming_fields)
    table_columns = _mysql_existing_columns(table_name)

    conn = _mysql_connect(include_database=True)
    try:
        cur = conn.cursor()
        col_sql = ", ".join(_escape_identifier(col) for col in table_columns)
        placeholders = ", ".join(["%s"] * len(table_columns))
        sql = f"INSERT INTO {_escape_identifier(table_name)} ({col_sql}) VALUES ({placeholders})"
        values = tuple(_mysql_value(row.get(col, "")) for col in table_columns)
        cur.execute(sql, values)
        conn.commit()
    finally:
        conn.close()


def ensure_csv(path, headers):
    if _use_database(path):
        if DB_BACKEND == 'mysql':
            table_name = STORAGE_TABLE_MAP.get(path)
            if table_name:
                _mysql_ensure_columns(table_name, headers)
        return
    if not os.path.exists(path):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", newline='', encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=headers)
            writer.writeheader()


def ensure_notes_csv():
    ensure_csv(NOTES_CSV, ['id','title','content','author','author_id','priority','is_pinned','created_at','updated_at','visible_to'])


ensure_csv(USERS_CSV, ["id","username","password_hash","full_name","role","created_at","is_active"])


ensure_csv(EMP_CSV, ["id","name","email","position","department","company","join_date","phone","skills","location","last_login","password_last_changed","avatar_url","status","productivity"])


ensure_csv(TASKS_CSV, ["id","title","description","project_id","assignee_id","assignee_name","status","priority","created_at","due_date","estimated_hours","actual_hours","progress"])


ensure_csv(PROJECTS_CSV, ["id","name","description","owner_id","start_date","end_date","status","team_members","company","progress"])


ensure_csv(PROJECT_MEMBERS_CSV, ["id","project_id","employee_id"])


ensure_csv(LEAVE_CSV, ["id","employee_id","start_date","end_date","reason","type","status","applied_at"])


ensure_csv(WORK_CSV, ["id","employee_id","task_id","start_time","end_time","duration_minutes","notes"])


ensure_csv(NOTIF_CSV, ["id","user_id","title","message","type","is_read","created_at"])


ensure_csv(SETTINGS_CSV, ["id","user_id","email_notifications","push_notifications","task_reminders","deadline_alerts","theme","language","timezone","updated_at","company_name","date_format","session_timeout","password_policy","notify_task_assignments","notify_project_updates","notify_system_alerts","desktop_notifications","sound_alerts","auto_backup","data_retention","api_access","webhook_url"])


ensure_csv(HELP_REQUESTS_CSV, ["id","requester_id","requester_name","task_id","task_title","message","urgency","status","recipient_type","recipient_id","recipient_name","request_type","created_at","updated_at"])


ensure_csv(TEAMS_CSV, ["id","name","department","manager_id","manager_name","teamlead_id","teamlead_name","member_ids","tagline","focus_area","created_at","updated_at"])


ensure_csv(PAYMENTS_CSV, ["id","employee_id","employee_name","role","team_id","team_name","department","base_salary","bonus","currency","payment_status","last_paid_date","next_pay_date","pay_cycle","updated_at"])


ensure_csv(TASK_SUBMISSIONS_CSV, ["id","task_id","project_id","employee_id","employee_name","manager_id","teamlead_id","recipient_ids","original_filename","stored_filename","file_path","file_size","status","notes","created_at","updated_at"])


ensure_notes_csv()


USER_FIELDNAMES = ['id','username','password_hash','full_name','role','created_at','is_active']


EMP_FIELDNAMES = ['id','name','email','position','department','company','join_date','phone','skills','location','last_login','password_last_changed','avatar_url','status','productivity']


TASK_FIELDNAMES = ['id','title','description','project_id','assignee_id','assignee_name','status','priority','created_at','due_date','estimated_hours','actual_hours','progress']


PROJECT_FIELDNAMES = ['id','name','description','owner_id','start_date','end_date','status','team_members','company','progress']


PROJECT_MEMBER_FIELDNAMES = ['id','project_id','employee_id']


LEAVE_FIELDNAMES = ['id', 'employee_id', 'start_date', 'end_date', 'reason', 'type', 'status', 'applied_at']


NOTIFICATION_FIELDNAMES = ['id', 'user_id', 'title', 'message', 'type', 'is_read', 'created_at']


SETTINGS_FIELDNAMES = ['id', 'user_id', 'email_notifications', 'push_notifications', 'task_reminders', 'deadline_alerts', 'theme', 'language', 'timezone', 'updated_at', 'company_name', 'date_format', 'session_timeout', 'password_policy', 'notify_task_assignments', 'notify_project_updates', 'notify_system_alerts', 'desktop_notifications', 'sound_alerts', 'auto_backup', 'data_retention', 'api_access', 'webhook_url']


HELP_REQUEST_FIELDNAMES = ['id', 'requester_id', 'requester_name', 'task_id', 'task_title', 'message', 'urgency', 'status', 'recipient_type', 'recipient_id', 'recipient_name', 'request_type', 'created_at', 'updated_at']


TEAM_FIELDNAMES = ['id', 'name', 'department', 'manager_id', 'manager_name', 'teamlead_id', 'teamlead_name', 'member_ids', 'tagline', 'focus_area', 'created_at', 'updated_at']


PAYMENT_FIELDNAMES = ['id', 'employee_id', 'employee_name', 'role', 'team_id', 'team_name', 'department', 'base_salary', 'bonus', 'currency', 'payment_status', 'last_paid_date', 'next_pay_date', 'pay_cycle', 'updated_at']


TASK_SUBMISSION_FIELDNAMES = ['id', 'task_id', 'project_id', 'employee_id', 'employee_name', 'manager_id', 'teamlead_id', 'recipient_ids', 'original_filename', 'stored_filename', 'file_path', 'file_size', 'status', 'notes', 'created_at', 'updated_at']


VALID_LEAVE_STATUSES = {'pending', 'approved', 'rejected'}


app = Flask(__name__, template_folder=os.path.join(BASE_DIR, 'templates'), static_folder=os.path.join(BASE_DIR, 'static'))


_configured_secret = os.environ.get("FLASK_SECRET") or os.environ.get("FLASK_SECRET_KEY")
app.secret_key = _configured_secret or __import__("secrets").token_hex(32)  # per-process key for local runs only


if IS_VERCEL and not _configured_secret:
    # sessions must survive across serverless instances, so the key has to be configured
    raise RuntimeError("Set FLASK_SECRET to a long random value in production.")


GOOGLE_CLIENT_ID = os.environ.get(
    "GOOGLE_CLIENT_ID",
    "",
)


GOOGLE_CLIENT_SECRET = os.environ.get(
    "GOOGLE_CLIENT_SECRET",
    "",
)


GOOGLE_REDIRECT_URI = os.environ.get(
    "GOOGLE_REDIRECT_URI",
    ""
)


def create_sample_users():
    """Create sample users for testing"""
    if not SEED_DEMO:
        return
    reset_passwords = os.environ.get('TASKVISE_RESET_SAMPLE_PASSWORDS', '').strip().lower() in {'1', 'true', 'yes', 'on'}
    sample_users = [
        {
            "username": "admin@gmail.com",
            "password": "admin123",
            "role": "admin",
            "full_name": "System Administrator"
        },
        {
            "username": "manager@gmail.com",
            "password": "manager123",
            "role": "manager",
            "full_name": "Project Manager"
        },
        {
            "username": "employee1@gmail.com",
            "password": "emp123",
            "role": "employee",
            "full_name": "John Doe"
        },
        {
            "username": "employee2@gmail.com",
            "password": "empl123",
            "role": "employee",
            "full_name": "Jane Smith"
        },
        {
            "username": "hr@gmail.com",
            "password": "hr123",
            "role": "hr",
            "full_name": "HR Manager"
        },
        {
            "username": "teamlead@gmail.com",
            "password": "lead123",
            "role": "teamlead",
            "full_name": "Team Lead"
        }
    ]

    existing_users = read_csv(USERS_CSV)
    existing_employees = read_csv(EMP_CSV)
    existing_usernames = [user['username'] for user in existing_users]

    for sample in sample_users:
        if sample['username'] not in existing_usernames:
            user_id = get_next_workforce_id(existing_users, existing_employees)
            user_row = {
                'id': user_id,
                'username': sample['username'],
                'password_hash': generate_password_hash(sample['password']),
                'full_name': sample['full_name'],
                'role': sample['role'],
                'created_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'is_active': 'true'
            }

            employee_row = {
                'id': user_id,
                'name': sample['full_name'],
                'email': sample['username'],
                'position': sample['role'].title(),
                'department': 'IT',
                'company': get_default_company_name(),
                'join_date': datetime.now().strftime('%Y-%m-%d'),
                'phone': '555-0100',
                'skills': 'Sample Skills',
                'location': 'Office',
                'last_login': '',
                'password_last_changed': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'avatar_url': '',
                'status': 'active',
                'productivity': '78'
            }

            append_csv(USERS_CSV, user_row, ['id','username','password_hash','full_name','role','created_at','is_active'])
            append_csv(EMP_CSV, employee_row, EMP_FIELDNAMES)
            existing_users.append(user_row)
            existing_employees.append(employee_row)
            print(f"Created sample user: {sample['username']}")
        elif reset_passwords:
            try:
                stored = next((u for u in existing_users if (u.get('username') == sample['username'])), None)
                if stored and stored.get('id'):
                    update_by_id(
                        USERS_CSV,
                        stored.get('id'),
                        {
                            'password_hash': generate_password_hash(sample['password']),
                            'is_active': 'true'
                        },
                        ['id','username','password_hash','full_name','role','created_at','is_active']
                    )
                    print(f"Reset sample password: {sample['username']}")
            except Exception as exc:
                print(f"Reset sample password error ({sample.get('username')}): {exc}")
    export_demo_credentials_file()


def read_csv(path):
    if _use_database(path):
        if DB_BACKEND == 'mysql':
            return _mysql_read_rows(path)
        if DB_BACKEND == 'mongodb':
            return _mongo_read_rows(path)
    if not os.path.exists(path):
        return []
    with open(path, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        return list(reader)


def _sync_secondary_stores(path, rows, fieldnames=None):
    if path not in STORAGE_TABLE_MAP:
        return

    snapshot = rows or []
    table_name = STORAGE_TABLE_MAP.get(path)
    columns = _collect_fieldnames(snapshot, fieldnames) or MYSQL_DEFAULT_COLUMNS.get(table_name, [])

    if CSV_SHADOW_SYNC and (DB_BACKEND != 'csv' or not os.path.exists(path)):
        try:
            _write_csv_file(path, snapshot, columns)
        except Exception as exc:
            print(f"CSV shadow sync error for {path}: {exc}")

    if MIRROR_MYSQL and DB_BACKEND != 'mysql' and mysql is not None:
        try:
            if _mysql_bootstrap():
                _mysql_write_rows(path, snapshot, columns)
        except Exception as exc:
            print(f"MySQL mirror sync error for {path}: {exc}")

    if MIRROR_MONGODB and DB_BACKEND != 'mongodb' and MongoClient is not None:
        try:
            if _mongo_bootstrap():
                _mongo_write_rows(path, snapshot, columns)
        except Exception as exc:
            print(f"MongoDB mirror sync error for {path}: {exc}")


def sync_registered_storage_tables(paths=None):
    target_paths = [
        path for path in (paths or STORAGE_TABLE_MAP.keys())
        if path in STORAGE_TABLE_MAP
    ]
    for path in target_paths:
        rows = read_csv(path)
        default_fields = MYSQL_DEFAULT_COLUMNS.get(STORAGE_TABLE_MAP.get(path), [])
        _sync_secondary_stores(path, rows, _collect_fieldnames(rows, default_fields))


def write_csv(path, rows, fieldnames):
    if _use_database(path):
        if DB_BACKEND == 'mysql':
            _mysql_write_rows(path, rows, fieldnames)
        elif DB_BACKEND == 'mongodb':
            _mongo_write_rows(path, rows, fieldnames)
    else:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)
    _sync_secondary_stores(path, rows, fieldnames)


def append_csv(path, row, fieldnames):
    if _use_database(path):
        if DB_BACKEND == 'mysql':
            _mysql_append_row(path, row, fieldnames)
        elif DB_BACKEND == 'mongodb':
            _mongo_append_row(path, row, fieldnames)
    else:
        exists = os.path.exists(path)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "a", newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            if not exists or os.path.getsize(path) == 0:
                writer.writeheader()
            writer.writerow(row)
    _sync_secondary_stores(path, read_csv(path), fieldnames)


def find_by_id(path, id):
    rows = read_csv(path)
    for r in rows:
        if r.get("id") == id:
            return r
    return None


def merge_fieldnames(rows, preferred_fieldnames=None):
    names = []
    for name in preferred_fieldnames or []:
        if name and name not in names:
            names.append(name)
    for row in rows:
        for key in row.keys():
            if key and key not in names:
                names.append(key)
    return names


def update_by_id(path, id, updates, fieldnames=None):
    if _use_database(path) and DB_BACKEND == 'mongodb':
        updated = _mongo_update_by_id(path, id, updates)
        if updated:
            snapshot = read_csv(path)
            _sync_secondary_stores(path, snapshot, _collect_fieldnames(snapshot, fieldnames))
        return updated

    rows = read_csv(path)
    updated = False
    for r in rows:
        if r.get("id") == id:
            r.update(updates)
            updated = True
    if updated:
        write_csv(path, rows, merge_fieldnames(rows, fieldnames))
    return updated


def delete_by_id(path, id, fieldnames=None):
    if _use_database(path) and DB_BACKEND == 'mongodb':
        deleted = _mongo_delete_by_id(path, id)
        if deleted:
            snapshot = read_csv(path)
            _sync_secondary_stores(path, snapshot, _collect_fieldnames(snapshot, fieldnames))
        return deleted

    rows = read_csv(path)
    new = [r for r in rows if r.get("id") != id]
    if len(new) != len(rows):
        source_rows = new if new else rows
        write_csv(path, new, merge_fieldnames(source_rows, fieldnames))
        return True
    return False


def get_storage_targets_status():
    status = {
        'csv': True,
        'mongodb': False,
        'mysql': False,
        'warnings': [],
    }

    if MongoClient is not None:
        try:
            status['mongodb'] = bool(_mongo_bootstrap())
        except Exception as exc:
            status['warnings'].append(f"MongoDB sync unavailable: {exc}")
    else:
        status['warnings'].append('MongoDB client library is not installed.')

    if mysql is not None:
        try:
            status['mysql'] = bool(_mysql_bootstrap())
        except Exception as exc:
            status['warnings'].append(f"MySQL sync unavailable: {exc}")
        if not status['mysql']:
            status['warnings'].append(
                'MySQL sync is unavailable. Configure MYSQL_USER and MYSQL_PASSWORD for mirrored writes.'
            )
    else:
        status['warnings'].append('MySQL connector is not installed.')

    return status


def persist_workforce_profile(user_row, employee_row, *, sync_org=True):
    append_csv(USERS_CSV, user_row, USER_FIELDNAMES)
    append_csv(EMP_CSV, employee_row, EMP_FIELDNAMES)
    if sync_org:
        ensure_demo_org_integrity(force=True)
        sync_registered_storage_tables([
            USERS_CSV,
            EMP_CSV,
            TEAMS_CSV,
            PROJECTS_CSV,
            PROJECT_MEMBERS_CSV,
            TASKS_CSV,
            PAYMENTS_CSV,
            NOTIF_CSV,
        ])
    return get_storage_targets_status()


def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if "user_id" not in session:
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated


def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if "user_id" not in session:
            return redirect(url_for("login"))
        if session.get("role") != "admin":
            return redirect(url_for("dashboard"))
        return f(*args, **kwargs)
    return decorated


def platform_admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if "user_id" not in session:
            return redirect(f"{TASKVISE_ADMIN_URL}/login")
        if session.get("role") != "platform_admin":
            return redirect(url_for("dashboard"))
        return f(*args, **kwargs)
    return decorated


def _looks_like_werkzeug_hash(value: str) -> bool:
    v = (value or "").strip()
    return ":" in v and "$" in v


def verify_password(stored_value, candidate_password: str) -> bool:
    """
    Accept either a werkzeug password hash or a legacy/plaintext password.
    This prevents "invalid for every login" when storage contains plaintext
    or slightly malformed hash strings (whitespace, etc.).
    """
    candidate = (candidate_password or "").strip()
    if not candidate:
        return False

    if stored_value is None:
        return False

    stored = str(stored_value).strip()
    if not stored:
        return False

    if _looks_like_werkzeug_hash(stored):
        return check_password_hash(stored, candidate)

    return stored == candidate


def get_role_title(role):
    role = normalize_role(role)
    role_titles = {
        'admin': 'Admin Credentials Generated!',
        'manager': 'Manager Credentials Generated!',
        'hr': 'HR Credentials Generated!',
        'teamlead': 'Team Lead Credentials Generated!',
        'employee': 'Employee Credentials Generated!'
    }
    return role_titles.get(role, 'Employee Credentials Generated!')


def get_role_description(role):
    role = normalize_role(role)
    role_descriptions = {
        'admin': 'Administrator account with full system access',
        'manager': 'Manager account with team management access',
        'hr': 'HR account with employee management access',
        'teamlead': 'Team Lead account with project team access',
        'employee': 'Employee account created successfully'
    }
    return role_descriptions.get(role, 'Employee account created successfully')


def get_role_access_description(role):
    role = normalize_role(role)
    access_descriptions = {
        'admin': 'Admin access includes all system privileges',
        'manager': 'Manager access includes team management features',
        'hr': 'HR access includes employee management and HR features',
        'teamlead': 'Team Lead access includes project team management',
        'employee': 'Employee can access personal dashboard and tasks'
    }
    return access_descriptions.get(role, 'Employee can access personal dashboard and tasks')


def _normalize_text(value):
    return str(value or '').strip().lower()


def normalize_role(value):
    aliases = {
        'lead': 'teamlead',
        'team lead': 'teamlead',
        'team-lead': 'teamlead',
        'administrator': 'admin',
        'platform admin': 'platform_admin',
        'platform-admin': 'platform_admin',
        'founder': 'platform_admin',
    }
    raw = _normalize_text(value)
    return aliases.get(raw, raw or 'employee')


def _truthy(value, default=False):
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    return _normalize_text(value) in {'1', 'true', 'yes', 'on'}


def resolve_employee_candidate_ids(user_id=None, username=None, full_name=None):
    employees = read_csv(EMP_CSV)
    ids = set()
    uid = str(user_id or '').strip()
    username_norm = _normalize_text(username)
    full_name_norm = _normalize_text(full_name)

    if uid:
        ids.add(uid)

    for emp in employees:
        emp_id = str(emp.get('id') or '').strip()
        if not emp_id:
            continue

        if uid and emp_id == uid:
            ids.add(emp_id)

        if username_norm and _normalize_text(emp.get('email')) == username_norm:
            ids.add(emp_id)

        if full_name_norm and _normalize_text(emp.get('name')) == full_name_norm:
            ids.add(emp_id)

    return ids, employees


def task_matches_employee(task, candidate_ids, username=None, full_name=None):
    ids = {str(v).strip() for v in (candidate_ids or set()) if str(v).strip()}
    assignee_id = str(task.get('assignee_id') or task.get('assignedTo') or '').strip()
    if assignee_id and assignee_id in ids:
        return True

    assignee_name = _normalize_text(task.get('assignee_name') or task.get('assigned_to_name'))
    full_name_norm = _normalize_text(full_name)
    username_norm = _normalize_text(username)
    username_local = username_norm.split('@')[0] if username_norm else ''

    if assignee_name and (
        assignee_name == full_name_norm or
        assignee_name == username_norm or
        (username_local and assignee_name == username_local)
    ):
        return True
    return False


def normalize_task_status(value):
    raw = _normalize_text(value)
    aliases = {
        'in progress': 'in-progress',
        'in_progress': 'in-progress',
        'todo': 'pending',
        'to do': 'pending',
        'done': 'completed',
    }
    return aliases.get(raw, raw or 'pending')


def normalize_project_status(value):
    raw = _normalize_text(value)
    aliases = {
        'on hold': 'on-hold',
        'on_hold': 'on-hold',
        'in progress': 'active',
        'in_progress': 'active',
    }
    return aliases.get(raw, raw or 'planning')


def get_user_settings_record(user_id):
    defaults = {
        'email_notifications': 'true',
        'push_notifications': 'false',
        'task_reminders': 'true',
        'deadline_alerts': 'true',
        'theme': 'system',
        'language': 'en',
        'timezone': 'UTC',
    }
    rows = read_csv(SETTINGS_CSV)
    existing = next((r for r in rows if str(r.get('user_id', '')) == str(user_id)), None)
    if existing:
        record = existing.copy()
    else:
        record = {'id': str(uuid.uuid4()), 'user_id': str(user_id)}

    for key, value in defaults.items():
        record[key] = str(record.get(key, value) or value)
    record['updated_at'] = str(record.get('updated_at') or datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
    return record, rows


def save_user_settings_record(user_id, incoming):
    record, rows = get_user_settings_record(user_id)
    for key in ['email_notifications', 'push_notifications', 'task_reminders', 'deadline_alerts', 'theme', 'language', 'timezone']:
        if key in incoming:
            record[key] = str(incoming.get(key) or record.get(key) or '')
    record['updated_at'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    replaced = False
    for idx, row in enumerate(rows):
        if str(row.get('user_id', '')) == str(user_id):
            rows[idx] = record
            replaced = True
            break
    if not replaced:
        rows.append(record)

    write_csv(SETTINGS_CSV, rows, SETTINGS_FIELDNAMES)
    return record


def _safe_int(value, default=0):
    try:
        return int(float(str(value or default).strip()))
    except Exception:
        return default


def infer_primary_company_name(employees=None, projects=None):
    counter = Counter()
    for row in employees or read_csv(EMP_CSV):
        company = str(row.get('company') or '').strip()
        if company:
            counter[company] += 1
    for row in projects or read_csv(PROJECTS_CSV):
        company = str(row.get('company') or '').strip()
        if company:
            counter[company] += 1
    if counter:
        return counter.most_common(1)[0][0]
    return DEFAULT_COMPANY_NAME


def get_default_company_name():
    rows = read_csv(SETTINGS_CSV)
    existing = next((r for r in rows if str(r.get('user_id', '')) == SYSTEM_SETTINGS_USER_ID), None)
    if existing and str(existing.get('company_name') or '').strip():
        return str(existing.get('company_name')).strip()
    return infer_primary_company_name()


def get_admin_system_settings_record():
    rows = read_csv(SETTINGS_CSV)
    existing = next((r for r in rows if str(r.get('user_id', '')) == SYSTEM_SETTINGS_USER_ID), None)
    defaults = {
        'company_name': infer_primary_company_name(),
        'theme': 'executive',
        'language': 'en',
        'timezone': 'Asia/Kolkata',
        'date_format': 'dd/mm/yyyy',
        'session_timeout': '30',
        'password_policy': 'medium',
        'notify_task_assignments': 'true',
        'notify_project_updates': 'true',
        'notify_system_alerts': 'true',
        'desktop_notifications': 'true',
        'sound_alerts': 'false',
        'auto_backup': 'weekly',
        'data_retention': '12',
        'api_access': 'true',
        'webhook_url': '',
    }
    record = existing.copy() if existing else {'id': str(uuid.uuid4()), 'user_id': SYSTEM_SETTINGS_USER_ID}
    for key, value in defaults.items():
        record[key] = str(record.get(key, value) or value)
    record['updated_at'] = str(record.get('updated_at') or datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
    return record, rows


def save_admin_system_settings_record(incoming):
    record, rows = get_admin_system_settings_record()
    allowed_fields = {
        'company_name', 'theme', 'language', 'timezone', 'date_format', 'session_timeout',
        'password_policy', 'notify_task_assignments', 'notify_project_updates', 'notify_system_alerts',
        'desktop_notifications', 'sound_alerts', 'auto_backup', 'data_retention', 'api_access',
        'webhook_url'
    }
    for key in allowed_fields:
        if key not in incoming:
            continue
        value = incoming.get(key)
        if key in {'notify_task_assignments', 'notify_project_updates', 'notify_system_alerts', 'desktop_notifications', 'sound_alerts', 'api_access'}:
            record[key] = 'true' if _truthy(value) else 'false'
        else:
            record[key] = str(value or '').strip()
    if not record.get('company_name'):
        record['company_name'] = infer_primary_company_name()
    record['updated_at'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    replaced = False
    for idx, row in enumerate(rows):
        if str(row.get('user_id', '')) == SYSTEM_SETTINGS_USER_ID:
            rows[idx] = record
            replaced = True
            break
    if not replaced:
        rows.append(record)

    write_csv(SETTINGS_CSV, rows, SETTINGS_FIELDNAMES)
    return record


def get_role_default_password(role):
    normalized_role = normalize_role(role)
    return ROLE_DEFAULT_PASSWORDS.get(normalized_role, ROLE_DEFAULT_PASSWORDS['employee'])


def build_demo_credentials_payload(users=None):
    rows = users if users is not None else read_csv(USERS_CSV)
    employee_lookup = _build_employee_index(read_csv(EMP_CSV))
    grouped = []
    role_order = ['platform_admin', 'admin', 'manager', 'hr', 'teamlead', 'employee']
    for role in role_order:
        members = []
        for user in rows:
            user_role = normalize_role(user.get('role'))
            if user_role != role:
                continue
            employee = employee_lookup.get(str(user.get('id', '')).strip(), {})
            members.append({
                'id': user.get('id', ''),
                'username': user.get('username', ''),
                'full_name': user.get('full_name', ''),
                'role': user_role,
                'password': get_role_default_password(role),
                'team_name': employee.get('team_name', user.get('team_name', '')),
                'manager_id': employee.get('manager_id', user.get('manager_id', '')),
                'teamlead_id': employee.get('teamlead_id', user.get('teamlead_id', '')),
            })
        if members:
            grouped.append({
                'role': role,
                'password': get_role_default_password(role),
                'users': sorted(
                    members,
                    key=lambda item: (
                        _prefixed_id_sort_key(item.get('id', ''), WORKFORCE_ID_PREFIX),
                        str(item.get('username', '')).lower(),
                    ),
                ),
            })
    return grouped


def export_demo_credentials_file(path=CREDENTIALS_EXPORT_TXT, users=None):
    if not SEED_DEMO:
        return
    role_labels = {
        'platform_admin': 'TaskVise Founder',
        'admin': 'Admin',
        'manager': 'Manager',
        'hr': 'HR',
        'teamlead': 'Team Lead',
        'employee': 'Employee',
    }
    grouped = build_demo_credentials_payload(users=users)
    lines = [
        'TaskVise Login Credentials',
        f'Generated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}',
        '',
        'All accounts below are grouped by role with the current default login password for that role.',
        '',
    ]
    if not grouped:
        lines.append('No users found.')
    else:
        for group in grouped:
            role = str(group.get('role') or 'employee').strip().lower()
            lines.append(f"[{role_labels.get(role, role.title())}]")
            lines.append(f"Default password: {group.get('password', '')}")
            for user in group.get('users', []):
                user_id = str(user.get('id') or '').strip()
                full_name = str(user.get('full_name') or 'Unknown User').strip()
                username = str(user.get('username') or '').strip()
                team_name = str(user.get('team_name') or '').strip()
                manager_id = str(user.get('manager_id') or '').strip()
                teamlead_id = str(user.get('teamlead_id') or '').strip()
                extra_parts = []
                if team_name:
                    extra_parts.append(f"Team: {team_name}")
                if manager_id:
                    extra_parts.append(f"Manager: {manager_id}")
                if teamlead_id:
                    extra_parts.append(f"Lead: {teamlead_id}")
                extra_text = f" | {' | '.join(extra_parts)}" if extra_parts else ''
                if user_id:
                    lines.append(f"- {user_id} | {full_name} | {username}{extra_text}")
                else:
                    lines.append(f"- {full_name} | {username}{extra_text}")
            lines.append('')

    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines).strip() + '\n')
    return path


def sync_demo_role_passwords():
    if not SEED_DEMO:
        return
    users = read_csv(USERS_CSV)
    if not users:
        export_demo_credentials_file(users=[])
        return 0

    changed = 0
    for user in users:
        role = str(user.get('role') or 'employee').strip().lower()
        desired_password = get_role_default_password(role)
        stored_value = user.get('password_hash') or user.get('password') or ''
        if verify_password(stored_value, desired_password):
            continue
        user['password_hash'] = generate_password_hash(desired_password)
        changed += 1

    if changed:
        write_csv(USERS_CSV, users, merge_fieldnames(users, USER_FIELDNAMES))
    export_demo_credentials_file(users=users)
    return changed


def get_employee_data(user_id):
    """Get comprehensive employee data for dashboard display"""
    username = session.get('username')
    full_name = session.get('full_name')

    candidate_ids, employees = resolve_employee_candidate_ids(user_id, username, full_name)

    employee = next((e for e in employees if str(e.get('id', '')) == str(user_id)), None)
    if not employee and username:
        employee = next((e for e in employees if _normalize_text(e.get('email')) == _normalize_text(username)), None)
    if not employee and full_name:
        employee = next((e for e in employees if _normalize_text(e.get('name')) == _normalize_text(full_name)), None)

    if not employee and candidate_ids:
        first_id = next(iter(candidate_ids))
        employee = next((e for e in employees if str(e.get('id', '')) == str(first_id)), None)

    if not employee:
        return {
            'profile': {
                'id': user_id,
                'name': session.get('full_name', 'Unknown'),
                'email': session.get('username', ''),
                'position': 'Unknown',
                'department': 'Unknown',
                'company': get_default_company_name(),
                'join_date': '',
                'phone': '',
                'skills': '',
                'location': '',
                'avatar_url': '',
                'designation': session.get('role', '').title(),
                'role': session.get('role', 'employee')
            },
            'stats': {
                'totalTasks': 0,
                'completedTasks': 0,
                'inProgressTasks': 0,
                'overdueTasks': 0,
                'activeProjects': 0,
                'workload': 'light'
            },
            'tasks': [],
            'projects': []
        }

    all_tasks = read_csv(TASKS_CSV)
    employee_tasks = [
        task for task in all_tasks
        if task_matches_employee(task, candidate_ids, username=username, full_name=full_name)
    ]

    normalized_tasks = []
    for task in employee_tasks:
        row = dict(task)
        row['status'] = normalize_task_status(row.get('status'))
        row['priority'] = str(row.get('priority') or 'medium').strip().lower()
        row['due_date'] = str(row.get('due_date') or row.get('dueDate') or '')[:10]
        row['created_at'] = str(row.get('created_at') or '')[:19]
        normalized_tasks.append(row)
    employee_tasks = normalized_tasks

    total_tasks = len(employee_tasks)
    completed_tasks = len([task for task in employee_tasks if task.get('status') == 'completed'])
    in_progress_tasks = len([task for task in employee_tasks if task.get('status') == 'in-progress'])

    today = datetime.now().date()
    overdue_tasks = 0
    for task in employee_tasks:
        if task.get('status') not in ['completed', 'cancelled'] and task.get('due_date'):
            try:
                due_date = datetime.strptime(task['due_date'], '%Y-%m-%d').date()
                if due_date < today:
                    overdue_tasks += 1
            except ValueError:
                continue

    all_projects = read_csv(PROJECTS_CSV)
    member_rows = read_csv(PROJECT_MEMBERS_CSV)
    member_project_ids = {m.get('project_id') for m in member_rows if m.get('employee_id') in candidate_ids}
    task_project_ids = {
        t.get('project_id')
        for t in employee_tasks
        if t.get('project_id')
    }
    visible_project_ids = member_project_ids.union(task_project_ids)
    employee_projects = [p for p in all_projects if p.get('owner_id') in candidate_ids or p.get('id') in visible_project_ids]
    active_projects = len([p for p in employee_projects if p.get('status') in ['active', 'planning']])

    if total_tasks == 0:
        workload = 'light'
    elif total_tasks <= 3:
        workload = 'balanced'
    else:
        workload = 'heavy'

    user = find_by_id(USERS_CSV, user_id)
    user_role = normalize_role(user.get('role', 'employee') if user else 'employee')

    profile_data = {
        'id': employee.get('id', user_id),
        'name': employee.get('name', 'Unknown'),
        'fullName': employee.get('name', 'Unknown'),
        'email': employee.get('email', ''),
        'position': employee.get('position', 'Unknown'),
        'department': employee.get('department', 'Unknown'),
        'company': employee.get('company', get_default_company_name()),
        'join_date': employee.get('join_date', ''),
        'phone': employee.get('phone', ''),
        'skills': employee.get('skills', ''),
        'location': employee.get('location', ''),
        'avatar_url': employee.get('avatar_url', ''),
        'designation': employee.get('position', ''),
        'role': user_role,
        'team_id': employee.get('team_id', ''),
        'team_name': employee.get('team_name', ''),
        'manager_id': employee.get('manager_id', ''),
        'teamlead_id': employee.get('teamlead_id', ''),
    }

    stats_data = {
        'totalTasks': total_tasks,
        'completedTasks': completed_tasks,
        'inProgressTasks': in_progress_tasks,
        'overdueTasks': overdue_tasks,
        'activeProjects': active_projects,
        'workload': workload
    }

    return {
        'profile': profile_data,
        'stats': stats_data,
        'tasks': employee_tasks,
        'projects': employee_projects
    }


def _prepare_dashboard_profile(profile):
    prepared = dict(profile or {})
    skills = prepared.get('skills')
    if isinstance(skills, str):
        prepared['skills'] = [skill.strip() for skill in skills.split(',') if skill.strip()]
    elif isinstance(skills, (list, tuple, set)):
        prepared['skills'] = [str(skill).strip() for skill in skills if str(skill).strip()]
    elif skills:
        prepared['skills'] = [str(skills).strip()]
    else:
        prepared['skills'] = []
    return prepared


def get_employee_dashboard_data(user_id):
    employee_data = get_employee_data(user_id)
    employee_data['profile'] = _prepare_dashboard_profile(employee_data.get('profile'))
    return employee_data


def get_manager_data(user_id):
    """Get comprehensive data for manager dashboard"""
    ensure_demo_org_integrity()
    ensure_projects_team_members()
    all_employees = _sort_rows_by_id(read_csv(EMP_CSV), WORKFORCE_ID_PREFIX)
    all_users = read_csv(USERS_CSV)
    all_tasks = read_csv(TASKS_CSV)
    all_projects = read_csv(PROJECTS_CSV)
    member_rows = read_csv(PROJECT_MEMBERS_CSV)
    teams = read_csv(TEAMS_CSV)
    payments = read_csv(PAYMENTS_CSV)
    normalized_user_id = str(user_id or '').strip()
    employee_lookup = _build_employee_index(all_employees)
    role_map = {
        str(user.get('id', '')).strip(): normalize_role(user.get('role', 'employee'))
        for user in all_users
        if str(user.get('id', '')).strip()
    }
    actor_row = employee_lookup.get(normalized_user_id, {})
    actor_role = role_map.get(normalized_user_id, normalize_role(actor_row.get('role', 'employee')))
    actor_team = get_team_record_for_user(normalized_user_id, teams)

    visible_employee_ids = set()
    visible_project_ids = set()
    visible_payments = []

    if actor_role == 'hr':
        visible_employee_ids = {
            str(emp.get('id', '')).strip()
            for emp in all_employees
            if str(emp.get('id', '')).strip() and role_map.get(str(emp.get('id', '')).strip(), 'employee') not in {'admin', 'platform_admin'}
        }
        visible_project_ids = {str(project.get('id', '')).strip() for project in all_projects if str(project.get('id', '')).strip()}
        visible_payments = payments
    elif actor_role == 'manager' and actor_team:
        visible_employee_ids = set(get_team_member_ids(actor_team, include_teamlead=True))
        visible_project_ids = {
            str(project.get('id', '')).strip()
            for project in all_projects
            if str(project.get('team_id', '')).strip() == str(actor_team.get('id', '')).strip()
        }
        visible_payments = [row for row in payments if str(row.get('team_id', '')).strip() == str(actor_team.get('id', '')).strip()]
    elif actor_role == 'teamlead' and actor_team:
        visible_employee_ids = set(get_team_member_ids(actor_team))
        visible_project_ids = {
            str(project.get('id', '')).strip()
            for project in all_projects
            if str(project.get('team_id', '')).strip() == str(actor_team.get('id', '')).strip()
        }
        visible_payments = [row for row in payments if str(row.get('team_id', '')).strip() == str(actor_team.get('id', '')).strip()]
    else:
        visible_employee_ids = set()
        visible_project_ids = set()
        visible_payments = []

    filtered_employees = []
    for emp in all_employees:
        emp_id = str(emp.get('id', '')).strip()
        if not emp_id or emp_id == normalized_user_id:
            continue
        role = role_map.get(emp_id, 'employee')
        if actor_role != 'hr' and emp_id not in visible_employee_ids:
            continue
        if actor_role == 'hr' and role in {'admin', 'platform_admin'}:
            continue
        emp_with_role = emp.copy()
        emp_with_role['role'] = role
        emp_with_role['fullName'] = emp.get('name', 'Unknown')
        emp_with_role['company'] = str(emp.get('company') or get_default_company_name()).strip()
        productivity = _safe_int(emp.get('productivity', ''), -1)
        if productivity < 0:
            productivity = calculate_employee_productivity(emp_id)
        emp_with_role['productivity'] = str(max(0, min(100, productivity)))
        filtered_employees.append(emp_with_role)
    filtered_employees = _sort_rows_by_id(filtered_employees, WORKFORCE_ID_PREFIX)

    visible_employee_index = {
        str(employee.get('id', '')).strip(): employee
        for employee in filtered_employees
        if str(employee.get('id', '')).strip()
    }

    projects = []
    for project in all_projects:
        project_id = str(project.get('id', '')).strip()
        if actor_role != 'hr' and project_id not in visible_project_ids:
            continue
        project_tasks = [
            task for task in all_tasks
            if str(task.get('project_id', '')).strip() == project_id
        ]
        completed_tasks = len([
            task for task in project_tasks
            if normalize_task_status(task.get('status')) == 'completed'
        ])
        estimated_hours = sum(_safe_int(task.get('estimated_hours', task.get('estimatedHours', 0)), 0) for task in project_tasks)
        actual_hours = sum(_safe_int(task.get('actual_hours', task.get('actualHours', 0)), 0) for task in project_tasks)
        owner_id = str(project.get('owner_id', '')).strip()
        owner = employee_lookup.get(owner_id, {})
        project_row = dict(project)
        team_member_ids = _normalize_list_strings(_parse_team_members(project, member_rows))
        project_row['team_members'] = ','.join(team_member_ids)
        project_row['team_members_count'] = len(team_member_ids)
        project_row['team_member_details'] = [
            {
                'id': member_id,
                'name': employee_lookup.get(member_id, {}).get('name', member_id),
                'position': employee_lookup.get(member_id, {}).get('position', ''),
                'department': employee_lookup.get(member_id, {}).get('department', ''),
            }
            for member_id in team_member_ids
        ]
        project_row['deadline'] = str(project.get('end_date', project.get('deadline', '')) or '')[:10]
        project_row['status'] = normalize_project_status(project.get('status', 'planning'))
        project_row['company'] = str(project.get('company') or get_default_company_name()).strip()
        project_row['progress'] = str(max(0, min(100, _safe_int(project.get('progress', 0), 0))))
        project_row['completed_tasks'] = completed_tasks
        project_row['total_tasks'] = len(project_tasks)
        project_row['estimated_hours'] = estimated_hours
        project_row['actual_hours'] = actual_hours
        project_row['owner_name'] = owner.get('name', project_row.get('owner_name', ''))
        projects.append(project_row)
    projects = sorted(projects, key=lambda item: _prefixed_id_sort_key(item.get('id', ''), PROJECT_ID_PREFIX))

    visible_project_ids = {str(project.get('id', '')).strip() for project in projects if str(project.get('id', '')).strip()}

    tasks = []
    for task in all_tasks:
        task_assignee_id = str(task.get('assignee_id', '')).strip()
        task_project_id = str(task.get('project_id', '')).strip()
        include_task = actor_role == 'hr' or task_project_id in visible_project_ids or task_assignee_id in visible_employee_ids
        if not include_task:
            continue
        task_row = dict(task)
        employee = employee_lookup.get(task_assignee_id, {})
        project = next((row for row in projects if str(row.get('id', '')).strip() == task_project_id), {})
        task_row['status'] = normalize_task_status(task_row.get('status'))
        task_row['priority'] = str(task_row.get('priority') or 'medium').strip().lower()
        task_row['due_date'] = str(task_row.get('due_date') or task_row.get('dueDate') or '')[:10]
        task_row['dueDate'] = task_row['due_date']
        task_row['estimated_hours'] = str(task_row.get('estimated_hours', task_row.get('estimatedHours', 0)) or 0)
        task_row['estimatedHours'] = task_row['estimated_hours']
        task_row['actual_hours'] = str(task_row.get('actual_hours', task_row.get('actualHours', 0)) or 0)
        task_row['actualHours'] = task_row['actual_hours']
        task_row['progress'] = str(max(0, min(100, _safe_int(task_row.get('progress', 0), 0))))
        task_row['assignee_name'] = task_row.get('assignee_name') or employee.get('name', '')
        task_row['project_name'] = project.get('name', task_row.get('project_name', ''))
        tasks.append(task_row)
    tasks = sorted(tasks, key=lambda item: _prefixed_id_sort_key(item.get('id', ''), TASK_ID_PREFIX))

    tasks_by_employee = {}
    for task in tasks:
        assignee_id = str(task.get('assignee_id', '')).strip()
        tasks_by_employee.setdefault(assignee_id, []).append(task)

    on_leave_ids = set()
    today = datetime.now().date()
    for leave in read_csv(LEAVE_CSV):
        if normalize_leave_status(leave.get('status')) != 'approved':
            continue
        employee_id = str(leave.get('employee_id', '')).strip()
        if employee_id not in visible_employee_index:
            continue
        try:
            start_date = datetime.strptime(str(leave.get('start_date') or '')[:10], '%Y-%m-%d').date()
            end_date = datetime.strptime(str(leave.get('end_date') or '')[:10], '%Y-%m-%d').date()
        except Exception:
            continue
        if start_date <= today <= end_date:
            on_leave_ids.add(employee_id)

    for employee in filtered_employees:
        employee_id = str(employee.get('id', '')).strip()
        employee_tasks = tasks_by_employee.get(employee_id, [])
        completed_tasks = len([
            task for task in employee_tasks
            if normalize_task_status(task.get('status')) == 'completed'
        ])
        total_tasks = len(employee_tasks)
        completion_rate = int(round((completed_tasks / max(total_tasks, 1)) * 100)) if total_tasks else 0
        productivity = max(0, min(100, _safe_int(employee.get('productivity', completion_rate), completion_rate)))
        skills_list = split_skills(employee.get('skills'))
        badge_key, badge_label = classify_employee_badge(productivity, completion_rate, len(skills_list), total_tasks)
        employee['productivity'] = str(productivity)
        employee['totalTasks'] = total_tasks
        employee['completedTasks'] = completed_tasks
        employee['completionRate'] = completion_rate
        employee['skills_list'] = skills_list
        employee['skillsCount'] = len(skills_list)
        employee['performance_badge_key'] = badge_key
        employee['performance_badge_label'] = badge_label
        employee['on_leave'] = 'true' if employee_id in on_leave_ids else 'false'
        employee['initials'] = employee.get('initials') or get_employee_initials(employee.get('name'))

    notifications = [
        {
            'id': row.get('id', ''),
            'title': row.get('title', 'Notification'),
            'message': row.get('message', ''),
            'type': str(row.get('type') or 'system').lower(),
            'is_read': _truthy(row.get('is_read')),
            'created_at': row.get('created_at', ''),
        }
        for row in read_csv(NOTIF_CSV)
        if str(row.get('user_id', '')).strip() == str(user_id).strip()
    ]
    notifications.sort(key=lambda row: row.get('created_at', ''), reverse=True)

    stats = {
        'totalEmployees': len(filtered_employees),
        'activeEmployees': len([e for e in filtered_employees if str(e.get('last_login') or '').strip()]),
        'totalProjects': len(projects),
        'activeProjects': len([p for p in projects if str(p.get('status') or '').lower() in ['active', 'planning']]),
        'totalTasks': len(tasks),
        'completedTasks': len([t for t in tasks if normalize_task_status(t.get('status')) == 'completed']),
        'overdueTasks': calculate_overdue_tasks(tasks),
        'totalHours': calculate_total_hours(tasks),
        'productivity': calculate_team_productivity(filtered_employees, tasks),
        'unreadNotifications': len([n for n in notifications if not n.get('is_read')]),
        'teamName': (actor_team or {}).get('name', 'Workforce Command'),
        'teamTagline': (actor_team or {}).get('tagline', ''),
        'teamFocus': (actor_team or {}).get('focus_area', ''),
        'managerName': (actor_team or {}).get('manager_name', ''),
        'teamLeadName': (actor_team or {}).get('teamlead_name', ''),
        'teamSize': len(get_team_member_ids(actor_team, include_teamlead=True)),
        'teamsCount': len(teams),
        'monthlyPayroll': sum(_safe_int(row.get('base_salary', 0), 0) + _safe_int(row.get('bonus', 0), 0) for row in visible_payments),
        'teamSummaries': [
            {
                'id': team.get('id', ''),
                'name': team.get('name', ''),
                'department': team.get('department', ''),
                'manager_id': team.get('manager_id', ''),
                'manager_name': team.get('manager_name', ''),
                'teamlead_id': team.get('teamlead_id', ''),
                'teamlead_name': team.get('teamlead_name', ''),
                'member_count': len(get_team_member_ids(team)),
                'tagline': team.get('tagline', ''),
                'focus_area': team.get('focus_area', ''),
            }
            for team in teams
        ],
    }

    return {
        'employees': filtered_employees,
        'tasks': tasks,
        'projects': projects,
        'stats': stats,
        'notifications': notifications,
        'payments': visible_payments,
        'teams': teams if actor_role == 'hr' else ([actor_team] if actor_team else []),
    }


def get_admin_data(user_id):
    """Get comprehensive data for admin dashboard with manager-style display"""
    all_employees = read_csv(EMP_CSV)
    all_tasks = read_csv(TASKS_CSV)
    all_projects = read_csv(PROJECTS_CSV)

    stats = {
        'totalEmployees': len(all_employees),
        'activeEmployees': len([e for e in all_employees if e.get('last_login')]),
        'totalProjects': len(all_projects),
        'activeProjects': len([p for p in all_projects if p.get('status') in ['active', 'planning']]),
        'totalTasks': len(all_tasks),
        'completedTasks': len([t for t in all_tasks if t.get('status') == 'completed']),
        'overdueTasks': calculate_overdue_tasks(all_tasks),
        'totalHours': calculate_total_hours(all_tasks),
        'productivity': calculate_team_productivity(all_employees, all_tasks),
        'unreadNotifications': 0
    }

    return {
        'employees': all_employees,
        'tasks': all_tasks,
        'projects': all_projects,
        'stats': stats,
        'notifications': []
    }


def calculate_overdue_tasks(tasks):
    """Calculate number of overdue tasks"""
    today = datetime.now().date()
    overdue = 0
    for task in tasks:
        status = normalize_task_status(task.get('status'))
        due_date_text = str(task.get('due_date') or task.get('dueDate') or '').strip()[:10]
        if status not in ['completed', 'cancelled'] and due_date_text:
            try:
                due_date = datetime.strptime(due_date_text, '%Y-%m-%d').date()
                if due_date < today:
                    overdue += 1
            except ValueError:
                continue
    return overdue


def calculate_total_hours(tasks):
    """Calculate total hours from task actual/estimated effort."""
    total = 0
    for task in tasks or []:
        total += _task_hour_value(task)
    return total


def calculate_team_productivity(employees, tasks):
    """Calculate team productivity percentage"""
    if not employees:
        return 0

    total_tasks = len(tasks)
    completed_tasks = len([t for t in tasks if normalize_task_status(t.get('status')) == 'completed'])

    if total_tasks == 0:
        return 0

    return int((completed_tasks / total_tasks) * 100)


def _parse_date_any(s: str):
    s = (s or '').strip()
    if not s:
        return None
    for fmt in ('%Y-%m-%d %H:%M:%S', '%Y-%m-%d', '%d-%m-%Y'):
        try:
            return datetime.strptime(s, fmt)
        except Exception:
            continue
    return None


def build_recent_activity(employees, projects, tasks, limit=10):
    """Build recent activity feed items from CSV rows.
    Returns list of {message, time, icon} sorted by time desc.
    """
    items = []
    for e in employees or []:
        dt = _parse_date_any(e.get('join_date',''))
        if dt:
            items.append({
                'message': f"Employee '{e.get('name','Unknown')}' joined",
                'time': dt.strftime('%Y-%m-%d %H:%M') if dt.time() != datetime.min.time() else dt.strftime('%Y-%m-%d'),
                'icon': 'fas fa-user-plus'
            })
    for p in projects or []:
        dt = _parse_date_any(p.get('start_date',''))
        if dt:
            items.append({
                'message': f"Project '{p.get('name','Unnamed')}' started",
                'time': dt.strftime('%Y-%m-%d'),
                'icon': 'fas fa-project-diagram'
            })
    for t in tasks or []:
        dt = _parse_date_any(t.get('created_at',''))
        if dt:
            items.append({
                'message': f"Task '{t.get('title','Untitled')}' created",
                'time': dt.strftime('%Y-%m-%d %H:%M') if dt.time() != datetime.min.time() else dt.strftime('%Y-%m-%d'),
                'icon': 'fas fa-tasks'
            })
    def _dt_of(item):
        return _parse_date_any(item['time']) or datetime.now()
    items.sort(key=_dt_of, reverse=True)
    return items[:limit]


def load_employees():
    """Load employees from CSV"""
    return read_csv(EMP_CSV)


def load_tasks():
    """Load tasks from CSV"""
    return read_csv(TASKS_CSV)


def load_projects():
    """Load projects from CSV"""
    return read_csv(PROJECTS_CSV)


def _normalize_list_strings(values):
    seen = set()
    ordered = []
    for value in values or []:
        item = str(value or '').strip()
        if not item or item in seen:
            continue
        seen.add(item)
        ordered.append(item)
    return ordered


def _build_role_map(users=None):
    rows = users if users is not None else read_csv(USERS_CSV)
    return {
        str(row.get('id', '')).strip(): normalize_role(row.get('role', 'employee'))
        for row in rows
        if str(row.get('id', '')).strip()
    }


def _build_employee_index(employees=None):
    rows = employees if employees is not None else read_csv(EMP_CSV)
    return {
        str(row.get('id', '')).strip(): row
        for row in rows
        if str(row.get('id', '')).strip()
    }


def _parse_team_members(project_row, member_rows=None):
    members = _normalize_list_strings(str(project_row.get('team_members', '') or '').split(','))
    if members:
        return members
    project_id = str(project_row.get('id', '')).strip()
    if not project_id:
        return []
    related = [
        row.get('employee_id')
        for row in (member_rows or read_csv(PROJECT_MEMBERS_CSV))
        if str(row.get('project_id', '')).strip() == project_id
    ]
    return _normalize_list_strings(related)


def _next_prefixed_id(prefix, rows, width):
    pattern = re.compile(rf"^{re.escape(prefix)}(\d+)$", re.IGNORECASE)
    highest = 0
    for row in rows or []:
        match = pattern.match(str(row.get('id', '')).strip())
        if match:
            highest = max(highest, int(match.group(1)))
    if highest:
        return f"{prefix}{highest + 1:0{width}d}"
    return f"{prefix}{uuid.uuid4().hex[:width].upper()}"


def _prefixed_id_sort_key(value, prefix=None):
    text = str(value or '').strip()
    if not text:
        return (2, float('inf'), '')
    if prefix:
        match = re.match(rf"^{re.escape(prefix)}(\d+)$", text, re.IGNORECASE)
        if match:
            return (0, int(match.group(1)), text.lower())
    suffix_match = re.search(r'(\d+)$', text)
    if suffix_match:
        return (1, int(suffix_match.group(1)), text.lower())
    return (2, float('inf'), text.lower())


def _sort_rows_by_id(rows, prefix=None, secondary_key='name'):
    return sorted(
        rows or [],
        key=lambda row: (
            _prefixed_id_sort_key((row or {}).get('id', ''), prefix),
            str((row or {}).get(secondary_key, '')).lower(),
        )
    )


def _team_blueprint_rows(employees=None):
    employee_lookup = _build_employee_index(employees)
    created_at = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    rows = []
    for blueprint in TEAM_BLUEPRINTS:
        manager = employee_lookup.get(blueprint['manager_id'], {})
        lead = employee_lookup.get(blueprint['teamlead_id'], {})
        rows.append({
            'id': blueprint['id'],
            'name': blueprint['name'],
            'department': blueprint['department'],
            'manager_id': blueprint['manager_id'],
            'manager_name': manager.get('name', blueprint['manager_id']),
            'teamlead_id': blueprint['teamlead_id'],
            'teamlead_name': lead.get('name', blueprint['teamlead_id']),
            'member_ids': ','.join(_normalize_list_strings(blueprint.get('member_ids', []))),
            'tagline': blueprint.get('tagline', ''),
            'focus_area': blueprint.get('focus_area', ''),
            'created_at': created_at,
            'updated_at': created_at,
        })
    return rows


def _build_team_indexes(team_rows=None):
    rows = team_rows if team_rows is not None else read_csv(TEAMS_CSV)
    by_id = {}
    by_member = {}
    for row in rows or []:
        team_id = str(row.get('id', '')).strip()
        if not team_id:
            continue
        by_id[team_id] = row
        manager_id = str(row.get('manager_id', '')).strip()
        teamlead_id = str(row.get('teamlead_id', '')).strip()
        member_ids = _normalize_list_strings(str(row.get('member_ids', '')).split(','))
        for employee_id in [manager_id, teamlead_id, *member_ids]:
            normalized_id = str(employee_id or '').strip()
            if normalized_id:
                by_member[normalized_id] = row
    return by_id, by_member


def get_team_record_for_user(user_id, team_rows=None):
    _by_id, by_member = _build_team_indexes(team_rows)
    return by_member.get(str(user_id or '').strip())


def get_team_member_ids(team_row, include_manager=False, include_teamlead=False):
    if not team_row:
        return []
    members = _normalize_list_strings(str(team_row.get('member_ids', '')).split(','))
    if include_teamlead and str(team_row.get('teamlead_id', '')).strip():
        members = [str(team_row.get('teamlead_id')).strip(), *members]
    if include_manager and str(team_row.get('manager_id', '')).strip():
        members = [str(team_row.get('manager_id')).strip(), *members]
    return _normalize_list_strings(members)


def _team_rotation_members(team_row):
    if not team_row:
        return []
    return _normalize_list_strings([
        str(team_row.get('teamlead_id', '')).strip(),
        *str(team_row.get('member_ids', '')).split(','),
    ])


def _project_team_assignment(project_row, team_rows):
    project_id = str(project_row.get('id', '')).strip()
    owner_id = str(project_row.get('owner_id', '')).strip()
    team = get_team_record_for_user(owner_id, team_rows)
    if team:
        return team
    sorted_teams = sorted(team_rows or [], key=lambda row: row.get('id', ''))
    if not sorted_teams:
        return None
    numeric = _prefixed_id_sort_key(project_id, PROJECT_ID_PREFIX)[1]
    if numeric == float('inf'):
        numeric = 1
    return sorted_teams[(int(numeric) - 1) % len(sorted_teams)]


def _project_member_selection(project_row, team_row):
    rotation = _team_rotation_members(team_row)
    if not rotation:
        return []
    owner_id = str(project_row.get('owner_id', '')).strip()
    if owner_id and owner_id in rotation:
        seed = rotation.index(owner_id)
    else:
        project_sort = _prefixed_id_sort_key(project_row.get('id', ''), PROJECT_ID_PREFIX)[1]
        seed = 0 if project_sort == float('inf') else int(project_sort) % len(rotation)
        owner_id = rotation[seed]
    ordered = rotation[seed:] + rotation[:seed]
    selected = [owner_id]
    for employee_id in ordered:
        if employee_id not in selected:
            selected.append(employee_id)
        if len(selected) >= 4:
            break
    return _normalize_list_strings(selected)


def _eligible_project_assignees(project_row, team_row):
    members = _normalize_list_strings(str(project_row.get('team_members', '')).split(','))
    manager_id = str(team_row.get('manager_id', '')).strip() if team_row else ''
    eligible = [member_id for member_id in members if member_id and member_id != manager_id]
    return eligible or members


def _salary_for_role(role):
    return _safe_int(ROLE_PAY_BANDS.get(normalize_role(role), ROLE_PAY_BANDS['employee']), ROLE_PAY_BANDS['employee'])


def ensure_platform_admin_account():
    if not (PLATFORM_FOUNDER_EMAIL and PLATFORM_FOUNDER_PASSWORD):
        return None
    users = read_csv(USERS_CSV)
    existing = next((row for row in users if normalize_role(row.get('role')) == 'platform_admin'), None)
    if existing:
        updated = False
        if str(existing.get('username') or '').strip().lower() != PLATFORM_FOUNDER_EMAIL.lower():
            existing['username'] = PLATFORM_FOUNDER_EMAIL
            updated = True
        password_hash = str(existing.get('password_hash') or '').strip()
        if not password_hash or not check_password_hash(password_hash, PLATFORM_FOUNDER_PASSWORD):
            existing['password_hash'] = generate_password_hash(PLATFORM_FOUNDER_PASSWORD)
            updated = True
        if str(existing.get('full_name') or '').strip() != 'TaskVise Founder':
            existing['full_name'] = 'TaskVise Founder'
            updated = True
        if str(existing.get('is_active') or '').strip().lower() != 'true':
            existing['is_active'] = 'true'
            updated = True
        if updated:
            write_csv(USERS_CSV, users, merge_fieldnames(users, USER_FIELDNAMES))
        return existing

    row = {
        'id': 'TVA001',
        'username': PLATFORM_FOUNDER_EMAIL,
        'password_hash': generate_password_hash(PLATFORM_FOUNDER_PASSWORD),
        'full_name': 'TaskVise Founder',
        'role': 'platform_admin',
        'created_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'is_active': 'true',
    }
    append_csv(USERS_CSV, row, USER_FIELDNAMES)
    return row


def ensure_demo_org_integrity(force=False):
    if not SEED_DEMO:
        ensure_platform_admin_account()
        return
    global _ORG_STRUCTURE_BOOTSTRAPPED
    if _ORG_STRUCTURE_BOOTSTRAPPED and not force:
        return

    ensure_platform_admin_account()
    users = read_csv(USERS_CSV)
    employees = read_csv(EMP_CSV)
    projects = read_csv(PROJECTS_CSV)
    tasks = read_csv(TASKS_CSV)
    role_map = _build_role_map(users)
    employee_lookup = _build_employee_index(employees)
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    today = datetime.now().date()
    teams = _team_blueprint_rows(employees)
    assigned_team_ids = {
        employee_id
        for team in teams
        for employee_id in [str(team.get('manager_id', '')).strip(), str(team.get('teamlead_id', '')).strip(), *str(team.get('member_ids', '')).split(',')]
        if str(employee_id or '').strip()
    }
    for employee in employees:
        employee_id = str(employee.get('id', '')).strip()
        role = role_map.get(employee_id, normalize_role(employee.get('role')))
        if not employee_id or employee_id in assigned_team_ids or role in {'admin', 'hr', 'platform_admin', 'manager', 'teamlead'}:
            continue
        target_team = next((
            team for team in teams
            if _normalize_text(team.get('department')) == _normalize_text(employee.get('department'))
        ), None)
        if not target_team:
            target_team = teams[0] if teams else None
        if not target_team:
            continue
        current_members = _normalize_list_strings(str(target_team.get('member_ids', '')).split(','))
        if employee_id not in current_members:
            current_members.append(employee_id)
            target_team['member_ids'] = ','.join(current_members)
            assigned_team_ids.add(employee_id)
    team_by_id, team_by_member = _build_team_indexes(teams)

    user_changed = False
    employee_changed = False
    project_changed = False
    task_changed = False
    member_rows = []
    member_counter = 1

    for user in users:
        user_id = str(user.get('id', '')).strip()
        role = normalize_role(user.get('role'))
        team = team_by_member.get(user_id)
        updates = {}
        if role == 'platform_admin':
            updates = {'full_name': user.get('full_name') or 'TaskVise Founder'}
        elif team:
            updates = {
                'team_id': team.get('id', ''),
                'team_name': team.get('name', ''),
                'manager_id': team.get('manager_id', ''),
                'teamlead_id': team.get('teamlead_id', ''),
            }
        else:
            updates = {'team_id': '', 'team_name': '', 'manager_id': '', 'teamlead_id': ''}
        for key, value in updates.items():
            if str(user.get(key, '')) != str(value):
                user[key] = value
                user_changed = True

    for employee in employees:
        employee_id = str(employee.get('id', '')).strip()
        role = role_map.get(employee_id, normalize_role(employee.get('role')))
        team = team_by_member.get(employee_id)
        updates = {
            'role': role,
            'team_id': team.get('id', '') if team else '',
            'team_name': team.get('name', '') if team else '',
            'manager_id': team.get('manager_id', '') if team else '',
            'teamlead_id': team.get('teamlead_id', '') if team else '',
        }
        for key, value in updates.items():
            if str(employee.get(key, '')) != str(value):
                employee[key] = value
                employee_changed = True

    employee_lookup = _build_employee_index(employees)

    for index, project in enumerate(projects):
        team = _project_team_assignment(project, teams)
        if not team:
            continue
        current_team_id = str(project.get('team_id', '')).strip()
        if current_team_id != str(team.get('id', '')).strip():
            project['team_id'] = team.get('id', '')
            project_changed = True
        for key in ['team_name', 'manager_id', 'teamlead_id']:
            source_key = key
            if key == 'team_name':
                desired = team.get('name', '')
            else:
                desired = team.get(key, '')
            if str(project.get(key, '')) != str(desired):
                project[key] = desired
                project_changed = True
        if str(project.get('owner_id', '')).strip() not in {team.get('manager_id', ''), team.get('teamlead_id', '')}:
            project['owner_id'] = team.get('manager_id', '') if index % 2 == 0 else team.get('teamlead_id', '')
            project_changed = True
        project_members = _project_member_selection(project, team)
        joined_members = ','.join(project_members)
        if str(project.get('team_members', '')).strip() != joined_members:
            project['team_members'] = joined_members
            project_changed = True
        for employee_id in project_members:
            member_rows.append({
                'id': f'{PROJECT_MEMBER_ID_PREFIX}{member_counter:0{PROJECT_MEMBER_ID_WIDTH}d}',
                'project_id': str(project.get('id', '')).strip(),
                'employee_id': employee_id,
            })
            member_counter += 1

    project_lookup = {str(project.get('id', '')).strip(): project for project in projects}
    task_buckets = {}
    for task in tasks:
        task_buckets.setdefault(str(task.get('project_id', '')).strip(), []).append(task)

    for project_id, project_tasks in task_buckets.items():
        project = project_lookup.get(project_id)
        team = team_by_id.get(str(project.get('team_id', '')).strip()) if project else None
        eligible = _eligible_project_assignees(project or {}, team)
        if not eligible:
            continue
        for offset, task in enumerate(sorted(project_tasks, key=lambda item: _prefixed_id_sort_key(item.get('id', ''), TASK_ID_PREFIX))):
            assignee_id = eligible[offset % len(eligible)]
            assignee = employee_lookup.get(assignee_id, {})
            desired_status = normalize_task_status(task.get('status'))
            desired_progress = max(0, min(100, _safe_int(task.get('progress', 0), 0)))
            if desired_status == 'completed':
                desired_progress = 100
            if desired_status == 'pending' and desired_progress > 0:
                desired_status = 'in-progress'
            if str(task.get('assignee_id', '')).strip() != assignee_id:
                task['assignee_id'] = assignee_id
                task_changed = True
            if str(task.get('assignee_name', '')).strip() != str(assignee.get('name', '')).strip():
                task['assignee_name'] = assignee.get('name', '')
                task_changed = True
            if str(task.get('status', '')).strip() != desired_status:
                task['status'] = desired_status
                task_changed = True
            if str(task.get('progress', '')) != str(desired_progress):
                task['progress'] = str(desired_progress)
                task_changed = True
            estimated_hours = max(1, _safe_int(task.get('estimated_hours', task.get('estimatedHours', 8)), 8))
            actual_hours = _safe_int(task.get('actual_hours', task.get('actualHours', 0)), 0)
            if desired_status in {'in-progress', 'review'} and actual_hours <= 0:
                task['actual_hours'] = str(max(1, estimated_hours // 2))
                task_changed = True
            elif desired_status == 'completed' and actual_hours <= 0:
                task['actual_hours'] = str(estimated_hours)
                task_changed = True

    if user_changed:
        write_csv(USERS_CSV, users, merge_fieldnames(users, USER_FIELDNAMES + ['team_id', 'team_name', 'manager_id', 'teamlead_id']))
    if employee_changed:
        write_csv(EMP_CSV, employees, merge_fieldnames(employees, EMP_FIELDNAMES + ['role', 'team_id', 'team_name', 'manager_id', 'teamlead_id']))
    write_csv(TEAMS_CSV, teams, TEAM_FIELDNAMES)
    if project_changed:
        write_csv(PROJECTS_CSV, projects, merge_fieldnames(projects, PROJECT_FIELDNAMES + ['team_id', 'team_name', 'manager_id', 'teamlead_id']))
    write_csv(PROJECT_MEMBERS_CSV, member_rows, PROJECT_MEMBER_FIELDNAMES)
    if task_changed:
        write_csv(TASKS_CSV, tasks, merge_fieldnames(tasks, TASK_FIELDNAMES))

    refreshed_employees = read_csv(EMP_CSV)
    refreshed_users = read_csv(USERS_CSV)
    role_map = _build_role_map(refreshed_users)
    payments = []
    for employee in refreshed_employees:
        employee_id = str(employee.get('id', '')).strip()
        if not employee_id:
            continue
        role = role_map.get(employee_id, normalize_role(employee.get('role')))
        team = get_team_record_for_user(employee_id, teams)
        productivity = max(0, min(100, _safe_int(employee.get('productivity', 0), 0)))
        base_salary = _salary_for_role(role)
        bonus = int(round(base_salary * (productivity / 100.0) * 0.08))
        last_paid = today.replace(day=1)
        if today.month == 12:
            next_paid = today.replace(year=today.year + 1, month=1, day=1)
        else:
            next_paid = today.replace(month=today.month + 1, day=1)
        payments.append({
            'id': f'PAY-{employee_id}',
            'employee_id': employee_id,
            'employee_name': employee.get('name', ''),
            'role': role,
            'team_id': team.get('id', '') if team else '',
            'team_name': team.get('name', '') if team else '',
            'department': employee.get('department', ''),
            'base_salary': str(base_salary),
            'bonus': str(bonus),
            'currency': 'INR',
            'payment_status': 'scheduled' if str(employee.get('status', 'active')).strip().lower() == 'active' else 'hold',
            'last_paid_date': last_paid.strftime('%Y-%m-%d'),
            'next_pay_date': next_paid.strftime('%Y-%m-%d'),
            'pay_cycle': 'monthly',
            'updated_at': timestamp,
        })
    write_csv(PAYMENTS_CSV, payments, PAYMENT_FIELDNAMES)
    export_demo_credentials_file(users=refreshed_users)
    _ORG_STRUCTURE_BOOTSTRAPPED = True


def _collect_id_rows(*collections):
    seen = set()
    rows = []
    for collection in collections:
        for row in collection or []:
            row_id = str((row or {}).get('id', '')).strip()
            if not row_id or row_id in seen:
                continue
            seen.add(row_id)
            rows.append({'id': row_id})
    return rows


def get_next_workforce_id(users=None, employees=None):
    return _next_prefixed_id(
        WORKFORCE_ID_PREFIX,
        _collect_id_rows(users if users is not None else read_csv(USERS_CSV), employees if employees is not None else read_csv(EMP_CSV)),
        WORKFORCE_ID_WIDTH,
    )


def get_next_project_id(projects=None):
    return _next_prefixed_id(
        PROJECT_ID_PREFIX,
        projects if projects is not None else read_csv(PROJECTS_CSV),
        PROJECT_ID_WIDTH,
    )


def get_next_task_id(tasks=None):
    return _next_prefixed_id(
        TASK_ID_PREFIX,
        tasks if tasks is not None else read_csv(TASKS_CSV),
        TASK_ID_WIDTH,
    )


def get_next_project_member_id(members=None):
    return _next_prefixed_id(
        PROJECT_MEMBER_ID_PREFIX,
        members if members is not None else read_csv(PROJECT_MEMBERS_CSV),
        PROJECT_MEMBER_ID_WIDTH,
    )


def _serialize_admin_employee(emp, role_map=None, default_company=None):
    roles = role_map or _build_role_map()
    employee_id = str(emp.get('id', '')).strip()
    role = roles.get(employee_id, normalize_role(emp.get('role', 'employee')))
    status = str(emp.get('status', 'active') or 'active').strip().lower()
    if status not in {'active', 'inactive'}:
        status = 'active'
    company_name = str(emp.get('company') or default_company or DEFAULT_COMPANY_NAME).strip()
    return {
        **emp,
        'id': employee_id,
        'name': emp.get('name', ''),
        'fullName': emp.get('name', ''),
        'email': emp.get('email', ''),
        'position': emp.get('position', ''),
        'department': emp.get('department', ''),
        'company': company_name,
        'phone': emp.get('phone', ''),
        'skills': emp.get('skills', ''),
        'location': emp.get('location', ''),
        'join_date': emp.get('join_date', ''),
        'last_login': emp.get('last_login', ''),
        'productivity': _safe_int(emp.get('productivity', 0), 0),
        'role': role,
        'team_id': emp.get('team_id', ''),
        'team_name': emp.get('team_name', ''),
        'manager_id': emp.get('manager_id', ''),
        'teamlead_id': emp.get('teamlead_id', ''),
        'status': status,
        'initials': ''.join(part[:1] for part in str(emp.get('name', '')).split()).upper()[:2],
    }


def _serialize_admin_project(project, employee_index=None, member_rows=None, default_company=None):
    employee_lookup = employee_index or _build_employee_index()
    team_member_ids = _parse_team_members(project, member_rows)
    owner = employee_lookup.get(str(project.get('owner_id', '')).strip(), {})
    team_members = []
    for member_id in team_member_ids:
        employee = employee_lookup.get(member_id, {})
        team_members.append({
            'id': member_id,
            'name': employee.get('name', member_id),
            'position': employee.get('position', ''),
            'department': employee.get('department', ''),
        })
    return {
        **project,
        'id': str(project.get('id', '')).strip(),
        'name': project.get('name', ''),
        'description': project.get('description', ''),
        'owner_id': str(project.get('owner_id', '')).strip(),
        'owner_name': owner.get('name', 'Unassigned'),
        'department': owner.get('department', project.get('department', 'Operations')),
        'company': project.get('company') or owner.get('company') or default_company or DEFAULT_COMPANY_NAME,
        'team_id': project.get('team_id', ''),
        'team_name': project.get('team_name', ''),
        'manager_id': project.get('manager_id', ''),
        'teamlead_id': project.get('teamlead_id', ''),
        'status': normalize_project_status(project.get('status', 'planning')),
        'deadline': str(project.get('end_date', project.get('deadline', '')) or '')[:10],
        'progress': max(0, min(100, int(project.get('progress', 0) or 0))),
        'team_members': team_member_ids,
        'team_members_count': len(team_member_ids),
        'team_member_details': team_members,
    }


def _serialize_admin_task(task, employee_index=None, project_lookup=None):
    employee_lookup = employee_index or _build_employee_index()
    projects = project_lookup or {}
    assignee_id = str(task.get('assignee_id', '')).strip()
    project_id = str(task.get('project_id', '')).strip()
    assignee = employee_lookup.get(assignee_id, {})
    project = projects.get(project_id, {})
    return {
        **task,
        'id': str(task.get('id', '')).strip(),
        'title': task.get('title', ''),
        'description': task.get('description', ''),
        'assignee_id': assignee_id,
        'assignee_name': task.get('assignee_name') or assignee.get('name', ''),
        'project_id': project_id,
        'project_name': project.get('name', task.get('project_name', '')),
        'status': normalize_task_status(task.get('status')),
        'priority': str(task.get('priority', 'medium') or 'medium').strip().lower(),
        'due_date': str(task.get('due_date', task.get('dueDate', '')) or '')[:10],
        'estimated_hours': str(task.get('estimated_hours', task.get('estimatedHours', '')) or '0'),
        'actual_hours': str(task.get('actual_hours', task.get('actualHours', '')) or '0'),
        'progress': max(0, min(100, int(task.get('progress', 0) or 0))),
    }


def get_admin_dashboard_payload():
    ensure_demo_org_integrity()
    ensure_projects_team_members()
    raw_employees = load_employees()
    raw_tasks = load_tasks()
    raw_projects = load_projects()
    default_company = infer_primary_company_name(raw_employees, raw_projects)
    users = read_csv(USERS_CSV)
    role_map = _build_role_map(users)
    employee_index = _build_employee_index(raw_employees)
    member_rows = read_csv(PROJECT_MEMBERS_CSV)

    employees = _sort_rows_by_id(
        [_serialize_admin_employee(emp, role_map, default_company) for emp in raw_employees],
        WORKFORCE_ID_PREFIX,
    )
    projects = sorted(
        [_serialize_admin_project(project, employee_index, member_rows, default_company) for project in raw_projects],
        key=lambda item: _prefixed_id_sort_key(item.get('id', ''), PROJECT_ID_PREFIX),
    )
    project_lookup = {project.get('id'): project for project in projects}
    tasks = sorted(
        [_serialize_admin_task(task, employee_index, project_lookup) for task in raw_tasks],
        key=lambda item: _prefixed_id_sort_key(item.get('id', ''), TASK_ID_PREFIX),
    )

    stats = {
        'total_employees': len(employees),
        'active_projects': len([p for p in projects if p.get('status') == 'active']),
        'completed_tasks': len([t for t in tasks if t.get('status') == 'completed']),
        'total_tasks': len(tasks),
        'completion_rate': calculate_completion_rate(tasks),
        'overdue_tasks': len([t for t in tasks if is_task_overdue(t)]),
        'total_projects': len(projects),
        'active_projects_count': len([p for p in projects if p.get('status') == 'active']),
        'completed_projects': len([p for p in projects if p.get('status') == 'completed']),
        'on_hold_projects': len([p for p in projects if p.get('status') == 'on-hold']),
        'employees_managed': len(employees),
        'projects_overseen': len(projects),
        'tasks_assigned': len([t for t in tasks if str(t.get('assignee_id', '')).strip()]),
        'avg_productivity': int(round(sum(_safe_int(e.get('productivity', 0), 0) for e in employees) / max(len(employees), 1))),
        'total_hours': calculate_total_hours(tasks),
    }
    recent_activity = build_recent_activity(employees, projects, tasks)
    return {
        'employees': employees,
        'tasks': tasks,
        'projects': projects,
        'stats': stats,
        'recent_activity': recent_activity,
    }


DEPARTMENT_SKILL_BASELINES = {
    'engineering': ['Python', 'JavaScript', 'React', 'SQL', 'Testing'],
    'design': ['Figma', 'UI Design', 'UX Research', 'Prototyping'],
    'product': ['Product Strategy', 'Analytics', 'Roadmapping', 'User Research'],
    'marketing': ['SEO', 'Content Strategy', 'Analytics', 'Campaign Planning'],
    'sales': ['CRM', 'Negotiation', 'Lead Generation', 'Client Relations'],
    'hr': ['Recruitment', 'Training', 'Compliance', 'People Operations'],
    'finance': ['Forecasting', 'Excel', 'Budgeting', 'Reporting'],
    'it': ['AWS', 'Networking', 'Security', 'Automation'],
    'operations': ['Process Design', 'Reporting', 'Coordination', 'Analytics'],
}


PROJECT_SKILL_HINTS = {
    'ai': ['Python', 'Machine Learning', 'Analytics'],
    'assistant': ['Python', 'NLP', 'Analytics'],
    'cloud': ['AWS', 'Docker', 'Kubernetes'],
    'migration': ['AWS', 'Docker', 'Security'],
    'mobile': ['React', 'UI Design', 'Testing'],
    'redesign': ['Figma', 'UI Design', 'UX Research'],
    'api': ['Python', 'API Design', 'Testing'],
    'compliance': ['Compliance', 'Reporting', 'Process Design'],
    'marketing': ['SEO', 'Content Strategy', 'Analytics'],
    'sales': ['CRM', 'Negotiation', 'Client Relations'],
    'finance': ['Forecasting', 'Budgeting', 'Reporting'],
    'pipeline': ['Python', 'Data Engineering', 'Automation'],
    'security': ['Security', 'Networking', 'AWS'],
}


def _clean_skill_label(value):
    text = str(value or '').strip()
    if not text:
        return ''
    replacements = {
        'ui design': 'UI Design',
        'ux research': 'UX Research',
        'ci/cd': 'CI/CD',
        'node.js': 'Node.js',
        'react native': 'React Native',
        'people operations': 'People Operations',
        'api design': 'API Design',
        'machine learning': 'Machine Learning',
        'data engineering': 'Data Engineering',
    }
    normalized = re.sub(r'\s+', ' ', text).strip()
    lowered = normalized.lower()
    if lowered in replacements:
        return replacements[lowered]
    if normalized.isupper() and len(normalized) <= 5:
        return normalized
    return ' '.join(part[:1].upper() + part[1:] for part in normalized.split(' '))


def _parse_skills(raw_value):
    pieces = re.split(r'[,/|;]+', str(raw_value or ''))
    return _normalize_list_strings(_clean_skill_label(piece) for piece in pieces)


def _build_skill_vocabulary(employees):
    vocabulary = set()
    for employee in employees or []:
        vocabulary.update(_parse_skills(employee.get('skills', '')))
    for values in DEPARTMENT_SKILL_BASELINES.values():
        vocabulary.update(values)
    for values in PROJECT_SKILL_HINTS.values():
        vocabulary.update(values)
    return sorted(vocabulary)


def _extract_skills_from_text(text, vocabulary):
    lowered = _normalize_text(text)
    if not lowered:
        return []
    found = []
    for skill in vocabulary:
        if _normalize_text(skill) and _normalize_text(skill) in lowered:
            found.append(skill)
    for keyword, suggested_skills in PROJECT_SKILL_HINTS.items():
        if keyword in lowered:
            found.extend(suggested_skills)
    return _normalize_list_strings(found)


def _build_month_window(count=6):
    cursor = datetime.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    window = []
    for _ in range(count):
        window.append(cursor.strftime('%Y-%m'))
        if cursor.month == 1:
            cursor = cursor.replace(year=cursor.year - 1, month=12)
        else:
            cursor = cursor.replace(month=cursor.month - 1)
    return list(reversed(window))


def _month_label(month_key):
    try:
        return datetime.strptime(month_key, '%Y-%m').strftime('%b %Y')
    except Exception:
        return month_key


def _task_hour_value(task):
    actual = _safe_int(task.get('actual_hours', 0), 0)
    estimated = _safe_int(task.get('estimated_hours', 0), 0)
    return actual or estimated or 6


def build_admin_analytics_payload(employees, projects, tasks):
    employee_index = {str(employee.get('id', '')).strip(): employee for employee in employees}
    project_index = {str(project.get('id', '')).strip(): project for project in projects}
    default_company = infer_primary_company_name(employees, projects)
    tasks_by_employee = {}
    departments = sorted(
        {str(employee.get('department') or 'Operations').strip() for employee in employees}
        | {str(project.get('department') or 'Operations').strip() for project in projects}
    )

    for task in tasks:
        assignee_id = str(task.get('assignee_id', '')).strip()
        tasks_by_employee.setdefault(assignee_id, []).append(task)

    department_stats = []
    for department in [dept for dept in departments if dept]:
        department_employee_ids = {
            str(employee.get('id', '')).strip()
            for employee in employees
            if str(employee.get('department') or '').strip() == department
        }
        department_projects = [
            project for project in projects
            if str(project.get('department') or '').strip() == department
        ]
        department_tasks = [
            task for task in tasks
            if str(task.get('assignee_id', '')).strip() in department_employee_ids
            or str(task.get('project_id', '')).strip() in {str(project.get('id', '')).strip() for project in department_projects}
        ]
        completed_count = len([task for task in department_tasks if task.get('status') == 'completed'])
        productivity = int(round((completed_count / max(len(department_tasks), 1)) * 100))
        department_stats.append({
            'department': department,
            'employee_count': len(department_employee_ids),
            'project_count': len(department_projects),
            'task_count': len(department_tasks),
            'productivity': productivity,
            'avg_progress': int(round(sum(_safe_int(task.get('progress', 0), 0) for task in department_tasks) / max(len(department_tasks), 1))),
        })
    department_stats.sort(key=lambda item: (-item['productivity'], item['department']))

    month_keys = _build_month_window(6)
    monthly_lookup = {
        month_key: {'month': _month_label(month_key), 'tasks': 0, 'completed': 0, 'hours': 0}
        for month_key in month_keys
    }
    for task in tasks:
        created = _parse_date_any(task.get('created_at'))
        if not created:
            continue
        month_key = created.strftime('%Y-%m')
        if month_key not in monthly_lookup:
            continue
        monthly_lookup[month_key]['tasks'] += 1
        if task.get('status') == 'completed':
            monthly_lookup[month_key]['completed'] += 1
        monthly_lookup[month_key]['hours'] += _task_hour_value(task)
    monthly_stats = [monthly_lookup[key] for key in month_keys]

    top_performers = []
    for employee in employees:
        employee_id = str(employee.get('id', '')).strip()
        owned_tasks = tasks_by_employee.get(employee_id, [])
        completed = len([task for task in owned_tasks if task.get('status') == 'completed'])
        overdue = len([task for task in owned_tasks if is_task_overdue(task)])
        completion_rate = int(round((completed / max(len(owned_tasks), 1)) * 100))
        productivity = _safe_int(employee.get('productivity', completion_rate), completion_rate) or completion_rate
        score = int(round((productivity * 0.6) + (completion_rate * 0.4) - (overdue * 4)))
        top_performers.append({
            'id': employee_id,
            'name': employee.get('name', 'Unknown'),
            'department': employee.get('department', 'Operations'),
            'role': employee.get('role', 'employee'),
            'productivity': productivity,
            'completion_rate': completion_rate,
            'completed_tasks': completed,
            'total_tasks': len(owned_tasks),
            'score': max(score, 0),
        })
    top_performers.sort(key=lambda item: (-item['score'], -item['completed_tasks'], item['name']))
    top_performers = top_performers[:5]

    workload_insights = []
    for employee in employees:
        employee_id = str(employee.get('id', '')).strip()
        owned_tasks = tasks_by_employee.get(employee_id, [])
        active_tasks = len([task for task in owned_tasks if task.get('status') not in {'completed', 'cancelled'}])
        overdue_tasks = len([task for task in owned_tasks if is_task_overdue(task)])
        avg_progress = int(round(sum(_safe_int(task.get('progress', 0), 0) for task in owned_tasks) / max(len(owned_tasks), 1)))
        workload_state = 'Balanced'
        if active_tasks >= 7 or overdue_tasks >= 2:
            workload_state = 'Overloaded'
        elif active_tasks <= 2:
            workload_state = 'Light'
        workload_insights.append({
            'name': employee.get('name', 'Unknown'),
            'department': employee.get('department', 'Operations'),
            'active_tasks': active_tasks,
            'overdue_tasks': overdue_tasks,
            'avg_progress': avg_progress,
            'state': workload_state,
        })
    workload_insights.sort(key=lambda item: (-item['overdue_tasks'], -item['active_tasks'], item['name']))
    workload_insights = workload_insights[:6]

    role_distribution = []
    role_counts = Counter(str(employee.get('role') or 'employee').strip().lower() for employee in employees)
    for role, count in role_counts.most_common():
        role_distribution.append({'role': role, 'count': count})

    company_overview = []
    company_counts = Counter()
    for employee in employees:
        company = str(employee.get('company') or default_company).strip()
        if company:
            company_counts[company] += 1
    for project in projects:
        company = str(project.get('company') or default_company).strip()
        if company:
            company_counts[company] += 1
    for company, count in company_counts.most_common(4):
        project_count = len([project for project in projects if str(project.get('company') or default_company).strip() == company])
        employee_count = len([employee for employee in employees if str(employee.get('company') or default_company).strip() == company])
        company_overview.append({
            'company': company,
            'employee_count': employee_count,
            'project_count': project_count,
            'task_count': len([
                task for task in tasks
                if str(project_index.get(str(task.get('project_id', '')).strip(), {}).get('company') or '').strip() == company
            ]),
        })

    return {
        'department_stats': department_stats,
        'monthly_stats': monthly_stats,
        'top_performers': top_performers,
        'workload_insights': workload_insights,
        'role_distribution': role_distribution,
        'company_overview': company_overview,
    }


def build_admin_skill_gap_payload(employees, projects, tasks):
    employee_map = {str(employee.get('id', '')).strip(): employee for employee in employees}
    default_company = infer_primary_company_name(employees, projects)
    tasks_by_project = {}
    for task in tasks:
        project_id = str(task.get('project_id', '')).strip()
        tasks_by_project.setdefault(project_id, []).append(task)

    vocabulary = _build_skill_vocabulary(employees)
    rows = []
    missing_skill_counter = Counter()
    severity_counter = Counter()

    for project in projects:
        project_id = str(project.get('id', '')).strip()
        project_tasks = tasks_by_project.get(project_id, [])
        base_skills = DEPARTMENT_SKILL_BASELINES.get(_normalize_text(project.get('department')), ['Planning', 'Coordination', 'Reporting'])
        text_blob = ' '.join([
            str(project.get('name') or ''),
            str(project.get('description') or ''),
            ' '.join(str(task.get('title') or '') for task in project_tasks),
            ' '.join(str(task.get('description') or '') for task in project_tasks),
        ])
        required_skills = _normalize_list_strings(base_skills + _extract_skills_from_text(text_blob, vocabulary))

        team_member_ids = _parse_team_members(project)
        if project.get('owner_id'):
            team_member_ids = _normalize_list_strings(team_member_ids + [project.get('owner_id')])

        available_skills = []
        for member_id in team_member_ids:
            available_skills.extend(_parse_skills(employee_map.get(str(member_id).strip(), {}).get('skills', '')))
        available_skills = _normalize_list_strings(available_skills)

        required_set = set(required_skills)
        available_set = set(available_skills)
        matched = len(required_set & available_set)
        match_rate = int(round((matched / max(len(required_set), 1)) * 100)) if required_set else 100
        missing_skills = sorted(required_set - available_set)

        if missing_skills:
            if match_rate < 55 or len(missing_skills) >= 3:
                severity = 'high'
            elif match_rate < 80 or len(missing_skills) >= 2:
                severity = 'medium'
            else:
                severity = 'low'
        else:
            severity = 'low'

        if missing_skills:
            missing_skill_counter.update(missing_skills)
        severity_counter[severity] += 1

        recommendation = 'Current team can deliver with minor enablement.'
        if severity == 'high' and missing_skills:
            recommendation = f"Prioritize upskilling or hiring for {', '.join(missing_skills[:3])}."
        elif severity == 'medium' and missing_skills:
            recommendation = f"Cross-train the project squad on {', '.join(missing_skills[:2])}."
        elif severity == 'low' and missing_skills:
            recommendation = f"Schedule a short knowledge transfer on {missing_skills[0]}."

        rows.append({
            'project_id': project_id,
            'project_name': project.get('name', 'Unnamed Project'),
            'department': project.get('department', 'Operations'),
            'company': project.get('company') or default_company,
            'required_skills': required_skills,
            'available_skills': available_skills,
            'missing_skills': missing_skills,
            'match_rate': match_rate,
            'gap_severity': severity,
            'recommendation': recommendation,
            'team_members_count': len(team_member_ids),
        })

    rows.sort(key=lambda item: ({'high': 0, 'medium': 1, 'low': 2}.get(item['gap_severity'], 3), item['match_rate'], item['project_name']))
    avg_match = int(round(sum(item['match_rate'] for item in rows) / max(len(rows), 1))) if rows else 100

    return {
        'rows': rows,
        'summary': {
            'high': severity_counter.get('high', 0),
            'medium': severity_counter.get('medium', 0),
            'low': severity_counter.get('low', 0),
            'avg_match_rate': avg_match,
            'projects_analyzed': len(rows),
        },
        'missing_skill_counts': [
            {'skill': skill, 'count': count}
            for skill, count in missing_skill_counter.most_common(8)
        ],
        'recommended_training': [
            {'skill': skill, 'count': count}
            for skill, count in missing_skill_counter.most_common(5)
        ],
        'departments': sorted({str(project.get('department') or 'Operations').strip() for project in projects}),
    }


def _sync_project_members(project_id, team_member_ids):
    existing = read_csv(PROJECT_MEMBERS_CSV)
    retained = [row for row in existing if str(row.get('project_id', '')).strip() != str(project_id).strip()]
    for member_id in _normalize_list_strings(team_member_ids):
        next_member_id = get_next_project_member_id(retained)
        retained.append({
            'id': next_member_id,
            'project_id': str(project_id).strip(),
            'employee_id': member_id,
        })
    write_csv(
        PROJECT_MEMBERS_CSV,
        retained,
        merge_fieldnames(retained if retained else existing, PROJECT_MEMBER_FIELDNAMES),
    )


def ensure_projects_team_members():
    """Ensure projects.csv has a 'team_members' column and backfill from project_members.csv.
    team_members stored as comma-separated employee_ids.
    """
    try:
        rows = read_csv(PROJECTS_CSV)
        if not rows:
            return
        has_col = any('team_members' in r for r in rows)
        if has_col:
            return
        members = read_csv(PROJECT_MEMBERS_CSV)
        team_map = {}
        for m in members:
            pid = m.get('project_id')
            eid = m.get('employee_id')
            if not pid:
                continue
            team_map.setdefault(pid, []).append(eid)
        for r in rows:
            pid = r.get('id')
            r['team_members'] = ','.join([e for e in team_map.get(pid, []) if e])
        write_csv(
            PROJECTS_CSV,
            rows,
            merge_fieldnames(
                rows,
                ['id', 'name', 'description', 'owner_id', 'start_date', 'end_date', 'status', 'team_members']
            )
        )
    except Exception:
        pass


def normalize_leave_status(value):
    raw = str(value or '').strip().lower()
    aliases = {
        'approve': 'approved',
        'approved leave': 'approved',
        'accept': 'approved',
        'accepted': 'approved',
        'reject': 'rejected',
        'declined': 'rejected',
        'deny': 'rejected',
        'denied': 'rejected',
        'pending approval': 'pending',
        'awaiting approval': 'pending',
    }
    return aliases.get(raw, raw)


def _extract_datetime_text(value):
    text = str(value or '').strip()
    if not text:
        return ''
    match = re.search(r'\d{4}-\d{2}-\d{2}[ T]\d{2}:\d{2}:\d{2}', text)
    if not match:
        return ''
    return match.group(0).replace('T', ' ')


def normalize_leave_row(row):
    source = row or {}
    extra = source.get('', '')
    normalized = {
        key: str(source.get(key, '') if source.get(key, '') is not None else '').strip()
        for key in LEAVE_FIELDNAMES
    }

    status_candidate = normalize_leave_status(normalized.get('status'))
    applied_candidate = normalize_leave_status(normalized.get('applied_at'))
    leave_type = (normalized.get('type') or '').strip().lower()

    if status_candidate not in VALID_LEAVE_STATUSES and applied_candidate in VALID_LEAVE_STATUSES:
        if not leave_type and status_candidate:
            leave_type = status_candidate
        status_candidate = applied_candidate
        normalized['applied_at'] = ''

    type_as_status = normalize_leave_status(leave_type)
    if status_candidate not in VALID_LEAVE_STATUSES and type_as_status in VALID_LEAVE_STATUSES:
        status_candidate = type_as_status
        leave_type = ''

    if status_candidate not in VALID_LEAVE_STATUSES and status_candidate:
        if not leave_type:
            leave_type = status_candidate
        status_candidate = ''

    if status_candidate not in VALID_LEAVE_STATUSES:
        status_candidate = 'pending'
    if not leave_type:
        leave_type = 'leave'

    applied_at = (normalized.get('applied_at') or '').strip()
    if normalize_leave_status(applied_at) in VALID_LEAVE_STATUSES or not applied_at:
        extracted = _extract_datetime_text(extra) or _extract_datetime_text(source.get('created_at', ''))
        if extracted:
            applied_at = extracted
    if not applied_at:
        applied_at = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    normalized['start_date'] = (normalized.get('start_date') or '')[:10]
    normalized['end_date'] = (normalized.get('end_date') or '')[:10]
    normalized['type'] = leave_type
    normalized['status'] = status_candidate
    normalized['applied_at'] = applied_at
    return normalized


def ensure_leave_data_integrity():
    try:
        rows = read_csv(LEAVE_CSV)
        if not rows:
            return []

        normalized_rows = []
        should_rewrite = False
        for row in rows:
            normalized = normalize_leave_row(row)
            normalized_rows.append(normalized)

            existing = {
                key: str(row.get(key, '') if row.get(key, '') is not None else '').strip()
                for key in LEAVE_FIELDNAMES
            }
            if existing != normalized:
                should_rewrite = True
            if any(k and k not in LEAVE_FIELDNAMES for k in row.keys()):
                should_rewrite = True

        if should_rewrite:
            write_csv(LEAVE_CSV, normalized_rows, LEAVE_FIELDNAMES)
        return normalized_rows
    except Exception:
        return []


def ensure_leave_type_column():
    """Back-compat wrapper used by existing routes."""
    ensure_leave_data_integrity()


def create_notification(user_id, title, message, notif_type='system'):
    if not user_id:
        return
    row = {
        'id': str(uuid.uuid4()),
        'user_id': str(user_id),
        'title': str(title or 'Notification'),
        'message': str(message or ''),
        'type': str(notif_type or 'system').lower(),
        'is_read': 'false',
        'created_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
    }
    append_csv(NOTIF_CSV, row, NOTIFICATION_FIELDNAMES)


def send_email_notification(to_email, subject, message):
    recipient = str(to_email or '').strip()
    if not recipient or not EMAIL_NOTIFICATIONS_ENABLED:
        return False
    if not SMTP_HOST or not SMTP_FROM:
        print(f"Email notifications skipped for {recipient}: SMTP is not configured.")
        return False

    email = EmailMessage()
    email['From'] = SMTP_FROM
    email['To'] = recipient
    email['Subject'] = str(subject or 'TaskVise Notification')
    email.set_content(str(message or ''))

    try:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=10) as server:
            if SMTP_USE_TLS:
                server.starttls(context=ssl.create_default_context())
            if SMTP_USER:
                server.login(SMTP_USER, SMTP_PASSWORD)
            server.send_message(email)
        return True
    except Exception as exc:
        print(f"Email notification error for {recipient}: {exc}")
        return False


def _get_user_notification_email(user_id):
    employee = find_by_id(EMP_CSV, user_id) or {}
    user = find_by_id(USERS_CSV, user_id) or {}
    return str(employee.get('email') or user.get('username') or '').strip()


def notify_user(user_id, title, message, notif_type='system', email_subject=None):
    if not user_id:
        return
    create_notification(user_id, title, message, notif_type)
    settings, _rows = get_user_settings_record(user_id)
    if _truthy(settings.get('email_notifications'), True):
        send_email_notification(
            _get_user_notification_email(user_id),
            email_subject or title,
            message,
        )


def notify_users(user_ids, title, message, notif_type='system', email_subject=None):
    for user_id in _normalize_list_strings(user_ids):
        notify_user(user_id, title, message, notif_type, email_subject=email_subject)


def notify_task_assignment(task_row, actor_label='Manager', is_new_assignment=False):
    assignee_id = str(task_row.get('assignee_id', '')).strip()
    if not assignee_id:
        return
    task_title = str(task_row.get('title') or 'Untitled Task').strip()
    project_name = ''
    if str(task_row.get('project_id', '')).strip():
        project = find_by_id(PROJECTS_CSV, task_row.get('project_id')) or {}
        project_name = str(project.get('name') or '').strip()
    due_date = str(task_row.get('due_date') or task_row.get('dueDate') or '').strip()[:10]

    if is_new_assignment:
        title = 'New Task Assigned'
        message = f'{actor_label} assigned "{task_title}" to you.'
    else:
        title = 'Task Updated'
        message = f'{actor_label} updated task "{task_title}".'

    detail_parts = []
    if project_name:
        detail_parts.append(f'Project: {project_name}')
    if due_date:
        detail_parts.append(f'Due: {due_date}')
    if task_row.get('status'):
        detail_parts.append(f'Status: {normalize_task_status(task_row.get("status"))}')
    if detail_parts:
        message = f'{message} ' + ' | '.join(detail_parts)

    notify_user(assignee_id, title, message, 'task', email_subject=title)


def notify_project_assignment(project_row, actor_label='Manager', is_new_assignment=False):
    project_name = str(project_row.get('name') or 'Untitled Project').strip()
    deadline = str(project_row.get('end_date') or project_row.get('deadline') or '').strip()[:10]
    team_members = _parse_team_members(project_row)
    owner_id = str(project_row.get('owner_id', '')).strip()
    recipients = _normalize_list_strings(team_members + ([owner_id] if owner_id else []))
    if not recipients:
        return

    if is_new_assignment:
        title = 'Project Assignment'
        message = f'{actor_label} added you to project "{project_name}".'
    else:
        title = 'Project Updated'
        message = f'{actor_label} updated project "{project_name}".'
    if deadline:
        message = f'{message} Deadline: {deadline}.'

    notify_users(recipients, title, message, 'project', email_subject=title)


def calculate_completion_rate(tasks):
    """Calculate task completion rate"""
    if not tasks:
        return "0%"
    completed = len([t for t in tasks if t.get('status') == 'completed'])
    return f"{(completed / len(tasks)) * 100:.0f}%"


def split_skills(value):
    return [item.strip() for item in str(value or '').split(',') if item.strip()]


def get_employee_initials(name):
    parts = [part for part in str(name or '').strip().split() if part]
    if not parts:
        return 'TV'
    if len(parts) == 1:
        return parts[0][:2].upper()
    return (parts[0][0] + parts[-1][0]).upper()


def classify_employee_badge(productivity, completion_rate, skills_count, total_tasks):
    productivity = max(0, min(100, _safe_int(productivity, 0)))
    completion_rate = max(0, min(100, _safe_int(completion_rate, 0)))
    skills_count = max(0, _safe_int(skills_count, 0))
    total_tasks = max(0, _safe_int(total_tasks, 0))

    if productivity >= 90 and completion_rate >= 75 and skills_count >= 4:
        return ('top-performer', 'Top Performer')
    if productivity >= 82 and skills_count >= 4:
        return ('highly-skilled', 'Highly Skilled')
    if productivity >= 70 and (completion_rate >= 60 or total_tasks >= 3):
        return ('proficient', 'Proficient')
    if productivity >= 55 or skills_count >= 3:
        return ('steady', 'Steady Contributor')
    return ('needs-improvement', 'Needs Improvement')


def is_task_overdue(task):
    """Check if a task is overdue"""
    due_date_text = str(task.get('due_date') or task.get('dueDate') or '').strip()[:10]
    if not due_date_text:
        return False
    try:
        due_date = datetime.strptime(due_date_text, '%Y-%m-%d')
        return due_date < datetime.now() and normalize_task_status(task.get('status')) != 'completed'
    except:
        return False


def build_manager_analytics_payload(user_id):
    manager_data = get_manager_data(user_id)
    employees = manager_data.get('employees', [])
    tasks = manager_data.get('tasks', [])
    projects = manager_data.get('projects', [])
    analytics = build_admin_analytics_payload(employees, projects, tasks)

    tasks_by_employee = {}
    monthly_created = Counter()
    status_counter = Counter()
    for task in tasks:
        assignee_id = str(task.get('assignee_id', '')).strip()
        tasks_by_employee.setdefault(assignee_id, []).append(task)
        status_counter[normalize_task_status(task.get('status'))] += 1
        created_at = _parse_date_any(task.get('created_at'))
        if created_at:
            monthly_created[created_at.strftime('%Y-%m')] += 1

    employee_performance = []
    active_employees = 0
    for employee in employees:
        employee_id = str(employee.get('id', '')).strip()
        employee_tasks = tasks_by_employee.get(employee_id, [])
        completed_tasks = len([
            task for task in employee_tasks
            if normalize_task_status(task.get('status')) == 'completed'
        ])
        total_tasks = len(employee_tasks)
        overdue_tasks = len([task for task in employee_tasks if is_task_overdue(task)])
        completion_rate = int(round((completed_tasks / max(total_tasks, 1)) * 100))
        productivity = _safe_int(employee.get('productivity', completion_rate), completion_rate) or completion_rate
        if total_tasks or str(employee.get('last_login') or '').strip():
            active_employees += 1
        employee_performance.append({
            'employee_id': employee_id,
            'name': employee.get('fullName') or employee.get('name') or 'Unknown',
            'department': employee.get('department', 'Operations'),
            'role': normalize_role(employee.get('role', 'employee')),
            'teamName': employee.get('team_name', ''),
            'completedTasks': completed_tasks,
            'totalTasks': total_tasks,
            'completionRate': completion_rate,
            'productivity': max(0, min(100, productivity)),
            'overdueTasks': overdue_tasks,
        })

    employee_performance.sort(
        key=lambda item: (-item['productivity'], -item['completedTasks'], item['name'])
    )

    total_completed = len([
        task for task in tasks
        if normalize_task_status(task.get('status')) == 'completed'
    ])
    total_tasks = len(tasks)
    completion_rate = int(round((total_completed / max(total_tasks, 1)) * 100)) if total_tasks else 0
    avg_productivity = int(round(
        sum(item.get('productivity', 0) for item in employee_performance) / max(len(employee_performance), 1)
    )) if employee_performance else 0

    return {
        'teamSize': len(employees),
        'activeEmployees': active_employees,
        'totalProjects': len(projects),
        'activeProjects': len([
            project for project in projects
            if str(project.get('status') or '').strip().lower() in {'active', 'planning'}
        ]),
        'totalTasks': total_tasks,
        'completedTasks': total_completed,
        'completionRate': completion_rate,
        'avgProductivity': avg_productivity,
        'overdueTasks': calculate_overdue_tasks(tasks),
        'employeePerformance': employee_performance,
        'teamPerformance': employee_performance,
        'tasksByStatus': dict(status_counter),
        'departmentStats': analytics.get('department_stats', []),
        'monthlyStats': analytics.get('monthly_stats', []),
        'topPerformers': analytics.get('top_performers', []),
        'workloadInsights': analytics.get('workload_insights', []),
        'generatedAt': datetime.now().isoformat(),
    }


def get_team_members(manager_id):
    """Get all employees assigned to a manager"""
    ensure_demo_org_integrity()
    if not _use_database(USERS_CSV) or DB_BACKEND != 'mongodb':
        team = get_team_record_for_user(manager_id)
        return get_team_member_ids(team, include_teamlead=True)
    try:
        team_coll = _mongo_collection('team_assignments')
        team = team_coll.find_one({'manager_id': manager_id})
        if team:
            return team.get('employee_ids', [])
        return []
    except:
        return []


def get_manager_for_employee(employee_id):
    """Get the manager assigned to an employee"""
    ensure_demo_org_integrity()
    if not _use_database(USERS_CSV) or DB_BACKEND != 'mongodb':
        team = get_team_record_for_user(employee_id)
        return str((team or {}).get('manager_id') or '').strip() or None
    try:
        team_coll = _mongo_collection('team_assignments')
        team = team_coll.find_one({'employee_ids': employee_id})
        if team:
            return team.get('manager_id')
        return None
    except:
        return None


def get_teamlead_for_employee(employee_id):
    ensure_demo_org_integrity()
    team = get_team_record_for_user(employee_id)
    return str((team or {}).get('teamlead_id') or '').strip() or None


def get_project_notification_recipients(project_row, exclude_ids=None):
    exclude = {str(value).strip() for value in (exclude_ids or []) if str(value).strip()}
    team_members = _parse_team_members(project_row)
    recipients = _normalize_list_strings([
        str(project_row.get('owner_id', '')).strip(),
        str(project_row.get('manager_id', '')).strip(),
        str(project_row.get('teamlead_id', '')).strip(),
        *team_members,
    ])
    return [user_id for user_id in recipients if user_id not in exclude]


def notify_employee_progress_update(task_row, actor_id, update_label, update_value):
    task_id = str(task_row.get('id', '')).strip()
    task_title = str(task_row.get('title') or task_id or 'Task').strip()
    actor = find_by_id(EMP_CSV, actor_id) or {}
    actor_name = str(actor.get('name') or session.get('full_name') or actor_id or 'Employee').strip()
    recipients = _normalize_list_strings([
        get_manager_for_employee(actor_id),
        get_teamlead_for_employee(actor_id),
        str((find_by_id(PROJECTS_CSV, task_row.get('project_id')) or {}).get('owner_id') or '').strip(),
    ])
    recipients = [user_id for user_id in recipients if user_id and user_id != str(actor_id).strip()]
    if not recipients:
        return
    notify_users(
        recipients,
        'Employee Progress Update',
        f'{actor_name} updated "{task_title}" {update_label} to {update_value}.',
        'task',
        email_subject='Employee Progress Update',
    )


def _resolve_current_employee_context():
    user_id = session.get('user_id')
    username = session.get('username')
    full_name = session.get('full_name')
    candidate_ids, employees = resolve_employee_candidate_ids(user_id, username, full_name)

    employee = next((e for e in employees if str(e.get('id', '')).strip() == str(user_id or '').strip()), None)
    if not employee and username:
        employee = next((e for e in employees if _normalize_text(e.get('email')) == _normalize_text(username)), None)
    if not employee and full_name:
        employee = next((e for e in employees if _normalize_text(e.get('name')) == _normalize_text(full_name)), None)

    employee_id = str((employee or {}).get('id') or '').strip()
    if not employee_id and candidate_ids:
        employee_id = next(iter(candidate_ids))
        employee = next((e for e in employees if str(e.get('id', '')).strip() == str(employee_id)), employee)

    return employee_id, (employee or {}), candidate_ids, employees


def _resolve_session_employee_task(task_id):
    employee_id, employee, candidate_ids, _employees = _resolve_current_employee_context()
    username = session.get('username')
    full_name = session.get('full_name')
    task = next((
        row for row in read_csv(TASKS_CSV)
        if str(row.get('id') or '').strip() == str(task_id or '').strip()
        and task_matches_employee(row, candidate_ids, username=username, full_name=full_name)
    ), None)
    return task, employee_id, employee, candidate_ids


def _allowed_task_submission(filename):
    extension = str(filename or '').strip().lower().rsplit('.', 1)
    if len(extension) != 2:
        return False
    return extension[-1] in {'zip', '7z', 'rar'}


def _submission_download_path(row):
    rel_path = str((row or {}).get('file_path') or '').strip().replace('\\', '/')
    if not rel_path:
        return ''
    return url_for('static', filename=rel_path)


def _serialize_task_submission(row):
    item = dict(row or {})
    item['download_url'] = _submission_download_path(item)
    item['file_size'] = _safe_int(item.get('file_size'), 0)
    item['created_at'] = str(item.get('created_at') or '')[:19]
    item['updated_at'] = str(item.get('updated_at') or '')[:19]
    return item


def _help_request_recipient_label(employee_id, employee_index=None, users=None):
    normalized_id = str(employee_id or '').strip()
    employee_lookup = employee_index or _build_employee_index()
    employee = employee_lookup.get(normalized_id, {})
    if employee.get('name'):
        return str(employee.get('name')).strip()

    user_rows = users if users is not None else read_csv(USERS_CSV)
    user = next((row for row in user_rows if str(row.get('id', '')).strip() == normalized_id), {})
    if user.get('full_name'):
        return str(user.get('full_name')).strip()
    if user.get('username'):
        return str(user.get('username')).strip()
    return normalized_id


def _resolve_help_request_recipients(requester_id, recipient_type='manager', explicit_recipient_id=None):
    requester = str(requester_id or '').strip()
    explicit = str(explicit_recipient_id or '').strip()
    employees = read_csv(EMP_CSV)
    users = read_csv(USERS_CSV)
    employee_index = _build_employee_index(employees)
    role_map = _build_role_map(users)
    requester_row = employee_index.get(requester, {})

    recipients = []
    if explicit and explicit != requester:
        recipients.append(explicit)
    elif recipient_type == 'teammate':
        manager_id = get_manager_for_employee(requester)
        if manager_id:
            recipients.extend([
                member_id for member_id in _normalize_list_strings(get_team_members(manager_id))
                if member_id != requester
            ])
        if not recipients:
            same_department = _normalize_text(requester_row.get('department'))
            same_company = _normalize_text(requester_row.get('company'))
            for employee in employees:
                employee_id = str(employee.get('id') or '').strip()
                if not employee_id or employee_id == requester:
                    continue
                role = role_map.get(employee_id, 'employee')
                if role in {'admin', 'manager', 'hr'}:
                    continue
                if same_department and _normalize_text(employee.get('department')) != same_department:
                    continue
                if same_company and _normalize_text(employee.get('company')) != same_company:
                    continue
                recipients.append(employee_id)
    else:
        manager_id = get_manager_for_employee(requester)
        if manager_id and manager_id != requester:
            recipients.append(manager_id)
        if not recipients:
            fallback_manager = next((
                user_id for user_id, role in role_map.items()
                if role == 'manager' and user_id != requester
            ), '')
            if fallback_manager:
                recipients.append(fallback_manager)
        if not recipients:
            fallback_admin = next((
                user_id for user_id, role in role_map.items()
                if role == 'admin' and user_id != requester
            ), '')
            if fallback_admin:
                recipients.append(fallback_admin)

    normalized = _normalize_list_strings(recipients)
    return [
        {
            'id': recipient_id,
            'name': _help_request_recipient_label(recipient_id, employee_index=employee_index, users=users),
        }
        for recipient_id in normalized
    ]


def _normalize_help_request_rows(rows):
    normalized = []
    for row in rows or []:
        item = {field: str(row.get(field, '') or '').strip() for field in HELP_REQUEST_FIELDNAMES}
        if item['status'] not in {'pending', 'cancelled', 'accepted', 'completed'}:
            item['status'] = 'pending'
        if item['urgency'] not in {'low', 'medium', 'high'}:
            item['urgency'] = 'medium'
        normalized.append(item)
    normalized.sort(key=lambda entry: entry.get('created_at', ''), reverse=True)
    return normalized


def calculate_project_progress(project_id):
    """Calculate project progress based on tasks"""
    tasks = read_csv(TASKS_CSV)
    project_tasks = [t for t in tasks if t.get('project_id') == project_id]
    if not project_tasks:
        return 0

    progress_sum = sum(int(t.get('progress', 0) or 0) for t in project_tasks)
    return int(progress_sum / len(project_tasks)) if project_tasks else 0


def calculate_employee_productivity(employee_id):
    """Calculate productivity percentage for an employee"""
    tasks = read_csv(TASKS_CSV)
    emp_tasks = [t for t in tasks if t.get('assignee_id') == employee_id]

    if not emp_tasks:
        return 0

    completed = len([t for t in emp_tasks if t.get('status') == 'completed'])
    productivity = (completed / len(emp_tasks)) * 100

    return int(productivity)


def update_project_progress(project_id):
    """Update project progress in database"""
    if not _use_database(PROJECTS_CSV) or DB_BACKEND != 'mongodb':
        return
    try:
        progress = calculate_project_progress(project_id)
        proj_coll = _mongo_collection('projects')
        proj_coll.update_one({'id': project_id}, {'$set': {'progress': str(progress)}})
    except:
        pass


def _role_redirect(role):
    role = normalize_role(role)
    if role == 'platform_admin':
        return redirect(f"{TASKVISE_ADMIN_URL}/dashboard")
    if role == 'admin':
        return redirect(url_for('admin_dashboard'))
    if role == 'manager':
        return redirect(url_for('manager_dashboard'))
    if role == 'hr':
        return redirect(url_for('hr_dashboard'))
    if role == 'teamlead':
        return redirect(url_for('teamlead_dashboard'))
    return redirect(url_for('employee_dashboard'))


def _start_user_session(user_row):
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    normalized_role = normalize_role(user_row.get('role', 'employee'))
    update_by_id(EMP_CSV, user_row['id'], {
        'last_login': now
    }, EMP_FIELDNAMES)
    employee_row = find_by_id(EMP_CSV, user_row['id']) or {}

    session['user_id'] = user_row['id']
    session['username'] = user_row['username']
    session['role'] = normalized_role
    session['full_name'] = user_row.get('full_name', '')
    session['email'] = user_row.get('username', employee_row.get('email', ''))
    session['last_login'] = now
    session['join_date'] = employee_row.get('join_date', '')
    return _role_redirect(normalized_role)


def _google_redirect_uri():
    configured = (GOOGLE_REDIRECT_URI or '').strip()
    if configured:
        return configured
    return url_for('google_callback', _external=True)


def authenticate_user_credentials(username, password, allowed_roles=None):
    ensure_demo_org_integrity()
    username_norm = str(username or '').strip().lower()
    password_norm = str(password or '').strip()
    allowed = {normalize_role(role) for role in (allowed_roles or []) if normalize_role(role)}
    users = read_csv(USERS_CSV)

    for user in users:
        identifier = str(user.get('username') or user.get('email') or '').strip().lower()
        role = normalize_role(user.get('role', 'employee'))
        is_active = _truthy(user.get('is_active', 'true'), default=True)
        if identifier != username_norm or not is_active:
            continue
        if allowed and role not in allowed:
            continue
        stored_hash = user.get('password_hash')
        stored_plain = user.get('password')
        if stored_hash and verify_password(stored_hash, password_norm):
            return user
        if stored_plain is not None and verify_password(stored_plain, password_norm):
            return user
    return None


def get_role_color(role):
    """Get CSS class for role badge colors"""
    role = normalize_role(role)
    role_colors = {
        'admin': 'badge-admin',
        'manager': 'badge-manager',
        'hr': 'badge-warning',
        'teamlead': 'badge-info',
        'employee': 'badge-employee'
    }
    return role_colors.get(role, 'badge-employee')


def generate_secure_password():
    import secrets
    import string

    password = ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(10 + secrets.randbelow(3)))
    for _ in range(1 + secrets.randbelow(2)):
        pos = secrets.randbelow(len(password) + 1)
        password = password[:pos] + secrets.choice('!@#$%^&*') + password[pos:]
    return password


def _session_user_payload():
    if 'user_id' not in session:
        return None
    return {
        'id': session.get('user_id'), 'name': session.get('full_name', ''), 'email': session.get('email', ''),
        'role': session.get('role', 'employee'),
    }


def _render_admin_dashboard():
    payload = get_admin_dashboard_payload()
    analytics = build_admin_analytics_payload(payload['employees'], payload['projects'], payload['tasks'])
    skill_gap = build_admin_skill_gap_payload(payload['employees'], payload['projects'], payload['tasks'])
    system_settings, _settings_rows = get_admin_system_settings_record()
    demo_credentials = build_demo_credentials_payload()
    employee_data = get_employee_dashboard_data(session.get('user_id'))
    return render_template('admin_dashboard.html',
                         username=session.get('username'),
                         role=session.get('role'),
                         stats=payload['stats'],
                         recent_activity=payload['recent_activity'],
                         employees=payload['employees'],
                         tasks=payload['tasks'],
                         projects=payload['projects'],
                         analytics=analytics,
                         department_stats=analytics.get('department_stats', []),
                         monthly_stats=analytics.get('monthly_stats', []),
                         top_performers=analytics.get('top_performers', []),
                         workload_insights=analytics.get('workload_insights', []),
                         role_distribution=analytics.get('role_distribution', []),
                         company_overview=analytics.get('company_overview', []),
                         skill_gap=skill_gap,
                         skill_gap_rows=skill_gap.get('rows', []),
                         departments=skill_gap.get('departments', []),
                         profile=employee_data['profile'],
                         system_settings=system_settings,
                         demo_credentials=demo_credentials)


__all__ = ['ADMIN_DATA_DIR', 'AVATAR_UPLOAD_DIR', 'BASE_DIR', 'CREDENTIALS_EXPORT_TXT', 'CSV_SHADOW_SYNC', 'Counter', 'DATA_DIR', 'DB_BACKEND', 'DEFAULT_COMPANY_NAME', 'DEPARTMENT_SKILL_BASELINES', 'EMAIL_NOTIFICATIONS_ENABLED', 'EMP_CSV', 'EMP_FIELDNAMES', 'EmailMessage', 'Flask', 'GOOGLE_CLIENT_ID', 'GOOGLE_CLIENT_SECRET', 'GOOGLE_REDIRECT_URI', 'HELP_REQUESTS_CSV', 'HELP_REQUEST_FIELDNAMES', 'IS_VERCEL', 'LEAVE_CSV', 'LEAVE_FIELDNAMES', 'MIRROR_MONGODB', 'MIRROR_MYSQL', 'MONGO_DATABASE', 'MONGO_REQUIRED', 'MONGO_URI', 'MYSQL_DATABASE', 'MYSQL_DEFAULT_COLUMNS', 'MYSQL_HOST', 'MYSQL_PASSWORD', 'MYSQL_PORT', 'MYSQL_USER', 'MongoClient', 'NOTES_CSV', 'NOTIFICATION_FIELDNAMES', 'NOTIF_CSV', 'PAYMENTS_CSV', 'PAYMENT_FIELDNAMES', 'PLATFORM_FOUNDER_EMAIL', 'PLATFORM_FOUNDER_PASSWORD', 'PROJECTS_CSV', 'PROJECT_FIELDNAMES', 'PROJECT_ID_PREFIX', 'PROJECT_ID_WIDTH', 'PROJECT_MEMBERS_CSV', 'PROJECT_MEMBER_FIELDNAMES', 'PROJECT_MEMBER_ID_PREFIX', 'PROJECT_MEMBER_ID_WIDTH', 'PROJECT_SKILL_HINTS', 'ROLE_DEFAULT_PASSWORDS', 'ROLE_PAY_BANDS', 'SEED_DEMO', 'SETTINGS_CSV', 'SETTINGS_FIELDNAMES', 'SMTP_FROM', 'SMTP_HOST', 'SMTP_PASSWORD', 'SMTP_PORT', 'SMTP_USER', 'SMTP_USE_TLS', 'SOURCE_DATA_DIR', 'SOURCE_STATIC_DIR', 'STORAGE_ROOT', 'STORAGE_TABLE_MAP', 'SYSTEM_SETTINGS_USER_ID', 'TASKS_CSV', 'TASKVISE_ADMIN_URL', 'TASK_FIELDNAMES', 'TASK_ID_PREFIX', 'TASK_ID_WIDTH', 'TASK_SUBMISSIONS_CSV', 'TASK_SUBMISSION_FIELDNAMES', 'TASK_SUBMISSION_UPLOAD_DIR', 'TEAMS_CSV', 'TEAM_BLUEPRINTS', 'TEAM_FIELDNAMES', 'USERS_CSV', 'USER_FIELDNAMES', 'VALID_LEAVE_STATUSES', 'WORKFORCE_ID_PREFIX', 'WORKFORCE_ID_WIDTH', 'WORK_CSV', '_DEMO_PASSWORD', '_MONGO_ENABLED', '_MYSQL_BOOTSTRAPPED', '_MYSQL_ENABLED', '_ORG_STRUCTURE_BOOTSTRAPPED', '_PooledConnection', '_allowed_task_submission', '_build_employee_index', '_build_month_window', '_build_role_map', '_build_skill_vocabulary', '_build_team_indexes', '_clean_skill_label', '_collect_fieldnames', '_collect_id_rows', '_eligible_project_assignees', '_ensure_runtime_storage', '_escape_identifier', '_extract_datetime_text', '_extract_skills_from_text', '_get_user_notification_email', '_google_redirect_uri', '_help_request_recipient_label', '_looks_like_werkzeug_hash', '_mongo_append_row', '_mongo_bootstrap', '_mongo_client', '_mongo_collection', '_mongo_delete_by_id', '_mongo_read_rows', '_mongo_update_by_id', '_mongo_write_rows', '_month_label', '_mysql_append_row', '_mysql_bootstrap', '_mysql_column_type', '_mysql_connect', '_mysql_ensure_columns', '_mysql_ensure_database', '_mysql_ensure_table', '_mysql_existing_columns', '_mysql_local', '_mysql_read_rows', '_mysql_schema_complete', '_mysql_value', '_mysql_write_rows', '_next_prefixed_id', '_normalize_help_request_rows', '_normalize_list_strings', '_normalize_text', '_parse_date_any', '_parse_skills', '_parse_team_members', '_prefixed_id_sort_key', '_prepare_dashboard_profile', '_project_member_selection', '_project_team_assignment', '_read_csv_file', '_render_admin_dashboard', '_resolve_current_employee_context', '_resolve_help_request_recipients', '_resolve_session_employee_task', '_role_redirect', '_safe_int', '_salary_for_role', '_serialize_admin_employee', '_serialize_admin_project', '_serialize_admin_task', '_serialize_task_submission', '_session_user_payload', '_sort_rows_by_id', '_start_user_session', '_submission_download_path', '_sync_project_members', '_sync_secondary_stores', '_task_hour_value', '_team_blueprint_rows', '_team_rotation_members', '_truthy', '_use_database', '_use_mongo', '_write_csv_file', 'admin_required', 'app', 'append_csv', 'authenticate_user_credentials', 'build_admin_analytics_payload', 'build_admin_skill_gap_payload', 'build_demo_credentials_payload', 'build_manager_analytics_payload', 'build_recent_activity', 'calculate_completion_rate', 'calculate_employee_productivity', 'calculate_overdue_tasks', 'calculate_project_progress', 'calculate_team_productivity', 'calculate_total_hours', 'check_password_hash', 'classify_employee_badge', 'create_notification', 'create_sample_users', 'csv', 'datetime', 'delete_by_id', 'ensure_csv', 'ensure_demo_org_integrity', 'ensure_leave_data_integrity', 'ensure_leave_type_column', 'ensure_notes_csv', 'ensure_platform_admin_account', 'ensure_projects_team_members', 'export_demo_credentials_file', 'find_by_id', 'generate_password_hash', 'generate_secure_password', 'get_admin_dashboard_payload', 'get_admin_data', 'get_admin_system_settings_record', 'get_default_company_name', 'get_employee_dashboard_data', 'get_employee_data', 'get_employee_initials', 'get_manager_data', 'get_manager_for_employee', 'get_next_project_id', 'get_next_project_member_id', 'get_next_task_id', 'get_next_workforce_id', 'get_project_notification_recipients', 'get_role_access_description', 'get_role_color', 'get_role_default_password', 'get_role_description', 'get_role_title', 'get_storage_targets_status', 'get_team_member_ids', 'get_team_members', 'get_team_record_for_user', 'get_teamlead_for_employee', 'get_user_settings_record', 'infer_primary_company_name', 'is_task_overdue', 'json', 'jsonify', 'load_dotenv', 'load_employees', 'load_projects', 'load_tasks', 'login_required', 'merge_fieldnames', 'mysql', 'normalize_leave_row', 'normalize_leave_status', 'normalize_project_status', 'normalize_role', 'normalize_task_status', 'notify_employee_progress_update', 'notify_project_assignment', 'notify_task_assignment', 'notify_user', 'notify_users', 'os', 'parse', 'persist_workforce_profile', 'platform_admin_required', 're', 'read_csv', 'redirect', 'render_template', 'request', 'resolve_employee_candidate_ids', 'save_admin_system_settings_record', 'save_user_settings_record', 'secure_filename', 'send_email_notification', 'send_from_directory', 'session', 'shutil', 'smtplib', 'split_skills', 'ssl', 'sync_demo_role_passwords', 'sync_registered_storage_tables', 'task_matches_employee', 'taskvise_admin_manager', 'tempfile', 'threading', 'time', 'timedelta', 'update_by_id', 'update_project_progress', 'url_for', 'urllib_error', 'urllib_request', 'uuid', 'verify_password', 'wraps', 'write_csv']
