from pathlib import Path
from datetime import datetime, timezone
import argparse
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from local_backend import backup_database

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--data-dir', required=True)
    parser.add_argument('--output', help='Optional backup directory on another drive.')
    args = parser.parse_args()
    folder = Path(args.data_dir)
    target = Path(args.output) if args.output else folder / 'backups'
    destination = target / ('dashboard-' + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ') + '.sqlite3')
    backup_database(folder / 'dashboard.sqlite3', destination)
    print('Verified backup created:', destination)
