import { Link } from 'react-router-dom';
import { usePointerParallax } from '../lib/usePointerParallax';
import { useMediaQuery } from '../lib/useMediaQuery';
import HeroVideo from './HeroVideo';

const BG_SRCSET =
  '/img/bg-1600.webp 1600w, /img/bg-2560.webp 2560w, /img/bg-3840.webp 3840w';
const STATUE_SRCSET =
  '/img/statue-900.webp 900w, /img/statue-1400.webp 1400w, /img/statue-2000.webp 2000w';

const SCRIM =
  '[background:linear-gradient(180deg,rgba(255,255,255,0.88)_0%,rgba(255,255,255,0.78)_30%,' +
  'rgba(255,255,255,0.55)_50%,rgba(255,255,255,0.15)_70%,rgba(255,255,255,0)_85%)]';

export default function Hero() {
  const parallaxRef = usePointerParallax<HTMLDivElement>();
  const showVideos = useMediaQuery('(min-width: 768px)');

  return (
    <section
      ref={parallaxRef}
      className="relative isolate flex min-h-screen min-h-[100svh] flex-col items-center
        overflow-hidden bg-[var(--bg)] pt-[clamp(5rem,12vh,9rem)]"
    >
      {/* Oversized + inset so an 8px parallax shift never exposes the
       * container edge behind it. */}
      <img
        className="absolute inset-[-1%] z-0 h-[104%] w-[104%] object-cover object-bottom
          [transform:translate3d(calc(var(--px,0)*-8px),calc(var(--py,0)*-8px),0)] will-change-transform"
        src="/img/bg-2560.webp"
        srcSet={BG_SRCSET}
        sizes="100vw"
        alt=""
        fetchPriority="high"
        decoding="async"
      />
      <div className={`absolute inset-0 z-[1] pointer-events-none ${SCRIM}`} aria-hidden="true" />
      {/* Parallax lives on this wrapper as a plain (non-animated) transform
       * so it keeps re-evaluating --px/--py forever. A CSS animation's held
       * fill-mode state does NOT live-update var() references after it
       * completes (confirmed empirically) — that's why the img itself only
       * carries the one-shot scale/opacity entrance, never the parallax.
       * -bottom-6 (not 0): the source art is hard-cropped at its own
       * bottom edge, not a natural silhouette end. Parked 24px below the
       * visible area — comfortably past the ±18px max parallax shift — so
       * that crop line never surfaces while it translates; the section's
       * overflow-hidden clips the rest. Centering is plain -50%: the
       * source is now trimmed to its alpha bbox, so no per-asset
       * correction constant is needed.
       *
       * The 95vh term in the width: the art is 1400x969, so width sets its
       * height. Sized on vw alone, the 900px cap binds above ~1800px wide but
       * stops binding the moment you zoom in -- the statue jumps from 0.469*W
       * to 0.5*W and its top edge climbs from 0.366*H to 0.325*H, which is
       * what put it through the Get Started button at 110%. Capping on vh too
       * pins that top edge at a constant share of the viewport instead. */}
      <div
        className="absolute -bottom-6 left-1/2 z-[2] pointer-events-none will-change-transform
          w-[clamp(300px,min(50vw,95vh),900px)] max-w-[96vw]
          [transform:translateX(-60%)_translate3d(calc(var(--px,0)*-18px),calc(var(--py,0)*-18px),0)]"
      >
        <img
          className="block h-auto w-full animate-statue-in"
          src="/img/statue-1400.webp"
          srcSet={STATUE_SRCSET}
          sizes="(max-width: 640px) 80vw, (max-width: 1200px) 60vw, 1080px"
          alt=""
          fetchPriority="high"
          decoding="async"
        />
      </div>

      {/* Pinned accents — deliberately do not reference var(--px)/var(--py),
       * which is the entire mechanism that keeps them still while the
       * background and statue drift under the pointer.
       *
       * Each clip carries its own transparent padding, so the box is larger
       * than the visible artwork: stack's art starts 16.7%/23.1% in and fills
       * 66.6% of the frame, reply's starts 9.2%/12.6% in and fills 81.6%.
       * The offsets below are back-solved from those so the *artwork* — not
       * the video box — lands where the mock puts it. */}
      {showVideos && (
        <>
          <HeroVideo
            src="/video/stack.webm"
            className="absolute left-[11%] top-[32%] z-[2] [width:clamp(180px,22.8vw,620px)]"
          />
          <HeroVideo
            src="/video/reply.webm"
            className="absolute left-[61.2%] top-[52.2%] z-[2] [width:clamp(150px,28.2vw,520px)]"
          />
        </>
      )}

      <div
        className="relative z-[3] mx-auto flex max-w-[64rem] flex-col items-center px-6 text-center
          gap-[clamp(0.6rem,2.2vh,1.5rem)]"
      >
        <h1
          className="hero-title mx-auto max-w-[46rem] font-medium text-brand-ink animate-rise [animation-delay:120ms]"
        >
          <span className="mr-[0.06em] font-georgia italic">Know It All,</span>{' '}
          <span className="font-sans font-medium not-italic">With Your Own</span>{' '}
          <span className="font-georgia italic">Company Brain</span>
        </h1>

        <p
          className="mx-auto max-w-[46rem] text-brand-ink leading-relaxed animate-rise [animation-delay:320ms]
            [font-size:clamp(0.75rem,min(1.4vw,1.9vh),1.0225rem)]"
        >
          Theia answers questions across Slack, Gmail, Linear, Jira, GitHub, Confluence,
          Drive, HubSpot and Fireflies, resolving who is who, preferring the fact that is
          still true, and declining to answer when the evidence is not there.
        </p>

        <Link
          to="/dashboard"
          className="mt-1 inline-flex items-center justify-center rounded-full bg-brand-solid
            px-[clamp(1.5rem,3.2vh,2rem)] py-[clamp(0.65rem,1.7vh,1rem)]
            text-[clamp(0.875rem,1.65vh,1rem)] font-medium text-white no-underline
            transition-[filter,transform] hover:brightness-110 active:scale-[0.98]
            animate-rise [animation-delay:420ms]"
        >
          Get Started
        </Link>
      </div>
    </section>
  );
}
