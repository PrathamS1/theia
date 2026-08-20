import { useEffect, useRef } from 'react';

interface HeroVideoProps {
  src: string;
  className?: string;
}

/**
 * Decorative looping accent video for the hero.
 *
 * Two rules this component exists to enforce:
 *  - The source WebM is transparent, so it must never carry a background
 *    or sit inside a wrapper that paints one.
 *  - The caller's positioning utilities land directly on the <video>. There
 *    is deliberately no wrapper element — a wrapper that ended up
 *    `position: relative` would drop the video into layout flow and shove
 *    the hero copy down the page.
 */
export default function HeroVideo({ src, className = '' }: HeroVideoProps) {
  const ref = useRef<HTMLVideoElement | null>(null);

  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    el.disableRemotePlayback = true; // not in React's known-prop list
    el.play().catch(() => {
      // Autoplay can still be refused even when muted; nothing to recover.
    });
  }, []);

  return (
    <video
      ref={ref}
      src={src}
      autoPlay
      muted
      loop
      playsInline
      preload="auto"
      disablePictureInPicture
      controlsList="nodownload noplaybackrate noremoteplayback"
      tabIndex={-1}
      aria-hidden="true"
      className={`pointer-events-none block h-auto select-none bg-transparent [transform:translateZ(0)] ${className}`}
    />
  );
}
