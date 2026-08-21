import type { Transition } from 'motion/react';

/**
 * Motion's easing/spring vocabulary for this app, kept deliberately small.
 *
 * EASE_OUT is the *same* curve already baked into `--animate-rise`,
 * `--animate-glass-in` and `--animate-statue-in` in styles/tailwind.css. The
 * two systems must stay identical: a JS-animated element sitting next to a
 * CSS-animated one on the same curve reads as one motion system, and on two
 * near-but-not-equal curves reads as a bug.
 */
export const EASE_OUT = [0.2, 0.7, 0.3, 1] as const;

/**
 * Springs follow Apple's damping/response framing rather than
 * mass/stiffness/damping. `bounce: 0` is critically damped -- graceful, no
 * overshoot -- and is the default for anything that did not come from a
 * gesture carrying momentum. Overshoot is reserved for SPRING_SWAP, where a
 * control visibly flips and a little bounce reads as physical.
 */
export const SPRING_LAYOUT: Transition = { type: 'spring', bounce: 0, duration: 0.4 };
export const SPRING_PRESS: Transition = { type: 'spring', bounce: 0, duration: 0.25 };
export const SPRING_SWAP: Transition = { type: 'spring', bounce: 0.2, duration: 0.35 };
