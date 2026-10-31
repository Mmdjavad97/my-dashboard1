from io import BytesIO
from pathlib import Path
import unittest
from fastapi.testclient import TestClient
from PIL import Image
from next_app.backend.main import app, ROOT

class IconTests(unittest.TestCase):
    def test_manifest_and_every_icon(self):
        client = TestClient(app)
        response = client.get('/manifest.webmanifest')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers['cache-control'], 'no-cache')
        manifest = response.json()
        self.assertEqual(manifest['id'], '/')
        self.assertEqual(manifest['start_url'], '/')
        self.assertEqual({i['purpose'] for i in manifest['icons']}, {'any', 'maskable'})
        for record in manifest['icons']:
            response = client.get(record['src'])
            self.assertEqual(response.status_code, 200)
            image = Image.open(BytesIO(response.content))
            self.assertEqual(f'{image.width}x{image.height}', record['sizes'])
            if record['purpose'] == 'maskable':
                self.assertEqual(image.getpixel((0, 0)), (19,43,75))
            else:
                self.assertEqual(image.mode, 'RGBA')
                self.assertEqual(image.getpixel((0,0))[3], 0)
        for name, size in [('rng-32.png', 32), ('rng-180.png', 180)]:
            image = Image.open(BytesIO(client.get('/brand/' + name).content))
            self.assertEqual(image.size, (size, size))
        ico = Image.open(BytesIO(client.get('/brand/rng.ico').content))
        self.assertEqual(ico.format, 'ICO')
        self.assertIn((256, 256), ico.ico.sizes())
        self.assertEqual(client.get('/brand/not-an-icon.png').status_code, 404)

    def test_apple_and_browser_links_in_built_page(self):
        response = TestClient(app).get('/')
        self.assertIn('apple-touch-icon', response.text)
        self.assertIn('/brand/rng-180.png', response.text)
        self.assertIn('/brand/rng-32.png', response.text)
        self.assertTrue((ROOT / 'next_app/frontend/dist/app-icons/rng.ico').is_file())
