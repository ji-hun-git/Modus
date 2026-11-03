import { useEffect, useRef, useState, useSyncExternalStore } from 'react';
import { FolderOpen } from 'lucide-react';
import App from './App';
import { Brand } from './ui';
import useAppearance from './useAppearance';
import { api, post, acceptLocalSession, clearLocalAccess, hasLocalAccess, lockLocalAccess, readAccessFile, subscribeLocalAccess } from './api';
import './local-access.css';

export default function AccessGate() {
  useAppearance();
  const unlocked = useSyncExternalStore(subscribeLocalAccess, hasLocalAccess, () => false);
  const [configured, setConfigured] = useState<boolean | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const input = useRef<HTMLInputElement>(null);

  useEffect(() => {
    const controller = new AbortController();
    void api<{configured: boolean}>('/access/status', {signal: controller.signal})
      .then(status => setConfigured(status.configured))
      .catch(() => { if (!controller.signal.aborted) setError('Modus is not available. Start the local launcher and try again.'); });
    return () => controller.abort();
  }, []);

  useEffect(() => {
    if (!unlocked) return;
    let lastTouch = 0;
    const touch = () => {
      if (Date.now() - lastTouch < 60000) return;
      lastTouch = Date.now();
      void post('/access/touch', {}).catch(() => {});
    };
    const controller = new AbortController();
    const poll = setInterval(() => {
      void api<{authenticated: boolean}>('/access/status', {signal: controller.signal})
        .then(status => { if (!controller.signal.aborted && !status.authenticated) clearLocalAccess(); })
        .catch(() => {});
    }, 15000);
    window.addEventListener('pointerdown', touch);
    window.addEventListener('keydown', touch);
    return () => {
      controller.abort(); clearInterval(poll);
      window.removeEventListener('pointerdown', touch);
      window.removeEventListener('keydown', touch);
    };
  }, [unlocked]);

  async function open(file: File | undefined) {
    if (!file) return;
    setError(''); setBusy(true);
    try {
      if (!file.name.endsWith('.modus-access') || file.size > 1024)
        throw new Error('Choose a Modus access file, not a medical report.');
      const token = readAccessFile(await file.text(), window.location.origin);
      const session = await post('/access/unlock', {token});
      acceptLocalSession(session);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'This file could not unlock Modus.');
    } finally {
      setBusy(false);
      if (input.current) input.current.value = '';
    }
  }

  async function lock() {
    setError(''); setBusy(true);
    try { await lockLocalAccess(); }
    catch { setError('This window is locked. Restart Modus if the service could not confirm locking other windows.'); }
    finally { clearLocalAccess(); setBusy(false); }
  }

  if (unlocked) return <App onLock={() => { void lock(); }} />;
  return <main className="local-access-screen">
    <header><Brand /></header>
    <section aria-labelledby="local-access-title" className="local-access-content">
      <svg className="local-access-orbit" viewBox="0 0 160 160" aria-hidden="true">
        <circle cx="80" cy="80" r="68" /><ellipse cx="80" cy="80" rx="68" ry="27" transform="rotate(-35 80 80)" />
        <circle cx="80" cy="80" r="32" /><path d="M73 80v-7a7 7 0 0 1 14 0v7m-17 0h20v17h-20z" />
      </svg>
      <h1 id="local-access-title">Open your history.</h1>
      <p>Use the local access file created when you start Modus.</p>
      <input ref={input} type="file" accept=".modus-access" aria-label="Local access file" hidden
        onChange={event => { void open(event.target.files?.[0]); }} />
      <button type="button" className="primary" disabled={busy || configured !== true} onClick={() => input.current?.click()}>
        <FolderOpen size={17} aria-hidden="true" />{busy ? 'Opening…' : 'Open access file'}
      </button>
      {error && <p className="local-access-error" role="alert">{error}</p>}
      {configured === false && <p role="status">Start Modus with its local launcher to create an access file.</p>}
      {configured === null && !error && <p role="status">Connecting to Modus…</p>}
      <details><summary>Where is my access file?</summary>
        <p>The launcher shows its location. Look for <strong>Modus-{window.location.port || '80'}.modus-access</strong>.</p>
        <p>Keep this file private. It unlocks records on this computer and is replaced when Modus restarts.</p>
        <p>Reloading locks this window. Sessions also lock after 30 minutes of inactivity or 8 hours. Saved records stay intact; unsaved reviews close.</p>
      </details>
    </section>
  </main>;
}
