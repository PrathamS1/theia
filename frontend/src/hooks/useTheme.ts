// This project made a deliberate light-only decision (see the parked dark
// palette in styles/tokens.css) — no theme context or matchMedia needed.
// This stub exists only to satisfy GlassSurface's import. The return type
// stays 'light' | 'dark' (not narrowed to a 'light' literal) so consumers
// like GlassSurface's `resolvedTheme === 'dark'` check remain valid
// TypeScript instead of a provably-false comparison.
type Theme = 'light' | 'dark';

export default function useTheme(): { theme: Theme; resolvedTheme: Theme } {
  return { theme: 'light', resolvedTheme: 'light' };
}
