"""Interactive migration. Never overwrite existing records or store cloud credentials."""
from contextlib import closing
from datetime import datetime, timezone
from getpass import getpass
from pathlib import Path
import argparse
import csv
import json
import os
import sys
import urllib.error
import urllib.request
import urllib.parse

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from local_backend import initialize, LocalClient, connect, backup_database


class MigrationRequestError(Exception):
    """Only fixed diagnostic text; never expose response bodies or credentials."""
    pass


def request_json(base, path, key, token=None, payload=None):
    headers = {'apikey': key, 'Content-Type': 'application/json'}
    if token:
        headers['Authorization'] = 'Bearer ' + token
    request = urllib.request.Request(base + path, headers=headers,
        data=json.dumps(payload).encode() if payload is not None else None)
    try:
        with urllib.request.urlopen(request, timeout=180) as response:
            body = response.read()
            return json.loads(body) if body else None
    except urllib.error.HTTPError as error:
        stage = 'sign-in' if path.startswith('/auth/v1/token') else 'record download' if path.startswith('/rest/') else 'session cleanup'
        hints = {
            'email_provider_disabled': 'Supabase reports that email/password login is disabled for this project.',
            'captcha_failed': 'Supabase requires a CAPTCHA that this migration login cannot complete.',
            'validation_failed': 'Supabase rejected the login request format.',
            'bad_json': 'Supabase could not parse the login request.',
            'invalid_credentials': 'Use the email and password for the existing DASHBOARD login, not your Supabase website account.',
            'email_not_confirmed': 'The dashboard login email has not been confirmed.',
            'invalid_api_key': 'Copy the publishable or anon PUBLIC key from this same Supabase project.',
            'over_request_rate_limit': 'Wait a few minutes before trying again.',
            'user_banned': 'This dashboard login account is disabled.',
            'PGRST205': 'The dashboard_data table was not found in the selected project.',
            '42501': 'The signed-in account cannot read dashboard_data. Check its existing database permissions; do not disable row-level security.',
        }
        hint = ''
        try:
            details = json.loads(error.read(16384))
            if isinstance(details, dict):
                code = details.get('error_code') or details.get('code') or details.get('error')
                hint = hints.get(code, '') if isinstance(code, str) else ''
                # Older GoTrue versions use error/error_description instead of code.
                fixed_messages = {
                    'Invalid API key': hints['invalid_api_key'],
                    'Invalid login credentials': 'Supabase explicitly returned: Invalid login credentials. This is its authentication response, not a Streamlit loading failure.',
                    'Email not confirmed': hints['email_not_confirmed'],
                    'Email logins are disabled': hints['email_provider_disabled'],
                }
                for field in ('message', 'msg', 'error_description'):
                    value = details.get(field)
                    if isinstance(value, str) and value in fixed_messages:
                        hint = fixed_messages[value]
                        break
                if not hint:
                    hint = 'The server returned a JSON error this installer does not recognize. This does not establish that your credentials are wrong.'
        except (ValueError, TypeError, OSError):
            hint = 'The response was not a readable Supabase JSON error. A network gateway or proxy may be involved; this does not establish that your credentials are wrong.'
        finally:
            error.close()
        if not hint:
            hint = {400: 'Check the project key and dashboard login details.',
                    401: 'The project key or login authorization was rejected.',
                    403: 'Access was refused. Check project permissions and whether your network or VPN blocks the request.',
                    404: 'Check the project URL and that the dashboard_data table exists.',
                    429: 'Wait a few minutes before trying again.'}.get(error.code, 'The service or network returned an error. Retry when connectivity is stable.')
        raise MigrationRequestError(f'Supabase {stage} failed (HTTP {error.code}). {hint}') from None


def cloud_rows(base, key, email, password, owner_uid):
    parsed = urllib.parse.urlsplit(base)
    if parsed.scheme != 'https' or not parsed.netloc or parsed.path not in ('', '/') or parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise ValueError('Use the HTTPS Supabase project URL, without a path.')
    base = base.rstrip('/')
    auth = request_json(base, '/auth/v1/token?grant_type=password', key, payload={'email': email, 'password': password})
    token = auth['access_token']
    try:
        if auth['user']['id'] != owner_uid:
            raise ValueError('The signed-in account is not the configured owner.')
        rows, offset = [], 0
        while True:
            batch = request_json(base, f'/rest/v1/dashboard_data?select=section,data&order=section.asc&limit=1000&offset={offset}', key, token)
            if not isinstance(batch, list):
                raise ValueError('Unexpected migration data.')
            rows.extend(batch)
            if len(batch) < 1000:
                break
            offset += len(batch)
        if not rows:
            raise ValueError('No records were returned. Migration stopped to prevent an empty dashboard.')
        return rows
    finally:
        try:
            request_json(base, '/auth/v1/logout?scope=local', key, token, {})
        except Exception:
            pass


def verify_copy(path, rows):
    with closing(connect(path)) as db:
        if db.execute('PRAGMA integrity_check').fetchone()[0] != 'ok':
            raise ValueError('Database verification failed.')
        copied = {r['section']: json.loads(r['data']) for r in db.execute('SELECT section,data FROM dashboard_data')}
    if copied != {r['section']: r['data'] for r in rows}:
        raise ValueError('The copied records differ from the source.')


def import_rows(folder, rows, email, password, owner):
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / 'dashboard.sqlite3'
    if path.exists():
        raise FileExistsError('A database already exists. Nothing was replaced.')
    timestamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    export = folder / ('supabase-export-' + timestamp + '.json')
    descriptor = os.open(export, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    with os.fdopen(descriptor, 'w', encoding='utf-8') as file:
        json.dump(rows, file, ensure_ascii=False, allow_nan=False)
    initialize(path, email, password, owner, rows)
    verify_copy(path, rows)
    backup_database(path, folder / 'backups' / ('initial-' + timestamp + '.sqlite3'))
    return path


def read_csv_export(path):
    """Read a Supabase dashboard CSV without contacting any cloud service."""
    csv.field_size_limit(1024 * 1024 * 1024)
    with Path(path).open('r', encoding='utf-8-sig', newline='') as file:
        reader = csv.DictReader(file)
        if not {'section', 'data'}.issubset(reader.fieldnames or []):
            raise ValueError('Export the dashboard_data table with its section and data columns.')
        rows, seen = [], set()
        for row in reader:
            section = row['section']
            if not section or section in seen:
                raise ValueError('The export has empty or duplicate section names. Do not combine different users or tables.')
            seen.add(section)
            rows.append({'section': section, 'data': json.loads(row['data'])})
        if not rows:
            raise ValueError('The export is empty. No database was created.')
        return rows


def choose_export_file():
    try:
        import tkinter as tk
        from tkinter import filedialog
        root = tk.Tk()
        root.withdraw()
        try:
            return filedialog.askopenfilename(title='Choose the dashboard_data CSV export', filetypes=[('Supabase CSV export', '*.csv')])
        finally:
            root.destroy()
    except Exception:
        return input('CSV export file path: ').strip().strip('"')


def run(folder):
    folder = Path(folder).resolve()
    folder.mkdir(parents=True, exist_ok=True)
    destination = folder / 'dashboard.sqlite3'
    if destination.exists():
        with closing(connect(destination)) as db:
            owner = db.execute('SELECT uid FROM owner').fetchone()['uid']
        LocalClient(destination, owner)
        print('Existing installation detected; it was not replaced.')
        return
    print('RNG Dashboard - configure the NEW app. Your old cloud app is unchanged.')
    print('1. Copy an existing local dashboard database (if the earlier migration finished).')
    print('2. Copy your records directly from Supabase (usual choice).')
    print('3. Import a dashboard_data CSV exported from Supabase Dashboard (no cloud login needed).')
    choice = input('Choose 1, 2 or 3: ').strip()
    if choice == '1':
        default = Path(os.environ.get('LOCALAPPDATA', str(Path.home()))) / 'RNGDashboard' / 'dashboard.sqlite3'
        source = Path(input(f'Existing database path [{default}]: ').strip().strip('"') or default).resolve()
        with closing(connect(source)) as db:
            owner = db.execute('SELECT uid FROM owner').fetchone()['uid']
            rows = [{'section': r['section'], 'data': json.loads(r['data'])} for r in db.execute('SELECT section,data FROM dashboard_data')]
        LocalClient(source, owner)
        backup_database(source, destination)
        verify_copy(destination, rows)
        backup_database(destination, folder / 'backups' / ('initial-' + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ') + '.sqlite3'))
        print('Copied and verified. Use your existing LOCAL login password.')
    elif choice == '2':
        print('Pause editing in the old app until this copy finishes. Enter credentials only here.')
        base = input('Supabase project URL [https://kbpfderanmjenrjieftw.supabase.co]: ').strip() or 'https://kbpfderanmjenrjieftw.supabase.co'
        owner = input('Owner UID [b240b34d-828b-47c7-8a13-6c9f3d8c1d94]: ').strip() or 'b240b34d-828b-47c7-8a13-6c9f3d8c1d94'
        key = getpass('Supabase publishable/anon key (hidden): ').strip()
        email = input('Existing dashboard login email: ').strip()
        password = getpass('Existing dashboard password (hidden): ')
        rows = cloud_rows(base, key, email, password, owner)
        local_password = getpass('New local password, or Enter to keep the existing password: ') or password
        if local_password != password:
            if len(local_password) < 8 or local_password != getpass('Confirm new password: '):
                raise ValueError('Passwords must match and have at least eight characters.')
        import_rows(folder, rows, email, local_password, owner)
        print('All records copied and verified. Your local login is ready.')
    elif choice == '3':
        source = choose_export_file()
        if not source:
            raise ValueError('File selection cancelled. Nothing was imported.')
        rows = read_csv_export(source)
        print(f'Export read: {len(rows)} record groups. Create your LOCAL login next.')
        email = input('Choose an email for your local dashboard login: ').strip()
        if not email or '@' not in email:
            raise ValueError('Enter an email for the local login.')
        password = getpass('Choose a local password (at least 8 characters, hidden): ')
        if len(password) < 8 or password != getpass('Confirm local password (hidden): '):
            raise ValueError('Passwords must match and have at least eight characters.')
        import_rows(folder, rows, email, password, 'b240b34d-828b-47c7-8a13-6c9f3d8c1d94')
        print('All exported records copied and verified. Your local login is ready.')
    else:
        raise ValueError('Choose 1, 2 or 3. Nothing was imported.')
    print('Check every section and file before switching. Cloud and local versions do NOT synchronize.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--data-dir', required=True)
    args = parser.parse_args()
    try:
        run(args.data_dir)
    except MigrationRequestError as error:
        print(str(error), file=sys.stderr)
        print('No cloud records were changed. Keep any existing local database or export.', file=sys.stderr)
        sys.exit(1)
    except Exception as error:
        print(f'Configuration stopped ({type(error).__name__}). No cloud records were changed. Keep any export/database created; do not delete it to retry.', file=sys.stderr)
        sys.exit(1)
