import { Link } from "react-router-dom";
import Logo from "./Logo";
import "./Nav.css";

export default function Nav() {
  return (
    <header className="nav">
      <div className="container nav-inner">
        <Logo />
        <nav className="nav-links">
          <a href="#features">Features</a>
          <a href="#how">How it works</a>
          <a href="#pricing">Pricing</a>
        </nav>
        <div className="nav-actions">
          <Link className="btn btn-primary" to="/explore">
            Try it free
          </Link>
        </div>
      </div>
    </header>
  );
}
