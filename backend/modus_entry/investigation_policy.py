"""Code-owned read capabilities for a bounded factual history investigation."""
from dataclasses import dataclass
import re
from typing import Literal

from .models import Strict
from .medical_terms import mentions, unquoted, normalize
from .record_topics import mentions as topic_mentions


MAX_READS = 3
MAX_RESPONSES = 4
READ_NAMES = frozenset({'history_inventory', 'search_history_evidence',
    'history_conflicts', 'compare_history_snapshots', 'latest_history_match'})


class ClarificationArgs(Strict):
    reason: Literal['record_name', 'record_type', 'comparison_date', 'unsupported_filter']


CLARIFICATIONS = {
    'record_name': 'Which recorded name or phrase should I look for? You can copy it from a report.',
    'record_type': 'Which part of your history should I look through: measurements, visits, prescriptions, vaccinations, procedures, or report text?',
    'comparison_date': 'Choose an earlier file-availability date before asking which records were added or corrected.',
    'unsupported_filter': 'I cannot apply every condition in that question exactly. Please use a recorded name or phrase and the date controls.',
}


def clarification(reason):
    return {'kind': 'record_investigation', 'reason': reason,
            'question': CLARIFICATIONS[reason], 'choices': []}


def words(text):
    return set(re.findall(r'\w+', text.casefold(), re.UNICODE))


GRAMMAR = words('show list find search retrieve look up what which when was were is are did do i have could would you your has been '
    'my me the their a an all whole medical health recorded records record history histories reports report had ever got get tell about pull bring '
    'entries sources source documents document available in between these views snapshots '
    'please of for from to and then also check inspect give get with latest last most recent '
    'count how many number total conflicts conflict disagreements disagreement compare '
    'added arrived newly became changed changes values value readings reading results result '
    'measurements measurement lab laboratory tests test visits visit encounters encounter '
    'appointments appointment prescriptions prescription medications medication medicines medicine '
    'prescribed vaccinations vaccination vaccines vaccine immunizations immunization '
    'immunisations immunisation diagnoses diagnosis procedures procedure imaging radiology text notes '
    '보여줘 보여주세요 찾아줘 찾아주세요 내 나의 모든 전체 기록 내역 보고서 문서 목록 알려줘 '
    '있나요 있어 그리고 또한 검사 결과 측정 진료 방문 내원 처방 약물 예방접종 접종 시술 수술 판독문 '
    '영상 기타 불일치 상충 충돌 최근 마지막 언제')
UNSUPPORTED_FILTER = re.compile(r'\b(?:except|excluding|without|not|never|above|below|greater|less|'
    r'average|mean|median|highest|lowest|before|after|since|until|earlier than|later than)\b|'
    r'[<>≤≥]|제외|빼고|이상|이하|평균', re.I)
LATEST = re.compile(r'\b(?:last|latest|most recent)\b|최근|마지막', re.I)
COMPOUND = re.compile(r'\b(?:and|then|also)\b|그리고|또한', re.I)
NUMERIC_LITERAL = re.compile(r'(?<!\w)[+-]?\d+(?:[./:-]\d+)*(?!\w)')
QUOTED_FILTER = re.compile(r'''(?:(?:source|title|document|from)\s*:?\s*)?(?:"[^"\n]+"|(?<!\w)'[^'\n]+'(?!\w)|“[^”\n]+”|‘[^’\n]+’)''', re.I)


@dataclass(frozen=True)
class RequestBounds:
    message: str
    kinds: frozenset[str]
    labels: frozenset[str]
    terms: frozenset[str]
    numbers: frozenset[str]
    phrases: tuple[str, ...]
    wants_conflicts: bool
    wants_comparison: bool
    wants_inventory: bool
    wants_latest: bool

    def validate(self, name, args, context):
        if name not in READ_NAMES:
            raise ValueError('Investigation tool is not permitted')
        if self.kinds and args.get('kind') not in self.kinds:
            raise ValueError('The model dropped or changed a requested record type')
        if name == 'compare_history_snapshots':
            if not self.wants_comparison or context.get('comparison') is None:
                raise ValueError('Availability comparison was not bound by the owner')
        if name == 'history_conflicts' and not self.wants_conflicts:
            raise ValueError('A discrepancy check was not requested')
        if name == 'latest_history_match' and not self.wants_latest:
            raise ValueError('A latest-record lookup was not requested')
        if name in {'search_history_evidence', 'latest_history_match'}:
            query = args['query']
            if not words(query) <= words(self.message):
                raise ValueError('The model invented a search term')
            # A bounded rewrite may remove grammar, but never dates, quantities,
            # quoted phrases or source restrictions present in the request.
            if not self.numbers <= set(NUMERIC_LITERAL.findall(query)):
                raise ValueError('The model dropped a numeric or date qualifier')
            if any(phrase.casefold() not in query.casefold() for phrase in self.phrases):
                raise ValueError('The model dropped a quoted/source qualifier')
            if not (words(query) - GRAMMAR) and not (name == 'latest_history_match' and self.kinds and not self.terms and not self.labels):
                raise ValueError('A literal search requires a named term')
            label_words = set().union(*(words(label) for label in self.labels))
            if not (self.terms - label_words) <= words(query):
                raise ValueError('The model dropped a literal request qualifier')
            if self.labels and not any(normalize(label) in normalize(query) for label in self.labels):
                raise ValueError('The model dropped the recorded name')
            if len(self.labels) > 1 and len(self.addressed_labels(args)) != 1:
                raise ValueError('Separate named records require separate literal reads')
        else:
            label = args.get('label')
            if label and (not words(label) <= words(self.message) or not (words(label) - GRAMMAR)):
                raise ValueError('An exact label must be grounded in the owner request')
            if self.terms and not label:
                raise ValueError('A broad read would drop a named filter')
            if label and not self.terms <= words(label):
                # Multiple explicit labels may be investigated separately.
                if label.casefold() not in {item.casefold() for item in self.labels}:
                    raise ValueError('The exact-label tool cannot represent all requested filters')
            if self.numbers or self.phrases:
                raise ValueError('This tool cannot represent the requested date or source qualifier')
            if name == 'history_inventory' and args.get('offset', 0) != 0:
                raise ValueError('Investigation reads start at the first bounded page')

    def addressed_labels(self, args):
        target = str(args.get('label') or args.get('query') or '')
        return {label for label in self.labels if re.search(r'(?<!\w)' + re.escape(normalize(label)) + r'(?!\w)', normalize(target))}

    def requirements(self):
        operations = set()
        if self.wants_latest:
            operations.add('latest_history_match')
        elif self.wants_inventory:
            operations.add('lookup')
        if self.wants_conflicts:
            operations.add('history_conflicts')
        if self.wants_comparison:
            operations.add('compare_history_snapshots')
        return {(kind, label, operation) for kind in self.kinds or {None}
                for label in self.labels or {None} for operation in operations}

    def completion(self, executed):
        covered = set()
        for name, args in executed:
            operation = 'lookup' if name in {'history_inventory', 'search_history_evidence'} else name
            for label in self.addressed_labels(args) if self.labels else {None}:
                covered.add((args.get('kind'), label, operation))
        if not self.requirements() <= covered:
            raise ValueError('The investigation did not cover every requested record type, label and task')


def request_bounds(context, message, kind_patterns, conflict_pattern, arrival_pattern):
    text = re.sub(r'"[^"\n]*"|“[^”\n]*”', '', message)
    filter_text, named_terms = mentions(text)
    for start, end, _, _ in reversed(named_terms):
        filter_text = filter_text[:start] + ' ' * (end-start) + filter_text[end:]
    if UNSUPPORTED_FILTER.search(filter_text):
        return None
    kinds = frozenset(kind for kind, pattern in kind_patterns.items() if re.search(pattern, text, re.I))
    visible_labels = {row['label'] for row in context['view']['facts'] + context['view']['undated_facts']
        if not row.get('value_withheld') and row.get('within_date_scope', True)}
    # A lifetime of repeated tests should not re-run the same label regex once
    # per observation. Scope eligibility is checked before deduplicating names.
    labels = frozenset(label for label in visible_labels
        if re.search(r'(?<!\w)' + re.escape(label) + r'(?!\w)', message, re.I))
    # Keep the owner's phrase as the request subject. Only the retrieval tool,
    # never the planner, expands a code-owned alias to recorded labels.
    if not labels:
        _, named = mentions(unquoted(message))
        named += topic_mentions(unquoted(message))[1]
        labels = frozenset(phrase for _, _, _, phrase in named)
    phrases = tuple(match[0] for match in QUOTED_FILTER.finditer(message))
    numeric = frozenset(NUMERIC_LITERAL.findall(message))
    wants_latest = bool(LATEST.search(text))
    # Numeric matching requires a typed comparator, not lexical co-occurrence.
    # The existing blood-pressure route is handled before this generic flow.
    if wants_latest and numeric:
        return None
    wants_conflicts = bool(conflict_pattern.search(text))
    wants_comparison = bool(arrival_pattern.search(text))
    if re.search(r'\bcompare\b', text, re.I) and not wants_comparison:
        return None
    wants_inventory = bool(re.search(r'\b(?:show|list|find|search|retrieve|look up|count|how many|when)\b|보여|찾|몇|언제', text, re.I))
    if not wants_conflicts and not wants_comparison:
        wants_inventory |= bool(re.search(r'\b(?:what|which)\b', text, re.I))
    if wants_conflicts and not wants_comparison:
        before_conflict = text[:conflict_pattern.search(text).start()]
        # "Show conflicts for A and B" requests only discrepancies. An earlier
        # record lookup plus "and ... conflicts" requests both for each subject.
        prefix_subject = any(re.search(r'(?<!\w)' + re.escape(label) + r'(?!\w)', before_conflict, re.I) for label in labels)
        prefix_subject |= any(re.search(pattern, before_conflict, re.I) for pattern in kind_patterns.values())
        prefix_count = bool(re.search(r'\b(?:count|how many|number of|total)\b|몇|개수', before_conflict, re.I))
        wants_inventory = bool(re.search(r'\b(?:records?|histories|history|values?|readings?|results?)\b', before_conflict, re.I)
            or (COMPOUND.search(before_conflict) and (prefix_subject or prefix_count)))
    bounds = RequestBounds(message, kinds, labels, frozenset(words(message) - GRAMMAR), numeric, phrases,
        wants_conflicts, wants_comparison, wants_inventory,
        wants_latest)
    return bounds if 0 < len(bounds.requirements()) <= MAX_READS else None
