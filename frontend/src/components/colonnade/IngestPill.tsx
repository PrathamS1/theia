/**
 * The centre stadium. Deliberately not a card: it is the hinge the two
 * connector strings run through, and a pill reads as a junction where a
 * rectangle would read as a third peer card.
 */
export function IngestPill() {
  return (
    <div
      /* Proportional to the cards rather than to the viewport, so the hinge
       * keeps its weight against them at every size -- and an explicit height
       * rather than one derived from padding, because the ring string
       * measures this box and a content-derived height would shift under it
       * as the webfont and the statue image settle. */
      className="relative z-[1] flex h-[clamp(5.5rem,calc(var(--card-h)*0.62),11rem)] w-full
        items-center justify-center gap-2 rounded-full bg-sand px-5 sm:px-6"
    >
      <img
        src="/img/statue-small-454.webp"
        srcSet="/img/statue-small-454.webp 454w, /img/statue-small-908.webp 908w"
        sizes="(max-width: 1024px) 56px, 72px"
        alt=""
        width={454}
        height={703}
        loading="lazy"
        decoding="async"
        className="h-[76%] w-auto shrink-0 object-contain"
      />
      <p className="text-ink [font-size:clamp(0.8125rem,1.2vw,1.125rem)] leading-snug">
        Theia ingests these into{' '}
        {/* The same mark GlassNav uses, so the lockup is identical everywhere
          * it appears on the page. Sized in `em` so it tracks the copy. */}
        <img
          src="/img/hydradb-mark.webp"
          alt="HydraDB"
          width={264}
          height={50}
          loading="lazy"
          decoding="async"
          className="inline-block h-[1.05em] w-auto translate-y-[0.12em]"
        />
      </p>
    </div>
  );
}
