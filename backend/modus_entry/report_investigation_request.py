"""Owner-bound report selection. A model never chooses or changes the pair."""
from datetime import datetime, timezone
import re

from .models import Strict
from .report_investigation_tools import REPORT_READS, prepare_reports


class ReportReadArgs(Strict):
    pass


class ReportBounds:
    read_order = REPORT_READS
    allowed_reads = frozenset(REPORT_READS)
    prompt_context = ('The owner selected exactly two reports. First call compare_selected_reports, '
        'then inspect_report_discrepancies, then select_claims. Both reads are required for a completed answer. '
        'Arguments are empty: the application owns the reports and dates. Discrepancy inspection also checks '
        'same-test, same-day companions in the captured view. Never discard a caveat or choose a winning value.')

    def validate(self, name, args, context):
        if name not in self.allowed_reads or args or not context.get('report_investigation'):
            raise ValueError('The report investigation is bound to the chosen reports and read-only operations')

    def completion(self, executed):
        if tuple(name for name, _ in executed) != self.read_order:
            raise ValueError('Both report comparison and discrepancy inspection are required')


REPORT_WORD = re.compile(r'\b(?:reports?|files?|documents?|checkups?)\b|보고서|문서|검진', re.I)
ACTION = re.compile(r'\b(?:compar\w*|investigat\w*|discrepanc\w*|disagree\w*|differ\w*|changed|changes)\b|비교|달라|바뀌|불일치|상충', re.I)
QUOTE = re.compile(r'"([^"\n]+)"|“([^”\n]+)”')
LATEST = re.compile(r'\b(?:latest|last|most recent)\s+(?:two|2)\b|최근\s*(?:두|2)', re.I)
GRAMMAR = set(('compare comparison comparing check inspect investigate investigation explain show tell me what which how '
    'has have had is are was were did do changed changes change differences difference different discrepancies discrepancy '
    'disagree disagrees disagreements conflicts and or between with to in of for from my the these those selected '
    'two 2 latest last most recent reports report files file documents document checkups checkup '
    'please can could would you their recorded values results original source sources evidence by date dates '
    '내 나의 최근 두 보고서 보고서를 문서 검진 비교 비교해줘 비교해주세요 차이 차이를 무엇이 뭐가 '
    '달라졌어 바뀌었어 바뀌었는지 알려줘 알려주세요 불일치 상충 확인해줘 그리고 설명해줘').split())


def requested_pair(context, message):
    quoted = [next(value for value in match.groups() if value is not None) for match in QUOTE.finditer(message)]
    rest = QUOTE.sub(' ', message)
    if not ACTION.search(rest) or not (REPORT_WORD.search(rest) or len(quoted) == 2):
        return None
    if not quoted and not LATEST.search(rest):
        # Preserve the existing deterministic, exact-filename checkup syntax.
        # Only an already validated plan can take this route, never a model
        # guess or a substring match that drops an owner-supplied filter.
        from .history_query import plan_for_chat
        established = plan_for_chat(context, message)
        if established and established.intent == 'two_checkup_comparison':
            return None
    if set(re.findall(r'\w+', rest.casefold())) - GRAMMAR:
        raise ValueError('I cannot apply every condition to this report comparison. Choose two files in Compare reports, or ask to compare two exact filenames in double quotes.')
    view = context['view']
    visible = [r for r in view['facts'] + view['undated_facts']
        if not r.get('value_withheld') and r.get('within_date_scope') is not False]
    source_ids = {r['source_id'] for r in visible}
    sources = [s for s in view['sources'] if s['id'] in source_ids]
    if len(quoted) == 2 and not LATEST.search(rest):
        matches = [[s['id'] for s in sources if s['title'].casefold() == title.casefold()] for title in quoted]
        if any(len(ids) != 1 for ids in matches) or matches[0] == matches[1]:
            raise ValueError('Those filenames do not identify two different, unambiguous reports in this view. Use Compare reports to choose the exact files.')
        return matches[0][0], matches[1][0]
    if not quoted and LATEST.search(rest) and not re.search(r'\bcheckups?\b|검진', rest, re.I):
        by_source = {s['id']: [r for r in visible if r['source_id'] == s['id']] for s in sources}
        today = datetime.fromisoformat(view['scope']['captured_at'].replace('Z', '+00:00')).astimezone(timezone.utc).date().isoformat()
        dated = []
        for sid, rows in by_source.items():
            dates = {r.get('date') for r in rows}
            if len(dates) != 1 or None in dates or any(r.get('date_precision', 'day') != 'day' for r in rows):
                raise ValueError('Some reports span multiple dates or have incomplete dates, so I cannot choose the latest two reliably. Choose the two files in Compare reports.')
            day = next(iter(dates))
            if day > today:
                raise ValueError('A report has a future recorded date. Choose the two files explicitly instead of letting me rank them as latest.')
            dated.append((day, sid))
        dated.sort(reverse=True)
        if len(dated) < 2:
            raise ValueError('I need two reports with visible reviewed records in this history view.')
        if dated[0][0] == dated[1][0] or len(dated) > 2 and dated[1][0] == dated[2][0]:
            raise ValueError('Several reports share a latest recorded date. Choose the exact two files in Compare reports; I will not select one copy as correct.')
        return dated[0][1], dated[1][1]
    raise ValueError('Which two reports should I compare? Use Compare reports, name two exact filenames in double quotes, or ask for your latest two reports by recorded date.')


def report_request(context, message):
    try:
        pair = requested_pair(context, message)
        if pair is None:
            return None, None
        return prepare_reports(context, pair), None
    except ValueError as error:
        return None, str(error)
