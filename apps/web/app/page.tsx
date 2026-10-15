import Link from "next/link";
import { ArrowRight, Languages, ScanSearch, ShieldCheck } from "lucide-react";

const benefits = [
  {
    icon: Languages,
    index: "01",
    title: "Understand the words.",
    copy: "Literal meaning stays separate from interpretation, across English, Urdu, Hindi, and Spanish.",
  },
  {
    icon: ScanSearch,
    index: "02",
    title: "Understand the context.",
    copy: "Inspect timestamps, transcript cues, and curated references behind every cultural explanation.",
  },
  {
    icon: ShieldCheck,
    index: "03",
    title: "Know what is certain.",
    copy: "Bridge abstains when evidence runs out and surfaces contradictions instead of smoothing them over.",
  },
];

export default function HomePage() {
  return (
    <main>
      <section className="hero">
        <div className="hero-orbit" aria-hidden="true"><span /><span /><span /></div>
        <p className="kicker"><i /> Beyond translation</p>
        <h1>Understand more<br /><em>than words.</em></h1>
        <p className="hero-copy">
          Bridge helps you understand the language, humor, and cultural context behind videos from around the world.
        </p>
        <div className="hero-actions">
          <Link className="primary-action" href="/analyze">
            Analyze a video <ArrowRight size={18} />
          </Link>
          <Link className="secondary-action" href="/evaluation">View evaluation</Link>
        </div>
        <p className="availability">Live analysis requires a configured Gemini API key.</p>
      </section>

      <section className="benefits" aria-labelledby="benefits-title">
        <div className="section-intro">
          <p className="kicker"><i /> The difference</p>
          <h2 id="benefits-title">Meaning, with receipts.</h2>
        </div>
        <div className="benefit-grid">
          {benefits.map(({ icon: Icon, index, title, copy }) => (
            <article key={title} className="benefit-card">
              <div className="benefit-top"><Icon size={23} /><span>{index}</span></div>
              <h3>{title}</h3>
              <p>{copy}</p>
            </article>
          ))}
        </div>
      </section>

      <section className="trust-strip" aria-label="Data and AI limitations">
        <span>Private by design</span>
        <p>Uploads require explicit third-party AI disclosure. Avoid sensitive media in this local prototype.</p>
        <span>Interpretations can be wrong</span>
        <p>Cultural context is presented as evidence-backed interpretation, never universal truth.</p>
      </section>
    </main>
  );
}
