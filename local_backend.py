"""Single-owner SQLite backend. Cloud mode remains the application's default."""
from contextlib import closing
from pathlib import Path
from types import SimpleNamespace
import hashlib
import hmac
import json
import os
import secrets
import sqlite3
import time


def connect(path):
    path = Path(path).resolve()
    # Never silently start an empty dashboard when the configured database is missing.
    connection = sqlite3.connect(path.as_uri() + '?mode=rw', uri=True, timeout=20)
    connection.row_factory = sqlite3.Row
    return connection


def password_hash(password, salt):
    return hashlib.scrypt(password.encode('utf-8'), salt=salt, n=16384, r=8, p=1, dklen=32)


def initialize(path, email, password, owner_uid, rows):
    """Create a new database atomically; refuse to replace existing data."""
    path = Path(path).resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        raise FileExistsError('The database already exists. No data was replaced.')
    temp = path.with_name(path.name + '.' + secrets.token_hex(8) + '.tmp')
    salt = secrets.token_bytes(16)
    try:
        with closing(sqlite3.connect(temp)) as db, db:
            db.execute('CREATE TABLE owner (uid TEXT PRIMARY KEY, email TEXT NOT NULL, salt BLOB NOT NULL, password_hash BLOB NOT NULL, revision TEXT NOT NULL, failures INTEGER NOT NULL DEFAULT 0, locked_until REAL NOT NULL DEFAULT 0)')
            db.execute('CREATE TABLE dashboard_data (section TEXT PRIMARY KEY, data TEXT NOT NULL)')
            db.execute('INSERT INTO owner(uid,email,salt,password_hash,revision) VALUES(?,?,?,?,?)',
                       (owner_uid, email.strip().casefold(), salt, password_hash(password, salt), secrets.token_hex(24)))
            seen = set()
            for row in rows:
                section = row['section']
                if not isinstance(section, str) or not section or section in seen:
                    raise ValueError('Invalid or duplicate section in migration data.')
                seen.add(section)
                db.execute('INSERT INTO dashboard_data VALUES(?,?)', (section, json.dumps(row['data'], ensure_ascii=False, allow_nan=False)))
            db.execute('PRAGMA user_version=1')
        # Exclusive destination creation also protects against simultaneous installers.
        descriptor = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        os.close(descriptor)
        try:
            os.replace(temp, path)
        except Exception:
            path.unlink(missing_ok=True)
            raise
    finally:
        temp.unlink(missing_ok=True)


def backup_database(source, destination):
    destination = Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(destination, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    os.close(descriptor)
    try:
        with closing(connect(source)) as src, closing(sqlite3.connect(destination)) as dst:
            src.backup(dst)
            if dst.execute('PRAGMA integrity_check').fetchone()[0] != 'ok':
                raise ValueError('Backup integrity check failed.')
        return destination
    except Exception:
        destination.unlink(missing_ok=True)
        raise


class LocalAuth:
    def __init__(self, client):
        self.client = client
        self.revision = None

    def get_user(self):
        with closing(connect(self.client.path)) as db:
            owner = db.execute('SELECT uid,revision FROM owner').fetchone()
        valid = owner is not None and owner['uid'] == self.client.owner_uid and self.revision == owner['revision']
        return SimpleNamespace(user=SimpleNamespace(id=owner['uid']) if valid else None)

    def sign_in_with_password(self, credentials):
        with closing(connect(self.client.path)) as db, db:
            db.execute('BEGIN IMMEDIATE')
            owner = db.execute('SELECT * FROM owner').fetchone()
            if owner['locked_until'] > time.time():
                raise ValueError('Please wait a minute before trying again.')
            candidate = password_hash(str(credentials['password']), owner['salt'])
            valid = hmac.compare_digest(candidate, owner['password_hash']) and hmac.compare_digest(
                str(credentials['email']).strip().casefold().encode(), owner['email'].encode())
            if valid:
                db.execute('UPDATE owner SET failures=0,locked_until=0')
                self.revision = owner['revision']
            else:
                failures = owner['failures'] + 1
                db.execute('UPDATE owner SET failures=?,locked_until=?', (0 if failures >= 5 else failures, time.time() + 60 if failures >= 5 else 0))
        if not valid:
            raise ValueError('Invalid credentials.')
        return self.get_user()

    def sign_out(self):
        self.revision = None


class LocalTable:
    def __init__(self, client):
        self.client = client
        self.value = None

    def select(self, columns):
        if columns != 'section,data':
            raise ValueError('Unsupported local query.')
        return self

    def upsert(self, value, on_conflict='section'):
        if on_conflict != 'section':
            raise ValueError('Unsupported conflict key.')
        self.value = value
        return self

    def execute(self):
        if self.client.auth.get_user().user is None:
            raise PermissionError('Sign in before accessing your records.')
        with closing(connect(self.client.path)) as db, db:
            if self.value is None:
                rows = [{'section': row['section'], 'data': json.loads(row['data'])}
                        for row in db.execute('SELECT section,data FROM dashboard_data ORDER BY section')]
                return SimpleNamespace(data=rows)
            value = self.value
            db.execute('INSERT INTO dashboard_data(section,data) VALUES(?,?) ON CONFLICT(section) DO UPDATE SET data=excluded.data',
                       (value['section'], json.dumps(value['data'], ensure_ascii=False, allow_nan=False)))
            return SimpleNamespace(data=[value])


class LocalClient:
    def __init__(self, path, owner_uid):
        self.path, self.owner_uid = str(Path(path).resolve()), owner_uid
        with closing(connect(self.path)) as db:
            if db.execute('PRAGMA user_version').fetchone()[0] != 1:
                raise ValueError('Unsupported database version.')
            owners = db.execute('SELECT uid FROM owner').fetchall()
            if len(owners) != 1 or owners[0]['uid'] != owner_uid:
                raise ValueError('The database owner does not match the configuration.')
        self.auth = LocalAuth(self)

    def table(self, name):
        if name != 'dashboard_data':
            raise ValueError('Unsupported local table.')
        return LocalTable(self)
