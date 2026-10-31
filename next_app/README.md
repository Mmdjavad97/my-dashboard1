# RNG Dashboard Next

React + FastAPI replacement for the original dashboard. This directory runs independently of Streamlit and Supabase. The existing `app.py` and cloud deployment are unchanged.

## Simplest migration: export a file, then import it

Open your project in Supabase Dashboard, select **Table Editor → dashboard_data**, clear any filters, and use the table's export option to download **all rows as CSV**. Keep the export private: it contains your records and embedded uploaded files. Do not send it in chat. This step uses the Supabase website, not the blocked Streamlit app.

Run the new Windows Setup, choose **3**, select that CSV in the file picker, and choose an email/password for your **local** login. No API key, old dashboard password or network connection to Supabase is needed for this import. The email does not need to match your previous cloud login. Import checks the CSV structure, rejects duplicate/empty section names and empty exports, copies the records, verifies the stored JSON exactly, and creates an initial backup. It refuses to replace an existing local database.

If configuration reports an existing installation, it will preserve it. Do not delete that database to force a CSV import; back it up and investigate before replacing records. Review the full set of records after import to ensure your export was not filtered or incomplete.

## Install on the Windows server

1. Keep the existing cloud app and Supabase project. Pause editing there while copying records.
2. Download the complete repository ZIP and extract it into a permanent folder. Do not copy just `next_app`: original images, fonts and report templates at repository root are required.
3. Install **Python 3.12, 64-bit**, including its launcher. No Node.js installation is needed on the server: the compiled React interface is included.
4. Run **`next_app\windows\Setup.cmd`**. This is a different installer from the earlier `server\windows\Setup.cmd`.
5. Choose **3** for the simpler CSV import described above. Alternatively, choose **2** to copy directly from Supabase if the previous migration never finished. Enter URL, publishable/anon key, existing login email and password into the local prompts only. The defaults contain your project URL and owner UID, not a secret key.
6. If you already finished the earlier local migration, choose **1** and copy that database. It preserves its existing local login credentials. The source database is not modified.
7. Open **RNG Dashboard Next** from the desktop. The server runs at `http://127.0.0.1:8765`; Edge opens it in a separate app window.

The Windows ZIP includes Python dependency wheels from PyPI, pinned with SHA-256 hashes. Setup installs them **offline**, without contacting PyPI. Python 3.12 itself must already be installed. Copying your live records from Supabase still requires an internet connection that can reach your project. Streamlit and the Supabase Python SDK are **not** installation dependencies. On normal use the app does not call either service. It remains an application built with browser technology, rather than a native Windows executable.

## Data and cutover

New records, login hashes and original file bytes are stored in `%LOCALAPPDATA%\RNGDashboardNext\dashboard.sqlite3`. The earlier `%LOCALAPPDATA%\RNGDashboard` folder is separate and untouched. Uploaded files retain their existing base64 encoding in the database so the copy can be verified exactly. The JSON export, initial backup and database are private; do not upload them to GitHub or chat.

Migration compares every section's JSON after copying, including unknown legacy fields and original uploaded bytes. It refuses to overwrite an existing database. If configuration fails after creating a database, preserve it and the export; do not delete them just to restart the wizard. Migration is a copy, not synchronization: later edits in the cloud and local app will diverge.

Before switching, check all your real tasks, subtasks, notes, meeting cards, requests, missions, BOMs, financial totals, transaction attachments, and each project's three file libraries. Download and inspect every kind of PDF; check the mission signature and RNG financial logo. Test from both PC and phone. Make and verify a backup on another physical disk. Only then use the new installation for ongoing edits and consider retiring the cloud deployment. Keep Supabase records until you are satisfied with your independent backups.

The replacement includes task jumps/notes/newest-first grouping, confirm-before-delete, report editors and original PDF generators, RTL Persian financial ledger, integer IRR amounts, category totals, transaction attachments, named file uploads/previews/download/share/rename/delete, Gregorian and Solar Hijri home dates, the portrait, and mobile navigation with native browser history. Employer Report remains a placeholder as in the original app. The new interface follows the existing navy visual style; it is not a pixel-identical copy of Streamlit.

## Private access from other devices

The default listener is **localhost only**, so typing the LAN IP on another PC will not work yet. Keep this default and use private HTTPS:

1. Install Tailscale on the Windows server and your other PC/phone. Sign in to your private tailnet and approve devices as required.
2. Start the dashboard on the server. In a server terminal, run:
   ```text
   tailscale serve --bg http://127.0.0.1:8765
   ```
3. Follow Tailscale's instructions to enable HTTPS if prompted. Open the **HTTPS `.ts.net` address it prints** on your other enrolled devices. Their Tailscale connection must be enabled.
4. On Samsung Chrome, use the browser menu's **Install app / Add to Home screen** action. Install the new address, not the old Streamlit Cloud address. Secure HTTPS enables installability and file sharing where the browser supports them. If sharing is unsupported or fails, Share downloads the original file instead.

Do not enable Tailscale Funnel or forward router ports. This is private access, not public publishing. Test access on your actual Iranian internet/mobile networks; connectivity and performance depend on them. App records and credentials are never cached by the service worker. Your server still needs to be reachable to log in and read/save records; installing the PWA does not make it an offline database.

For LAN access without Tailscale, have an administrator set up a trusted HTTPS reverse proxy and a firewall rule limited to the private LAN. Keep the API bound to localhost behind the proxy; preserve Host and forward the HTTPS scheme. Do not expose plain HTTP passwords on the LAN or internet. There is no LAN certificate or firewall change hidden in Setup.

## Startup and backups

Setup creates a Startup shortcut for this Windows user and attempts to schedule a daily backup at **19:00 in the Windows server's configured local timezone**. It reports if the task cannot be registered. Keep that Windows account signed in, the server awake, and its clock/timezone correct. This release does not install a Windows service or promise startup before sign-in. Remote Desktop can disconnect while leaving the account signed in; logging out stops user-session processes.

Use **`next_app\windows\Backup.cmd`** or **Back up on server** in the app at any time. Backups are SQLite-consistent, verified with integrity checks, and saved under the data folder's `backups` directory. These server-local backups do not protect against disk failure; copy them to another drive regularly. No backup retention deletion runs automatically.

To restore, first stop this app's Python process (identify it by `uvicorn next_app.backend.main:app`, not the old Streamlit process). Preserve the current database. Copy a verified backup to `dashboard.sqlite3` in the new data folder and reopen the app. The login password is the one used when that backup was made.

## RNG Logo icon update

The login page, app header and dashboard home now display the RNG mark. Its white logo sections and burgundy accent sit on a dark navy icon with rounded corners. The app supplies RNG monogram PNG icons for Android/desktop installation, a maskable Android variant, an Apple touch icon, a browser favicon, and a Windows ICO. The original full RNG Logo used in reports is unchanged.

For an existing Windows installation, download `downloads/RNG-Logo-Update.zip`, extract the entire archive, and run **Apply-Logo-Update.cmd on the server PC**. In the folder picker choose the existing installed program folder containing `next_app`, not the update folder. The updater checks old program hashes before changing files, saves old program files, restarts only the selected installation's server, and refreshes its existing server desktop shortcut icon. It does not read, replace or re-import the database. This package supports the earlier versions distributed in this conversation; a modified program file causes it to stop rather than overwrite changes.

Afterward close the app on your phone/PC and refresh its existing Tailscale HTTPS address. Browsers may retain the installed icon; if it stays old, remove the app shortcut and install that same address again. The records stay on the server. Re-pin a Windows taskbar shortcut if needed. `RNG.ico` in the update archive is also available for manual Windows shortcut properties. Do not delete the server installation or its AppData folder, and do not rerun the CSV import.

The icon routes, dimensions, manifest and package hashes have automated checks. The native Windows updater and installed-icon refresh still need verification on your devices.

## Updates and troubleshooting

Updates on GitHub do not automatically update this extracted installation. Back up, stop the new server, replace the program files in the same permanent folder, then rerun its Setup. Keep AppData untouched. Use the new Open shortcut to restart.

- `No suitable Python runtime`: install Python 3.12 alongside your other versions; verify `py -3.12 --version`.
- Missing offline package: extract the entire new ZIP, including `next_app\windows\wheels`; use Python 3.12, 64-bit. A timeout during migration means the server could not reach your Supabase project.
- Server fails to open: inspect `%LOCALAPPDATA%\RNGDashboardNext\server-errors.log` locally. Do not share passwords, exports or database files.
- Another-device conflict: the app rejects stale saves and keeps the current editor open. Copy any unsaved text before reloading the latest records and reapplying your change. It does not silently merge transactions.
- Migration HTTP error: the installer prints the failing stage and HTTP status, with a fixed hint. Share only that diagnostic line; do not send keys, passwords, exports or database files. Use your existing dashboard login credentials, which may differ from your Supabase website account.
- Login expires: reload and sign in again. Sessions expire after twelve hours and on server restart.
- PDF/share: save edits first. Use Download if the device's native share dialog is unavailable.

The API/browser behavior was tested in Linux with sample data at desktop and phone sizes. The PowerShell scripts, actual Windows installation, private networking and the owner's live data must be verified on the server before retiring the original installation.

## Development

From the repository root:

```bash
python3.12 -m venv next_app/.venv
next_app/.venv/bin/python -m pip install -r next_app/backend/requirements.txt
npm --prefix next_app/frontend ci
npm --prefix next_app/frontend run build
# Configure a NEW data folder using the interactive local migration wizard:
next_app/.venv/bin/python next_app/backend/configure.py --data-dir /absolute/private/path
RNG_DATA_DIR=/absolute/private/path next_app/.venv/bin/python -m uvicorn next_app.backend.main:app --host 127.0.0.1 --port 8765
```

Tests: additionally install `httpx`, then run `python -m unittest discover -s next_app/tests -v` from the repository root. Test fixtures are synthetic and never connect to Supabase. Reports were ported as static source, rather than executing or importing `app.py`; the legacy code is not evaluated by the new runtime.
