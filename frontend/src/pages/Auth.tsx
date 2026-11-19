import { useState, type FormEvent } from "react";
import { LogoMark } from "../components/Brand";
import { useAuth } from "../lib/auth";
import { navigate, type Route } from "../lib/router";

function home(role: string) {
  return role === "ADMIN" ? "/admin" : role === "VENUE_OPERATOR" || role === "GUIDE" ? "/operator" : "/dashboard";
}

export function Login({ route }: { route: Route }) {
  const { login } = useAuth();
  const [u, setU] = useState("");
  const [p, setP] = useState("");
  const [err, setErr] = useState("");
  const [busy, setBusy] = useState(false);
  const submit = async (e: FormEvent) => {
    e.preventDefault(); setBusy(true); setErr("");
    try { const user = await login(u, p); navigate(route.query.get("next") || home(user.role)); }
    catch (x) { setErr((x as Error).message); } finally { setBusy(false); }
  };
  return (
    <div className="auth-wrap">
      <form className="auth-card" onSubmit={submit}>
        <LogoMark size={52} />
        <h1>Welcome back</h1>
        <p className="muted">Log in to reserve venues and guides.</p>
        <label>Username<input autoComplete="username" required value={u} onChange={(e) => setU(e.target.value)} /></label>
        <label>Password<input type="password" autoComplete="current-password" required value={p} onChange={(e) => setP(e.target.value)} /></label>
        {err && <div className="result result-err">{err}</div>}
        <button className="pill pill-solid pill-lg" disabled={busy}>{busy ? "Signing in…" : "Log in"}</button>
        <p className="small">New to CampBlazer? <a href="#/register">Create an account</a></p>
      </form>
    </div>
  );
}

export function Register() {
  const { register } = useAuth();
  const [v, setV] = useState<Record<string, string>>({ first_name: "", last_name: "", username: "", email: "", phone: "", password: "" });
  const [err, setErr] = useState("");
  const [busy, setBusy] = useState(false);
  const set = (k: string) => (e: { target: { value: string } }) => setV({ ...v, [k]: e.target.value });
  const submit = async (e: FormEvent) => {
    e.preventDefault(); setBusy(true); setErr("");
    try { await register(v); navigate("/dashboard"); }
    catch (x) { setErr((x as Error).message); } finally { setBusy(false); }
  };
  return (
    <div className="auth-wrap">
      <form className="auth-card" onSubmit={submit}>
        <LogoMark size={52} />
        <h1>Create your account</h1>
        <p className="muted">Campers can register here. Operators and guides are set up by an administrator.</p>
        <div className="grid-2">
          <label>First name<input required value={v.first_name} onChange={set("first_name")} /></label>
          <label>Last name<input required value={v.last_name} onChange={set("last_name")} /></label>
        </div>
        <label>Username<input required minLength={3} pattern="[\w.@+\-]+" value={v.username} onChange={set("username")} /></label>
        <label>Email<input required type="email" value={v.email} onChange={set("email")} /></label>
        <label>Mobile number <span className="muted">(optional)</span><input value={v.phone} onChange={set("phone")} placeholder="09XX XXX XXXX" /></label>
        <label>Password<input required type="password" minLength={8} autoComplete="new-password" value={v.password} onChange={set("password")} /></label>
        <small className="muted">At least 8 characters; avoid common or all-numeric passwords.</small>
        {err && <div className="result result-err">{err}</div>}
        <button className="pill pill-solid pill-lg" disabled={busy}>{busy ? "Creating…" : "Create account"}</button>
        <p className="small">Already registered? <a href="#/login">Log in</a></p>
      </form>
    </div>
  );
}
