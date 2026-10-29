"""Record persistence and frozen temporal views, independent of product analysis."""
from contextlib import contextmanager
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import re
import sqlite3

from .record_conflicts import conflicts
from .record_models import Observation, ReviewedObservation
from .temporal import instant, utc_now
from .record_history_models import date_information, temporal_original_allowed


class RecordStore:
    """A separately identified store whose initial records are explicitly supplied.

    Only the full-product compatibility subclass admits its unmarked legacy
    databases. Neutral stores never migrate an unmarked or foreign database.
    """
    _allow_unmarked_store = False
    schema_version = "1"

    def __init__(self, path, *, seed_provider, application_id="modus-records-v1",
                 clock=utc_now, require_review=True, commit_event_factory=None):
        if not callable(seed_provider):
            raise TypeError("An explicit record seed provider is required")
        if not isinstance(application_id, str) or not re.fullmatch(r"[a-z][a-z0-9-]{1,63}", application_id):
            raise ValueError("Invalid record-store application identity")
        if commit_event_factory is not None and not callable(commit_event_factory):
            raise TypeError('A commit event factory must be a server-owned callable')
        self.path = str(path)
        self.clock = clock
        self.application_id = application_id
        self.require_review = require_review
        self._seed_provider = seed_provider
        self._commit_event_factory = commit_event_factory
        self._preflight_identity()
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            self._check_identity(db)
            for statement in (
                'CREATE TABLE IF NOT EXISTS record_store_meta (key TEXT PRIMARY KEY, value TEXT NOT NULL)',
                'CREATE TABLE IF NOT EXISTS sources (id TEXT PRIMARY KEY, data TEXT NOT NULL)',
                'CREATE TABLE IF NOT EXISTS observations (id TEXT PRIMARY KEY, source_id TEXT NOT NULL REFERENCES sources(id), metric TEXT NOT NULL, date TEXT NOT NULL, data TEXT NOT NULL)',
                'CREATE TABLE IF NOT EXISTS drafts (id TEXT PRIMARY KEY, data TEXT NOT NULL, committed INTEGER NOT NULL DEFAULT 0)',
                'CREATE TABLE IF NOT EXISTS documents (id TEXT PRIMARY KEY, filename TEXT NOT NULL, mime TEXT NOT NULL, raw BLOB NOT NULL)',
                'CREATE TABLE IF NOT EXISTS runs (id INTEGER PRIMARY KEY, created_at TEXT NOT NULL, data TEXT NOT NULL)',
                'CREATE TABLE IF NOT EXISTS record_commits (draft_id TEXT PRIMARY KEY REFERENCES drafts(id), data TEXT NOT NULL)',
            ):
                db.execute(statement)
            db.executemany('INSERT OR IGNORE INTO record_store_meta VALUES (?,?)',
                           [('application_id', self.application_id), ('schema_version', self.schema_version)])
            columns = {row['name'] for row in db.execute('PRAGMA table_info(sources)')}
            if 'available_at' not in columns:
                db.execute('ALTER TABLE sources ADD COLUMN available_at TEXT')
            db.execute('CREATE INDEX IF NOT EXISTS source_available ON sources(available_at)')
            db.execute('CREATE INDEX IF NOT EXISTS observation_event_source ON observations(date,source_id)')
            seeded_sources, seeded_observations = deepcopy(self._seed_provider())
            if db.execute('SELECT count(*) FROM sources').fetchone()[0] == 0:
                self._insert_seed(db, seeded_sources, seeded_observations)
            self._migrate_availability(db, seeded_sources)
            from .record_history import initialize_history
            initialize_history(db)
            self._initialize_extensions(db)

    def _check_identity(self, db):
        tables = {row[0] for row in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        if not tables:
            return
        if 'record_store_meta' not in tables:
            if self._allow_unmarked_store:
                return
            raise ValueError('Incompatible database: an explicit record-store identity is required')
        metadata = dict(db.execute('SELECT key,value FROM record_store_meta'))
        if metadata.get('application_id') != self.application_id or metadata.get('schema_version') != self.schema_version:
            raise ValueError('Incompatible database application or schema identity')

    def _preflight_identity(self):
        """Refuse foreign stores using a read-only connection, before any DDL."""
        path = Path(self.path)
        if not path.exists() or path.stat().st_size == 0:
            return
        try:
            db = sqlite3.connect(path.resolve().as_uri() + '?mode=ro', uri=True, timeout=15)
            try:
                self._check_identity(db)
            finally:
                db.close()
        except sqlite3.DatabaseError as exc:
            raise ValueError('Incompatible or unreadable record database') from exc

    def _initialize_extensions(self, db):
        """Full-product wrappers may initialize their own reference capability."""

    def _insert_seed(self, db, sources, observations):
        for source in sources:
            source.update(
                available_at=instant(source.get('available_at') or source['date'] + 'T00:00:00Z'),
                availability_basis=source.get('availability_basis') or 'authored_synthetic_timeline',
            )
            db.execute('INSERT INTO sources(id,data,available_at) VALUES (?,?,?)',
                       (source['id'], json.dumps(source), source['available_at']))
        for observation in observations:
            db.execute('INSERT INTO observations VALUES (?,?,?,?,?)',
                       (observation['id'], observation['source_id'], observation['metric'],
                        observation['date'], json.dumps(observation)))

    def _migrate_availability(self, db, seeded_sources):
        """Never infer knowledge time from a measurement date for legacy imports."""
        seeded = {source['id']: source for source in seeded_sources}
        migrated_at = instant(self.clock())
        for row in db.execute('SELECT id,data FROM sources WHERE available_at IS NULL').fetchall():
            source = json.loads(row['data'])
            candidate, basis = None, 'legacy_first_verified_at_migration'
            if source['id'] in seeded and source.get('content') == seeded[source['id']].get('content'):
                candidate = seeded[source['id']].get('available_at') or source['date'] + 'T00:00:00Z'
                basis = seeded[source['id']].get('availability_basis') or 'authored_synthetic_timeline'
            else:
                for run in db.execute('SELECT created_at,data FROM runs ORDER BY id'):
                    saved = json.loads(run['data'])
                    if saved.get('kind') == 'import' and saved.get('draft_id') == source['id']:
                        candidate, basis = run['created_at'], 'legacy_import_run'
                        break
                if candidate is None and source.get('review', {}).get('reviewed_at'):
                    candidate, basis = source['review']['reviewed_at'], 'legacy_review_audit'
            try:
                available = instant(candidate) if candidate else migrated_at
            except (ValueError, TypeError):
                available, basis = migrated_at, 'legacy_first_verified_at_migration'
            source.update(available_at=available, availability_basis=basis)
            if basis == 'legacy_first_verified_at_migration':
                source['availability_note'] = 'Earlier availability is unknown; this record is included only from its first verified migration timestamp.'
            db.execute('UPDATE sources SET data=?,available_at=? WHERE id=?',
                       (json.dumps(source), available, source['id']))

    @contextmanager
    def connect(self):
        db = sqlite3.connect(self.path, timeout=15)
        db.execute('PRAGMA foreign_keys=ON')
        db.row_factory = sqlite3.Row
        try:
            yield db
            db.commit()
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

    def _build_snapshot(self, captured_at, known_at, sources, observations):
        return RecordSnapshot(captured_at, known_at, sources, observations)

    def snapshot(self, known_at=None):
        with self.connect() as db:
            # Serialize the timestamp and eligible rows with commits. Comparison
            # callers capture once, then narrow this in-memory superset twice.
            db.execute('BEGIN IMMEDIATE')
            captured_at = instant(self.clock())
            cutoff = min(instant(known_at), captured_at) if known_at is not None else captured_at
            sources = [json.loads(row[0]) for row in db.execute(
                'SELECT data FROM sources WHERE available_at<=?', (cutoff,))]
            observations = [json.loads(row[0]) for row in db.execute(
                'SELECT o.data FROM observations o JOIN sources s ON s.id=o.source_id WHERE s.available_at<=? ORDER BY o.date,o.id',
                (cutoff,))]
            from .record_revisions import read_amendments
            amendments = read_amendments(db, cutoff)
        snapshot = self._build_snapshot(captured_at, cutoff, sources, observations)
        snapshot._amendments = amendments
        return snapshot

    def observations(self, as_of='9999-12-31', known_at=None):
        return self.snapshot(known_at).observations(as_of)

    def sources(self, as_of='9999-12-31', known_at=None):
        return self.snapshot(known_at).sources(as_of)

    def add_draft(self, draft, raw=None, filename=None, mime=None):
        draft = deepcopy(draft)
        with self.connect() as db:
            if raw is not None:
                if hashlib.sha256(raw).hexdigest() != draft['source'].get('sha256'):
                    raise ValueError('Original document hash does not match the draft')
                draft['source']['original_available'] = True
                draft['source']['ingested_at'] = instant(self.clock())
                db.execute('INSERT OR IGNORE INTO documents VALUES (?,?,?,?)',
                           (draft['source']['id'], filename, mime, raw))
            db.execute('INSERT OR IGNORE INTO drafts VALUES (?,?,0)', (draft['id'], json.dumps(draft)))
            row = db.execute('SELECT data,committed FROM drafts WHERE id=?', (draft['id'],)).fetchone()
            return {**json.loads(row['data']), 'already_committed': bool(row['committed'])}

    def draft(self, draft_id):
        with self.connect() as db:
            row = db.execute('SELECT data,committed FROM drafts WHERE id=?', (draft_id,)).fetchone()
            return {**json.loads(row['data']), 'already_committed': bool(row['committed'])} if row else None

    def document(self, source_id):
        with self.connect() as db:
            row = db.execute('SELECT filename,mime,raw FROM documents WHERE id=?', (source_id,)).fetchone()
            return dict(row) if row else None

    def _reviewed_rows(self, draft, reviewed_observations):
        if reviewed_observations is None:
            if self.require_review:
                raise ValueError('Explicit reviewed measurements are required')
            return deepcopy(draft['observations'])
        if not 1 <= len(reviewed_observations) <= 1000:
            raise ValueError('Select at least one and at most 1,000 reviewed measurements')
        proposed = {row['id']: row for row in draft['observations']}
        reviewed = [ReviewedObservation.model_validate(row).model_dump(mode='json') for row in reviewed_observations]
        ids = [row['id'] for row in reviewed]
        if len(set(ids)) != len(ids) or not set(ids) <= proposed.keys():
            raise ValueError('Reviewed measurements must have distinct IDs from this draft')
        observations = [Observation.model_validate({**proposed[row['id']], **row}).model_dump(mode='json') for row in reviewed]
        for observation in observations:
            observation['reviewed_fields'] = [key for key in ('metric', 'value', 'unit', 'date')
                                              if observation[key] != proposed[observation['id']][key]]
        return observations

    def _existing_commit_result(self, db, draft):
        receipt = db.execute('SELECT data FROM record_commits WHERE draft_id=?', (draft['id'],)).fetchone()
        if receipt:
            return {**json.loads(receipt['data']), 'inserted': 0, 'duplicate': True}
        source = db.execute('SELECT data,available_at FROM sources WHERE id=?', (draft['source']['id'],)).fetchone()
        if not source:
            raise ValueError('Committed draft has no accepted source')
        # A legacy full-product commit has no saved receipt; its own immutable
        # rows/time are recoverable, but its original disagreement set is not.
        ids = [row[0] for row in db.execute('SELECT id FROM observations WHERE source_id=? ORDER BY date,id',
                                          (draft['source']['id'],))]
        return {'inserted': 0, 'duplicate': True, 'available_at': source['available_at'],
                'source_id': draft['source']['id'], 'draft_id': draft['id'],
                'observation_ids': ids, 'affected_conflicts': []}

    def commit_draft(self, draft_id, reviewed_observations=None):
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            row = db.execute('SELECT data,committed FROM drafts WHERE id=?', (draft_id,)).fetchone()
            if not row:
                raise ValueError('Draft not found')
            draft = json.loads(row['data'])
            observations = self._reviewed_rows(draft, reviewed_observations)
            source = draft['source']
            if row['committed'] or db.execute('SELECT 1 FROM sources WHERE id=?', (source['id'],)).fetchone():
                result = self._existing_commit_result(db, draft)
                db.execute('UPDATE drafts SET committed=1 WHERE id=?', (draft_id,))
                return result
            if any(observation['source_id'] != source['id'] for observation in observations):
                raise ValueError('Proposed measurements must belong to their draft source')
            committed_at = instant(self.clock())
            source.update(available_at=committed_at, availability_basis='review_commit', committed_at=committed_at)
            broader = draft.get('facts') or draft.get('extraction_proposal', {}).get('fields')
            if broader:
                source['source_fact_dates'] = [date_information(fact.get('occurred_on'))['date'] for fact in broader]
                source['source_fact_dates'].extend(observation['date'] for observation in observations)
            if reviewed_observations is not None:
                ids = [observation['id'] for observation in observations]
                proposed_ids = {observation['id'] for observation in draft['observations']}
                source['review'] = {'reviewed_at': committed_at, 'proposed_observations': draft['observations'],
                                    'accepted_ids': ids, 'excluded_ids': sorted(proposed_ids - set(ids))}
                source['original_date'] = source['date']
                source['date'] = max(observation['date'] for observation in observations)
                if broader:
                    source['original_date'] = max([source['original_date'], source['date']] + [day for day in source['source_fact_dates'] if day])
            db.execute('INSERT INTO sources(id,data,available_at) VALUES (?,?,?)',
                       (source['id'], json.dumps(source), committed_at))
            for observation in observations:
                # Availability is always projected from the server-owned source.
                observation.pop('available_at', None)
                observation.pop('availability_basis', None)
                db.execute('INSERT INTO observations VALUES (?,?,?,?,?)',
                           (observation['id'], source['id'], observation['metric'], observation['date'], json.dumps(observation)))
            affected_rows = []
            for metric, day in sorted({(observation['metric'], observation['date']) for observation in observations}):
                affected_rows.extend(json.loads(row[0]) for row in db.execute(
                    'SELECT o.data FROM observations o JOIN sources s ON s.id=o.source_id '
                    'WHERE o.metric=? AND o.date=? AND s.available_at<=? ORDER BY o.id',
                    (metric, day, committed_at)))
            result = {'inserted': len(observations), 'duplicate': False, 'available_at': committed_at,
                      'source_id': source['id'], 'draft_id': draft_id,
                      'observation_ids': [observation['id'] for observation in observations],
                      'affected_conflicts': conflicts(affected_rows)}
            db.execute('UPDATE drafts SET committed=1 WHERE id=?', (draft_id,))
            db.execute('INSERT INTO record_commits VALUES (?,?)', (draft_id, json.dumps(result)))
            if self._commit_event_factory is not None:
                # A trusted application supplies its own event schema. Persist
                # it atomically with the rows/receipt; never pass model arguments
                # or allow the callback to change the returned receipt.
                event = self._commit_event_factory(deepcopy(result))
                if not isinstance(event, dict):
                    raise TypeError('A commit event factory must return an object')
                db.execute('INSERT INTO runs(created_at,data) VALUES (?,?)',
                           (committed_at, json.dumps(event)))
            return result

    def save_run(self, result):
        with self.connect() as db:
            cursor = db.execute('INSERT INTO runs(created_at,data) VALUES (?,?)', (instant(self.clock()), json.dumps(result)))
            return cursor.lastrowid

    def history(self, known_at=None):
        cutoff = instant(known_at if known_at is not None else self.clock())
        with self.connect() as db:
            rows = [row for row in db.execute('SELECT * FROM runs ORDER BY id DESC') if instant(row['created_at']) <= cutoff][:30]
            return [{'id': row['id'], 'created_at': row['created_at'], **json.loads(row['data'])} for row in rows]

    def reset(self):
        self._preflight_identity()
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            self._check_identity(db)
            from .record_history import reset_history
            reset_history(db)
            for table in ('record_commits', 'observations', 'sources', 'drafts', 'documents', 'runs'):
                db.execute('DELETE FROM ' + table)
            self._insert_seed(db, *deepcopy(self._seed_provider()))


class RecordSnapshot:
    """Frozen record values with read/narrow capabilities and no store handle."""
    def __init__(self, captured_at, known_at, sources, observations):
        self.captured_at = instant(captured_at)
        self.known_at = instant(known_at)
        if self.known_at > self.captured_at:
            raise ValueError('A record scope cannot extend beyond its capture')
        self._sources = {source['id']: deepcopy(source) for source in sources}
        self._amendments = []
        self._observations = [
            {**deepcopy(observation), 'available_at': self._sources[observation['source_id']]['available_at'],
             'availability_basis': self._sources[observation['source_id']]['availability_basis']}
            for observation in observations
        ]

    def snapshot(self, known_at=None):
        if known_at is not None and instant(known_at) != self.known_at:
            raise ValueError('A frozen evidence scope cannot be changed')
        return self

    def _derive_snapshot(self, known_at, sources, observations):
        return RecordSnapshot(self.captured_at, known_at, sources, observations)

    def narrow(self, known_at=None):
        cutoff = min(instant(known_at), self.known_at) if known_at is not None else self.known_at
        sources = [source for source in self._sources.values() if source['available_at'] <= cutoff]
        ids = {source['id'] for source in sources}
        result = self._derive_snapshot(cutoff, sources, [row for row in self._observations if row['source_id'] in ids])
        result._amendments = deepcopy([row for row in self._amendments if row['available_at'] <= cutoff and row['source_id'] in ids])
        return result

    def observations(self, as_of='9999-12-31'):
        from .record_revisions import revised_observations
        rows = [observation for observation in revised_observations(self._observations, self._amendments, self.known_at) if observation['date'] <= as_of]
        for observation in rows:
            source = self._sources[observation['source_id']]
            partial = not temporal_original_allowed(source, as_of)
            observation['source_span_withheld'] = partial
            if partial:
                # An uploaded/model-proposed span may quote several dated rows.
                # Do not let it bypass the full-original projection boundary.
                observation['source_span'] = 'Original excerpt withheld because the full document is outside this measurement-date scope.'
                observation.pop('fhir_provenance', None)
        return rows

    def sources(self, as_of='9999-12-31'):
        visible = {}
        for observation in self.observations(as_of):
            visible.setdefault(observation['source_id'], []).append(observation)
        sources = []
        for source in self._sources.values():
            if temporal_original_allowed(source, as_of):
                sources.append(deepcopy(source))
            elif source['id'] in visible:
                observations = visible[source['id']]
                projected = {key: deepcopy(value) for key, value in source.items() if key not in {'review', 'extraction_telemetry', 'ocr_pages', 'ocr_execution'}}
                sources.append({**projected, 'original_available': False,
                    'original_date': max(source['date'], source.get('original_date', source['date'])),
                    'date': max(observation['date'] for observation in observations), 'historical_projection': True,
                    'content': 'Historical view: observations through ' + as_of + '\n' + '\n'.join(
                        f"{observation['date']}: {observation['metric']} {observation['value']} {observation['unit']}"
                        for observation in observations)})
        return sorted(sources, key=lambda source: source['date'], reverse=True)
