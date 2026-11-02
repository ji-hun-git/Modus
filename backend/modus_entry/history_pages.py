"""Bounded pages over immutable, scope-bound history captures. No model access."""
from collections import OrderedDict, defaultdict
from copy import deepcopy
from threading import RLock
from time import monotonic
from uuid import uuid4

from modus.record_history_view import history_views
from modus.temporal import instant
from .history_retrieval import plan, retrieve
from .checkup_comparison import compare_checkups


class SnapshotExpired(ValueError):
    pass


class HistoryPages:
    MAX_SNAPSHOTS = 4
    MAX_BYTES = 48 * 1024 * 1024
    TTL = 600

    def __init__(self, store):
        self.store = store
        self.lock = RLock()
        self.captures = OrderedDict()
        self.keys = {}

    def _key(self, as_of, known_at):
        with self.store.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            now = instant(self.store.clock())
            cutoff = min(instant(known_at), now) if known_at else now
            revision = db.execute("SELECT value FROM record_store_meta WHERE key='history_revision'").fetchone()[0]
            # Future authored records can become eligible without a write.
            frontier = db.execute('SELECT max(t) FROM (SELECT available_at t FROM sources UNION ALL '
                'SELECT available_at FROM history_facts UNION ALL SELECT available_at FROM history_amendments '
                'UNION ALL SELECT updated_at FROM history_profiles) WHERE t<=?', (cutoff,)).fetchone()[0]
        return (revision, as_of, cutoff if known_at else ('latest', frontier)), cutoff

    def _expire(self):
        for token, item in list(self.captures.items()):
            if monotonic() - item['created'] > self.TTL:
                del self.captures[token]
        self.keys = {k: token for k, token in self.keys.items() if token in self.captures}

    def open(self, as_of=None, known_at=None):
        # Single-flight construction prevents simultaneous clients from each
        # projecting thousands of rows. Only bounded captures are retained.
        with self.lock:
            self._expire()
            key, cutoff = self._key(as_of, known_at)
            if key in self.keys:
                token = self.keys[key]
                self.captures.move_to_end(token)
                return token, self.captures[token]
            views, revision = history_views(self.store, as_of, (cutoff,), include_revision=True)
            view = views[0]
            token = uuid4().hex
            rows = view['facts'] + view['undated_facts']
            by_source = defaultdict(list)
            field_counts = defaultdict(int)
            facilities = set()
            for row in rows:
                by_source[row['source_id']].append(row)
                field_counts[(row['kind'], row['label'])] += 1
                if row.get('facility'):
                    facilities.add(row['facility'])
            sources = []
            for source in view['sources']:
                facts = by_source[source['id']]
                dates = sorted(row['date'] for row in facts if row.get('date'))
                labels = {row['label'] for row in facts}
                kinds = {row['kind'] for row in facts}
                sources.append({**source, 'fact_count': len(facts), 'latest_date': dates[-1] if dates else None,
                    'first_date': dates[0] if dates else None, 'has_undated': any(not r.get('date') for r in facts),
                    'display_label': next(iter(labels)) if len(labels) == 1 else ('Measurements' if kinds == {'measurement'} else 'Health records')})
            sources.sort(key=lambda s: (s['latest_date'] is None, -(int(s['latest_date'].replace('-','')) if s['latest_date'] else 0), s['id']))
            fields = [{'kind': k, 'label': label, 'count': count} for (k, label), count in sorted(field_counts.items())]
            # Estimate resident JSON payload without allocating another full
            # encoded history. A single capture over this bound is rejected.
            size = sum(len(str(row).encode('utf-8')) for row in rows) + sum(len(str(s).encode('utf-8')) for s in sources)
            if size > self.MAX_BYTES:
                raise ValueError('This history is too large for one browsing snapshot. Choose an earlier date cutoff.')
            item = {'view': view, 'rows': rows, 'sources': sources, 'fields': fields,
                    'by_source': by_source, 'facilities': sorted(facilities), 'created': monotonic(), 'size': size,
                    'revision': revision}
            while self.captures and (len(self.captures) >= self.MAX_SNAPSHOTS or
                    sum(x['size'] for x in self.captures.values()) + size > self.MAX_BYTES):
                self.captures.popitem(last=False)
            self.captures[token] = item
            # If a commit happened between key acquisition and capture, never
            # publish the newer view under the older database generation.
            if revision == key[0]:
                self.keys[key] = token
            self._expire()
            return token, item

    def get(self, token):
        with self.lock:
            self._expire()
            if token not in self.captures:
                raise SnapshotExpired('This history view expired. Refresh to open a new view; your records are unchanged.')
            self.captures.move_to_end(token)
            return self.captures[token]

    def view(self, as_of=None, known_at=None):
        return self.open(as_of, known_at)[1]['view']

    def page(self, *, snapshot_id=None, as_of=None, known_at=None, section='facts', offset=0, limit=50,
             kind=None, label=None, facility=None, source_id=None, order='newest', query='', conflict_id=None, through=None, conflicts_only=False, compare_fact_id=None):
        if not 1 <= limit <= 50 or not 0 <= offset <= 100000 or section not in ('facts','sources','fields') or order not in ('newest','oldest'):
            raise ValueError('Invalid page request')
        if snapshot_id:
            item = self.get(snapshot_id)
            if (as_of is not None and as_of != item['view']['scope']['as_of']) or (known_at and instant(known_at) != item['view']['scope']['known_at']):
                raise ValueError('Page bounds do not match the captured history')
        else:
            snapshot_id, item = self.open(as_of, known_at)
        view = item['view']
        needle = query.strip().casefold()
        retrieval = plan(query)['info'] if needle else None
        query_ids = None
        if retrieval and (retrieval['mappings'] or retrieval['status'] != 'ready'):
            matching, _, retrieval = retrieve(view, {'query':query})
            query_ids = {r['id'] for r in matching}
        title_matches = {s['id'] for s in item['sources'] if needle and needle in s['title'].casefold()}
        rows = item['by_source'].get(source_id, []) if source_id else item['rows']
        group = next((g for g in view['conflicts'] if g['id'] == conflict_id), None) if conflict_id else None
        ids = set(group['fact_ids']) if group else set()
        conflict_ids = {identity for g in view['conflicts'] for identity in g['fact_ids']} if conflicts_only else set()
        rows = [r for r in rows if (not kind or r['kind'] == kind) and (not label or r['label'] == label)
                and (not facility or r.get('facility') == facility) and (not conflict_id or r['id'] in ids)
                and (not conflicts_only or r['id'] in conflict_ids)
                and (not through or (r.get('date') and r['date'] <= through))
                and ((r['id'] in query_ids) if query_ids is not None else
                     (not needle or r['source_id'] in title_matches or needle in ' '.join(str(r.get(k) or '') for k in ('label','value','unit','facility','occurred_on')).casefold()))]
        if order == 'oldest':
            rows = sorted(rows, key=lambda r: (r.get('date') is None, r.get('date') or '', r['id']))
        visible_ids = {r['source_id'] for r in rows}
        field_counts = defaultdict(int)
        if section == 'fields':
            for row in rows:
                if not needle or query_ids is not None or needle in row['label'].casefold():
                    field_counts[(row['kind'],row['label'])] += 1
        fields = [{'kind':k,'label':name,'count':count} for (k,name),count in sorted(field_counts.items())]
        sources = [s for s in item['sources'] if s['id'] in visible_ids]
        candidates = sources if section == 'sources' else fields if section == 'fields' else rows
        selected = candidates[offset:offset + limit]
        facts = selected if section == 'facts' else []
        source_ids = {f['source_id'] for f in facts}
        selected_ids = {f['id'] for f in facts}
        conflicts = [g for g in view['conflicts'] if selected_ids.intersection(g['fact_ids'])]
        dates = [r['date'] for r in item['rows'] if r.get('date')]
        result = {'scope': deepcopy(view['scope']), 'counts': deepcopy(view['counts']), 'profile': deepcopy(view['profile']),
            'retrieval': retrieval,
            'facts': [r for r in facts if r.get('date')], 'undated_facts': [r for r in facts if not r.get('date')],
            'sources': selected if section == 'sources' else [s for s in item['sources'] if s['id'] in source_ids],
            'conflicts': conflicts, 'fields': selected if section == 'fields' else [],
            'facets': {'kinds': sorted({r['kind'] for r in item['rows']}), 'facilities': item['facilities'][:200],
                'facilities_truncated': len(item['facilities']) > 200, 'date_bounds': [min(dates),max(dates)] if dates else []},
            'page': {'snapshot_id': snapshot_id, 'section': section, 'offset': offset, 'limit': limit,
                'total': len(candidates), 'matched_sources': len(visible_ids), 'returned': len(selected),
                'next_offset': offset + limit if offset + limit < len(candidates) else None,
                'previous_offset': max(0, offset-limit) if offset else None}}
        # Defensive copy: presentation callers cannot mutate a retained snapshot.
        if compare_fact_id:
            result['checkup_comparison'] = compare_checkups(view, compare_fact_id)
        return deepcopy(result)
