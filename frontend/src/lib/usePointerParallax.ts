import { useEffect, useRef } from 'react';

/**
 * Tracks pointer position as a normalised [-1, 1] offset from the element's
 * centre and writes it to `--px` / `--py` custom properties on the given
 * ref, lerped toward the target each frame so motion settles instead of
 * snapping to the raw pointer delta.
 *
 * Disabled entirely on touch input and when the user prefers reduced
 * motion — no listener is attached, not just a no-op animation.
 */
export function usePointerParallax<T extends HTMLElement>() {
  const ref = useRef<T | null>(null);

  useEffect(() => {
    const el = ref.current;
    if (!el) return;

    const prefersReducedMotion = window.matchMedia(
      '(prefers-reduced-motion: reduce)',
    ).matches;
    const isCoarsePointer = window.matchMedia('(pointer: coarse)').matches;
    if (prefersReducedMotion || isCoarsePointer) return;

    let targetX = 0;
    let targetY = 0;
    let currentX = 0;
    let currentY = 0;
    let frame = 0;

    const tick = () => {
      currentX += (targetX - currentX) * 0.08;
      currentY += (targetY - currentY) * 0.08;
      el.style.setProperty('--px', currentX.toFixed(4));
      el.style.setProperty('--py', currentY.toFixed(4));
      frame = requestAnimationFrame(tick);
    };

    const onPointerMove = (e: PointerEvent) => {
      const rect = el.getBoundingClientRect();
      targetX = ((e.clientX - rect.left) / rect.width - 0.5) * 2;
      targetY = ((e.clientY - rect.top) / rect.height - 0.5) * 2;
    };

    const onPointerLeave = () => {
      targetX = 0;
      targetY = 0;
    };

    el.addEventListener('pointermove', onPointerMove);
    el.addEventListener('pointerleave', onPointerLeave);
    frame = requestAnimationFrame(tick);

    return () => {
      el.removeEventListener('pointermove', onPointerMove);
      el.removeEventListener('pointerleave', onPointerLeave);
      cancelAnimationFrame(frame);
    };
  }, []);

  return ref;
}
