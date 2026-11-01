"""Package only frontend changes; retain the desktop layout and database."""
from pathlib import Path
import hashlib
import json
import subprocess
import zipfile
ROOT = Path(__file__).resolve().parents[2]
BASE = '2e1c2d01231465ef9e313444f559732fffde583d'
paths = ['next_app/frontend/src/main.jsx', 'next_app/frontend/src/style.css', 'next_app/frontend/dist/index.html']
paths += [p.relative_to(ROOT).as_posix() for p in sorted((ROOT/'next_app/frontend/dist/assets').glob('*'))]
files=[]
for path in paths:
    old=subprocess.run(['git','show',BASE+':'+path],cwd=ROOT,capture_output=True)
    files.append({'path':path,'sha256':hashlib.sha256((ROOT/path).read_bytes()).hexdigest(),
        'previous':hashlib.sha256(old.stdout).hexdigest() if old.returncode==0 else None})
readme='''RNG Phone Layout Update - run on the SERVER PC.

1. Extract the entire ZIP.
2. Double-click Apply-Phone-Update.cmd.
3. Select your EXISTING installed dashboard folder containing next_app.
4. After the server reopens, close/reopen the app on your PHONE and refresh
   its existing Tailscale HTTPS address.

This update only replaces frontend program files. Phone styles require a
touch screen with a smaller side at most 700px and viewport at most 1000px,
including landscape. Narrow desktop windows do not activate these changes.
Desktop layouts are unchanged. The BOM table becomes editable item cards
on phones; saved data, calculations and PDFs retain their existing format.
The login fits ordinary phone screens, the bottom navigation and home tiles
are slightly smaller, and sticky notes use a little less space.

No Setup, credentials, CSV import, icon reinstall or Tailscale changes.
Your database and uploaded files are not read or replaced by this updater.
The previous navy-logo update must already be installed. Modified or
unexpected program files make the updater stop without replacing files.
Old program copies are saved in your private AppData program-updates folder.
If the server does not reopen after an error, use its existing desktop shortcut.

Browser checks cover PC and phone layouts, phone BOM edits, saving and PDFs.
Native Windows updater execution still needs verification on your server.
'''
archive=ROOT/'downloads/RNG-Phone-Update.zip'
with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as z:
    prefix='RNG-Phone-Update/'
    for name in ('Apply-Phone-Update.ps1','Apply-Phone-Update.cmd'):
        z.write(ROOT/'next_app/windows'/name,prefix+name)
    z.writestr(prefix+'phone-update.json',json.dumps({'version':'phone-layout-20261101','files':files},indent=2))
    z.writestr(prefix+'README.txt',readme.replace('\n','\r\n'))
    for path in paths:z.write(ROOT/path,prefix+'payload/'+path)
with zipfile.ZipFile(archive) as z:
    assert z.testzip() is None
    assert not any(n.endswith(('.sqlite3','secrets.toml')) for n in z.namelist())
print(archive.name,archive.stat().st_size,'bytes; frontend only')
