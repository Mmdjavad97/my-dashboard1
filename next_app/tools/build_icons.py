"""Export platform sizes from the prepared RNG icon artwork; no logo redesign."""
from pathlib import Path
from PIL import Image
import base64
ROOT = Path(__file__).resolve().parents[2]
source = Image.open(ROOT / 'assets' / 'RNG-App-Icon.png').convert('RGBA')
output = ROOT / 'next_app' / 'frontend' / 'public' / 'app-icons'
output.mkdir(parents=True, exist_ok=True)
for size in (32, 192, 512):
    source.resize((size, size), Image.Resampling.LANCZOS).save(output / f'rng-{size}.png', optimize=True)
navy = (19, 43, 75)
apple = Image.new('RGB', (180, 180), navy)
small = source.resize((180, 180), Image.Resampling.LANCZOS)
apple.paste(small, (0, 0), small)
apple.save(output / 'rng-180.png', optimize=True)
maskable = Image.new('RGB', (512, 512), navy)
small = source.resize((384, 384), Image.Resampling.LANCZOS)
maskable.paste(small, (64, 64), small)
maskable.save(output / 'rng-maskable-512.png', optimize=True)
source.resize((256, 256), Image.Resampling.LANCZOS).save(output / 'rng.ico', sizes=[(n,n) for n in (16,24,32,48,64,128,256)])
encoded = base64.b64encode((output / 'rng-512.png').read_bytes()).decode('ascii')
(ROOT / 'next_app' / 'frontend' / 'public' / 'icon.svg').write_text(
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 512 512"><image width="512" height="512" href="data:image/png;base64,' + encoded + '"/></svg>\n')
