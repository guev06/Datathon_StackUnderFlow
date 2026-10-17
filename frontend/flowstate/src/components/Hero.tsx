import type { CSSProperties } from 'react';
import { brand } from '../config/brand';
import HeroPreviews from './HeroPreviews';
import RepoInput from './RepoInput';
import './Hero.css';

export default function Hero() {
  return (
    <section className="hero">
      <div className="painting" style={{ '--painting': `url(${brand.paintings.hero})` } as CSSProperties} />
      <div className="hero-wash" />
      <HeroPreviews />
      <div className="container hero-content">
        <div className="accent-pill">
          <span>New</span> AI dataflow maps powered by IBM Granite
        </div>
        <h1>
          See how your code <em className="serif gradient-text">flows</em>.
        </h1>
        <p className="hero-sub">
          Point {brand.name} at any repository. Get an interactive map of how data moves through it —
          click any node to jump straight to the line of code behind it.
        </p>
        <RepoInput />
        <p className="hero-note">Works with public Python repos on GitHub · No sign-up needed</p>
      </div>
    </section>
  );
}
