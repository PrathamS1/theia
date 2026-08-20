import { useEffect, useRef, useState } from 'react';

interface UseInViewOptions {
  /** Stop observing after the first intersection. Default true. */
  once?: boolean;
  rootMargin?: string;
  threshold?: number;
}

/**
 * Reports whether the referenced element has entered the viewport.
 *
 * Used to start one-shot reveals (the citation stagger, the connector
 * draw-in) when the section is actually on screen rather than at mount --
 * a below-the-fold animation that plays while nobody is looking has simply
 * not happened as far as the user is concerned.
 */
export function useInView<T extends Element>({
  once = true,
  rootMargin = '0px 0px -15% 0px',
  threshold = 0,
}: UseInViewOptions = {}) {
  const ref = useRef<T | null>(null);
  const [inView, setInView] = useState(false);

  useEffect(() => {
    const el = ref.current;
    if (!el) return;

    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          setInView(true);
          if (once) observer.disconnect();
        } else if (!once) {
          setInView(false);
        }
      },
      { rootMargin, threshold },
    );

    observer.observe(el);
    return () => observer.disconnect();
  }, [once, rootMargin, threshold]);

  return [ref, inView] as const;
}
