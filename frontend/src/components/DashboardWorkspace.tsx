import { useLayoutEffect, useRef, useState } from 'react';
import type { ReactNode } from 'react';
import { X } from 'lucide-react';

export const workspaceButton = 'rounded-lg border border-ui-line px-3 py-2 text-xs font-medium text-ui-body hover:bg-ui-raised focus-visible:outline focus-visible:outline-2 focus-visible:outline-ui-ink-amber-400 disabled:opacity-50';

export function DashboardWorkspace({ id, title, description, open, busy, dirty, size = 'wide', trigger, onClose, onDiscard, children }: {
  id: string; title: string; description: string; open: boolean; busy?: boolean; dirty?: boolean;
  size?: 'wide' | 'compact';
  trigger: HTMLElement | null; onClose: () => void; onDiscard?: () => void; children: ReactNode;
}) {
  const ref = useRef<HTMLDialogElement>(null);
  const keep = useRef<HTMLButtonElement>(null);
  const [confirmClose, setConfirmClose] = useState(false);
  useLayoutEffect(() => {
    const dialog = ref.current;
    if (!open || !dialog) return;
    dialog.showModal();
    const previous = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    return () => {
      dialog.close();
      document.body.style.overflow = previous;
      const fallback = document.querySelector<HTMLElement>(`[data-workspace-entry="${id}"]`);
      (trigger?.isConnected ? trigger : fallback)?.focus({ preventScroll: true });
    };
  }, [id, open, trigger]);
  useLayoutEffect(() => { if (confirmClose) keep.current?.focus(); }, [confirmClose]);
  function close() {
    if (busy) return;
    if (dirty) setConfirmClose(true);
    else onClose();
  }
  return <dialog ref={ref} id={id} aria-labelledby={`${id}-title`} aria-describedby={`${id}-description`}
    onCancel={event => { event.preventDefault(); if (confirmClose) setConfirmClose(false); else close(); }}
    className={`fixed inset-0 m-auto h-dvh max-h-none w-full max-w-none overflow-hidden border-0 border-ui-line bg-ui-page p-0 text-ui-primary shadow-2xl backdrop:bg-black/55 open:flex open:flex-col md:w-[calc(100%_-_3rem)] md:rounded-2xl md:border ${size === 'compact'
      ? 'md:h-fit md:max-h-[min(48rem,calc(100dvh_-_3rem))] md:max-w-[52rem]'
      : 'md:h-[calc(100dvh_-_3rem)] md:max-h-[56rem] md:max-w-[76rem]'}`}>
    <header className="flex shrink-0 items-start justify-between gap-3 border-b border-ui-line bg-ui-panel px-4 py-3 sm:px-6 sm:py-4">
      <div className="min-w-0">
        <p className="text-[0.66rem] font-semibold uppercase tracking-widest text-ui-ink-amber-400">Dashboard workspace</p>
        <h3 id={`${id}-title`} className="mt-1 text-xl font-semibold text-ui-heading">{title}</h3>
        <p id={`${id}-description`} className="mt-1 text-xs text-ui-muted">{description}</p>
      </div>
      <button type="button" className={workspaceButton} aria-label="Close workspace" onClick={close} disabled={busy}><X className="h-4 w-4" /></button>
    </header>
    {confirmClose && <div role="alert" className="flex shrink-0 flex-wrap items-center gap-3 border-b border-ui-line bg-ui-panel px-4 py-3 text-sm sm:px-6">
      <p>Discard unsaved changes?</p>
      <button ref={keep} type="button" className={workspaceButton} onClick={() => setConfirmClose(false)}>Keep editing</button>
      <button type="button" className={workspaceButton} disabled={busy} onClick={() => { onDiscard?.(); setConfirmClose(false); onClose(); }}>Discard changes</button>
    </div>}
    <div className="min-h-0 flex-1 overflow-y-auto overscroll-contain">{children}</div>
  </dialog>;
}
