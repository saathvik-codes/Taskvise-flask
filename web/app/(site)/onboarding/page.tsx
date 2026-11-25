"use client";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { api, roleHome, type User } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import "../auth.css";

const DESIGNATIONS = ["Software Engineer", "Senior Software Engineer", "Lead Developer", "Frontend Developer", "Backend Developer", "Full Stack Developer", "DevOps Engineer", "UI/UX Designer", "Product Manager", "Project Manager", "Technical Architect", "Quality Assurance", "Business Analyst", "Data Analyst", "Marketing Specialist", "Sales Representative", "HR Specialist", "Operations Manager", "Finance Manager"];
const DEPARTMENTS = ["Engineering", "Product", "Design", "Marketing", "Sales", "Human Resources", "Finance", "Operations", "Quality Assurance", "DevOps", "Data Science", "Business Development", "Customer Support", "Legal", "IT"];

export default function Onboarding() {
  const router = useRouter();
  const { refresh } = useAuth();
  const [profile, setProfile] = useState<{ email: string; name: string } | null>(null);
  const [f, setF] = useState({ phone: "", designation: "", department: "" });
  const [skills, setSkills] = useState<string[]>([]);
  const [draft, setDraft] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    api<{ profile: { email: string; name: string } }>("/api/auth/google-profile").then((r) => setProfile(r.profile)).catch(() => router.replace("/login"));
  }, [router]);

  const addSkill = (raw: string) => { const v = raw.trim().replace(/,$/, ""); if (v && !skills.some((x) => x.toLowerCase() === v.toLowerCase())) setSkills((s) => [...s, v]); setDraft(""); };

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    const all = draft.trim() ? [...skills, draft.trim()] : skills;
    if (!all.length) { setError("Add at least one skill."); return; }
    setBusy(true); setError("");
    try {
      const r = await api<{ user: User }>("/api/auth/google-onboarding", { body: { ...f, skills: all } });
      await refresh(); router.replace(roleHome[r.user.role]);
    } catch (err) { setError(err instanceof Error ? err.message : "Could not finish setup"); setBusy(false); }
  }

  if (!profile) return null;
  return (
    <div className="auth-root">
      <header className="top"><Link className="brand" href="/"><img src="/apple-touch-icon.png" alt="" width={28} height={28} style={{ borderRadius: 7 }} />TaskVise</Link></header>
      <main className="stage">
        <img className="flank flank-l" src="/art/tv-auth-signup.webp" alt="" width={640} height={640} />
        <section className="card">
          <h1>Finish your profile</h1>
          <p className="lede">Signed in as {profile.email}. Tell us where you work and what you are good at.</p>
          {error && <div className="alert" role="alert">{error}</div>}
          <form onSubmit={submit}>
            <label className="field"><span>Phone (optional)</span><input type="tel" autoComplete="tel" value={f.phone} onChange={(e) => setF({ ...f, phone: e.target.value })} /></label>
            <label className="field"><span>Designation</span><select required value={f.designation} onChange={(e) => setF({ ...f, designation: e.target.value })}><option value="">Select designation</option>{DESIGNATIONS.map((d) => <option key={d}>{d}</option>)}</select></label>
            <label className="field"><span>Department</span><select required value={f.department} onChange={(e) => setF({ ...f, department: e.target.value })}><option value="">Select department</option>{DEPARTMENTS.map((d) => <option key={d}>{d}</option>)}</select></label>
            <label className="field"><span>Skills</span>
              <span className="chips">
                {skills.map((s) => <span key={s} className="chip">{s}<button type="button" aria-label={`Remove ${s}`} onClick={() => setSkills((x) => x.filter((y) => y !== s))}>×</button></span>)}
                <input placeholder="Type a skill, press Enter" aria-label="Add a skill" autoComplete="off" value={draft} onChange={(e) => setDraft(e.target.value)}
                  onKeyDown={(e) => { if (e.key === "Enter" || e.key === ",") { e.preventDefault(); addSkill(draft); } else if (e.key === "Backspace" && !draft) setSkills((x) => x.slice(0, -1)); }} />
              </span></label>
            <div className="actions"><button className="btn btn-primary" type="submit" disabled={busy}>{busy ? "Saving…" : "Go to my dashboard"}</button></div>
          </form>
        </section>
        <img className="flank flank-r" src="/art/tv-carousel-team.webp" alt="" width={640} height={640} />
      </main>
    </div>
  );
}
