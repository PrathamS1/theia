import { useEffect, useRef } from 'react';

/**
 * Fallback for `animation-timeline: view()`.
 *
 * On Chrome/Edge the statues are driven entirely by a scroll-progress
 * timeline in CSS and this hook attaches nothing at all -- that check is the
 * point, not a nicety: a scroll listener that duplicates work the compositor
 * is already doing is pure jank on the platform that needs it least.
 *
 * Where the timeline is unsupported (Safari, Firefox), it writes the same
 * `--enter` custom property the CSS keyframe would have written, so both
 * paths drive one identical `transform` rule. Progress is a plain 0..1 ramp
 * across the same range the CSS declares, which makes the motion reversible
 * for free: scrolling back up simply walks the value back down.
 */
export function useScrollReveal<T extends HTMLElement>() {
  const ref = useRef<T | null>(null);

  useEffect(() => {
    const el = ref.current;
    if (!el) return;

    // Supported natively -> let CSS own it, attach nothing.
    if (CSS.supports('animation-timeline', 'view()')) return;
    if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
      el.style.setProperty('--enter', '1');
      return;
    }

    let frame = 0;
    let queued = false;

    const measure = () => {
      queued = false;
      const rect = el.getBoundingClientRect();
      const vh = window.innerHeight;
      // Mirrors `animation-range: entry 15% cover 40%`: 0 while the top edge
      // is still well below the fold, 1 once the section is 40% covered.
      const start = vh * 0.85;
      const end = vh * 0.4 - rect.height * 0.4;
      const span = start - end;
      const progress = span <= 0 ? 1 : (start - rect.top) / span;
      el.style.setProperty('--enter', Math.min(1, Math.max(0, progress)).toFixed(4));
    };

    const onScroll = () => {
      if (queued) return;
      queued = true;
      frame = requestAnimationFrame(measure);
    };

    // Only listen while the section is anywhere near the viewport.
    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          window.addEventListener('scroll', onScroll, { passive: true });
          measure();
        } else {
          window.removeEventListener('scroll', onScroll);
        }
      },
      { rootMargin: '50% 0px' },
    );

    observer.observe(el);
    window.addEventListener('resize', onScroll, { passive: true });
    measure();

    return () => {
      observer.disconnect();
      window.removeEventListener('scroll', onScroll);
      window.removeEventListener('resize', onScroll);
      cancelAnimationFrame(frame);
    };
  }, []);

  return ref;
}
