"""Package warehouse tables and the matching multi-page PDF renderer."""
from pathlib import Path
import hashlib,json,subprocess,zipfile
ROOT=Path(__file__).resolve().parents[2]
SUPPORTED=['6a8cc84950a520963a75056265fd9c81f4b1c17c','517d5b28f12635eedd8df716d7c1a94373f7e612','2e1c2d01231465ef9e313444f559732fffde583d']
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
readme='''RNG Warehouse Update - run on the SERVER PC.

1. Extract the entire ZIP.
2. Double-click Apply-Warehouse-Update.cmd.
3. Select the EXISTING program folder containing next_app.
4. When the app reopens, refresh it on your PC and phone.

Warehouse cards now have Add another table below their items.
Each click adds 10 new rows. Existing table entries are preserved.
The page moves to the added table. Save report stores every table.
Download PDF and Share PDF include one original A5 landscape page per table,
with the same request metadata, logo, signatures and approvals on each page.
Older cards without extra tables remain compatible and retain one-page exports.

The updater replaces program files only. It does not read or replace your
database, uploaded files, credentials, icons or Tailscale configuration.
No Setup, CSV import, new dependencies or app reinstall is required.
Supported program versions: previous navy-logo, phone-layout or midnight update.
Version checks precede file replacement, and old program files are backed up.
If the server does not reopen after an error, use its existing desktop shortcut.

Browser tests cover PC/phone, added tables, save/reopen, and both PDF actions.
Native Windows update execution still needs verification on your server.
'''
archive=ROOT/'downloads/RNG-Warehouse-Update.zip'
with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as z:
    prefix='RNG-Warehouse-Update/'
    for name in ('Apply-Warehouse-Update.ps1','Apply-Warehouse-Update.cmd'):z.write(ROOT/'next_app/windows'/name,prefix+name)
    z.writestr(prefix+'warehouse-update.json',json.dumps({'version':'warehouse-tables-20261102','files':files},indent=2))
    z.writestr(prefix+'README.txt',readme.replace('\n','\r\n'))
    for path in paths:z.write(ROOT/path,prefix+'payload/'+path)
with zipfile.ZipFile(archive) as z:assert z.testzip() is None
print(archive.name,archive.stat().st_size,'bytes; program files only')
