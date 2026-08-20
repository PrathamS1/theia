import { useCallback, useEffect, useLayoutEffect, useRef, useState } from 'react';
import type { RefObject } from 'react';

/**
 * The teal strings that wire the cards together.
 *
 * Inline SVG rather than <img> so the stroke can take the brand colour and a
 * reveal.
 *
 * `RingString` measures the boxes it connects instead of carrying a fitted
 * path. The previous version hand-fitted coordinates into a 100x100 box
 * stretched by `preserveAspectRatio="none"`, which meant every one of its
 * numbers was really a statement about the grid's aspect ratio -- so changing
 * a card height silently slid the curve off the cards it was supposed to
 * touch. Measuring makes the geometry a consequence of the layout rather than
 * a duplicate of it, and as a bonus the viewBox can now be 1:1 with pixels,
 * which retires both `preserveAspectRatio="none"` and the
 * `vector-effect="non-scaling-stroke"` that existed only to undo it.
 */

const STROKE = '#4E9FA2';

const REVEAL = 'transition-opacity duration-700 ease-[cubic-bezier(0.2,0.7,0.3,1)]';

/** The straight run in the left column's gap, between card 1 and card 2. */
export function VerticalString({ drawn }: { drawn: boolean }) {
  return (
    <svg
      aria-hidden="true"
      viewBox="0 0 2 20"
      preserveAspectRatio="none"
      className={`pointer-events-none absolute left-1/2 z-0 hidden w-0.5 -translate-x-1/2 lg:block
        ${REVEAL} ${drawn ? 'opacity-100' : 'opacity-0'}`}
      style={{ top: 'var(--card-h)', height: 'var(--card-gap)' }}
    >
      <path d="M1 0 L1 20" stroke={STROKE} strokeWidth={2} vectorEffect="non-scaling-stroke" />
    </svg>
  );
}

type Anchor = RefObject<HTMLElement | null>;

interface Geometry {
  width: number;
  height: number;
  d: string;
}

/**
 * Builds the S that leaves `from`'s right edge, passes through the centre of
 * `through`, and lands on `to`'s left edge -- all in `host`'s coordinate
 * space.
 *
 * The two control points either side of the midpoint are *vertical* offsets,
 * which is the whole trick: `S` mirrors the incoming handle `(cx, cy + m)`
 * about the midpoint to `(cx, cy - m)`, so the curve arrives at the pill
 * travelling straight up and leaves it travelling straight up, with C1
 * continuity across the join. That is what reads as one string threaded
 * through the pill rather than two arcs that happen to meet it. The outer
 * handles are horizontal for the same reason at the cards: the string appears
 * to grow out of an edge instead of poking at a corner.
 */
function ringPath(host: DOMRect, from: DOMRect, through: DOMRect, to: DOMRect): string {
  const sx = from.right - host.left;
  const sy = from.top - host.top + from.height * 0.5;
  const cx = through.left - host.left + through.width * 0.5;
  const cy = through.top - host.top + through.height * 0.5;
  const ex = to.left - host.left;
  const ey = to.top - host.top + to.height * 0.28;

  const k = (cx - sx) * 0.55;
  const m = (sy - cy) * 0.55;
  const k2 = (ex - cx) * 0.55;

  return (
    `M ${sx} ${sy} C ${sx + k} ${sy}, ${cx} ${cy + m}, ${cx} ${cy}` +
    ` S ${ex - k2} ${ey}, ${ex} ${ey}`
  );
}

/**
 * The ring that leaves card 2's right edge, threads behind the centre pill,
 * and climbs to the tall card's left edge. It sits at z-0 inside the grid
 * while every column sits at z-1, which is what makes the string read as
 * passing *behind* the pill rather than butting into it.
 */
export function RingString({
  drawn,
  fromRef,
  throughRef,
  toRef,
}: {
  drawn: boolean;
  fromRef: Anchor;
  throughRef: Anchor;
  toRef: Anchor;
}) {
  const hostRef = useRef<HTMLDivElement>(null);
  const [geometry, setGeometry] = useState<Geometry | null>(null);

  const measure = useCallback(() => {
    const host = hostRef.current;
    const from = fromRef.current;
    const through = throughRef.current;
    const to = toRef.current;
    if (!host || !from || !through || !to) return;

    const hostRect = host.getBoundingClientRect();
    // Below lg the host is `hidden`, so every rect collapses to zero and there
    // is nothing meaningful to connect -- the columns are one stack there.
    if (hostRect.width === 0 || hostRect.height === 0) {
      setGeometry(null);
      return;
    }

    const next: Geometry = {
      width: hostRect.width,
      height: hostRect.height,
      d: ringPath(
        hostRect,
        from.getBoundingClientRect(),
        through.getBoundingClientRect(),
        to.getBoundingClientRect(),
      ),
    };
    setGeometry((prev) =>
      prev && prev.width === next.width && prev.height === next.height && prev.d === next.d
        ? prev
        : next,
    );
  }, [fromRef, throughRef, toRef]);

  useLayoutEffect(() => {
    measure();

    const targets = [hostRef.current, fromRef.current, throughRef.current, toRef.current];
    const observer = new ResizeObserver(measure);
    for (const target of targets) if (target) observer.observe(target);

    return () => observer.disconnect();
  }, [measure, fromRef, throughRef, toRef]);

  // A ResizeObserver on the host covers reflow, but not the case where the
  // boxes keep their sizes and only move -- a fresh webfont reflowing the copy
  // above the grid does exactly that.
  useEffect(() => {
    if (!document.fonts) return;
    let cancelled = false;
    document.fonts.ready.then(() => {
      if (!cancelled) measure();
    });
    return () => {
      cancelled = true;
    };
  }, [measure]);

  return (
    <div ref={hostRef} className="pointer-events-none absolute inset-0 z-0 hidden lg:block">
      {geometry && (
        <svg
          aria-hidden="true"
          viewBox={`0 0 ${geometry.width} ${geometry.height}`}
          className={`absolute inset-0 h-full w-full
            ${REVEAL} ${drawn ? 'opacity-100' : 'opacity-0'}`}
        >
          <path
            d={geometry.d}
            fill="none"
            stroke={STROKE}
            strokeWidth={2}
            strokeLinecap="round"
          />
        </svg>
      )}
    </div>
  );
}
