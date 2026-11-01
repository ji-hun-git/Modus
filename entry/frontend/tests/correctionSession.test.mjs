import test from 'node:test';
import assert from 'node:assert/strict';
import { build } from 'esbuild';
import { fileURLToPath } from 'node:url';
import { createElement } from 'react';
import { renderToStaticMarkup } from 'react-dom/server';

const built = await build({ stdin: { contents: `export * from './correctionSession';
  export {default as RecordCorrection} from './RecordCorrection';
  export {default as CorrectionRecoveryNotice} from './CorrectionRecoveryNotice';`,
  resolveDir: fileURLToPath(new URL('../src/', import.meta.url)), loader: 'ts' },
  bundle: true, write: false, format: 'esm', platform: 'node', target: 'es2022', jsx: 'automatic',
  plugins: [{ name: 'react', setup(b) { b.onResolve({ filter: /^(react(?:\/.*)?|react-dom(?:\/.*)?|lucide-react)$/ },
    args => ({ path: import.meta.resolve(args.path), external: true })); } }] });
const { createCorrectionSession, correctionSession, RecordCorrection, CorrectionRecoveryNotice } =
  await import('data:text/javascript;base64,' + Buffer.from(built.outputFiles[0].text).toString('base64'));
const ready = () => ({ request: { expected_revision_id: 'original', reason: 'Transcription correction',
  corrected: { id: 'f', kind: 'measurement', label: 'Pulse', value: '72', unit: 'bpm', occurred_on: '2024-01-02', facility: 'Example' } },
  preview: { preview_id: 'reviewed-preview', changes: { value: { before: '71', after: '72' } } }, confirmed: true, originScope: 'current' });
const receipt = { available_at: '2026-10-30T00:00:00Z' };

test('uncertain save survives subscriber unmount and retries the identical reviewed payload', async () => {
  const s = createCorrectionSession(); s.patch('f', ready());
  const unsubscribe = s.subscribe(() => {}); let first;
  await s.save('f', async body => { first = structuredClone(body); throw new TypeError('Connection lost'); });
  unsubscribe(); // Closing a source dialog must not own this transaction.
  s.patch('f', { request: { ...ready().request, corrected: { ...ready().request.corrected, value: '999' } } });
  const calls = []; await s.save('f', async body => { calls.push(body); return receipt; });
  assert.deepEqual(calls, [first]); assert.equal(calls[0].corrected.value, '72');
  assert.equal(s.get('f').pending, null); assert.equal(s.get('f').savedAt, receipt.available_at);
});

test('completion arrives after close and remains available on remount', async () => {
  const s = createCorrectionSession(); s.patch('f', ready());
  let resolve; const wait = new Promise(r => { resolve = r; });
  const unsubscribe = s.subscribe(() => {}); const task = s.save('f', () => wait); unsubscribe();
  resolve(receipt); await task;
  assert.equal(s.getSnapshot()[0][1].savedAt, receipt.available_at);
  assert.equal(s.get('f').acknowledged, false); assert.equal(s.get('f').busy, false);
});

test('simultaneous dialog and recovery clicks issue one request', async () => {
  const s = createCorrectionSession(); s.patch('f', ready()); let count = 0; let resolve;
  const send = () => { count++; return new Promise(r => { resolve = r; }); };
  const first = s.save('f', send); await s.save('f', send); assert.equal(count, 1);
  resolve(receipt); await first;
});

for (const status of [408, 429, 500, 503]) test(`HTTP ${status} preserves retry identity`, async () => {
  const s = createCorrectionSession(); s.patch('f', ready());
  await s.save('f', async () => { throw Object.assign(new Error('Unavailable'), { status }); });
  assert.equal(s.get('f').pending.preview_id, 'reviewed-preview'); assert.equal(s.get('f').rejected, false);
});

test('definitive conflict retains edits but requires a fresh review', async () => {
  const s = createCorrectionSession(); s.patch('f', ready());
  await s.save('f', async () => { throw Object.assign(new Error('A newer revision exists'), { status: 409 }); });
  assert.equal(s.get('f').request.corrected.value, '72'); assert.equal(s.get('f').pending, null);
  assert.equal(s.get('f').preview, null); assert.equal(s.get('f').confirmed, false); assert.equal(s.get('f').rejected, true);
  let count = 0; await s.save('f', async () => { count++; return receipt; }); assert.equal(count, 0);
});

test('unreviewed drafts cannot save; independent records do not overwrite one another', async () => {
  const s = createCorrectionSession(); s.patch('f', { ...ready(), confirmed: false }); s.patch('other', ready());
  let count = 0; await s.save('f', async () => { count++; return receipt; });
  await s.save('other', async () => { count++; return receipt; }); assert.equal(count, 1);
  assert.equal(s.get('f').request.corrected.value, '72'); assert.equal(s.get('f').savedAt, null);
});

test('historical scope never renders a resumed current edit without explicit action', () => {
  correctionSession.patch('historical', ready());
  const html = renderToStaticMarkup(createElement(RecordCorrection, { fact: { id: 'historical' }, scope: { scope_id: 'past' } }));
  assert.match(html, /Continue latest correction/); assert.doesNotMatch(html, /Transcription correction|value="72"/);
});

test('saved-version lists are bound to the scope that fetched them', () => {
  correctionSession.patch('versions', { versionsScope: 'current', versions: [{ fact: { id: 'v', value: 'private-future-value' }, reason: null }] });
  const html = renderToStaticMarkup(createElement(RecordCorrection, { fact: { id: 'versions' }, scope: { scope_id: 'past' } }));
  assert.doesNotMatch(html, /private-future-value/);
});

test('completed correction still permits viewing versions and starting a new correction', () => {
  correctionSession.patch('completed', { savedAt: receipt.available_at });
  const html = renderToStaticMarkup(createElement(RecordCorrection, { fact: { id: 'completed' }, scope: { scope_id: 'current' } }));
  assert.match(html, /Correction saved/); assert.match(html, /View saved versions/); assert.match(html, /Correct saved record/);
});

test('recovery remains visible outside a closed dialog and does not disclose medical values', async () => {
  correctionSession.patch('lost', ready());
  await correctionSession.save('lost', async () => { throw new Error('Connection lost'); });
  const html = renderToStaticMarkup(createElement(CorrectionRecoveryNotice));
  assert.match(html, /Check save result/); assert.doesNotMatch(html, /Pulse|Transcription correction/);
});
