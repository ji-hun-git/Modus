"""Trusted authored demo documents, installed only when creating/resetting a demo.

This is not an import or review bypass exposed to models or HTTP clients. It
must not claim that an owner or a model reviewed the authored fixture.
"""
from copy import deepcopy
from hashlib import sha256
import json

from .record_history_models import ReviewedFact, SourceEvidence, date_information
from .temporal import instant


def insert_authored_documents(db, documents):
    for document in documents:
        draft, raw = deepcopy(document['draft']), document['raw']
        source = draft['source']
        if source.get('synthetic') is not True or sha256(raw).hexdigest() != source.get('sha256'):
            raise ValueError('Authored demo originals must be synthetic and hash-bound')
        available = instant(document['available_at'])
        facts = []
        for proposal in draft['facts']:
            fields = ReviewedFact.model_validate({key: proposal.get(key) for key in ReviewedFact.model_fields}).model_dump()
            evidence = SourceEvidence.model_validate({key: proposal.get(key) for key in SourceEvidence.model_fields}).model_dump()
            if not evidence['source_quote'] or evidence['source_quote'] not in raw.decode('utf-8-sig'):
                raise ValueError('Every authored demo fact needs a literal original excerpt')
            facts.append({**fields, **evidence, **date_information(fields['occurred_on']),
                'id': source['id'] + '-' + fields['id'], 'source_id': source['id'], 'observation_id': None,
                'available_at': available, 'availability_basis': 'authored_synthetic_timeline',
                'extractor': 'authored_seed', 'reviewer': None, 'reviewed_at': None, 'reviewed_fields': [],
                'source_proposal': {key: value for key, value in fields.items() if key != 'id'}})
        dates = [fact['date'] for fact in facts]
        source.update(available_at=available, availability_basis='authored_synthetic_timeline',
            extraction_mode='authored_seed', original_available=True,
            date=max((day for day in dates if day), default=''), source_fact_dates=dates,
            original_date=max((day for day in dates if day), default=''))
        db.execute('INSERT INTO sources(id,data,available_at) VALUES(?,?,?)', (source['id'], json.dumps(source), available))
        db.execute('INSERT INTO documents VALUES(?,?,?,?)', (source['id'], document['filename'], 'text/csv', raw))
        # Re-uploading an included example must not bill for extraction or offer
        # a save that can only fail. A closed authored proposal is not a human
        # review receipt; keep that distinction explicit in its mode/warning.
        draft.update(extraction_mode='authored_seed', warnings=[
            'This file is already in the authored demo history. No owner or model review was performed.'])
        db.execute('INSERT INTO drafts(id,data,committed) VALUES(?,?,1)', (draft['id'], json.dumps(draft)))
        for fact in facts:
            db.execute('INSERT INTO history_facts VALUES(?,?,?,?,?,?)',
                (fact['id'], source['id'], fact['kind'], fact['date'], available, json.dumps(fact)))
