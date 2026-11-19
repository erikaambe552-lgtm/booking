import { useEffect, useState } from "react";
import { FiMenu, FiX, FiLogOut, FiUser } from "react-icons/fi";
import { useAuth } from "../lib/auth";
import { navigate } from "../lib/router";
import { Wordmark, LogoMark } from "./Brand";
import { LiveDot } from "../lib/realtime";

export function Navbar({ path }: { path: string }) {
  const { user, logout } = useAuth();
  const [open, setOpen] = useState(false);
  const [scrolled, setScrolled] = useState(false);
  useEffect(() => {
    const on = () => setScrolled(window.scrollY > 40);
    on();
    window.addEventListener("scroll", on);
    return () => window.removeEventListener("scroll", on);
  }, []);
  useEffect(() => setOpen(false), [path]);

  const dash = user?.role === "ADMIN" ? "/admin" : user?.role === "VENUE_OPERATOR" || user?.role === "GUIDE" ? "/operator" : "/dashboard";
  const links: [string, string][] = [["/", "Home"], ["/explore?category=BEACH", "Beaches"], ["/explore?category=MOUNTAIN", "Mountains"], ["/explore", "Explore"]];
  const isActive = (to: string) => (to === "/" ? path === "/" : path === to.split("?")[0] && !to.includes("?")) ;

  return (
    <header className={`nav ${scrolled || path !== "/" ? "nav-solid" : ""}`}>
      <a href="#/" className="nav-brand" aria-label="CampBlazer home"><Wordmark size={34} /></a>
      <nav className={`nav-links ${open ? "open" : ""}`}>
        {links.map(([to, label]) => (
          <a key={to} href={`#${to}`} className={isActive(to) ? "active" : ""}>{label}</a>
        ))}
        <div className="nav-mobile-auth">
          {user ? (
            <>
              <a href={`#${dash}`}>My dashboard</a>
              <button className="link-btn" onClick={() => logout().then(() => navigate("/"))}>Log out</button>
            </>
          ) : (
            <a href="#/login">Log in</a>
          )}
        </div>
      </nav>
      <div className="nav-actions">
        <LiveDot />
        {user ? (
          <>
            <a className="pill pill-ghost" href={`#${dash}`}><FiUser /> {user.first_name || user.username}</a>
            <button className="icon-btn" title="Log out" onClick={() => logout().then(() => navigate("/"))}><FiLogOut /></button>
          </>
        ) : (
          <>
            <a className="pill pill-ghost hide-sm" href="#/login">Log in</a>
            <a className="pill pill-solid" href="#/explore">Book now</a>
          </>
        )}
        <button className="icon-btn nav-toggle" aria-label="Menu" onClick={() => setOpen(!open)}>{open ? <FiX /> : <FiMenu />}</button>
      </div>
    </header>
  );
}

export function Footer() {
  return (
    <footer className="footer">
      <div className="footer-grid container">
        <div>
          <a href="#/"><LogoMark size={44} /></a>
          <p className="footer-tag">Discover and reserve camping destinations across the eight municipalities of Biliran Province, Philippines.</p>
        </div>
        <div>
          <h4>Explore</h4>
          <a href="#/explore?category=BEACH">Beaches · venue booking</a>
          <a href="#/explore?category=MOUNTAIN">Mountains · tour guides</a>
        </div>
        <div>
          <h4>Account</h4>
          <a href="#/register">Create account</a>
          <a href="#/login">Log in</a>
          <a href="#/dashboard">My reservations</a>
        </div>
        <div>
          <h4>About</h4>
          <p className="muted small">Discover, check availability, and book the best beaches, campsites, and mountain getaways in Biliran Province with CampBlazer.</p>
        </div>
      </div>
      <div className="footer-bottom container">
        <span>© {new Date().getFullYear()} CampBlazer · Biliran Province only</span>
        <span>Photos are shown with credit; illustrations are used where a licensed photo is pending.</span>
      </div>
    </footer>
  );
}

export function Splash() {
  const [hide, setHide] = useState(false);
  const [gone, setGone] = useState(false);
  useEffect(() => {
    const a = setTimeout(() => setHide(true), 900);
    const b = setTimeout(() => setGone(true), 1500);
    return () => { clearTimeout(a); clearTimeout(b); };
  }, []);
  if (gone) return null;
  return (
    <div className={`splash ${hide ? "splash-hide" : ""}`}>
      <LogoMark size={72} />
      <div className="splash-word">CAMP<b>BLAZER</b></div>
      <div className="splash-bar"><span /></div>
      <div className="splash-sub">Loading Biliran</div>
    </div>
  );
}
