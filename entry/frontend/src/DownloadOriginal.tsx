import { useEffect, useRef, useState, type ReactNode } from 'react';
import { localRequest } from './api';

export default function DownloadOriginal({href, className = 'text-button', children}: {
  href: string; className?: string; children: ReactNode;
}) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const active = useRef<AbortController | null>(null);
  useEffect(() => {
    setBusy(false); setError('');
    return () => active.current?.abort();
  }, [href]);
  async function download() {
    const controller = new AbortController(); active.current?.abort(); active.current = controller;
    setBusy(true); setError('');
    try {
      const response = await localRequest(href, {signal: controller.signal});
      if (!response.ok) throw new Error('The original is unavailable in this view. Open updated history and try again.');
      const blob = await response.blob();
      if (controller.signal.aborted) return;
      let filename = 'modus-original';
      const encoded = response.headers.get('content-disposition')?.match(/filename\*=UTF-8''([^;]+)/i)?.[1];
      if (encoded) { try { filename = decodeURIComponent(encoded).replace(/[\\/\x00-\x1f]/g, '_'); } catch { /* safe default */ } }
      const url = URL.createObjectURL(blob);
      const link = document.createElement('a'); link.href = url; link.download = filename; link.click();
      setTimeout(() => URL.revokeObjectURL(url), 1000);
    } catch (reason) {
      if (!controller.signal.aborted) setError(reason instanceof Error ? reason.message : 'The original could not be downloaded.');
    } finally { if (!controller.signal.aborted) setBusy(false); }
  }
  return <><button type="button" className={className} disabled={busy} onClick={() => { void download(); }} aria-busy={busy}>{children}</button>
    {error && <span className="original-download-error" role="alert">{error}</span>}</>;
}
