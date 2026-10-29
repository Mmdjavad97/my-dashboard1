"""Run on the Windows server. Copies owner data; never writes to Supabase."""
from pathlib import Path
from datetime import datetime, timezone
import argparse
import getpass
import json
import os
import sys
import tomllib

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from local_backend import initialize, LocalClient, backup_database


def write_config(folder, database, owner_uid):
    config = folder / 'secrets.toml'
    if config.exists():
        raise FileExistsError('Local configuration already exists. No configuration was replaced.')
    text = '[storage]\nbackend = "sqlite"\npath = ' + json.dumps(str(database), ensure_ascii=False) + '\nowner_uid = ' + json.dumps(owner_uid) + '\n'
    with config.open('x', encoding='utf-8') as file:
        file.write(text)
    os.chmod(config, 0o600)


def run(folder, source_secrets=None):
    from supabase import create_client
    folder = Path(folder).resolve()
    folder.mkdir(parents=True, exist_ok=True)
    database = folder / 'dashboard.sqlite3'
    if database.exists() or (folder / 'secrets.toml').exists():
        raise FileExistsError('This folder already has local data or configuration. Migration stopped without replacing it.')
    source = {}
    if source_secrets:
        source = tomllib.loads(Path(source_secrets).read_text(encoding='utf-8'))['supabase']
    url = str(source.get('url') or input('Supabase project URL: ')).strip()
    key = str(source.get('key') or getpass.getpass('Supabase publishable/anon key (hidden): ')).strip()
    owner_uid = str(source.get('owner_uid') or input('Owner user UID from your existing Streamlit Secrets: ')).strip().lower()
    email = input('Your existing dashboard login email: ').strip()
    password = getpass.getpass('Your existing dashboard password (hidden): ')
    client = create_client(url, key)
    try:
        signed = client.auth.sign_in_with_password({'email': email, 'password': password})
        if not signed.user or str(signed.user.id).lower() != owner_uid:
            raise PermissionError('The signed-in account does not match the dashboard owner.')
        rows = client.table('dashboard_data').select('section,data').execute().data
        if not rows:
            raise ValueError('No source sections were returned; migration stopped before creating a database.')
        # Validate all data before creating the destination database.
        json.dumps(rows, ensure_ascii=False, allow_nan=False)
        print(f'Read {len(rows)} sections. Existing records and uploaded file bytes will be preserved.')
        local_password = getpass.getpass('Local login password (Enter to keep your existing password): ')
        if local_password:
            if len(local_password) < 8:
                raise ValueError('Choose a local password of at least 8 characters.')
            if getpass.getpass('Confirm local password: ') != local_password:
                raise ValueError('The passwords did not match.')
        else:
            local_password = password
        timestamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
        backup = folder / ('supabase-export-' + timestamp + '.json')
        with backup.open('x', encoding='utf-8') as file:
            json.dump({'exported_at': timestamp, 'sections': rows}, file, ensure_ascii=False, allow_nan=False)
        os.chmod(backup, 0o600)
        initialize(database, email, local_password, owner_uid, rows)
        local = LocalClient(database, owner_uid)
        local.auth.sign_in_with_password({'email': email, 'password': local_password})
        copied = local.table('dashboard_data').select('section,data').execute().data
        if {row['section']: row['data'] for row in copied} != {row['section']: row['data'] for row in rows}:
            raise ValueError('Verification failed. The exported JSON is intact; no cloud data was changed.')
        backup_database(database, folder / 'backups' / ('dashboard-initial-' + timestamp + '.sqlite3'))
        write_config(folder, database, owner_uid)
        print('Migration verified. The local login and all sections are ready.')
        print('Your original Supabase data was not changed. Use only the new installation after testing it.')
    finally:
        try:
            client.auth.sign_out({'scope': 'local'})
        except Exception:
            pass


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--data-dir', required=True)
    parser.add_argument('--cloud-secrets', help='Optional local TOML file containing your existing [supabase] settings.')
    args = parser.parse_args()
    try:
        run(args.data_dir, args.cloud_secrets)
    except Exception as exc:
        # Do not print SDK/network exception strings that might contain credentials.
        print(f'Migration stopped ({type(exc).__name__}). No cloud data was modified. Check your credentials and local folder, then retry.', file=sys.stderr)
        sys.exit(1)
