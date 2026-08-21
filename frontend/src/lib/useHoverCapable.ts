import { useMediaQuery } from './useMediaQuery';

/**
 * True only for input that can genuinely hover *and* point precisely, so
 * hover-to-preview affordances never fire from a touch's synthesized hover
 * (which sticks until the next tap elsewhere and leaves the UI stuck open).
 */
export function useHoverCapable(): boolean {
  return useMediaQuery('(hover: hover) and (pointer: fine)');
}
