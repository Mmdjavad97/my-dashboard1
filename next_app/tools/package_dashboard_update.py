"""Package the compact desktop dashboard and shared midnight background."""
from pathlib import Path
import hashlib
import json
import subprocess
import zipfile
ROOT=Path(__file__).resolve().parents[2]
SUPPORTED=['517d5b28f12635eedd8df716d7c1a94373f7e612','2e1c2d01231465ef9e313444f559732fffde583d']
paths=['next_app/frontend/src/main.jsx','next_app/frontend/src/style.css','next_app/frontend/dist/index.html']
paths += [p.relative_to(ROOT).as_posix() for p in sorted((ROOT/'next_app/frontend/dist/assets').glob('*'))]
files=[]
for path in paths:
    versions=[]
    for ref in SUPPORTED:
        old=subprocess.run(['git','show',ref+':'+path],cwd=ROOT,capture_output=True)
        if old.returncode==0:versions.append(hashlib.sha256(old.stdout).hexdigest())
    files.append({'path':path,'sha256':hashlib.sha256((ROOT/path).read_bytes()).hexdigest(),
                  'previous':versions[0] if versions else None,'previous_versions':versions})
readme='''RNG Dashboard Update - run on your SERVER PC.

1. Extract this entire ZIP.
2. Double-click Apply-Dashboard-Update.cmd.
3. Select the EXISTING dashboard program folder containing next_app.
4. When the server reopens, refresh/reopen the app on your PC and phone.

PC home fits standard desktop/laptop windows, with a 3-by-3 navigation grid
including Log out. Longer note lists scroll inside their panel rather than
making the entire dashboard scroll. All notes remain available.
The upper branding bar is removed. PC pages have Log out beside their
navigation tabs; phones have Log out at the end of the bottom navigation.
Swipe that bar horizontally to reach it. All pages have a dark navy backdrop
with subtle grid/line texture and light cards for readable forms and tables.

This update replaces frontend program files only. It does not read or change
your database, uploads, login password, report files, icons or Tailscale settings.
No Setup, CSV import, credentials, dependencies or icon reinstall is needed.
The previous navy-logo or phone layout update must already be installed.
Program version checks run before changes; old program files are backed up.
If the server does not reopen after an error, use its existing desktop shortcut.

Browser checks cover PC/phone layout, navigation, logout and long note lists.
Native Windows updater execution still needs verification on your server.
'''
archive=ROOT/'downloads/RNG-Dashboard-Update.zip'
with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as z:
    prefix='RNG-Dashboard-Update/'
    for name in ('Apply-Dashboard-Update.ps1','Apply-Dashboard-Update.cmd'):
        z.write(ROOT/'next_app/windows'/name,prefix+name)
    z.writestr(prefix+'dashboard-update.json',json.dumps({'version':'midnight-dashboard-20261101','files':files},indent=2))
    z.writestr(prefix+'README.txt',readme.replace('\n','\r\n'))
    for path in paths:z.write(ROOT/path,prefix+'payload/'+path)
with zipfile.ZipFile(archive) as z:assert z.testzip() is None
print(archive.name,archive.stat().st_size,'bytes; frontend only')
