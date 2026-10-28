"""Durable cumulative provider reservations. Interrupted/unknown calls retain cost."""
from contextlib import contextmanager
from decimal import Decimal
import json
import os
from pathlib import Path
from uuid import uuid4

from .schema import canonical, json_loads


def append(path, row):
    with Path(path).open('a', encoding='utf-8') as stream:
        stream.write(canonical(row) + '\n')
        stream.flush()
        os.fsync(stream.fileno())


def write_new(path, value):
    with Path(path).open('x', encoding='utf-8') as stream:
        stream.write(canonical(value) + '\n')
        stream.flush()
        os.fsync(stream.fileno())


class BudgetDenied(RuntimeError):
    pass


class Book:
    def __init__(self, root):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self.path = self.root / 'spend.jsonl'

    @contextmanager
    def locked(self):
        lock = self.root / '.spend.lock'
        try:
            fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        except FileExistsError:
            raise BudgetDenied('spend_lock_busy_or_interrupted') from None
        try:
            yield
        finally:
            os.close(fd)
            lock.unlink()

    def events(self):
        if not self.path.exists():
            return []
        # A truncated ledger fails closed. It is never silently repaired/reset.
        return [json_loads(line) for line in self.path.read_text(encoding='utf-8').splitlines()]

    @staticmethod
    def balances(events, provider, run_id=None):
        prior = Decimal('0')
        calls = {}
        for row in events:
            if row['provider'] != provider:
                continue
            if row['event'] == 'baseline':
                prior = max(prior, Decimal(row['amount_usd']))
            elif row['event'] == 'reserved' and (run_id is None or row['run_id'] == run_id):
                calls[row['request_id']] = Decimal(row['amount_usd'])
            elif row['event'] == 'settled' and row['request_id'] in calls:
                calls[row['request_id']] = Decimal(row['amount_usd'])
        return (prior if run_id is None else Decimal('0')) + sum(calls.values(), Decimal('0'))

    @staticmethod
    def estimate(provider, input_tokens, output_tokens):
        return (Decimal(input_tokens) * Decimal(str(provider.input_usd_per_million)) * Decimal(str(provider.input_cost_multiplier))
            + Decimal(output_tokens) * Decimal(str(provider.output_usd_per_million))) / Decimal(1_000_000)

    def reserve(self, provider, run_id, cache_key, request, image_count=0):
        # Pixel encodings can be compact; keep an additional image-token floor.
        proxy = max(len(canonical(request).encode('utf-8')), image_count * 32768)
        reservation = self.estimate(provider, proxy, provider.max_output_tokens)
        with self.locked():
            events = self.events()
            if any(row.get('cache_key') == cache_key and row['event'] == 'reserved' for row in events):
                raise BudgetDenied('previous_attempt_exists_no_automatic_retry')
            baselines = [Decimal(row['amount_usd']) for row in events if row['provider'] == provider.provider and row['event'] == 'baseline']
            prior = Decimal(str(provider.prior_spend_usd))
            if baselines and prior < max(baselines):
                raise BudgetDenied('prior_spend_cannot_be_reset')
            if not baselines or prior > max(baselines):
                row = {'event': 'baseline', 'provider': provider.provider, 'amount_usd': str(prior)}
                append(self.path, row)
                events.append(row)
            total = self.balances(events, provider.provider)
            run_total = self.balances(events, provider.provider, run_id)
            if total + reservation > Decimal(str(provider.ceiling_usd)):
                raise BudgetDenied('provider_cumulative_ceiling')
            if run_total + reservation > Decimal(str(provider.allocation_usd)):
                raise BudgetDenied('provider_run_allocation')
            request_id = uuid4().hex
            append(self.path, {'event': 'reserved', 'provider': provider.provider, 'request_id': request_id,
                'run_id': run_id, 'cache_key': cache_key, 'amount_usd': str(reservation),
                'input_token_proxy': proxy, 'max_output_tokens': provider.max_output_tokens,
                'basis': 'UTF8 request bytes or image floor plus maximum output; estimate, not an invoice guarantee'})
            return request_id, reservation

    def settle(self, provider, request_id, reservation, usage, status):
        known = isinstance(usage, dict) and all(type(usage.get(k)) is int and usage[k] >= 0 for k in ('input_tokens', 'output_tokens'))
        cost = self.estimate(provider, usage['input_tokens'], usage['output_tokens']) if known else reservation
        with self.locked():
            events = self.events()
            if any(e['event'] == 'settled' and e.get('request_id') == request_id for e in events):
                raise BudgetDenied('duplicate_settlement')
            append(self.path, {'event': 'settled', 'provider': provider.provider, 'request_id': request_id,
                'amount_usd': str(cost), 'status': status,
                'basis': 'reported_usage_conservative_rates' if known else 'unknown_usage_reservation_retained'})
        return float(cost)

    def summary(self, providers, run_id):
        events = self.events()
        prior = lambda p: max([Decimal(e['amount_usd']) for e in events
            if e['event'] == 'baseline' and e['provider'] == p.provider] or [Decimal('0')])
        return {p.provider: {'cumulative_accounted_usd': float(self.balances(events, p.provider)
                + max(Decimal('0'), Decimal(str(p.prior_spend_usd)) - prior(p))),
            'run_accounted_usd': float(self.balances(events, p.provider, run_id)),
            'ceiling_usd': p.ceiling_usd, 'allocation_usd': p.allocation_usd,
            'invoice_verified': False} for p in providers}
