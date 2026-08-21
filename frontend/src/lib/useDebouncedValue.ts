import { useEffect, useState } from 'react';

/**
 * Returns `value` after it has stopped changing for `delay` ms.
 *
 * Both search fields were wired as forms that only applied on Enter, so typing
 * into them appeared to do nothing at all — the single most common way to make
 * a filter feel broken. Applying on every keystroke is the other failure mode:
 * a topology fetch over 25,812 documents is far too expensive to fire per
 * character. Debouncing is the middle path, and the caller pairs it with a
 * visible pending state so the delay reads as work rather than as lag.
 */
export function useDebouncedValue<T>(value: T, delay = 350): T {
  const [settled, setSettled] = useState(value);

  useEffect(() => {
    const id = window.setTimeout(() => setSettled(value), delay);
    return () => window.clearTimeout(id);
  }, [value, delay]);

  return settled;
}
