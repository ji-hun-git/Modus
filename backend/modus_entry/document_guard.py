"""Bounded known-pattern screening of untrusted record text before model reuse.

This is deterministic defense in depth, not Prompt Guard, Llama Guard, content
moderation or a guarantee of injection detection. Originals and draft facts are
never rewritten here. Quarantining blocks the next model round, not record access.
"""
import hashlib
import json
import re
import unicodedata

VERSION = 'record-instruction-patterns-v1'
MAX_CHARACTERS = 128000
MAX_STRINGS = 4096
MAX_DEPTH = 24
QUARANTINED = ('This answer was paused because the retrieved record contains instruction-like text '
    'or could not be fully screened. That text was not sent to another model round. '
    'The original records and reviewed facts are unchanged; inspect them in Records.')
REQUEST_QUARANTINED = ('This request contains instruction-like text outside the record question boundary. '
    'No model request or record tool ran. Ask about recorded facts, sources or disagreements; '
    'the original records remain unchanged.')

PATTERNS = tuple((name, re.compile(pattern, re.I | re.S)) for name, pattern in (
    ('instruction_override', r'\b(?:ignore|disregard|forget|override|bypass)\b.{0,90}\b(?:previous|prior|above|system|developer|all)\b.{0,70}\b(?:instructions?|prompts?|rules?|polic(?:y|ies)|messages?)\b'),
    ('forged_chat_role', r'<\|(?:im_start|start_header_id)\|>\s*(?:system|developer|assistant)|\[INST\]|<<SYS>>|<system(?:\s|>)|<developer(?:\s|>)'),
    ('authority_reassignment', r'\byou are now\b.{0,45}\b(?:system|developer|administrator|root)\b'),
    ('executable_tool_request', r'\b(?:call|invoke|execute|run)\b.{0,65}\b(?:shell|sql|powershell|cmd\.exe|delete_records|commit_records|update_records)\b'),
    ('secret_disclosure_request', r'\b(?:reveal|print|display|show|leak|return)\b.{0,60}\b(?:api[ _-]?keys?|credentials?|system prompts?|developer prompts?|environment variables?)\b'),
    ('secret_exfiltration_request', r'\b(?:send|upload|post|forward|exfiltrate)\b.{0,80}\b(?:api[ _-]?keys?|credentials?|secrets?|system prompts?|all (?:records|files|documents))\b.{0,130}https?://'),
    ('instruction_override_ko', r'(?:이전|기존|위의|시스템|개발자).{0,35}(?:지시|명령|규칙|프롬프트).{0,35}(?:무시|우회|덮어)'),
))


def screen_untrusted(value):
    """Return metadata only. Unknown/oversized payloads fail closed for reuse."""
    report = {'version': VERSION, 'method': 'deterministic_known_patterns', 'model_executed': False,
        'status': 'passed', 'matched_rules': [], 'strings_scanned': 0, 'characters_scanned': 0,
        'coverage': 'Only listed patterns are detected; a pass is not proof that text is safe.'}
    try:
        encoded = json.dumps(value, ensure_ascii=False, sort_keys=True, allow_nan=False)
    except (ValueError, TypeError, RecursionError):
        return {**report, 'status': 'quarantined', 'matched_rules': ['unsupported_payload']}
    report['input_sha256'] = hashlib.sha256(encoded.encode('utf-8', errors='surrogatepass')).hexdigest()
    if len(encoded) > MAX_CHARACTERS:
        return {**report, 'status': 'quarantined', 'matched_rules': ['scan_budget_exceeded']}
    stack = [(value, 0)]
    found = set()
    while stack:
        item, depth = stack.pop()
        if depth > MAX_DEPTH:
            found.add('scan_depth_exceeded'); break
        if isinstance(item, dict):
            for key, child in item.items():
                stack.extend(((key, depth + 1), (child, depth + 1)))
        elif isinstance(item, (list, tuple)):
            stack.extend((child, depth + 1) for child in item)
        elif isinstance(item, str):
            report['strings_scanned'] += 1
            report['characters_scanned'] += len(item)
            if report['strings_scanned'] > MAX_STRINGS:
                found.add('scan_string_budget_exceeded'); break
            # Inspection normalization never modifies the preserved source.
            inspected = unicodedata.normalize('NFKC', item)
            inspected = ''.join(char for char in inspected if unicodedata.category(char) != 'Cf')
            found.update(name for name, pattern in PATTERNS if pattern.search(inspected))
    report['matched_rules'] = sorted(found)
    if found:
        report['status'] = 'quarantined'
    return report
