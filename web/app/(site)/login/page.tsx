"use client";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useState } from "react";
import { useAuth } from "@/lib/auth";
import { roleHome } from "@/lib/api";
import GoogleMark from "@/components/GoogleMark";
import "../auth.css";

export default function Login() {
  const { login } = useAuth();
  const router = useRouter();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [show, setShow] = useState(false);
  const [error, setError] = useState(useSearchParams().get("error") || "");
  const [busy, setBusy] = useState(false);

  async function submit(e: React.FormEvent) {
    e.preventDefault(); setBusy(true); setError("");
    try { const u = await login(username.trim(), password); router.replace(roleHome[u.role] || "/employee/overview"); }
    catch (err) { setError(err instanceof Error ? err.message : "Could not sign in"); setBusy(false); }
  }

  return (
    <div className="auth-root">
      <header className="top">
        <Link className="brand" href="/"><img src="/apple-touch-icon.png" alt="" width={28} height={28} style={{ borderRadius: 7 }} />TaskVise</Link>
        <Link className="back" href="/">Back to home</Link>
      </header>
      <main className="stage">
        <img className="flank flank-l" src="/art/tv-auth-signin.webp" alt="" width={640} height={640} />
        <section className="card">
          <h1>Sign in to TaskVise</h1>
          <p className="lede">Pick up your tasks, projects and team.</p>
          {error && <div className="alert" role="alert">{error}</div>}
          <form onSubmit={submit}>
            <label className="field"><span>Email or username</span>
              <input type="text" autoComplete="username" placeholder="you@company.com" required autoFocus value={username} onChange={(e) => setUsername(e.target.value)} /></label>
            <label className="field"><span>Password</span>
              <span className="pw"><input type={show ? "text" : "password"} autoComplete="current-password" placeholder="Your password" required value={password} onChange={(e) => setPassword(e.target.value)} />
                <button type="button" aria-pressed={show} aria-label="Show or hide password" onClick={() => setShow((s) => !s)}>{show ? "Hide" : "Show"}</button></span></label>
            <button className="btn btn-primary" type="submit" disabled={busy}>{busy ? "Signing in…" : "Sign in"}</button>
            <div className="or">or</div>
            <a className="btn btn-ghost" href={`${process.env.NEXT_PUBLIC_FLASK_URL || ""}/auth/google`}><GoogleMark />Continue with Google</a>
          </form>
          <p className="switch">New here? <Link href="/signup">Create an account</Link></p>
        </section>
        <img className="flank flank-r" src="/art/tv-carousel-board.webp" alt="" width={640} height={640} />
      </main>
    </div>
  );
}
