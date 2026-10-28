"""Read a small OCR formatting grammar; never evaluate TeX or infer field values.

The original transcription remains the source artifact. This derived text removes
only whitelisted display wrappers and preserves explicit table row boundaries.
"""
import re


_ALIGNED = re.compile(r"\\begin\{aligned\}(.*?)\\end\{aligned\}", re.S)
_LITERAL = r"[A-Za-z0-9 \t.,:/%()\[\]\-²?]"
_TOKEN = re.compile(rf"(?P<literal>{_LITERAL}+)|\\text\{{(?P<wrapped>{_LITERAL}*)\}}|(?P<percent>\\%)")
_MARKDOWN_HEADING = re.compile(r"^\s{0,3}#{1,6}[ \t]+")


class OCRTextFormatError(ValueError):
    """Unsupported model markup is extraction failure, not empty evidence."""


def _cell_text(cell):
    cell = cell.strip()
    parts, position = [], 0
    while position < len(cell):
        match = _TOKEN.match(cell, position)
        if match is None:
            return None
        parts.append('%' if match['percent'] is not None else
                     match['wrapped'] if match['wrapped'] is not None else match['literal'])
        position = match.end()
    return ''.join(parts).strip()


def _unsupported(text):
    # Keep context words such as Reference/Instructions visible to parse_text,
    # while preventing a rejected or nested row from becoming a standalone fact.
    return '[unsupported OCR markup] ' + ' '.join(text.split())


def _plain_lines(text):
    lines = []
    for original in text.splitlines():
        line = _MARKDOWN_HEADING.sub('', original)
        stripped = line.strip()
        if stripped == '$':
            continue
        wrapped = stripped.startswith('$') and stripped.endswith('$')
        if wrapped:
            stripped = stripped[1:-1].strip()
        if wrapped or '\\' in stripped:
            decoded = _cell_text(stripped)
            if decoded is None:
                raise OCRTextFormatError('Unsupported OCR text markup')
            lines.append(decoded)
        else:
            lines.append(line)
    return lines


def _table_rows(body):
    if r'\begin{' in body or r'\end{' in body:
        raise OCRTextFormatError('Nested OCR table markup is unsupported')
    rows = []
    for row in body.split(r'\\'):
        cells = row.split('&')
        if cells and not cells[0].strip():
            cells = cells[1:]
        decoded = [_cell_text(cell) for cell in cells]
        if any(cell is None for cell in decoded):
            raise OCRTextFormatError('Unsupported OCR cell markup')
        if not cells or all(cell == '' for cell in decoded):
            continue
        if len(cells) == 4:
            rows.append(' '.join(decoded))
        else:
            # Non-four-cell rows may be section headings. They cannot supply a
            # measurement, but must still suppress reference/instruction facts.
            context = ' '.join(cell for cell in decoded if cell is not None)
            rows.append(_unsupported(context + ' ' + row))
    return rows


def normalize_ocr_text(text):
    """Preserve plain rows and decode only explicit, literal aligned-table cells.

    Unknown commands, expressions and nested/unclosed structures fail extraction;
    they are never executed or converted into a successful empty result. Missing
    cells remain missing. Repeated rows
    retain their order and multiplicity; no deduplication or date/unit repair.
    """
    matches = list(_ALIGNED.finditer(text))
    outside = _ALIGNED.sub('', text)
    if r'\begin{' in outside or r'\end{' in outside:
        raise OCRTextFormatError('Unclosed or unsupported OCR table markup')
    lines, start = [], 0
    for match in matches:
        lines.extend(_plain_lines(text[start:match.start()]))
        lines.extend(_table_rows(match[1]))
        start = match.end()
    lines.extend(_plain_lines(text[start:]))
    return '\n'.join(lines)
