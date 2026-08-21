import GlassNav from '../components/GlassNav';
import Hero from '../components/Hero';
import ColonnadeSection from '../components/colonnade/ColonnadeSection';
import SiteFooter from '../components/SiteFooter';
import './Landing.css';

export default function Landing() {
  return (
    <div className="landing">
      <a className="skip-link" href="#main">Skip to content</a>

      {/* <main> wraps both sections so the skip link, the main landmark and
        * the footer's contentinfo all still line up. GlassNav stays inside
        * .hero-shell because that element is what its absolute positioning
        * resolves against. */}
      <main id="main">
        <div className="hero-shell">
          <GlassNav />
          <Hero />
        </div>

        <ColonnadeSection />
      </main>

      <SiteFooter />
    </div>
  );
}
