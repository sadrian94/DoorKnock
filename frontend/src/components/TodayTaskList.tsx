import { useLayoutEffect, useRef, useState } from 'react';
import { CalendarClock, ChevronRight, ClipboardList, Clock3, Mail } from 'lucide-react';
import type { NextAction } from '../types';

const visibleLimit = 3;

export function TodayTaskList({ items, dateLabel, onOpen }: {
  items: NextAction[]; dateLabel: (item: NextAction) => string;
  onOpen: (id: string, trigger: HTMLButtonElement) => void;
}) {
  const viewport = useRef<HTMLDivElement>(null);
  const list = useRef<HTMLUListElement>(null);
  const [range, setRange] = useState('');
  const overflow = items.length > visibleLimit;
  function updateRange() {
    const el = viewport.current;
    if (!overflow || !el || !list.current) return;
    const bounds = el.getBoundingClientRect();
    const rows = Array.from(list.current.children);
    const visible = rows.map((row, index) => {
      const rect = row.getBoundingClientRect();
      return rect.top >= bounds.top - 1 && rect.bottom <= bounds.bottom + 1 ? index + 1 : 0;
    }).filter(Boolean);
    setRange(visible.length > 1 ? `${visible[0]}–${visible.at(-1)} of ${items.length}` : visible.length ? `${visible[0]} of ${items.length}` : `${items.length} due`);
  }
  useLayoutEffect(() => {
    const el = viewport.current;
    const ul = list.current;
    if (!el || !ul) return;
    if (!overflow) { el.style.removeProperty('max-height'); return; }
    const size = () => {
      const last = ul.children[visibleLimit - 1];
      const first = ul.firstElementChild;
      if (!first || !last) return;
      el.style.maxHeight = `${Math.ceil(last.getBoundingClientRect().bottom - first.getBoundingClientRect().top)}px`;
      updateRange();
    };
    size();
    const observer = new ResizeObserver(size);
    observer.observe(ul);
    Array.from(ul.children).slice(0, visibleLimit).forEach(row => observer.observe(row));
    return () => observer.disconnect();
  }, [overflow, items]);
  return <div className="min-w-0 overflow-hidden rounded-2xl border border-ui-line-soft bg-ui-panel/70">
    <div id="dashboard-task-scroll" ref={viewport} role="region" aria-label="Today’s due tasks" tabIndex={overflow ? 0 : undefined}
      aria-describedby={overflow ? 'dashboard-task-scroll-note' : undefined} onScroll={updateRange}
      className={overflow ? 'overflow-y-auto overscroll-y-contain [scrollbar-gutter:stable] focus-visible:outline focus-visible:outline-2 focus-visible:-outline-offset-2 focus-visible:outline-ui-ink-amber-400' : ''}>
      <ul ref={list} className="divide-y divide-ui-line-soft px-4">
        {items.map(item => {
          const Icon = item.kind === 'assessment' ? ClipboardList : ['interview', 'interview_review'].includes(item.kind) ? CalendarClock : ['followup', 'thank_you'].includes(item.kind) ? Mail : Clock3;
          return <li key={item.application_id}>
            <button type="button" aria-haspopup="dialog" aria-controls="daily-workspace" data-task-id={item.application_id}
              onClick={event => onOpen(item.application_id, event.currentTarget)}
              className="flex w-full items-center gap-2 rounded-md py-3 text-left hover:bg-ui-raised focus-visible:outline focus-visible:outline-2 focus-visible:-outline-offset-2 focus-visible:outline-ui-ink-amber-400 sm:gap-3">
              <span className="shrink-0 rounded-lg bg-ui-fill-amber-500/10 p-2 text-ui-ink-amber-400"><Icon className="h-4 w-4" aria-hidden="true" /></span>
              <span className="min-w-0 flex-1"><span className="block break-words text-sm font-semibold text-ui-heading">{item.label}</span><span className="block break-words text-xs text-ui-muted">{item.company} · {item.title}</span></span>
              <span className="max-w-[30%] text-right text-xs text-ui-muted">{dateLabel(item)}</span>
              <ChevronRight className="h-4 w-4 shrink-0 text-ui-muted" aria-hidden="true" />
            </button>
          </li>;
        })}
        {!items.length && <li className="py-4 text-sm text-ui-muted">No actions due. Open the queue to see what’s coming up.</li>}
      </ul>
    </div>
    {overflow && <div id="dashboard-task-scroll-note" className="flex justify-between gap-3 border-t border-ui-line-soft px-4 py-1.5 text-xs text-ui-muted"><span>Scroll for more</span><span>{range}</span></div>}
  </div>;
}
