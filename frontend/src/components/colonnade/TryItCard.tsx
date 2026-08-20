import { Link } from 'react-router-dom';
import { CitationsReveal } from './Citations';

/**
 * The tall right-hand card: an illustration tile, the source reveal in the
 * gap beneath it, and the closing CTA. Its height is derived from the left
 * column (two cards plus the gap between them) so the two columns end on the
 * same line at every viewport.
 */
export function TryItCard({ revealed }: { revealed: boolean }) {
  return (
    <div
      className="flex h-[calc(var(--card-h)*2+var(--card-gap))] w-full flex-col rounded-card
        bg-sand p-4 sm:p-5"
    >
      <div className="flex min-h-0 flex-1 items-center justify-center rounded-tile bg-white p-4">
        <img
          src="/img/misc-600.webp"
          srcSet="/img/misc-600.webp 600w, /img/misc-1000.webp 1000w"
          sizes="(max-width: 1024px) 80vw, 320px"
          alt=""
          width={600}
          height={577}
          loading="lazy"
          decoding="async"
          className="max-h-full w-auto max-w-full object-contain"
        />
      </div>

      <div className="shrink-0 py-3">
        <CitationsReveal active={revealed} />
      </div>

      {/* Black, not the hero's teal `bg-brand-solid`. Two identically styled
       * CTAs on one page would read as the same destination; the contrast is
       * what marks this as the section's own close. 15.9:1 on white. */}
      <Link
        to="/dashboard"
        className="block shrink-0 rounded-full bg-ink py-3 text-center text-base font-medium
          text-white no-underline transition-[filter,transform] hover:brightness-150
          active:scale-[0.99]"
      >
        Try It Out
      </Link>
    </div>
  );
}
