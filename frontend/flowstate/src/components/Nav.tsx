import { Link } from 'react-router-dom';
import Logo from './Logo';
import './Nav.css';

export default function Nav() {
  return (
    <header className="nav">
      <div className="container nav-inner">
        <Logo />
        <nav className="nav-links">
          <a href="#features">Features</a>
          <a href="#how">How it works</a>
          <a href="#pricing">Pricing</a>
          <a href="#docs">Docs</a>
        </nav>
        <div className="nav-actions">
          <a className="btn btn-ghost" href="#signin">Sign in</a>
          <Link className="btn btn-primary" to="/explore">Try it free</Link>
        </div>
      </div>
    </header>
  );
}
