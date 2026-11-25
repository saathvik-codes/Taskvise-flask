"use client";
import Link from "next/link";
import { useState } from "react";
import { api } from "@/lib/api";
import GoogleMark from "@/components/GoogleMark";
import "../auth.css";

const DESIGNATIONS = ["Software Engineer", "Senior Software Engineer", "Lead Developer", "Frontend Developer", "Backend Developer", "Full Stack Developer", "DevOps Engineer", "UI/UX Designer", "Product Manager", "Project Manager", "Technical Architect", "Quality Assurance", "Business Analyst", "Data Analyst", "Marketing Specialist", "Sales Representative", "HR Specialist", "Operations Manager", "Finance Manager"];
const DEPARTMENTS = ["Engineering", "Product", "Design", "Marketing", "Sales", "Human Resources", "Finance", "Operations", "Quality Assurance", "DevOps", "Data Science", "Business Development", "Customer Support", "Legal", "IT"];
type Creds = { employeeId: string; name: string; username: string; password: string };

export default function Signup() {
  const [step, setStep] = useState(0);
  const [f, setF] = useState({ fullName: "", email: "", phone: "", designation: "", department: "" });
  const [skills, setSkills] = useState<string[]>([]);
  const [draft, setDraft] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [creds, setCreds] = useState<Creds | null>(null);
  const set = (k: string, v: string) => setF((s) => ({ ...s, [k]: v }));

  const addSkill = (raw: string) => {
    const v = raw.trim().replace(/,$/, "");
    if (v && !skills.some((s) => s.toLowerCase() === v.toLowerCase())) setSkills((s) => [...s, v]);
    setDraft("");
  };
  const next = (e: React.FormEvent) => { e.preventDefault(); setError(""); setStep((s) => s + 1); };

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    if (draft.trim()) addSkill(draft);
    const all = draft.trim() ? [...skills, draft.trim()] : skills;
    if (!all.length) { setError("Add at least one skill."); return; }
    setBusy(true); setError("");
    try { const r = await api<{ credentials: Creds }>("/api/auth/signup", { body: { ...f, skills: all } }); setCreds(r.credentials); }
    catch (err) { setError(err instanceof Error ? err.message : "Could not create the account"); setBusy(false); }
  }

  if (creds) {
    return (
      <div className="auth-root">
        <header className="top"><Link className="brand" href="/"><img src="/apple-touch-icon.png" alt="" width={28} height={28} style={{ borderRadius: 7 }} />TaskVise</Link></header>
        <main className="stage"><section className="card">
          <h1>Your account is ready</h1>
          <p className="lede">Save these sign-in details now. The password is shown only once.</p>
          <dl style={{ display: "grid", gap: ".75rem", margin: "1.25rem 0 0" }}>
            {[["Name", creds.name], ["Employee ID", creds.employeeId], ["Email", creds.username], ["Password", creds.password]].map(([k, v]) => (
              <div key={k}><dt style={{ fontSize: ".8rem", color: "var(--muted)" }}>{k}</dt><dd style={{ margin: 0, fontWeight: 700, fontFamily: k === "Password" ? "ui-monospace, monospace" : undefined }}>{v}</dd></div>
            ))}
          </dl>
          <div className="actions" style={{ marginTop: "1.5rem" }}><Link className="btn btn-primary" href="/login">Go to sign in</Link></div>
        </section></main>
      </div>
    );
  }

  return (
    <div className="auth-root">
      <header className="top">
        <Link className="brand" href="/"><img src="/apple-touch-icon.png" alt="" width={28} height={28} style={{ borderRadius: 7 }} />TaskVise</Link>
        <Link className="back" href="/">Back to home</Link>
      </header>
      <main className="stage">
        <img className="flank flank-l" src="/art/tv-auth-signup.webp" alt="" width={640} height={640} />
        <section className="card">
          <h1>Create your account</h1>
          <p className="lede">Three short steps and you are in.</p>
          <ol className="stepper" aria-label="Progress">
            {["You", "Your work", "Skills"].map((t, i) => <li key={t} aria-current={i === step ? "step" : undefined} data-done={i < step ? "" : undefined}>{t}</li>)}
          </ol>
          {error && <div className="alert" role="alert">{error}</div>}
          {step === 0 && (
            <form onSubmit={next}>
              <label className="field"><span>Full name</span><input autoComplete="name" placeholder="Asha Verma" required autoFocus value={f.fullName} onChange={(e) => set("fullName", e.target.value)} /></label>
              <label className="field"><span>Work email</span><input type="email" autoComplete="email" placeholder="you@company.com" required value={f.email} onChange={(e) => set("email", e.target.value)} /></label>
              <label className="field"><span>Phone</span><input type="tel" autoComplete="tel" placeholder="+91 98765 43210" required value={f.phone} onChange={(e) => set("phone", e.target.value)} /></label>
              <div className="actions"><button className="btn btn-primary" type="submit">Continue</button></div>
              <div className="or">or</div>
              <a className="btn btn-ghost" href={`${process.env.NEXT_PUBLIC_FLASK_URL || ""}/auth/google`}><GoogleMark />Continue with Google</a>
            </form>
          )}
          {step === 1 && (
            <form onSubmit={next}>
              <label className="field"><span>Designation</span>
                <select required value={f.designation} onChange={(e) => set("designation", e.target.value)}><option value="">Select designation</option>{DESIGNATIONS.map((d) => <option key={d}>{d}</option>)}</select></label>
              <label className="field"><span>Department</span>
                <select required value={f.department} onChange={(e) => set("department", e.target.value)}><option value="">Select department</option>{DEPARTMENTS.map((d) => <option key={d}>{d}</option>)}</select></label>
              <div className="actions"><button className="btn btn-ghost" type="button" onClick={() => setStep(0)}>Back</button><button className="btn btn-primary" type="submit">Continue</button></div>
            </form>
          )}
          {step === 2 && (
            <form onSubmit={submit}>
              <label className="field"><span>Skills</span>
                <span className="chips">
                  {skills.map((s) => <span key={s} className="chip">{s}<button type="button" aria-label={`Remove ${s}`} onClick={() => setSkills((x) => x.filter((y) => y !== s))}>×</button></span>)}
                  <input placeholder="Type a skill, press Enter" aria-label="Add a skill" autoComplete="off" value={draft} onChange={(e) => setDraft(e.target.value)}
                    onKeyDown={(e) => { if (e.key === "Enter" || e.key === ",") { e.preventDefault(); addSkill(draft); } else if (e.key === "Backspace" && !draft) setSkills((x) => x.slice(0, -1)); }} />
                </span>
                <span className="hint">Press Enter or comma after each one. We use them to match you to tasks.</span></label>
              <div className="actions"><button className="btn btn-ghost" type="button" onClick={() => setStep(1)}>Back</button><button className="btn btn-primary" type="submit" disabled={busy}>{busy ? "Creating…" : "Create account"}</button></div>
            </form>
          )}
          <p className="switch">Already have an account? <Link href="/login">Sign in</Link></p>
        </section>
        <img className="flank flank-r" src="/art/tv-carousel-team.webp" alt="" width={640} height={640} />
      </main>
    </div>
  );
}
