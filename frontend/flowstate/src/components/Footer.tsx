import { brand } from '../config/brand';
import Logo from './Logo';
import './Footer.css';

export default function Footer() {
  return (
    <footer className="footer">
      <div className="container footer-inner">
        <Logo />
        <nav>
          <a href="#docs">Docs</a>
          <a href="#changelog">Changelog</a>
          <a href="#privacy">Privacy</a>
          <a href="#terms">Terms</a>
        </nav>
        <span className="footer-copy">© {new Date().getFullYear()} {brand.name}</span>
      </div>
    </footer>
  );
}
