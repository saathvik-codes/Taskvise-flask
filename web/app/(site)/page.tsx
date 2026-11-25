import Link from "next/link";
import "./landing.css";

const roles = [
  ["admin", "Admin", "Manage people, projects and tasks, and see analytics and skill gaps across the organisation."],
  ["hr", "HR", "Keep the people directory current and follow leave and onboarding."],
  ["manager", "Manager", "Approve leave, balance workload, review payments and write team notes."],
  ["lead", "Team lead", "Plan the team's projects and tasks, and check progress in reports."],
  ["employee", "Employee", "See your tasks, projects and workload, request leave and read notifications."],
];
const steps = [
  ["Add your people", "Create accounts, or let people sign in with Google and set up their profile."],
  ["Plan the work", "Create projects, break them into tasks and assign them with a due date and priority."],
  ["Track and balance", "Follow progress, spot overloaded teammates and move work before deadlines slip."],
];

export default function Landing() {
  return (
    <div className="landing-root">
      <header className="bar">
        <Link className="brand" href="/"><img src="/apple-touch-icon.png" alt="" width={30} height={30} />TaskVise</Link>
        <nav aria-label="Main">
          <a href="#roles">Roles</a>
          <a href="#how">How it works</a>
          <Link href="/login">Sign in</Link>
          <Link className="btn btn-primary" href="/signup">Create account</Link>
        </nav>
      </header>
      <main>
        <section className="hero">
          <div className="hero-copy">
            <h1>Run your team&apos;s work in one place.</h1>
            <p>Assign tasks, track projects, balance workload and handle leave. Everyone sees the view that fits their role.</p>
            <div className="cta">
              <Link className="btn btn-primary" href="/signup">Create account</Link>
              <Link className="btn btn-ghost" href="/login">Sign in</Link>
            </div>
          </div>
          <img className="hero-art" src="/art/tv-hero.webp" alt="Hands moving task cards between three columns on a worktable" width={1200} height={675} fetchPriority="high" />
        </section>
        <section id="roles" className="band">
          <h2>One workspace, five roles</h2>
          <div className="roles">
            {roles.map(([k, t, d]) => (
              <article key={k}><img src={`/art/tv-role-${k}.webp`} alt="" width={120} height={120} loading="lazy" /><h3>{t}</h3><p>{d}</p></article>
            ))}
          </div>
        </section>
        <section id="how" className="band">
          <h2>How it works</h2>
          <ol className="steps">{steps.map(([t, d], i) => <li key={t}><span>{i + 1}</span><h3>{t}</h3><p>{d}</p></li>)}</ol>
        </section>
        <section className="closing"><h2>Start with your team.</h2><Link className="btn btn-primary" href="/signup">Create account</Link></section>
      </main>
      <footer><span>TaskVise</span><Link href="/login">Sign in</Link></footer>
    </div>
  );
}
