"""Package financial contracts, clean calendar dates and consistent new agenda defaults."""
from pathlib import Path
import hashlib,json,subprocess,zipfile
ROOT=Path(__file__).resolve().parents[2]
SUPPORTED=['daf0318c317d2af96424be61b1e50a48b07eba7c','5819eda8df0d3362fd80d2c3f9757cb9367bfdb0','6a8cc84950a520963a75056265fd9c81f4b1c17c','517d5b28f12635eedd8df716d7c1a94373f7e612','2e1c2d01231465ef9e313444f559732fffde583d']
paths=['next_app/backend/main.py','next_app/backend/reports.py','next_app/frontend/src/dates.js','next_app/frontend/src/meeting-defaults.js','next_app/frontend/src/main.jsx','next_app/frontend/src/style.css','next_app/frontend/dist/index.html']
paths += [p.relative_to(ROOT).as_posix() for p in sorted((ROOT/'next_app/frontend/dist/assets').glob('*'))]
files=[]
for path in paths:
    versions=[]
    for ref in SUPPORTED:
        old=subprocess.run(['git','show',ref+':'+path],cwd=ROOT,capture_output=True)
        if old.returncode==0:versions.append(hashlib.sha256(old.stdout).hexdigest())
    files.append({'path':path,'sha256':hashlib.sha256((ROOT/path).read_bytes()).hexdigest(),
                  'previous':versions[0] if versions else None,'previous_versions':versions})
readme="""RNG Financial and Agenda Update - run on the SERVER PC.

1. Extract the entire ZIP.
2. Double-click Apply-Financial-Update.cmd.
3. Select your EXISTING program folder containing next_app.
4. When the server reopens, refresh the app on your PC and phone.

New meeting agendas default to Not Raised and Not Started. Previously saved
nonblank statuses are preserved; existing status colors remain available.

Financial now has a Project contract upload beside the budget (below it on
phones). Files are up to 5 MB each and 20 MB total per project. View, Download,
Share and confirmed Remove are available. Uploads/removals are drafts until
Save financial. Your original file bytes are stored in the local database;
they are fetched only when viewed/downloaded, not during every login.

Financial automatic dates contain only Solar Hijri year/month/day, without
AP. Dates remain editable. Existing AP suffixes are cleaned in the editor;
Save financial keeps the corrected date. No live records are bulk rewritten.

The updater changes program files only. It does not read or replace your
database, uploaded files, credentials, icons or Tailscale configuration.
No Setup, CSV import, dependency installation or icon reinstall is needed.
Program hashes are checked and old program files are backed up before changes.
If the app does not reopen after an error, use the existing desktop shortcut.

Contracts can be opened/downloaded from Financial; they are not embedded
inside the generated transaction PDF. Existing report layouts remain unchanged.
PC/phone and API checks cover file integrity, new defaults and editable dates.
Native Windows updater execution still needs verification on the actual server.
"""
archive=ROOT/'downloads/RNG-Financial-Update.zip'
with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as z:
    prefix='RNG-Financial-Update/'
    for name in ('Apply-Financial-Update.ps1','Apply-Financial-Update.cmd'):z.write(ROOT/'next_app/windows'/name,prefix+name)
    z.writestr(prefix+'financial-update.json',json.dumps({'version':'financial-contracts-20261110','files':files},indent=2))
    z.writestr(prefix+'README.txt',readme.replace('\n','\r\n'))
    for path in paths:z.write(ROOT/path,prefix+'payload/'+path)
with zipfile.ZipFile(archive) as z:assert z.testzip() is None
print(archive.name,archive.stat().st_size,'bytes; program files only')
