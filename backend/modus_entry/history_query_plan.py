"""Compositional, read-only plans for recorded measurements.

Names come from the fixed alias vocabulary or exact visible labels. Parsing
never calculates results. Unconsumed restrictions require clarification; the
optional Muse interpreter cannot replace the numeric/date/name anchors.
"""
from datetime import date
from decimal import Decimal
import re
from typing import Literal

from pydantic import Field, field_validator, model_validator

from .models import Strict
from .medical_terms import TERMS, ambiguous_request, normalize
from .comparison_rules import test_key

VERSION = 'record-query-plan-v1'
Intent = Literal['latest_observation', 'historical_observations', 'threshold_observation',
    'longitudinal_history', 'first_last_comparison', 'source_inspection',
    'two_checkup_comparison', 'clarification', 'unsupported']
NUMBER = r'[+-]?(?:\d{1,30}(?:\.\d{1,20})?|\.\d{1,20})'


class Condition(Strict):
    operator: Literal['lt', 'lte', 'gt', 'gte', 'eq']
    value: str = Field(strict=True, pattern=rf'^{NUMBER}$')
    unit: str | None = Field(default=None, strict=True, min_length=1, max_length=80)

    @field_validator('value')
    @classmethod
    def finite(cls, value):
        if not Decimal(value).is_finite():
            raise ValueError('Finite literal thresholds only')
        return value


class QueryPlan(Strict):
    intent: Intent
    metric: str | None = Field(default=None, strict=True, max_length=240)
    condition: Condition | None = None
    selection: Literal['latest', 'earliest', 'count', 'all'] = 'all'
    start_date: str | None = None
    end_date: str | None = None
    exclusive_before: str | None = None
    exclusive_after: str | None = None
    source_ids: list[str] = Field(default_factory=list, max_length=2)
    fact_id: str | None = Field(default=None, strict=True, max_length=160)
    time_basis: Literal['occurrence'] = 'occurrence'
    evidence_required: Literal[True] = True
    reason: str | None = Field(default=None, strict=True, max_length=80)
    question: str | None = Field(default=None, strict=True, max_length=500)

    @field_validator('start_date', 'end_date', 'exclusive_before', 'exclusive_after')
    @classmethod
    def full_dates(cls, value):
        if value is not None:
            if not isinstance(value, str) or not re.fullmatch(r'\d{4}-\d{2}-\d{2}', value):
                raise ValueError('Use a full recorded date')
            date.fromisoformat(value)
        return value

    @field_validator('evidence_required', mode='before')
    @classmethod
    def actual_true(cls, value):
        if value is not True:
            raise ValueError('Evidence cannot be disabled or numerically coerced')
        return value

    @model_validator(mode='after')
    def bounded_shape(self):
        if self.metric is not None and not re.fullmatch(r'(?:concept|literal):.{1,220}', self.metric):
            raise ValueError('A resolved recorded test is required')
        if self.intent == 'threshold_observation' and (not self.metric or self.condition is None):
            raise ValueError('Threshold plans need a test and condition')
        if self.condition is not None and self.intent != 'threshold_observation':
            raise ValueError('Do not discard or apply an undeclared condition')
        if self.intent not in {'clarification', 'unsupported', 'two_checkup_comparison', 'source_inspection'} and not self.metric:
            raise ValueError('A recorded measurement is required')
        if self.start_date and self.end_date and self.start_date > self.end_date:
            raise ValueError('Reversed date interval')
        if self.exclusive_after and self.exclusive_before and self.exclusive_after >= self.exclusive_before:
            raise ValueError('Empty date interval')
        if len(set(self.source_ids)) != len(self.source_ids):
            raise ValueError('Two distinct reports are required')
        if self.intent != 'two_checkup_comparison' and self.source_ids:
            raise ValueError('Source selection only belongs to a report comparison')
        return self


def clarify(reason, question):
    return QueryPlan(intent='clarification', reason=reason, question=question)


# Operations are independent of the chosen metric and of sentence order.
OPERATORS = (
    ('lte', r'no more than|not (?:greater|more) than|less than or equal to|at most|<=|≤'),
    ('gte', r'no less than|not (?:less|lower) than|greater than or equal to|at least|>=|≥'),
    ('lt', r'less than|lower than|below|under|<'),
    ('gt', r'greater than|higher than|more than|above|over(?!\s+time)|>'),
    ('eq', r'equal to|equals?|exactly|(?:reading|value) of|='),
)
OP_PATTERN = re.compile(r'(?<!\w)(?P<operator>' + '|'.join('(?:'+p+')' for _, p in OPERATORS)
    + r')\s*(?P<value>'+NUMBER+r')(?!\d|\.\d)', re.I)
UNIT_PATTERN = re.compile(r'\s*([%]|[A-Za-zµμ][A-Za-z0-9µμ%^.*\[\]-]*(?:\s*/\s*[A-Za-z0-9µμ^.*\[\]-]+)+|mmHg|bpm|mIU|IU|U)(?=\s|[?.,!]|$)')
BARE_VALUE = re.compile(r'\s+(?:(?:of|at|was|were|is)\s+)?(?P<value>'+NUMBER+r')(?!\d|\.\d)', re.I)
CLINICAL = re.compile(r'\b(?:diagnos(?:e|ing)|treat(?:ment|ments)?|advice|recommend\w*|should|'
    r'interpret\w*|normal|abnormal|healthy|dangerous|risk|caus\w*|improv\w*|worsen\w*|'
    r'prognos\w*|predict\w*|prescribe|triage|disease|supplements?|dosage)\b|'
    r'\b(?:am i|do i have|what does .{0,60} mean|why)\b|'
    r'진단해|치료|추천|권장|해석|정상|비정상|위험|원인', re.I)
FORBIDDEN = re.compile(r'\b(?:delete|overwrite|edit|replace|merge|insert|commit|send|upload|'
    r'execute|shell|sql|permissions?|ignore|bypass|override|widen|backdate)\b|'
    r'\b(?:another|different|other) (?:person|profile|user)\b|https?://|삭제|수정|권한|무시', re.I)
LATEST = re.compile(r'\b(?:latest|last|most recent|newest)\b', re.I)
EARLIEST = re.compile(r'\b(?:earliest|first|oldest)\b', re.I)
COUNT = re.compile(r'\b(?:count|how many|number of|total)\b', re.I)
CHANGE = re.compile(r'\b(?:chang(?:e|ed|es)|compare|comparison|difference|trend|over time|across|longitudinal)\b', re.I)
SOURCE = re.compile(r'\b(?:where.*(?:come from|source)|source|original|evidence)\b', re.I)
DATE_WORD = re.compile(r'\b(?:before|after|since|until|through|during|between|on|in)\s+(\d{4}(?:-\d{2}(?:-\d{2})?)?)\b', re.I)
MONTH = re.compile(r'\b(?:january|february|march|april|may|june|july|august|september|october|november|december)\b', re.I)
FILLER = frozenset(('please can could would you i me my mine the a an of for to from '
    'is was were are has have had did do does it its be been ever when what which '
    'how show list find search retrieve locate look up pull bring tell give get '
    'record recorded records result results measurement measurements test tests '
    'value values reading readings level levels lab labs history historical '
    'checkup checkups visit visits report reports time over across throughout '
    'latest last most recent newest earliest first oldest previous earlier '
    'count many number total all any matching match than at and between '
    'change changed changes compare comparison difference trend longitudinal '
    'come source original evidence where in on through since until').split())
# Model interpretation is allowed for conversational paraphrases, never for
# unknown source names, collection contexts or assay qualifiers. These words
# carry no new record filter. The model may still abstain.
SEMANTIC_WORDS = frozenset('walk talk take outline trace recap summarize sketch journey path trajectory progression evolution chronicle track recall'.split())


def _mask(text, spans):
    result = list(text)
    for start, end in spans:
        result[start:end] = ' ' * (end-start)
    return ''.join(result)


def metric_mentions(context, text):
    """Longest name wins; dynamic exact labels extend beyond the vocabulary."""
    options = [(f"concept:{t['id']}", alias) for t in TERMS for alias in t['aliases']]
    for row in context['view']['facts'] + context['view']['undated_facts']:
        if row['kind'] == 'measurement' and not row.get('value_withheld') and row.get('within_date_scope', True):
            _, typ, name = test_key(row)
            options.append((typ+':'+name, row['label']))
    matches = []
    for key, alias in set(options):
        # Whitespace / hyphens in ordinary aliases are equivalent, while literal
        # punctuation in a qualified assay name stays part of that name.
        pattern = re.escape(alias).replace(r'\ ', r'[\s-]+')
        for found in re.finditer(r'(?<!\w)'+pattern+r'(?!\w)', text, re.I):
            matches.append((found.start(), found.end(), key))
    chosen = []
    for item in sorted(matches, key=lambda x: (x[0]-x[1], x[0], x[2])):
        if not any(item[0] < b and a < item[1] for a, b, _ in chosen):
            chosen.append(item)
    return sorted(chosen)


def _dates(text):
    fields, spans = {}, []
    for match in DATE_WORD.finditer(text):
        token = match[1]
        prep = match[0].split()[0].lower()
        try:
            if len(token) == 4 and prep in {'in', 'during'}:
                values = {'start_date': token+'-01-01', 'end_date': token+'-12-31'}
            elif len(token) == 10:
                date.fromisoformat(token)
                values = ({'exclusive_before':token} if prep=='before' else
                    {'exclusive_after':token} if prep=='after' else
                    {'start_date':token} if prep=='since' else
                    {'end_date':token} if prep in {'until','through'} else
                    {'start_date':token,'end_date':token} if prep=='on' else None)
            else:
                values = None
            if not values or fields.keys() & values.keys():
                raise ValueError('Ambiguous recorded date')
            fields.update(values)
            spans.append(match.span())
        except ValueError:
            return None, []
    return fields, spans


def interpret(context, message, *, allow_unfamiliar_wording=False):
    """Return a validated plan, a fixed clarification, or defer to legacy reads.

    Even the Muse fallback uses the same anchors. Unknown filtering clauses
    cannot disappear into a model prompt.
    """
    text = ' '.join(message.translate(str.maketrans({'“':'"','”':'"'})).split())
    mentioned = metric_mentions(context, text)
    keys = {key for _, _, key in mentioned}
    operation = OP_PATTERN.search(text) or CHANGE.search(text) or SOURCE.search(text)
    if CLINICAL.search(text) and (keys or operation or re.search(r'\bhealth|medicine|medication|diagnos', text, re.I)):
        return QueryPlan(intent='unsupported', reason='clinical_interpretation', question=
            'I can show and compare recorded values with their sources. I cannot interpret what they mean for your health, diagnose, or recommend treatment.')
    if FORBIDDEN.search(text):
        return None  # Existing request guard remains authoritative for forbidden actions.
    if re.search(r'\bcompare\b.*\b(?:two|2)\b.*\b(?:reports?|checkups?)\b', text, re.I) and not keys:
        found = [s['id'] for s in context['view']['sources'] if s.get('title')
            and re.search(r'(?<![\w.-])'+re.escape(s['title'])+r'(?![\w.-])', text, re.I)]
        # Never guess a visit or equate two arbitrary files with two checkups.
        if len(found) != 2:
            return clarify('report_pair', 'Which two reports should I compare? Choose two files in Records → Compare, or include both exact file names.')
        return QueryPlan(intent='two_checkup_comparison', source_ids=found)
    if re.search(r'\b(?:blood pressure|bp)\b|혈압', text, re.I) and operation:
        if not re.search(r'\b(?:systolic|diastolic|top number|bottom number)\b|수축기|이완기', text, re.I):
            return clarify('pressure_component', 'Do you mean the top number (systolic) or the bottom number (diastolic) of your blood pressure?')
    if not keys:
        if SOURCE.search(text) and re.search(r'\b(?:this|that) (?:value|result|record)\b', text, re.I):
            return clarify('source_subject', 'Which saved result do you mean? Name the test and date, or open a result’s Source button.')
        if re.search(r'\b(?:result|value)\b.*\bbefore\b', text, re.I):
            return clarify('measurement_and_date', 'Which test and date do you mean? Include a year and full date, for example “Ferritin before 2025-10-01”.')
        return None
    ambiguous = ambiguous_request(text)
    if ambiguous:
        return clarify('measurement', ambiguous['question'])
    if len(keys) != 1:
        # Existing bounded compound investigation can handle separate named reads.
        if not operation:
            return None
        return clarify('measurement', 'Which single recorded test should I use? Separate tests are not interchangeable.')
    metric = next(iter(keys))
    if metric == 'concept:glucose' and any(test_key(r)[2] == 'fasting_glucose' for r in context['view']['facts'] + context['view']['undated_facts']):
        return clarify('glucose_test', 'Which glucose test do you mean: Glucose or Fasting glucose? They remain separate recorded tests.')
    remaining = _mask(text, [(a,b) for a,b,_ in mentioned])
    # Leave established conflict/availability/compound read paths intact.
    if re.search(r'\b(?:conflicts?|disagreements?|arrived|added|available|snapshots?)\b', remaining, re.I):
        return None
    conditions = list(OP_PATTERN.finditer(remaining))
    date_fields, date_spans = _dates(remaining)
    if date_fields is None or MONTH.search(remaining):
        return clarify('date', 'Please use a full recorded date with a year (YYYY-MM-DD). I will keep your current availability view.')
    if len(conditions) > 1:
        return clarify('multiple_conditions', 'Please use one numeric condition at a time; I will not drop any of your conditions.')
    # "When was my Ferritin 30 ng/mL?" has a literal equality anchor. Require
    # one named test and a printed unit; an unqualified number might be a year.
    # All remaining words still pass the same date/filter/negation checks below.
    implicit = None
    if not conditions and len(mentioned) == 1 and re.match(r'^(?:please\s+)?when\b', text, re.I):
        candidate = BARE_VALUE.match(remaining, mentioned[0][1])
        if candidate and UNIT_PATTERN.match(remaining[candidate.end():]):
            implicit = candidate
    numeric = None
    spans = list(date_spans)
    if conditions or implicit:
        match = conditions[0] if conditions else implicit
        operator = next(key for key, pattern in OPERATORS if re.fullmatch(pattern, match['operator'], re.I)) if conditions else 'eq'
        tail = remaining[match.end():]
        # Unit spelling is literal, case-sensitive in execution; no conversion.
        unit = None
        unit_match = UNIT_PATTERN.match(tail)
        end = match.end()
        if unit_match:
            unit = unit_match[1].strip().rstrip('.')
            end += unit_match.end()
        numeric = Condition(operator=operator, value=match['value'], unit=unit)
        spans.append((match.start(), end))
    reduced = _mask(remaining, spans)
    # Negations, extra quantities, source/assay qualifiers and relative dates
    # are not conversational filler. They must not widen the requested read.
    if re.search(r'\b(?:not|never|without|except|excluding|only|during|while|before|after|between|if|unless|last year|last month|today|yesterday)\b|[<>≤≥=\d]|["\']|\b(?:method|specimen|fasting|lab at|clinic|hospital)\b', reduced, re.I):
        return clarify('unapplied_filter', 'I need that condition stated more precisely. Use one test, one numeric comparison and optional full recorded dates; source or method filters need the Records view.')
    selection = 'count' if COUNT.search(reduced) else 'latest' if LATEST.search(reduced) else 'earliest' if EARLIEST.search(reduced) else 'all'
    if (COUNT.search(reduced) and (LATEST.search(reduced) or EARLIEST.search(reduced))
            or numeric and EARLIEST.search(reduced) and LATEST.search(reduced)):
        return clarify('multiple_tasks', 'Please choose one selection: earliest, latest, count, or all matching records. I will not silently drop a requested selection.')
    if numeric:
        intent = 'threshold_observation'
    elif EARLIEST.search(reduced) and LATEST.search(reduced):
        intent, selection = 'first_last_comparison', 'all'
    elif SOURCE.search(reduced):
        intent = 'source_inspection'
    elif CHANGE.search(reduced):
        intent, selection = 'longitudinal_history', 'all'
    elif selection == 'latest':
        intent = 'latest_observation'
    else:
        intent = 'historical_observations'
    # Compound tasks must not be reduced to the first recognized operator.
    if numeric and CHANGE.search(reduced) or re.search(r'\b(?:and|then|also)\s+(?:show|find|list|compare|count|explain)\b', reduced, re.I):
        return clarify('multiple_tasks', 'Please ask one recorded-value operation at a time so every condition can be applied exactly.')
    words = set(re.findall(r'[A-Za-z]+', reduced.lower()))
    unknown = words - FILLER
    if allow_unfamiliar_wording and unknown - SEMANTIC_WORDS:
        return clarify('unapplied_filter', 'I cannot safely apply the extra wording or restriction. Please state one test and condition, or use the Records filters.')
    if unknown and not allow_unfamiliar_wording:
        # Ordinary existing literal searches retain all words in their retriever.
        if not operation and numeric is None and selection == 'all' and not date_fields:
            return None
        return clarify('unfamiliar_wording', 'I could not map the wording reliably offline. Please name the recorded test and ask for its history, latest result, or one numeric comparison.')
    try:
        return QueryPlan(intent=intent, metric=metric, condition=numeric, selection=selection, **date_fields)
    except ValueError:
        return clarify('date', 'Those recorded-date bounds conflict. Please give one valid date interval.')


def validate_model_plan(context, message, proposed):
    """Validate semantics against code-extracted anchors before any tool runs."""
    candidate = QueryPlan.model_validate(proposed)
    expected = interpret(context, message, allow_unfamiliar_wording=True)
    if expected is None or expected.intent in {'clarification','unsupported'}:
        raise ValueError('No safely anchored operation')
    # No model-selected metric, number, unit, date, scope, source or code path.
    if candidate.model_dump() != expected.model_dump():
        raise ValueError('The model changed the anchored record operation')
    return candidate
