/**
 * Joins class name fragments, dropping falsy ones. Deliberately not `clsx` +
 * `tailwind-merge`: nothing in this codebase passes conflicting utilities to
 * the same slot, so conflict resolution would be two dependencies of dead
 * weight. Keep it that way -- if a component ever needs override semantics,
 * give it an explicit prop rather than reaching for a merger.
 */
export function cn(...parts: (string | false | null | undefined)[]): string {
  return parts.filter(Boolean).join(' ');
}
