import { useRef } from 'react';
import { useInView } from '../../lib/useInView';
import { useScrollReveal } from '../../lib/useScrollReveal';
import { RingString, VerticalString } from './Connectors';
import { FilePreview } from './FilePreview';
import { IngestPill } from './IngestPill';
import { IntegrationsCard } from './IntegrationsCard';
import { ProjectFolder } from './ProjectFolder';
import { TryItCard } from './TryItCard';
import { SOURCE_FILES } from './sourceFiles';

const STATUE_SRCSET =
  '/img/statue-side-700.webp 700w, /img/statue-side-1100.webp 1100w, /img/statue-side-1600.webp 1600w';
const CEILING_SRCSET =
  '/img/ceiling-1600.webp 1600w, /img/ceiling-2400.webp 2400w, /img/ceiling-3600.webp 3600w';
const PILLAR_SRCSET = '/img/pillar-900.webp 900w, /img/pillar-1300.webp 1300w';

const FOLDER_PREVIEWS = SOURCE_FILES.map((file) => ({
  id: file.id,
  content: <FilePreview file={file} />,
}));

/**
 * A statue that glides in from off-frame as the section scrolls past, and
 * back out on the way up.
 *
 * The mirror lives on the <img>, never on the animated wrapper: composing
 * scaleX(-1) with the translate on one element inverts the direction of
 * travel, which is a quietly maddening bug to chase.
 */
function Statue({ side, className }: { side: 'left' | 'right'; className: string }) {
  return (
    <div
      /* Hidden at the same breakpoint as the pillars: the whole effect is a
       * figure half-occluded by a column, so without the column it is not a
       * smaller version of the effect, it is just clutter over the cards. */
      className={`statue-frame statue-frame--${side} pointer-events-none absolute z-[2]
        hidden md:block ${className}`}
    >
      <img
        src="/img/statue-side-1100.webp"
        srcSet={STATUE_SRCSET}
        sizes="(max-width: 1024px) 30vw, 470px"
        alt=""
        width={1100}
        height={1711}
        loading="lazy"
        decoding="async"
        className={`block h-auto w-full select-none ${side === 'right' ? 'scale-x-[-1]' : ''}`}
      />
    </div>
  );
}

export default function ColonnadeSection() {
  // Drives the JS fallback for `animation-timeline: view()`; attaches nothing
  // at all on browsers that support the timeline natively.
  const sectionRef = useScrollReveal<HTMLElement>();
  const [gridRef, gridInView] = useInView<HTMLDivElement>();

  // The ring string measures these three boxes rather than assuming the grid's
  // proportions. IngestPill and ProjectFolder take no `ref` prop, and threading
  // one through both just to be measured would put layout plumbing into their
  // APIs -- a wrapper element is the cheaper trade. Each wrapper is `w-full`
  // and unstyled otherwise, so it is exactly its child's box.
  const folderRef = useRef<HTMLDivElement>(null);
  const pillRef = useRef<HTMLDivElement>(null);
  const tryRef = useRef<HTMLDivElement>(null);

  return (
    <section
      ref={sectionRef}
      /* The nav's "About" link used to target the failures list below this
       * section; that list is gone, so the anchor lands here instead. */
      id="about"
      aria-labelledby="colonnade-h"
      /* -mt-px closes the sub-pixel seam under the hero's full-bleed art. */
      /* The section is budgeted to fill one screen from lg up. The top padding
       * keeps a vw term because what it has to clear is the ceiling strip
       * plus the barcode, and both are 100vw images whose height tracks width
       * alone; the clamp on top of it is the breathing gap below the barcode.
       * `--card-h` and the row variables are solved for in tailwind.css --
       * see the "Colonnade: one-screen budget" block there. */
      className="colonnade relative isolate -mt-px overflow-hidden bg-[var(--bg)]
        pb-[clamp(2.5rem,min(7vw,7vh),5rem)] pt-[calc(8.1vw+clamp(0.75rem,2.5vh,2rem))]"
    >
      {/* Asymmetric by design, per the mock: the left figure sits high, the
       * right one low and running off the bottom edge. Both are far wider
       * than the sliver that shows -- most of each is behind its pillar or
       * past the frame, which is what sells the depth. */}
      <Statue side="left" className="left-[-11%] top-[14%] w-[clamp(210px,30vw,470px)]" />
      <Statue side="right" className="right-[-8%] top-[36%] w-[clamp(210px,30vw,470px)]" />

      {/* Ceiling + barcode, top-anchored as one stack so the barcode always
       * sits directly under the molding.
       *
       * They sit on opposite sides of the pillars in z: the ceiling is an
       * unbroken band the capitals hang below (z-[5]), the barcode is what
       * the capitals overlap (z-[3]). Both source images are uniform
       * horizontal patterns, so stretching them is safe -- but the ceiling
       * takes its natural height rather than a forced one, because
       * object-cover would crop away the very edge lines that make the
       * molding read as molding. */}
      {/* The wrapper deliberately carries no z-index: at `auto` it does not
       * open a stacking context, so the two children's z values compete
       * directly with the pillars instead of being trapped inside it. */}
      <div className="pointer-events-none absolute inset-x-0 top-0 flex flex-col">
        <img
          src="/img/ceiling-2400.webp"
          srcSet={CEILING_SRCSET}
          sizes="100vw"
          alt=""
          className="relative z-[5] h-auto w-full"
          decoding="async"
        />
        {/* The lettering is baked into the artwork, so this carries a real alt
         * rather than being marked decorative. It is inset on wider screens
         * so the pillars never eat the first and last letters. */}
        <img
          src="/img/barcode-2400.webp"
          srcSet="/img/barcode-1600.webp 1600w, /img/barcode-2400.webp 2400w"
          sizes="100vw"
          alt="Entire knowledge graph for your organization"
          className="relative z-[3] h-auto w-full md:w-[87%] md:self-center"
          decoding="async"
        />
      </div>

      {/* Pillars. h-full w-auto keeps the column's own proportions instead of
       * stretching the capital; the negative translate is what clips them
       * against the viewport edge for the framed look. */}
      <img
        src="/img/pillar-1300.webp"
        srcSet={PILLAR_SRCSET}
        sizes="200px"
        alt=""
        aria-hidden="true"
        loading="lazy"
        decoding="async"
        className="pointer-events-none absolute left-0 top-0 z-[4] hidden h-full w-auto max-w-none
          -translate-x-[15%] scale-x-[-1] select-none md:block"
      />
      <img
        src="/img/pillar-1300.webp"
        srcSet={PILLAR_SRCSET}
        sizes="200px"
        alt=""
        aria-hidden="true"
        loading="lazy"
        decoding="async"
        className="pointer-events-none absolute right-0 top-0 z-[4] hidden h-full w-auto max-w-none
          translate-x-[15%]  select-none md:block"
      />

      <div
        /* 72rem, not 68: the cards are now tall enough that the logo tile
         * fills its row, and at 68rem that tile left too little width for
         * "Connects with your org email" to hold one line. */
        className="relative z-[6] mx-auto max-w-[72rem] px-6"
      >
        <h2
          id="colonnade-h"
          className="section-title mx-auto max-w-[22ch] text-balance text-center font-georgia
            font-normal italic text-brand-ink animate-rise"
        >
          See What Is Happening Under the Table
        </h2>
        <p
          className="mx-auto mt-[clamp(0.75rem,1.6vh,1.25rem)] max-w-[42rem] text-center
            leading-relaxed text-brand-ink animate-rise [animation-delay:160ms]
            [font-size:clamp(0.75rem,min(1.25vw,1.7vh),0.95rem)]"
        >
          Nine tools, one graph. Theia folds 25,812 documents into 18,262 resolved entities
          and 10,357 facts &mdash; linking the aliases that mean the same person, preferring
          the fact that is still true, and keeping a citation on every one of them.
        </p>

        <div
          ref={gridRef}
          className="relative mt-[clamp(1.5rem,min(4vw,5.5vh),3.5rem)] grid gap-8
            lg:grid-cols-3 lg:items-center lg:gap-x-[clamp(2rem,4vw,3.5rem)]"
        >
          {/* Strings are decorative wiring between columns; below lg the grid
           * is a single stack and they would connect nothing. */}
          <RingString
            drawn={gridInView}
            fromRef={folderRef}
            throughRef={pillRef}
            toRef={tryRef}
          />

          <div className="relative z-[1] flex w-full flex-col gap-[var(--card-gap)]">
            <IntegrationsCard />
            <VerticalString drawn={gridInView} />
            <div ref={folderRef} className="w-full">
              <ProjectFolder
                className="h-[var(--card-h)] w-full z-2"
                title="Uniform Format"
                description="Ingestion complete"
                count={25812}
                itemLabel="file"
                previews={FOLDER_PREVIEWS}
                ariaLabel="Uniform Format, 25,812 files. Open to browse."
              />
            </div>
          </div>

          <div ref={pillRef} className="w-full">
            <IngestPill />
          </div>

          <div ref={tryRef} className="relative z-[1] w-full">
            <TryItCard revealed={gridInView} />
          </div>
        </div>
      </div>
    </section>
  );
}
