import { Link } from 'react-router-dom';
import { GITHUB_URL } from './GlassNav';

const BG_SRCSET =
  '/img/footer-bg-1600.webp 1600w, /img/footer-bg-2560.webp 2560w, /img/footer-bg-3840.webp 3840w';
const STATUE_SRCSET =
  '/img/footer-statue-600.webp 600w, /img/footer-statue-1000.webp 1000w, /img/footer-statue-1500.webp 1500w';

const LINK = 'text-[14px] text-white/65 no-underline transition-colors hover:text-white';

/**
 * The closing band: night-ruins artwork, the statue centred low, and the
 * wordmark tracked across the full width behind it.
 *
 * It butts straight against the colonnade with no seam. Nothing here has to
 * reach up to do that -- the colonnade's pillars are `absolute top-0 h-full`,
 * so that section's bottom edge already *is* the pillar base and its bottom
 * padding sits inside. The -mt-px is only for the sub-pixel gap a fractional
 * layout height can leave, the same one the colonnade closes under the hero.
 */
export default function SiteFooter() {
  return (
    <footer className="relative isolate -mt-px overflow-hidden bg-[#0b0c0a]">
      {/* Painted, not a gradient: object-bottom keeps the ruins and the
        * lit colonnade on the right anchored while the sky is what gets
        * cropped on short viewports. */}
      <img
        src="/img/footer-bg-2560.webp"
        srcSet={BG_SRCSET}
        sizes="100vw"
        alt=""
        loading="lazy"
        decoding="async"
        className="absolute inset-0 z-0 h-full w-full object-cover object-bottom"
      />

      {/* 36vw reproduces the mock's proportion (the band runs about 0.36 of
        * the viewport's width); the floor keeps it usable on a phone and the
        * ceiling stops it running away on an ultrawide. */}
      <div className="relative z-[1] flex min-h-[clamp(22rem,36vw,46rem)] flex-col
        pt-[clamp(2.5rem,5vw,4.5rem)]">
        <div className="mx-auto flex w-full max-w-[72rem] flex-wrap items-start justify-between
          gap-x-8 gap-y-6 px-6">
          <div>
            {/* Spelled out rather than the nav's mark-as-the-"T" lockup: that
              * mark is a dark teal silhouette that reads on light glass and
              * disappears against this art, leaving the word as "HEIA". */}
            <span className="font-instrument-serif text-[24px] italic uppercase leading-none
              text-white">
              Theia
            </span>
            <p className="mt-3 max-w-[28ch] text-[13px] leading-relaxed text-white/50">
              Every answer arrives with the documents it came from.
            </p>
          </div>

          <nav aria-label="Footer" className="flex flex-wrap items-center gap-x-7 gap-y-2">
            <Link to="/dashboard" className={LINK}>
              Dashboard
            </Link>
            <a href={GITHUB_URL} target="_blank" rel="noreferrer" className={LINK}>
              GitHub
            </a>
            {/* Text rather than /img/hydradb-mark.webp: that mark's wordmark
              * is solid black and would disappear against this art. */}
            <span className="text-[13px] text-white/35">Built on HydraDB</span>
          </nav>
        </div>

        <div className="mt-auto">
          <p className="pb-[clamp(1rem,2.5vw,2.25rem)] text-center text-[11px] uppercase
            tracking-[0.14em] text-white/55">
            &copy; 2026 Theia
          </p>

          <div className="relative px-[clamp(1.5rem,5.5vw,6rem)]">
            <img
              src="/img/footer-statue-1000.webp"
              srcSet={STATUE_SRCSET}
              sizes="(max-width: 640px) 40vw, 23vw"
              alt=""
              width={1665}
              height={1447}
              loading="lazy"
              decoding="async"
              /* h-auto is load-bearing: tailwind.css skips Preflight, so there
                * is no `img { height: auto }` to fall back on. With a CSS width
                * set and no CSS height, the height="1447" attribute stays in
                * force as a presentational hint and the statue renders 432x1447
                * -- a tall thin smear rather than a figure. */
              className="absolute bottom-[clamp(0.75rem,2.8vw,3.5rem)] left-1/2 z-[1] h-auto
                w-[clamp(150px,23vw,440px)] -translate-x-1/2"
            />

            {/* An outlined wordmark has to be SVG. `-webkit-text-stroke` takes
              * no gradient, and background-clip:text fills glyphs rather than
              * outlining them -- only `fill="none" stroke="url(...)"` gives a
              * gradient *outline*.
              *
              * The tracking comes from textLength + lengthAdjust="spacing"
              * rather than a letter-spacing value: it pins both ends to the
              * box exactly and puts all the slack between glyphs, where a
              * letter-spacing would also add a trailing gap after the A and
              * quietly throw off any centring built on top of it.
              *
              * non-scaling-stroke keeps the outline a hairline at every
              * viewport instead of thickening with the viewBox scale, which
              * is what makes it read as barely-there. */}
            <svg viewBox="0 0 1640 120" aria-hidden="true" className="block w-full">
              <defs>
                <linearGradient id="theia-outline" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="#FFCE66" />
                  <stop offset="100%" stopColor="#FFCE66" stopOpacity="0" />
                </linearGradient>
              </defs>
              {/* The viewBox is the clip. Georgia's cap height is 0.693em, so
                * at 340 the caps run y=3 to y=238 -- and a 120-unit box shows
                * the top 49.8% of them, letting the footer's bottom edge cut
                * the word in half. Nothing overflows: an SVG viewport clips to
                * its bounds by default.
                *
                * Raising the size necessarily costs tracking, since textLength
                * pins the span: the glyphs eat 1053 of the 1640 units at this
                * size, leaving ~0.43em between letters instead of the 2.3em
                * the old 132 left. */}
              <text
                x="0"
                y="238"
                textLength="1640"
                lengthAdjust="spacing"
                fontFamily="Georgia, 'Times New Roman', Times, serif"
                fontSize="340"
                fill="none"
                stroke="url(#theia-outline)"
                strokeWidth="1.5"
                vectorEffect="non-scaling-stroke"
              >
                THEIA
              </text>
            </svg>
          </div>
        </div>
      </div>
    </footer>
  );
}
