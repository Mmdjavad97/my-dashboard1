"""Single-owner, same-origin dashboard API. Run behind private HTTPS for remote use."""
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path
from threading import RLock
import base64
import copy
import hashlib
import hmac
import json
import os
import secrets
import sqlite3
import sys
import time

from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import FileResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from local_backend import LocalClient, backup_database, connect
from . import reports, financial

DATA_DIR = Path(os.environ.get('RNG_DATA_DIR', str(Path.home() / 'RNGDashboardNext'))).resolve()
DATABASE = DATA_DIR / 'dashboard.sqlite3'
FRONTEND = ROOT / 'next_app' / 'frontend' / 'dist'
app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)
lock = RLock()
sessions = {}
SESSION_SECONDS = 12 * 3600
MAX_BODY = 96 * 1024 * 1024
EMPTY = {'sticky_notes': [], 'tasks': [], 'development_tasks': [], 'meeting_cards': [],
         'warehouse_cards': [], 'warehouse_card_ids': [], 'warehouse_forms': {},
         'mission_report_cards': [], 'mission_report_card_ids': [], 'mission_report_forms': {},
         'bom_cards': [], 'bom_card_ids': [], 'bom_forms': {}, 'financial_projects': {}}


@app.middleware('http')
async def protect(request: Request, call_next):
    if request.url.path.startswith('/api/'):
        # Reverse proxies must preserve Host. Reject cross-origin writes (including login).
        if request.method not in ('GET', 'HEAD', 'OPTIONS'):
            origin = request.headers.get('origin')
            allowed = f'{request.url.scheme}://{request.headers.get("host", "")}'
            if (origin and origin != allowed) or request.headers.get('sec-fetch-site') == 'cross-site':
                return JSONResponse({'detail': 'Cross-origin request refused.'}, status_code=403)
        body_size = 0
        original_receive = request._receive
        async def limited_receive():
            nonlocal body_size
            message = await original_receive()
            body_size += len(message.get('body', b''))
            if body_size > MAX_BODY:
                raise HTTPException(413, 'Request is too large.')
            return message
        request._receive = limited_receive
    response = await call_next(request)
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['Referrer-Policy'] = 'same-origin'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['Content-Security-Policy'] = "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' blob: data:; font-src 'self'; connect-src 'self'; frame-src 'self' blob:; object-src 'none'; base-uri 'self'; frame-ancestors 'none'; form-action 'self'"
    if request.url.path.startswith('/api/'):
        response.headers['Cache-Control'] = 'no-store'
    return response


def client():
    if not DATABASE.is_file():
        raise HTTPException(503, 'Run Configure.cmd on the server before opening the app.')
    with closing(connect(DATABASE)) as db:
        owner = db.execute('SELECT uid FROM owner').fetchone()
    return LocalClient(DATABASE, owner['uid'])


def authenticate(request, *, write=False):
    token = request.cookies.get('rng_session', '')
    with lock:
        now = time.time()
        for key in list(sessions):
            if sessions[key]['expires'] <= now:
                del sessions[key]
        session = sessions.get(hashlib.sha256(token.encode()).hexdigest()) if token else None
    if not session or not session['client'].auth.get_user().user:
        raise HTTPException(401, 'Please sign in again.')
    if write and not hmac.compare_digest(request.headers.get('x-csrf-token', ''), session['csrf']):
        raise HTTPException(403, 'Please reload before saving.')
    return session


def read_state():
    with closing(connect(DATABASE)) as db:
        rows = db.execute('SELECT section,data FROM dashboard_data ORDER BY section').fetchall()
    raw = {r['section']: json.loads(r['data']) for r in rows}
    state = {**EMPTY, **raw}
    version = hashlib.sha256(json.dumps(raw, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
    return state, version


def file_records(state):
    for project in state.get('financial_projects', {}).values():
        for field in ('meeting_files', 'plan_files', 'documents'):
            for record in project.get(field, []):
                if isinstance(record, dict) and isinstance(record.get('data'), str):
                    yield record
        for transaction in project.get('transactions', []):
            for record in transaction.get('attachments', []):
                if isinstance(record, dict) and isinstance(record.get('data'), str):
                    yield record


def project_state(state):
    # Send file metadata at login; fetch original bytes only when opened/downloaded.
    projected = copy.deepcopy(state)
    for record in file_records(projected):
        data = record.pop('data')
        record['_blob_ref'] = hashlib.sha256(data.encode()).hexdigest()
    return projected


def hydrate_sections(sections, original):
    index = {hashlib.sha256(r['data'].encode()).hexdigest(): r['data'] for r in file_records(original)}
    hydrated = copy.deepcopy(sections)
    for project in hydrated.get('financial_projects', {}).values():
        records = [r for field in ('meeting_files', 'plan_files', 'documents') for r in project.get(field, [])]
        records += [r for t in project.get('transactions', []) for r in t.get('attachments', [])]
        for record in records:
            reference = record.pop('_blob_ref', None)
            if reference is not None:
                if reference not in index or 'data' in record:
                    raise HTTPException(422, 'An existing file reference is invalid. Reload before saving.')
                record['data'] = index[reference]
    return hydrated


class Credentials(BaseModel):
    email: str = Field(max_length=320)
    password: str = Field(max_length=1024)


@app.post('/api/login')
def login(credentials: Credentials, request: Request):
    local = client()
    try:
        local.auth.sign_in_with_password(credentials.model_dump())
    except ValueError:
        raise HTTPException(401, 'Incorrect email or password, or too many attempts. Wait a minute and retry.') from None
    token, csrf = secrets.token_urlsafe(32), secrets.token_urlsafe(32)
    with lock:
        now = time.time()
        for key in list(sessions):
            if sessions[key]['expires'] <= now:
                del sessions[key]
        if len(sessions) >= 100:
            del sessions[next(iter(sessions))]
        sessions[hashlib.sha256(token.encode()).hexdigest()] = {'client': local, 'csrf': csrf, 'expires': now + SESSION_SECONDS}
    response = JSONResponse({'csrf': csrf})
    response.set_cookie('rng_session', token, httponly=True, secure=request.url.scheme == 'https', samesite='strict', max_age=SESSION_SECONDS)
    return response


@app.get('/api/session')
def session(request: Request):
    return {'csrf': authenticate(request)['csrf']}


@app.post('/api/logout')
def logout(request: Request):
    authenticate(request, write=True)
    token = request.cookies.get('rng_session', '')
    with lock:
        sessions.pop(hashlib.sha256(token.encode()).hexdigest(), None)
    response = JSONResponse({'ok': True})
    response.delete_cookie('rng_session')
    return response


@app.get('/api/state')
def get_state(request: Request):
    authenticate(request)
    with lock:
        state, version = read_state()
    return {'state': project_state(state), 'version': version}


class Changes(BaseModel):
    version: str
    sections: dict


def validate_section(key, value, previous=None):
    if key not in EMPTY and not key.startswith('meeting_data_'):
        raise HTTPException(422, 'Unknown record group.')
    expected = dict if key.endswith('_forms') or key == 'financial_projects' else list
    if not isinstance(value, expected):
        raise HTTPException(422, f'Invalid record group: {key}')
    if key in ('tasks', 'development_tasks'):
        if any(not isinstance(t, dict) or not isinstance(t.get('title'), str) or not isinstance(t.get('subtasks', []), list) for t in value):
            raise HTTPException(422, 'Invalid task.')
    if key == 'financial_projects':
        for project_id, project in value.items():
            try:
                if not isinstance(project.get('title'), str) or not project['title'].strip():
                    raise ValueError()
                old = (previous or {}).get(project_id, {})
                if project.get('budget') != old.get('budget'):
                    financial.rial(project.get('budget', '0'))
                if project.get('transactions', []) != old.get('transactions', []):
                    financial.validate_rows(project.get('transactions', []))
            except (ValueError, KeyError, TypeError, AttributeError, ArithmeticError):
                raise HTTPException(422, 'Check project dates, amounts, names, and categories.') from None


@app.patch('/api/state')
def patch_state(changes: Changes, request: Request):
    authenticate(request, write=True)
    # One DB transaction covers the revision check and every changed group.
    with lock, closing(connect(DATABASE)) as db, db:
        db.execute('BEGIN IMMEDIATE')
        rows = {r['section']: json.loads(r['data']) for r in db.execute('SELECT section,data FROM dashboard_data ORDER BY section')}
        version = hashlib.sha256(json.dumps(rows, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
        if not hmac.compare_digest(version, changes.version):
            raise HTTPException(409, 'Another device changed your data. Reload the latest records before trying again. Your draft is still open.')
        try:
            hydrated = hydrate_sections(changes.sections, rows)
        except (AttributeError, TypeError, KeyError):
            raise HTTPException(422, "Invalid project or file records.") from None
        for key, value in hydrated.items():
            validate_section(key, value, rows.get(key))
            db.execute('INSERT INTO dashboard_data VALUES(?,?) ON CONFLICT(section) DO UPDATE SET data=excluded.data',
                       (key, json.dumps(value, ensure_ascii=False, allow_nan=False)))
        rows.update(hydrated)
        version = hashlib.sha256(json.dumps(rows, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
    return {'version': version}


@app.get('/api/file/{reference}')
def file_content(reference: str, request: Request):
    authenticate(request)
    if len(reference) != 64:
        raise HTTPException(404)
    with lock:
        state, _ = read_state()
        for record in file_records(state):
            if hmac.compare_digest(hashlib.sha256(record['data'].encode()).hexdigest(), reference):
                try:
                    data = base64.b64decode(record['data'], validate=True)
                except (ValueError, TypeError):
                    raise HTTPException(422, 'The original file could not be decoded.') from None
                return Response(data, media_type='application/octet-stream', headers={'Content-Disposition': 'attachment; filename="document"'})
    raise HTTPException(404, 'File not found. Reload the latest records.')


@app.get('/api/report/{kind}/{record_id}')
def report(kind: str, record_id: str, request: Request):
    authenticate(request)
    with lock:
        state, _ = read_state()
        try:
            if kind == 'financial':
                project = state['financial_projects'][record_id]
                content = financial.pdf_report(project, reports.rng_pdf_runs)
            elif kind == 'meeting':
                title = state['meeting_cards'][int(record_id)]
                content = reports.create_meeting_pdf(state.get('meeting_data_' + title, [[''] * 6 for _ in range(11)]))
            else:
                groups = {'warehouse': ('warehouse', reports.create_warehouse_pdf, reports.load_warehouse_template),
                          'mission': ('mission_report', reports.create_mission_pdf, reports.load_mission_template),
                          'bom': ('bom', reports.create_bom_pdf, reports.load_bom_template)}
                prefix, generate, template = groups[kind]
                if record_id not in state[prefix + '_card_ids']:
                    raise KeyError()
                form = state[prefix + '_forms'][record_id]
                content = generate(form, template())
        except (KeyError, IndexError, ValueError, TypeError):
            raise HTTPException(422, 'This report has missing or invalid fields. Save and check the record first.') from None
    return Response(content, media_type='application/pdf', headers={'Content-Disposition': f'attachment; filename="RNG-{kind}-report.pdf"'})


@app.post('/api/backup')
def backup(request: Request):
    authenticate(request, write=True)
    destination = DATA_DIR / 'backups' / (datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ') + '.sqlite3')
    with lock:
        backup_database(DATABASE, destination)
    return {'message': 'Verified backup saved on the server.', 'filename': destination.name}


@app.get('/api/health')
def health():
    return {'ready': DATABASE.is_file()}


# Public files are a strict allowlist; never serve the repository or data directory.
ASSETS = {'portrait.png': ROOT / 'My Pic.png', 'logo.png': ROOT / 'assets' / 'RNG Logo.png',
          'nazanin.ttf': ROOT / 'B-NAZANIN.TTF'}


@app.get('/brand/{name}')
def brand(name: str):
    if name not in ASSETS:
        raise HTTPException(404)
    return FileResponse(ASSETS[name])


@app.get('/manifest.webmanifest')
def manifest():
    return JSONResponse({'name': 'RNG Dashboard', 'short_name': 'RNG', 'start_url': '/', 'scope': '/',
        'display': 'standalone', 'background_color': '#edf2f8', 'theme_color': '#132b4b',
        'icons': [{'src': '/icon.svg', 'sizes': 'any', 'type': 'image/svg+xml', 'purpose': 'any'}]}, media_type='application/manifest+json')


if (FRONTEND / 'assets').is_dir():
    app.mount('/assets', StaticFiles(directory=FRONTEND / 'assets'), name='assets')


@app.get('/{path:path}')
def frontend(path: str):
    if path.startswith(('api/', 'brand/', 'assets/')):
        raise HTTPException(404)
    if path in ('sw.js', 'icon.svg'):
        return FileResponse(FRONTEND / path, headers={'Cache-Control': 'no-cache', 'Service-Worker-Allowed': '/'})
    if not (FRONTEND / 'index.html').is_file():
        raise HTTPException(503, 'Build the frontend first.')
    return FileResponse(FRONTEND / 'index.html', headers={'Cache-Control': 'no-cache'})
