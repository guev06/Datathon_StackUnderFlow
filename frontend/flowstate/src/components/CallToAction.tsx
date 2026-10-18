import type { CSSProperties } from 'react';
import { brand } from '../config/brand';
import RepoInput from './RepoInput';
import './CallToAction.css';

export default function CallToAction() {
  return (
    <section className="cta container" id="pricing">
      <div className="cta-card">
        <div className="painting" style={{ '--painting': `url(${brand.paintings.section})` } as CSSProperties} />
        <div className="cta-wash" />
        <h2>
          Paint a picture <span className="serif">of your codebase.</span>
        </h2>
        <p>Free for public repositories.</p>
        <RepoInput />
      </div>
    </section>
  );
}
