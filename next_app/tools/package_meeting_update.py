"""Package meeting status colors and defaults, retaining prior warehouse support."""
from pathlib import Path
import hashlib,json,subprocess,zipfile
ROOT=Path(__file__).resolve().parents[2]
SUPPORTED=['5819eda8df0d3362fd80d2c3f9757cb9367bfdb0','6a8cc84950a520963a75056265fd9c81f4b1c17c','517d5b28f12635eedd8df716d7c1a94373f7e612','2e1c2d01231465ef9e313444f559732fffde583d']
paths=['next_app/backend/reports.py','next_app/frontend/src/main.jsx','next_app/frontend/src/style.css','next_app/frontend/dist/index.html']
paths += [p.relative_to(ROOT).as_posix() for p in sorted((ROOT/'next_app/frontend/dist/assets').glob('*'))]
files=[]
for path in paths:
    versions=[]
    for ref in SUPPORTED:
        old=subprocess.run(['git','show',ref+':'+path],cwd=ROOT,capture_output=True)
        if old.returncode==0:versions.append(hashlib.sha256(old.stdout).hexdigest())
    files.append({'path':path,'sha256':hashlib.sha256((ROOT/path).read_bytes()).hexdigest(),
                  'previous':versions[0] if versions else None,'previous_versions':versions})
readme="""RNG Meeting Status Update - run on the SERVER PC.

1. Extract the entire ZIP.
2. Double-click Apply-Meeting-Update.cmd.
3. Select your EXISTING program folder containing next_app.
4. After the app reopens, refresh the same app address on PC and phone.

Meeting agenda badges and selected status controls now use:
Raised / Done: light green
Not Raised / Stopped: red
Not Started: gray
In Progress: yellow

All eleven NEW agendas start as Not Raised / Not Started. Previously saved
nonblank statuses are preserved, including older capitalization variants.
Blank legacy statuses use the new defaults in the editor; Save meeting
stores them. Defaults pending saving are marked as unsaved so PDF exports
continue to reflect saved records. PDF layouts are otherwise unchanged.
Unknown legacy statuses remain available instead of being silently replaced.

The update includes prior warehouse multi-table PDF support and does not
read or replace your database, uploads, login credentials or Tailscale settings.
No Setup, CSV import, dependencies or icon reinstall is required.
Existing program files are checked and backed up before replacement.
If the app does not reopen after an error, use its existing desktop shortcut.

PC/phone browser checks cover all colors, new defaults, existing statuses,
and saving/reopening. Native Windows updater execution still needs verification
on your actual server.
"""
archive=ROOT/'downloads/RNG-Meeting-Update.zip'
with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as z:
    prefix='RNG-Meeting-Update/'
    for name in ('Apply-Meeting-Update.ps1','Apply-Meeting-Update.cmd'):z.write(ROOT/'next_app/windows'/name,prefix+name)
    z.writestr(prefix+'meeting-update.json',json.dumps({'version':'meeting-status-20261103','files':files},indent=2))
    z.writestr(prefix+'README.txt',readme.replace('\n','\r\n'))
    for path in paths:z.write(ROOT/path,prefix+'payload/'+path)
with zipfile.ZipFile(archive) as z:assert z.testzip() is None
print(archive.name,archive.stat().st_size,'bytes; program files only')
