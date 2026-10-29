from pathlib import Path
import argparse
import sys
import tomllib
from zoneinfo import ZoneInfo
from contextlib import closing

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from local_backend import LocalClient, connect

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--data-dir', required=True)
    args = parser.parse_args()
    required = ['app.py', 'local_backend.py', 'project_financial.py', 'project_files.py',
                'mobile.css', 'mobile_viewport.html', 'task_navigation.html', 'mobile_history/index.html',
                'B-NAZANIN.TTF', 'BOM Raw.xlsx', 'My Pic.png', 'dashboard_background.png',
                'assets/RNG Logo.png', 'assets/Mission signature.png',
                'فرم گزارش ماموریت.xlsx', 'فرم درخواست کالا.xlsx']
    missing = [name for name in required if not (ROOT / name).is_file()]
    if missing:
        raise SystemExit('Installation is incomplete. Extract the full ZIP again. Missing: ' + ', '.join(missing))
    settings = tomllib.loads((Path(args.data_dir) / 'secrets.toml').read_text(encoding='utf-8'))['storage']
    if settings['backend'] != 'sqlite':
        raise SystemExit('The Windows installation must select the sqlite backend.')
    LocalClient(settings['path'], settings['owner_uid'])
    with closing(connect(settings['path'])) as db:
        if db.execute('PRAGMA quick_check').fetchone()[0] != 'ok':
            raise SystemExit('Database verification failed. Preserve the database and restore a verified backup.')
    ZoneInfo('Asia/Tehran')
    print('Runtime assets, Tehran time zone and local database verified.')
