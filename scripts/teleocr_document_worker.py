"""One local document to unverified OCR text. Never reads a corpus or annotations.

The application launches this fixed script with generated local paths. No tools,
database, provider credentials, downloads or model-selected paths are available.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
import time
import warnings

from teleocr_assets import spec
from teleocr_runtime import TeleOCRRuntime

MAX_BYTES = 8 * 1024 * 1024
MAX_PAGES = 12
MAX_PAGE_TEXT = 16000
MAX_TOTAL_TEXT = 80000


class DocumentImages:
    """Decode a bounded document and close native resources on every exit path."""
    def __init__(self, path):
        self.path = path
        self.pdf = self.image = None
        self.limit = spec()['max_input_pixels']

    def __enter__(self):
        from PIL import Image
        Image.MAX_IMAGE_PIXELS = self.limit
        if self.path.suffix == '.pdf':
            import pypdfium2 as pdfium
            self.pdf = pdfium.PdfDocument(self.path)
            if not 1 <= len(self.pdf) <= MAX_PAGES:
                self.pdf.close()
                self.pdf = None
                raise ValueError('Page limit exceeded')
        else:
            with warnings.catch_warnings():
                warnings.simplefilter('error', Image.DecompressionBombWarning)
                with Image.open(self.path) as original:
                    if original.format not in ('PNG', 'JPEG') or getattr(original, 'n_frames', 1) != 1:
                        raise ValueError('Unsupported image encoding or multiple frames')
                    if original.width * original.height > self.limit:
                        raise ValueError('Image pixel limit exceeded')
                    self.image = original.convert('RGB')
        return self

    def __iter__(self):
        if self.image is not None:
            yield self.image
        else:
            for index in range(len(self.pdf)):
                page = self.pdf[index]
                bitmap = image = None
                try:
                    width, height = page.get_size()
                    if not all(math.isfinite(v) and v > 0 for v in (width, height)):
                        raise ValueError('Invalid page dimensions')
                    scale = min(2.0, (self.limit / (width * height)) ** 0.5)
                    # Account for renderer rounding before allocating the bitmap.
                    if math.ceil(width * scale) * math.ceil(height * scale) > self.limit:
                        scale *= 0.999
                    bitmap = page.render(scale=scale)
                    image = bitmap.to_pil().convert('RGB')
                    yield image
                finally:
                    if image is not None:
                        image.close()
                    if bitmap is not None:
                        bitmap.close()
                    page.close()

    def __exit__(self, *args):
        if self.image is not None:
            self.image.close()
        if self.pdf is not None:
            self.pdf.close()


def run(input_path, output_path, resolution='primary'):
    started = time.perf_counter()
    report = {'status': 'failed', 'mode': 'local-teleocr', 'pages': []}
    try:
        if input_path.is_symlink() or not input_path.is_file() or not 0 < input_path.stat().st_size <= MAX_BYTES:
            raise ValueError('Document path or size rejected')
        if input_path.suffix not in ('.pdf', '.png', '.jpg', '.jpeg'):
            raise ValueError('Unsupported document extension')
        report['input_sha256'] = hashlib.sha256(input_path.read_bytes()).hexdigest()
        with DocumentImages(input_path) as images:
            runtime = TeleOCRRuntime(resolution=resolution)
            for number, image in enumerate(images, 1):
                page = runtime.read_page(image, number)
                if len(page['text']) > MAX_PAGE_TEXT:
                    raise ValueError('Page text limit exceeded')
                report['pages'].append(page)
                if sum(len(p['text']) for p in report['pages']) > MAX_TOTAL_TEXT:
                    raise ValueError('Document text limit exceeded')
                if page['truncated']:
                    break
            report.update(runtime.metadata())
        report['status'] = 'partial' if any(p['truncated'] for p in report['pages']) else 'completed'
    except Exception as exc:
        report['error_type'] = type(exc).__name__
    report['duration_seconds'] = round(time.perf_counter() - started, 3)
    output_path.write_text(json.dumps(report, ensure_ascii=False), encoding='utf-8')
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--execute', action='store_true')
    parser.add_argument('--input', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--resolution', choices=('primary', 'fallback'), default='primary')
    args = parser.parse_args()
    if not args.execute:
        parser.error('Execution must be explicitly enabled')
    run(args.input, args.output, args.resolution)
