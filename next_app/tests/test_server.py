"""Run with: python -m unittest discover -s next_app/tests -v"""
from contextlib import closing
from pathlib import Path
from tempfile import TemporaryDirectory
import base64
import copy
import json
import unittest
from unittest.mock import patch
from fastapi.testclient import TestClient
from local_backend import initialize, connect
from next_app.backend import main, reports, configure


def fixture():
    data = copy.deepcopy(main.EMPTY)
    data.update({'sticky_notes': ['یادداشت'], 'tasks': [{'title': 'Existing task', 'subtasks': [], 'done': False}],
                 'meeting_cards': ['Meeting'], 'meeting_data_Meeting': [[''] * 6 for _ in range(11)],
                 'warehouse_cards': ['Request'], 'warehouse_card_ids': ['w'], 'warehouse_forms': {'w': reports.create_empty_warehouse_form()},
                 'mission_report_cards': ['Mission'], 'mission_report_card_ids': ['m'], 'mission_report_forms': {'m': reports.create_empty_mission_form()},
                 'bom_cards': ['BOM'], 'bom_card_ids': ['b'], 'bom_forms': {'b': reports.create_empty_bom()},
                 'unknown_legacy': {'keep': 'exactly'},
                 'financial_projects': {'p': {'title': 'پروژه', 'budget': '1000000', 'notes': '', 'currency': 'IRR',
                    'transactions': [{'id': 'r', 'date': '1405/08/07', 'type': 'Expense', 'category': 'متریال', 'amount': '12000', 'description': 'خرید', 'attachments': []}],
                    'documents': [{'id': 'f', 'title': 'Original file', 'filename': 'original.txt', 'mime': 'text/plain', 'size': 3, 'data': base64.b64encode(b'abc').decode()}]}}})
    return data


class ServerTests(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        self.path = Path(self.temp.name) / 'dashboard.sqlite3'
        self.original = fixture()
        initialize(self.path, 'owner@example.invalid', 'fixture-password', 'owner', [{'section': k, 'data': v} for k, v in self.original.items()])
        self.patches = [patch.object(main, 'DATABASE', self.path), patch.object(main, 'DATA_DIR', Path(self.temp.name))]
        for p in self.patches: p.start()
        main.sessions.clear()
        self.client = TestClient(main.app)
        self.csrf = self.client.post('/api/login', json={'email': 'owner@example.invalid', 'password': 'fixture-password'}).json()['csrf']
    def tearDown(self):
        self.client.close()
        for p in self.patches: p.stop()
        self.temp.cleanup()
    def update(self, sections, version=None, headers=None):
        version = version or self.client.get('/api/state').json()['version']
        return self.client.patch('/api/state', json={'version': version, 'sections': sections}, headers=headers or {'X-CSRF-Token': self.csrf})
    def test_auth_csrf_logout(self):
        anonymous = TestClient(main.app)
        self.assertEqual(anonymous.get('/api/state').status_code, 401)
        self.assertEqual(anonymous.get('/api/report/financial/p').status_code, 401)
        self.assertEqual(anonymous.post('/api/login', headers={'Origin': 'https://evil.invalid'}, json={'email': 'owner@example.invalid', 'password': 'fixture-password'}).status_code, 403)
        self.assertEqual(self.update({'sticky_notes': ['x']}, headers={'X-CSRF-Token': 'wrong'}).status_code, 403)
        self.assertEqual(self.client.post('/api/logout', headers={'X-CSRF-Token': self.csrf}).status_code, 200)
        self.assertEqual(self.client.get('/api/state').status_code, 401)
    def test_atomic_conflict_and_preservation(self):
        version = self.client.get('/api/state').json()['version']
        self.assertEqual(self.update({'sticky_notes': ['new']}, version).status_code, 200)
        self.assertEqual(self.update({'tasks': []}, version).status_code, 409)
        stored = self.client.get('/api/state').json()['state']
        self.assertEqual(stored['sticky_notes'], ['new'])
        self.assertEqual(stored['tasks'], self.original['tasks'])
        self.assertEqual(stored['unknown_legacy'], self.original['unknown_legacy'])
        self.assertEqual(stored['financial_projects'], main.project_state(self.original)['financial_projects'])
        self.assertEqual(self.update({'dashboard_data': []}).status_code, 422)
    def test_backup_and_private_files(self):
        response = self.client.post('/api/backup', headers={'X-CSRF-Token': self.csrf})
        self.assertEqual(response.status_code, 200)
        with closing(connect(Path(self.temp.name) / 'backups' / response.json()['filename'])) as db:
            self.assertEqual(db.execute('PRAGMA integrity_check').fetchone()[0], 'ok')
        for path in ('/brand/dashboard.sqlite3', '/api/secrets.toml', '/assets/missing.txt'):
            self.assertEqual(self.client.get(path).status_code, 404)
        self.assertEqual(self.client.get('/api/state').headers['cache-control'], 'no-store')
    def test_reports_and_farsi(self):
        for kind, key in [('meeting', '0'), ('warehouse', 'w'), ('mission', 'm'), ('bom', 'b'), ('financial', 'p')]:
            response = self.client.get(f'/api/report/{kind}/{key}')
            self.assertEqual(response.status_code, 200, response.text[:100] if response.status_code != 200 else '')
            self.assertTrue(response.content.startswith(b'%PDF-'))
        self.assertEqual(self.client.get('/api/report/unknown/x').status_code, 422)
    def test_invalid_financial_not_saved(self):
        projects = copy.deepcopy(self.original['financial_projects'])
        projects['p']['transactions'][0]['amount'] = '-10'
        self.assertEqual(self.update({'financial_projects': projects}).status_code, 422)
        self.assertEqual(self.client.get('/api/state').json()['state']['financial_projects'], main.project_state(self.original)['financial_projects'])
    def test_file_bytes_lazy_and_preserved_after_rename(self):
        state = self.client.get('/api/state').json()['state']
        record = state['financial_projects']['p']['documents'][0]
        self.assertNotIn('data', record)
        self.assertEqual(self.client.get('/api/file/' + record['_blob_ref']).content, b'abc')
        self.assertEqual(TestClient(main.app).get('/api/file/' + record['_blob_ref']).status_code, 401)
        state['financial_projects']['p']['title'] = 'Renamed project'
        self.assertEqual(self.update({'financial_projects': state['financial_projects']}).status_code, 200)
        with closing(connect(self.path)) as db:
            stored = json.loads(db.execute("SELECT data FROM dashboard_data WHERE section='financial_projects'").fetchone()[0])
        self.assertEqual(stored['p']['documents'], self.original['financial_projects']['p']['documents'])
        state['financial_projects']['p']['documents'][0]['_blob_ref'] = '0' * 64
        self.assertEqual(self.update({'financial_projects': state['financial_projects']}).status_code, 422)

    def test_migration_exact_and_no_overwrite(self):
        folder = Path(self.temp.name) / 'migration'
        rows = [{'section': k, 'data': v} for k, v in self.original.items()]
        path = configure.import_rows(folder, rows, 'owner@example.invalid', 'fixture-password', 'owner')
        configure.verify_copy(path, rows)
        with self.assertRaises(FileExistsError):
            configure.import_rows(folder, rows, 'other@example.invalid', 'other-password', 'other')
        configure.verify_copy(path, rows)


class CloudMigrationTests(unittest.TestCase):
    def test_read_only_paginated_copy_and_owner_check(self):
        calls = []
        batch = [{'section': f'section{i}', 'data': {'value': i}} for i in range(1000)]
        def api(base, path, key, token=None, payload=None):
            calls.append((path, payload))
            if path.startswith('/auth/v1/token'):
                return {'access_token': 'fixture-token', 'user': {'id': 'owner'}}
            if path.startswith('/auth/v1/logout'):
                return None
            return [] if 'offset=1000' in path else batch
        with patch.object(configure, 'request_json', side_effect=api):
            rows = configure.cloud_rows('https://example.invalid', 'fixture-key', 'owner@example.invalid', 'fixture-password', 'owner')
        self.assertEqual(rows, batch)
        self.assertTrue(any('offset=1000' in path for path, _ in calls))
        self.assertTrue(all(payload is None for path, payload in calls if path.startswith('/rest/')))
        self.assertEqual(calls[-1][0], '/auth/v1/logout?scope=local')
        with patch.object(configure, 'request_json', side_effect=api):
            with self.assertRaises(ValueError):
                configure.cloud_rows('https://example.invalid', 'fixture-key', 'owner@example.invalid', 'fixture-password', 'different-owner')


if __name__ == '__main__': unittest.main()

class SafeMigrationDiagnostics(unittest.TestCase):
    def test_http_status_and_stage_without_sensitive_response(self):
        from io import BytesIO
        from urllib.error import HTTPError
        secret = 'NEVER-PRINT-THIS-CREDENTIAL'
        error = HTTPError('https://example.invalid/auth/v1/token', 400, secret, {}, BytesIO(json.dumps({'code':'invalid_credentials', 'message':secret}).encode()))
        with patch.object(configure.urllib.request, 'urlopen', side_effect=error):
            with self.assertRaises(configure.MigrationRequestError) as result:
                configure.request_json('https://example.invalid', '/auth/v1/token?grant_type=password', secret, payload={'password':secret})
        message = str(result.exception)
        self.assertIn('sign-in failed (HTTP 400)', message)
        self.assertIn('DASHBOARD login', message)
        self.assertNotIn(secret, message)

    def test_table_error_and_untrusted_body_are_safe(self):
        from io import BytesIO
        from urllib.error import HTTPError
        for body in (b'{"code":"PGRST205"}', b'<html>private response</html>'):
            error = HTTPError('https://example.invalid/rest/v1/dashboard_data', 404, 'private reason', {}, BytesIO(body))
            with patch.object(configure.urllib.request, 'urlopen', side_effect=error):
                with self.assertRaises(configure.MigrationRequestError) as result:
                    configure.request_json('https://example.invalid', '/rest/v1/dashboard_data', 'fixture-key')
            self.assertIn('record download failed (HTTP 404)', str(result.exception))
            self.assertNotIn('private', str(result.exception))
