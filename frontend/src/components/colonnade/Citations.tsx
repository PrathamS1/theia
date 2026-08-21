import { BookOpenText, ChevronDown } from 'lucide-react';
import { motion, useReducedMotion } from 'motion/react';
import { useCallback, useEffect, useId, useState, type ReactNode } from 'react';
import { EASE_OUT, SPRING_SWAP } from '../../lib/ease';
import { cn } from '../../lib/cn';

export interface CitationItem {
  id: string;
  title: ReactNode;
  domain?: ReactNode;
  /** A graph entity colour from tokens.css -- semantic, not decorative. */
  tint?: string;
}

export interface CitationsProps {
  citations: CitationItem[];
  /**
   * How many rows have arrived. Every row is always mounted -- this only
   * fades them in -- so the block holds its full height from the first frame
   * and the card around it never resizes mid-reveal. Defaults to all of them,
   * which is the plain-disclosure behaviour.
   */
  visible?: number;
  title?: ReactNode;
  /** Total available, so the badge can read "3 of 812" honestly. */
  total?: number;
  open?: boolean;
  defaultOpen?: boolean;
  onOpenChange?: (open: boolean) => void;
  className?: string;
}

/* Rows are intentionally inert: this is a marketing card, and a row that
 * navigates away from the page it is selling is a leak, not a feature. The
 * upstream component's `url`, favicon fetch and external-link icon are gone
 * with it -- which also removes one cross-origin request per row. */
function CitationRow({ citation, index }: { citation: CitationItem; index: number }) {
  return (
    <div className="flex items-center gap-2 rounded-md px-1 py-1">
      <span
        aria-hidden="true"
        className="grid size-4 shrink-0 place-items-center rounded-[3px] text-[7px] font-bold
          leading-none text-white"
        style={{ background: citation.tint ?? 'var(--n-document)' }}
      >
        {String(citation.domain ?? '?').charAt(0)}
      </span>
      <span className="flex min-w-0 flex-1 items-baseline gap-x-1.5">
        <span className="truncate text-[11px] font-medium text-ink/80">{citation.title}</span>
        {citation.domain ? (
          <span className="shrink-0 text-[10px] text-muted/70">{citation.domain}</span>
        ) : null}
      </span>
      <span
        className="grid size-4 shrink-0 place-items-center rounded-[3px] bg-ink/5 text-[9px]
          font-semibold tabular-nums text-muted"
      >
        {index}
      </span>
    </div>
  );
}

export function Citations({
  citations,
  visible = citations.length,
  title = 'Sources',
  total,
  open,
  defaultOpen = false,
  onOpenChange,
  className,
}: CitationsProps) {
  const reduce = useReducedMotion() ?? false;
  const baseId = useId();
  const contentId = `${baseId}-content`;
  const [internalOpen, setInternalOpen] = useState(defaultOpen);
  const currentOpen = open ?? internalOpen;
  const setOpen = useCallback(
    (next: boolean) => {
      if (open === undefined) setInternalOpen(next);
      onOpenChange?.(next);
    },
    [onOpenChange, open],
  );

  return (
    <div className={cn('w-full', className)}>
      <button
        type="button"
        aria-expanded={currentOpen}
        aria-controls={contentId}
        onClick={() => setOpen(!currentOpen)}
        className="group -ml-1 flex min-h-7 w-full cursor-pointer appearance-none items-center
          gap-1.5 rounded-lg border-0 bg-transparent px-1 py-0 text-left text-muted
          transition-colors hover:text-ink"
      >
        <BookOpenText className="size-3.5 shrink-0" aria-hidden="true" />
        <span className="text-xs font-medium">{title}</span>
        <span className="rounded-full bg-ink/5 px-1.5 py-0.5 text-[9px] font-semibold tabular-nums">
          {total ? `${visible} of ${total.toLocaleString()}` : visible}
        </span>
        <motion.span
          aria-hidden="true"
          animate={{ rotate: currentOpen ? 180 : 0 }}
          transition={reduce ? { duration: 0 } : SPRING_SWAP}
          className="ml-auto text-muted/60"
        >
          <ChevronDown className="size-3.5" />
        </motion.span>
      </button>

      {/* Stands in for the upstream AgentDisclosure. Height-animated rather
       * than display-toggled so the surrounding card does not jump. */}
      <motion.div
        id={contentId}
        initial={false}
        animate={{ height: currentOpen ? 'auto' : 0, opacity: currentOpen ? 1 : 0 }}
        transition={reduce ? { duration: 0 } : { duration: 0.24, ease: EASE_OUT }}
        className="overflow-hidden"
      >
        {/* Every row is mounted from the start and reveals in place. Mounting
          * them one at a time grew this block as the stagger ran, and since
          * the card's height is fixed, that growth was paid for by the
          * illustration tile above -- which read as the card resizing itself. */}
        <div className="mt-0.5 grid gap-0.5">
          {citations.map((citation, index) => {
            const arrived = index < visible;
            return (
              <motion.div
                key={citation.id}
                initial={false}
                animate={{
                  opacity: arrived ? 1 : 0,
                  y: arrived || reduce ? 0 : 6,
                }}
                transition={reduce ? { duration: 0 } : { duration: 0.22, ease: EASE_OUT }}
              >
                <CitationRow citation={citation} index={index + 1} />
              </motion.div>
            );
          })}
        </div>
      </motion.div>
    </div>
  );
}

const CITATION_ITEMS: CitationItem[] = [
  {
    id: 'confluence',
    title: 'Secret rotation runbook',
    domain: 'Confluence',
    tint: 'var(--n-document)',
  },
  {
    id: 'linear',
    title: 'ENG-4844 Rollback state machine',
    domain: 'Linear',
    tint: 'var(--n-ticket)',
  },
  { id: 'slack', title: '#eng-releases, pinned', domain: 'Slack', tint: 'var(--n-person)' },
];

/**
 * Reveals the sources one at a time, once, when `active` flips true -- which
 * the section wires to "this scrolled into view", not to mount. A staggered
 * reveal that plays below the fold has not happened as far as the reader is
 * concerned.
 */
export function CitationsReveal({ active }: { active: boolean }) {
  const reduce = useReducedMotion() ?? false;
  const [visible, setVisible] = useState(0);

  useEffect(() => {
    if (!active) return;
    if (reduce) {
      setVisible(CITATION_ITEMS.length);
      return;
    }
    const timers = CITATION_ITEMS.map((_, index) =>
      window.setTimeout(() => setVisible(index + 1), 120 + index * 420),
    );
    return () => timers.forEach(window.clearTimeout);
  }, [active, reduce]);

  return (
    <div className="flex flex-col gap-1.5">
      <p className="text-[11px] leading-[1.45] text-muted">
        Every answer arrives with the documents it came from.
      </p>
      <Citations citations={CITATION_ITEMS} visible={visible} total={25812} defaultOpen />
    </div>
  );
}
