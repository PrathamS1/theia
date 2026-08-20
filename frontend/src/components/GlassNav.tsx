import { Link } from 'react-router-dom';
import GlassSurface from './GlassSurface';

// Exported: SiteFooter links to the same repo, and one definition beats two.
export const GITHUB_URL = 'https://github.com/PrathamS1/hydra-brain';

export default function GlassNav() {
  return (
    <nav
      className="absolute inset-x-6 top-6 z-10 flex items-center justify-between gap-3"
      aria-label="Primary"
    >
      <div className="flex items-center gap-2 animate-glass-in">
        <span className="hidden text-[13px] font-medium text-[#17181a]/75 sm:inline">
          powered by
        </span>
        <img src="/img/hydradb-mark.webp" alt="HydraDB" className="h-[18px] w-auto" />
      </div>

      <GlassSurface
        borderRadius={50}
        className="absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 animate-glass-in"
      >
        {/* The mark stands in for the "T" — image + "heia" together read
         * "THEIA", so the link's own name carries the full word. */}
        <Link to="/" aria-label="Theia" className="flex items-baseline py-2 pl-3 pr-5 no-underline">
          <img src="/img/theia-mark.webp" alt="" className="h-[22px] w-auto" />
          <span className="-ml-[5px] font-instrument-serif text-[24px] italic uppercase leading-none text-[#17181a]">
            heia
          </span>
        </Link>
      </GlassSurface>

      <GlassSurface borderRadius={50} className="animate-glass-in">
        <div className="flex items-center gap-1 p-2">
          <a
            href="#about"
            className="hidden rounded-full px-4 py-2 text-[15px] text-[#17181a] no-underline transition-colors hover:bg-white/30 sm:inline-flex"
          >
            About
          </a>
          <a
            href={GITHUB_URL}
            target="_blank"
            rel="noreferrer"
            className="hidden rounded-full px-4 py-2 text-[15px] text-[#17181a] no-underline transition-colors hover:bg-white/30 sm:inline-flex"
          >
            GitHub
          </a>
          <Link
            to="/dashboard"
            className="ml-1 inline-flex items-center justify-center rounded-full bg-brand-solid px-6 py-2 text-[15px] font-medium text-white no-underline transition-[filter] hover:brightness-110 active:scale-[0.98]"
          >
            Get Started
          </Link>
        </div>
      </GlassSurface>
    </nav>
  );
}
