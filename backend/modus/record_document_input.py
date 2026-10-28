"""Local page preparation. No model-supplied path, URL or command is accepted."""
import asyncio
import base64
import hashlib
import io
import math
from pathlib import Path
import warnings
import threading

from pypdf import PdfReader

from .ingest import MAX_BYTES

MAX_PAGES = 12
MAX_PAGE_TEXT = 16000
MAX_TOTAL_TEXT = 80000
MAX_PIXELS = 16_000_000
MAX_RENDER_PIXELS = 2_000_000
MAX_IMAGE_BYTES = 8 * 1024 * 1024
_PDF_RENDER_LOCK = threading.Lock()


def _jpeg(image):
    image.thumbnail((1536, 1536))
    output = io.BytesIO()
    image.save(output, format='JPEG', quality=85)
    return output.getvalue()


def _image(raw):
    from PIL import Image, ImageOps
    with warnings.catch_warnings():
        warnings.simplefilter('error', Image.DecompressionBombWarning)
        with Image.open(io.BytesIO(raw)) as original:
            if original.format not in ('PNG', 'JPEG') or getattr(original, 'n_frames', 1) != 1:
                raise ValueError('Use a single PNG or JPEG image')
            if original.width * original.height > MAX_PIXELS:
                raise ValueError('Image pixel limit exceeded')
            with ImageOps.exif_transpose(original).convert('RGB') as image:
                return _jpeg(image)


def _render_pdf(raw, numbers):
    # PDFium is not thread-safe. Serialize this adapter's native rendering work.
    with _PDF_RENDER_LOCK:
        return _render_pdf_locked(raw, numbers)


def _render_pdf_locked(raw, numbers):
    import pypdfium2 as pdfium
    images = {}
    with pdfium.PdfDocument(raw) as pdf:
        for number in numbers:
            page = pdf[number - 1]
            bitmap = image = None
            try:
                width, height = page.get_size()
                if not all(math.isfinite(v) and v > 0 for v in (width, height)):
                    raise ValueError('Invalid PDF page geometry')
                scale = min(2, (MAX_RENDER_PIXELS / (width * height)) ** .5) * .999
                bitmap = page.render(scale=scale)
                image = bitmap.to_pil().convert('RGB')
                images[number] = _jpeg(image)
            finally:
                if image is not None:
                    image.close()
                if bitmap is not None:
                    bitmap.close()
                page.close()
    return images


def _has_page_images(page):
    """Inspect resource dictionaries without decoding image or Form streams."""
    visited = set()
    def inspect(resources, depth=0):
        if depth > 4 or len(visited) > 256:
            return True  # Complex resources need visual inspection, never omission.
        resources = resources.get_object() if hasattr(resources, 'get_object') else resources
        objects = resources.get('/XObject', {}) if isinstance(resources, dict) else {}
        objects = objects.get_object() if hasattr(objects, 'get_object') else objects
        for item in objects.values() if isinstance(objects, dict) else []:
            item = item.get_object() if hasattr(item, 'get_object') else item
            if id(item) in visited:
                continue
            visited.add(id(item))
            if not isinstance(item, dict):
                continue
            if item.get('/Subtype') == '/Image':
                return True
            if item.get('/Subtype') == '/Form' and inspect(item.get('/Resources', {}), depth + 1):
                return True
        return False
    return inspect(page.get('/Resources', {}))


def _image_metadata(data):
    from PIL import Image
    with Image.open(io.BytesIO(data)) as image:
        return {'width': image.width, 'height': image.height, 'sha256': hashlib.sha256(data).hexdigest(),
                'mime': 'image/jpeg', 'coordinate_system': 'normalized_top_left',
                'orientation': 'rendered_display_orientation'}


def _read_pages(raw, filename, mime):
    if not isinstance(raw, bytes) or not 0 < len(raw) <= MAX_BYTES:
        raise ValueError('Record documents must contain 1 byte to 8 MB')
    if mime not in ('application/pdf', 'image/png', 'image/jpeg'):
        raise ValueError('Record extraction accepts PDF, PNG and JPEG')
    expected = {'application/pdf': ('.pdf',), 'image/png': ('.png',), 'image/jpeg': ('.jpg', '.jpeg')}
    if Path(filename).suffix.lower() not in expected[mime]:
        raise ValueError('Document extension must agree with its media type')
    if mime == 'application/pdf':
        if not raw.startswith(b'%PDF-'):
            raise ValueError('Invalid PDF signature')
        reader = PdfReader(io.BytesIO(raw))
        if reader.is_encrypted or not 1 <= len(reader.pages) <= MAX_PAGES:
            raise ValueError('Use an unencrypted PDF with 1 to 12 pages')
        pages = []
        for number, page in enumerate(reader.pages, 1):
            text = page.extract_text(extraction_mode='layout', layout_mode_space_vertically=False) or ''
            if len(text) > MAX_PAGE_TEXT:
                raise ValueError('PDF page text limit exceeded; no content was silently truncated')
            pages.append({'page': number, 'text': text, 'text_source': 'pdf_text' if text.strip() else 'none'})
        sparse = [p['page'] for p, original in zip(pages, reader.pages, strict=True)
                  if len(''.join(p['text'].split())) < 80 or _has_page_images(original)]
        images = _render_pdf(raw, sparse) if sparse else {}
    else:
        images = {1: _image(raw)}
        pages = [{'page': 1, 'text': '', 'text_source': 'none'}]
    if sum(len(p['text']) for p in pages) > MAX_TOTAL_TEXT:
        raise ValueError('Document text limit exceeded; no content was silently truncated')
    if sum(len(data) for data in images.values()) > MAX_IMAGE_BYTES:
        raise ValueError('Rendered document size limit exceeded')
    return pages, images


async def prepare_document(raw, filename, mime, telemetry, *, use_local_ocr=False):
    pages, images = await asyncio.to_thread(_read_pages, raw, filename, mime)
    ocr_status = 'not_requested' if not use_local_ocr else 'not_needed'
    if use_local_ocr and images:
        from . import local_ocr
        if not local_ocr.status()['available']:
            ocr_status = 'unavailable'
        else:
            try:
                result = await asyncio.to_thread(local_ocr.extract_document, raw, filename)
                telemetry['local_ocr'] = result['telemetry']
                for page, ocr_page in zip(pages, result['pages'], strict=True):
                    if page['page'] in images:
                        page['ocr_text'] = ocr_page['text']
                        if not page['text'].strip():
                            page.update(text=ocr_page['text'], text_source='local_teleocr')
                ocr_status = 'completed'
            except local_ocr.LocalOCRError as error:
                telemetry['local_ocr'] = error.telemetry or {'status': 'failed', 'mode': 'local-teleocr'}
                ocr_status = 'failed'
    text_sizes = [len(p['text']) + (len(p.get('ocr_text', '')) if p['text_source'] != 'local_teleocr' else 0) for p in pages]
    if any(size > MAX_PAGE_TEXT for size in text_sizes) or sum(text_sizes) > MAX_TOTAL_TEXT:
        raise ValueError('Combined source text limit exceeded')
    parts = []
    for page in pages:
        number = page['page']
        parts.append({'type': 'text', 'text': f"UNTRUSTED SOURCE PAGE {number}; transcription={page['text_source']}\n{page['text']}"})
        if page.get('ocr_text') and page['text_source'] != 'local_teleocr':
            parts.append({'type': 'text', 'text': f"UNTRUSTED LOCAL OCR FOR PAGE {number}\n{page['ocr_text']}"})
        if number in images:
            parts.append({'type': 'image_url', 'image_url': {
                'url': 'data:image/jpeg;base64,' + base64.b64encode(images[number]).decode()}})
    mode = 'pdf_text' if not images else 'pdf_text_and_vision' if any(p['text_source'] == 'pdf_text' for p in pages) else 'vision'
    return {'pages': pages, 'parts': parts, 'metadata': {
        'mode': mode, 'input_sha256': hashlib.sha256(raw).hexdigest(), 'page_count': len(pages),
        'pages': [{'page': p['page'], 'text_source': p['text_source'], 'vision_supplied': p['page'] in images,
                   'image': _image_metadata(images[p['page']]) if p['page'] in images else None} for p in pages],
        'local_ocr_status': ocr_status,
        'confidence_basis': 'model_self_report_not_calibrated',
        'bbox_basis': 'model_proposed_not_independently_located',
    }}
