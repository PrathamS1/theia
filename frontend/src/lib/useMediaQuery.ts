import { useState, useEffect } from 'react';

/**
 * Tracks whether a media query currently matches. Reads the initial value
 * synchronously (no SSR here), so consumers that gate mounting on this
 * never mount-then-unmount — e.g. content gated on a min-width query is
 * simply never mounted on a narrow viewport, not mounted and torn down.
 */
export function useMediaQuery(query: string): boolean {
  const [matches, setMatches] = useState(() => window.matchMedia(query).matches);

  useEffect(() => {
    const mql = window.matchMedia(query);
    setMatches(mql.matches);

    const onChange = (e: MediaQueryListEvent) => setMatches(e.matches);
    mql.addEventListener('change', onChange);
    return () => mql.removeEventListener('change', onChange);
  }, [query]);

  return matches;
}
