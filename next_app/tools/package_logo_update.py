"""Build the small Windows logo updater against the pre-icon app version."""
from pathlib import Path
import hashlib
import json
import subprocess
import zipfile
ROOT = Path(__file__).resolve().parents[2]
BASE = 'a97d8d8e39f23aa50f6a9a185a8d9578d6d101f8'
paths = ['assets/RNG-App-Icon.png', 'next_app/tools/build_icons.py', 'next_app/backend/main.py',
         'next_app/frontend/index.html', 'next_app/frontend/dist/index.html',
         'next_app/frontend/public/icon.svg', 'next_app/frontend/dist/icon.svg', 'next_app/windows/Setup.ps1']
for folder in ('public', 'dist'):
    paths += [p.relative_to(ROOT).as_posix() for p in sorted((ROOT / 'next_app/frontend' / folder / 'app-icons').glob('*'))]
files = []
for path in paths:
    old = subprocess.run(['git','show',BASE + ':' + path], cwd=ROOT, capture_output=True)
    files.append({'path':path, 'sha256':hashlib.sha256((ROOT/path).read_bytes()).hexdigest(),
                  'previous':hashlib.sha256(old.stdout).hexdigest() if old.returncode == 0 else None})
readme = '''RNG Logo update - run on your SERVER PC only.

1. Extract this entire ZIP.
2. Double-click Apply-Logo-Update.cmd.
3. In the folder picker, choose your EXISTING installed dashboard folder:
   the folder containing next_app (not this update folder).
4. Wait for the dashboard to reopen.

No Setup rerun, CSV import, credentials or database changes are needed.
The updater checks program versions, saves copies of old program files, and
restarts only the dashboard process from the selected installation.

On your phone and other PC: close the app and refresh its existing Tailscale
HTTPS address. If the installed icon stays old, remove only the app shortcut
and install the same address again through Chrome/Edge. Your records remain
on the server. Do not delete the server installation or AppData folder.

If a taskbar icon stays old on Windows, unpin and pin the refreshed app again.
A standalone Windows ICO is included as RNG.ico for optional shortcut settings.

If the updater reports a version mismatch, nothing is replaced. Keep the
installation and share the error text. If the app does not reopen after an
update error, use your existing desktop shortcut. Native Windows execution
requires verification on your server; API/assets and archive integrity have
been tested separately.
'''
archive = ROOT / 'downloads/RNG-Logo-Update.zip'
with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as z:
    prefix = 'RNG-Logo-Update/'
    for name in ('Apply-Logo-Update.ps1','Apply-Logo-Update.cmd'):
        z.write(ROOT/'next_app/windows'/name,prefix+name)
    z.writestr(prefix+'logo-update.json',json.dumps({'version':'rng-logo-20261031','files':files},indent=2))
    z.writestr(prefix+'README.txt',readme.replace('\n','\r\n'))
    z.write(ROOT/'next_app/frontend/dist/app-icons/rng.ico',prefix+'RNG.ico')
    for path in paths: z.write(ROOT/path,prefix+'payload/'+path)
with zipfile.ZipFile(archive) as z:
    assert z.testzip() is None
    assert not any(n.endswith(('.sqlite3','secrets.toml')) for n in z.namelist())
print(archive.name,archive.stat().st_size,'bytes; checksums and baseline versions included')
