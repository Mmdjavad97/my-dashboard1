# RNG Dashboard on your Windows server

The dashboard keeps its existing pages, designs, financial reports, uploads and mobile layout. This installation uses a local SQLite database and local password authentication. Streamlit Cloud continues to use Supabase by default; nothing switches until you install and migrate on Windows.

## Install once

1. Keep the original cloud app available. Stop editing it during migration so the copy has a clear cutover point.
2. Install **Python 3.12 for 64-bit Windows** from https://www.python.org/downloads/windows/ (include the Python launcher). Internet is needed for this installation and for the initial data copy.
3. Extract the complete ZIP into a permanent folder, such as `C:\RNGDashboard`. Keep all files together. Do not run it inside the ZIP or move the folder afterward.
4. Double-click `server\windows\Setup.cmd` as the Windows user who will run the server. The installer creates a private Python environment and a desktop shortcut.
5. At the local prompts, enter your existing Supabase project URL, publishable/anon key, owner user UID, dashboard email and password. Find the first three in your existing Streamlit app's Secrets. Passwords and the key are hidden while entered. **Do not send them in chat.** Alternatively, run `migrate.py --data-dir <folder> --cloud-secrets <local TOML file>` after dependency installation.
6. Choose a local password, or press Enter to keep your existing one. It is stored as a salted password hash, never plaintext.
7. The tool saves an export, copies every section and embedded uploaded file, compares the source and destination, then creates an initial SQLite backup. It never writes to or deletes from Supabase.
8. Open **RNG Dashboard** from your desktop. It opens in an Edge app window; the server runs in the background. Sign in with the same email and your chosen local password.
9. Check task notes, sticky notes, project files, financial transactions and PDF exports before switching to this installation. After switching, edit only this installation. The old cloud app and this server **do not synchronize**.

After verifying the new server and its backups, retire the old Streamlit Cloud deployment if you want the old public address removed. Keep your GitHub repository and Supabase records/exports until you are satisfied with the migration; removing the old deployment does not require deleting those records.

## Private access from your phone or another PC

Recommended: **Tailscale**, a private network client. It must be installed and signed in on the Windows server and each device you want to use. This does not publish the dashboard on the public internet. Check that Tailscale connects reliably from your own networks before relying on it.

1. Install Tailscale from https://tailscale.com/download/windows and sign in. Install it on your Samsung phone and other PCs too. Use the same private tailnet; do not share access with people who should not reach your server.
2. In PowerShell on the server, run:

   ```powershell
   tailscale serve --bg http://127.0.0.1:8501
   ```

3. If prompted, follow Tailscale's admin link to enable HTTPS certificates/MagicDNS. Use the **HTTPS address printed by Tailscale**, normally `https://your-server.your-tailnet.ts.net/`.
4. Open that address on your phone while Tailscale is connected. Add it to the home screen and replace the old `streamlit.app` shortcut; the old shortcut still opens the old cloud app. The dashboard still requires its own email/password login.
5. Check file sharing and PDFs on the phone. HTTPS is needed for browser file sharing and the app's secure browser features.

Keep Streamlit bound to **127.0.0.1** as supplied. No router port forwarding or public Streamlit port is required. `tailscale serve status` shows the private address. `tailscale serve reset` removes the proxy. Do **not** enable Tailscale Funnel, which would publish a public endpoint.

If you choose a normal public domain instead, use a trusted HTTPS reverse proxy, keep the app login enabled, and configure Windows/router networking deliberately. That is a different exposure model from a private Tailscale installation.

## Startup and everyday use

- The setup creates a Startup shortcut: the server starts **when this Windows account signs in**, including after a restart followed by sign-in. It does not start before sign-in. Locking the screen is fine; signing out stops this user session. For unattended startup before sign-in, use the optional boot setup below.
- Keep the PC powered, awake and connected to the internet for remote access. The local app and local records do not need Supabase during ordinary use.
- Use the desktop shortcut or `Open Dashboard.cmd` to start/open it manually.
- It remains Streamlit internally, so reruns still exist. Local database access removes the previous Supabase round trips; speed also depends on the PC and connection.
- Existing external document links remain links. File contents uploaded into the dashboard are included in the migrated database.

## Optional: run automatically before Windows sign-in

After normal Setup, double-click `EnableBootStartup.cmd`. Windows will request administrator approval to register scheduled tasks. The application itself runs under your original **limited user account**, not SYSTEM; the task does not store your Windows password. It uses Windows S4U and local files, so keep the program and database on a local disk rather than an authenticated network share. It also changes the backup task to run before sign-in.

The current server keeps running. At your next convenient Windows restart, test the private HTTPS address from another device before signing into Windows. The existing sign-in Startup shortcut is retained as a fallback; the server lock prevents duplicate launches. Windows account/domain policy may restrict S4U tasks; if registration is rejected, the normal sign-in startup still works. Disable the `RNG Dashboard Server` task in Task Scheduler if retiring this mode.

## Updating this installation

The Windows server runs its own copy of the program. Future GitHub/Streamlit Cloud updates do not automatically update it. Before an update, make a verified backup, stop this dashboard's Python process, copy the new program files into the same permanent folder, and run Setup again to refresh dependencies. Setup skips migration when local configuration already exists. Keep `%LOCALAPPDATA%\RNGDashboard` intact; it contains your actual records.

## Data and backups

All local records, uploaded file contents, local credential hashes and configuration are under:

```
%LOCALAPPDATA%\RNGDashboard
```

`dashboard.sqlite3` is the database. `secrets.toml` selects local storage. `server.log` and `server-errors.log` contain startup/runtime output. Keep the original migration export and `backups` folder private.

The installer attempts to schedule a verified daily backup at **19:00 Windows local time**, under your signed-in Windows account. It reports whether this scheduling succeeded. You can always double-click `Backup.cmd` manually. Backup files accumulate; copy verified backups to another disk and manage retention yourself. To send a backup directly to another folder:

```powershell
.\.venv\Scripts\python.exe .\server\windows\backup.py --data-dir "$env:LOCALAPPDATA\RNGDashboard" --output 'D:\RNGBackups'
```

To restore: stop this dashboard server process, preserve the current database, copy a verified `.sqlite3` backup over `dashboard.sqlite3`, and restart. Restore backups created by `Backup.cmd`, not a raw copy taken during writes. The restored login password is the password stored at backup time.

## Troubleshooting

- Setup refuses to overwrite an existing database or local configuration. If migration stops, keep the export and database; do not delete them to force a retry. The original cloud records remain intact. A valid database can be recovered using its verified backup and matching owner configuration.
- If Python installation fails, check internet/package access and rerun Setup. Existing records are not replaced.
- If the app will not start, inspect `%LOCALAPPDATA%\RNGDashboard\server.log` and `server-errors.log`. Ensure another app is not using port 8501.
- To stop automatic startup, remove `RNG Dashboard Server.lnk` from `shell:startup`. Disable the `RNG Dashboard Daily Backup` scheduled task if retiring the installation.
- The supplied scripts have been reviewed and their Python components tested, but the actual Windows startup, Edge window and Tailscale connection must be verified on your PC.
