"use client";
import { useState } from "react";
import { api, when } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { apiBase } from "@/lib/nav";
import { Avatar, Badge, Bar, Empty, Field, Loading, Msg, Page, Panel, Strip, Table, useApi } from "@/components/kit";
import { useRole } from "./common";

const arr = (x: any): any[] => (Array.isArray(x) ? x : []);
const Row = ({ k, v }: { k: string; v: React.ReactNode }) => <div className="flex justify-between gap-3 border-b border-line py-2 text-sm last:border-0"><span className="text-muted">{k}</span><b>{v}</b></div>;

// ---- employee ----
export function EmployeeOverview() {
  const { user } = useAuth();
  const a = useApi<any>("/api/employee/analytics");
  const t = useApi<any[]>("/api/employee/tasks");
  const p = useApi<any[]>("/api/employee/projects");
  if (a.loading) return <Loading />;
  const s = a.data || {};
  const tasks = arr(t.data).filter((x) => String(x.status).toLowerCase() !== "done").slice(0, 6);
  return (
    <Page title={`Hello, ${user!.name.split(" ")[0]}`} subtitle="Here is where your work stands today.">
      <Strip items={[["Total tasks", s.totalTasks], ["Completed", s.completedTasks], ["Completion", `${s.completionRate ?? 0}%`], ["Active projects", s.activeProjects]]} />
      <div className="grid gap-5 lg:grid-cols-2">
        <Panel title="Up next" pad={false}>
          <Table rows={tasks} empty="No open tasks." art="tv-empty-tasks" cols={[{ head: "Task", cell: (r) => <b>{r.title}</b> }, { head: "Due", cell: (r) => <span className="text-muted">{when(r.due_date)}</span> }, { head: "Priority", cell: (r) => <Badge>{r.priority}</Badge> }]} />
        </Panel>
        <Panel title="Projects" pad={false}>
          <Table rows={arr(p.data).slice(0, 6)} empty="No projects yet." art="tv-empty-projects" cols={[{ head: "Project", cell: (r) => <b>{r.name}</b> }, { head: "Progress", cell: (r) => <Bar value={Number(r.progress || 0)} /> }]} />
        </Panel>
      </div>
    </Page>
  );
}

export function WorkloadView() {
  const team = useApi<any>("/api/employee/team-info");
  const help = useApi<any>("/api/employee/help-requests");
  const [f, setF] = useState({ message: "", urgency: "medium", requestType: "help" });
  const [msg, setMsg] = useState<{ ok: boolean; text: string } | null>(null);
  if (team.loading) return <Loading />;
  const requests = arr(help.data?.requests);
  async function send(ev: React.FormEvent) {
    ev.preventDefault(); setMsg(null);
    try { await api("/api/employee/help-request", { body: f }); setF({ ...f, message: "" }); setMsg({ ok: true, text: "Request sent." }); help.reload(); } catch (err) { setMsg({ ok: false, text: err instanceof Error ? err.message : "Could not send" }); }
  }
  const m = team.data?.manager;
  return (
    <Page title="Workload and help" subtitle="Your team, and a direct line when you are stuck.">
      <div className="grid gap-5 lg:grid-cols-2">
        <Panel title="Your team">
          {m && <div className="mb-3 flex items-center gap-2.5 rounded-lg bg-[#faf9f6] p-2.5"><Avatar name={m.name} /><div><p className="text-sm font-semibold">{m.name}</p><p className="text-xs text-muted">Manager</p></div></div>}
          {arr(team.data?.teammates).length ? <ul className="grid gap-2">{arr(team.data?.teammates).map((x) => <li key={x.id} className="flex items-center gap-2.5 text-sm"><Avatar name={x.name} />{x.name}</li>)}</ul> : <Empty text="No teammates listed yet." art="tv-empty-employees" />}
        </Panel>
        <Panel title="Ask for help">
          <form onSubmit={send} className="grid gap-3">
            <Field label="What do you need?"><textarea className="dx-input" rows={3} required value={f.message} onChange={(e) => setF({ ...f, message: e.target.value })} /></Field>
            <div className="grid grid-cols-2 gap-3">
              <Field label="Urgency"><select className="dx-input" value={f.urgency} onChange={(e) => setF({ ...f, urgency: e.target.value })}><option>low</option><option>medium</option><option>high</option></select></Field>
              <Field label="Type"><select className="dx-input" value={f.requestType} onChange={(e) => setF({ ...f, requestType: e.target.value })}><option value="help">Help</option><option value="workload">Workload</option></select></Field>
            </div>
            {msg && <Msg ok={msg.ok}>{msg.text}</Msg>}
            <button className="dx-btn dx-primary justify-self-start">Send request</button>
          </form>
        </Panel>
      </div>
      <Panel title="Your requests" pad={false}>
        <Table rows={requests} empty="No help requests yet." art="tv-empty-help" cols={[{ head: "Message", cell: (r) => r.message }, { head: "Urgency", cell: (r) => <Badge>{r.urgency || "medium"}</Badge> }, { head: "Status", cell: (r) => <Badge>{r.status || "pending"}</Badge> }, { head: "Sent", cell: (r) => <span className="text-muted">{when(r.created_at)}</span> }]} />
      </Panel>
    </Page>
  );
}

export function EmployeeReports() {
  const { data, loading } = useApi<any>("/api/employee/reports");
  if (loading) return <Loading />;
  const s = data?.summary || {};
  return (
    <Page title="Reports" subtitle={data?.period || ""}>
      <Strip items={[["Tasks", s.totalTasks], ["Completed", s.completedTasks], ["In progress", s.inProgressTasks], ["Completion", `${s.completionRate ?? 0}%`]]} />
      <Panel title={data?.reportTitle || "Summary"}>
        <Row k="Performance grade" v={data?.performanceGrade || "-"} /><Row k="Projects" v={s.totalProjects ?? 0} /><Row k="Pending tasks" v={s.pendingTasks ?? 0} />
        <Row k="Leave approved" v={s.approvedLeaves ?? 0} /><Row k="Leave pending" v={s.pendingLeaves ?? 0} />
      </Panel>
    </Page>
  );
}

export function EmployeeSettings() {
  const { data, loading, reload } = useApi<any>("/api/employee/settings");
  const [msg, setMsg] = useState("");
  if (loading) return <Loading />;
  const s = data?.settings || {};
  const toggles: [string, string][] = [["emailNotifications", "Email notifications"], ["pushNotifications", "Push notifications"], ["taskReminders", "Task reminders"], ["deadlineAlerts", "Deadline alerts"]];
  const isOn = (v: any) => v === true || String(v).toLowerCase() === "true";
  async function save(patch: Record<string, unknown>) { try { await api("/api/employee/settings/update", { body: { ...s, ...patch } }); setMsg("Saved."); reload(); } catch (e) { setMsg(e instanceof Error ? e.message : "Could not save"); } }
  return (
    <Page title="Settings" subtitle="Notifications and preferences.">
      <Panel title="Notifications">
        <ul className="divide-y divide-line">{toggles.map(([k, l]) => (
          <li key={k} className="flex items-center justify-between py-2.5 text-sm"><span>{l}</span>
            <input type="checkbox" className="size-4 accent-[#ea580c]" aria-label={l} checked={isOn(s[k])} onChange={(e) => save({ [k]: e.target.checked })} /></li>))}</ul>
      </Panel>
      <Panel title="Language and time zone">
        <div className="grid gap-3 sm:grid-cols-2">
          <Field label="Language"><select className="dx-input" value={s.language || "en"} onChange={(e) => save({ language: e.target.value })}><option value="en">English</option><option value="hi">Hindi</option></select></Field>
          <Field label="Time zone"><input className="dx-input" defaultValue={s.timezone || ""} onBlur={(e) => save({ timezone: e.target.value })} placeholder="Asia/Kolkata" /></Field>
        </div>
      </Panel>
      {msg && <Msg ok>{msg}</Msg>}
    </Page>
  );
}

// ---- manager, hr, team lead ----
export function LeadOverview() {
  const role = useRole(); const base = apiBase(role) === "teamlead" ? "teamlead" : "manager";
  const stats = useApi<any>(`/api/${base}/stats`);
  const notes = useApi<any[]>(`/api/${base}/notifications`);
  if (stats.loading) return <Loading />;
  const s = stats.data || {};
  return (
    <Page title={s.teamName || "Overview"} subtitle={[s.teamFocus, s.managerName && `Manager: ${s.managerName}`].filter(Boolean).join(" · ")}>
      <Strip items={[["Team size", s.teamSize], ["Active projects", s.activeProjects], ["Completed tasks", s.completedTasks], ["Overdue", s.overdueTasks]]} />
      <div className="grid gap-5 lg:grid-cols-2">
        <Panel title="Teams" pad={false}>
          <Table rows={arr(s.teamSummaries)} empty="No team data yet." art="tv-empty-employees" cols={[{ head: "Team", cell: (r) => <b>{r.team_name || r.department || r.id}</b> }, { head: "Focus", cell: (r) => <span className="text-muted">{r.focus_area}</span> }]} />
        </Panel>
        <Panel title="Latest notifications" pad={false}>
          {arr(notes.data).length ? <ul className="divide-y divide-line">{arr(notes.data).slice(0, 5).map((n) => <li key={n.id} className="px-4 py-2.5 text-sm"><b>{n.title}</b><span className="block text-muted">{n.message}</span></li>)}</ul> : <Empty text="Nothing new." art="tv-empty-notifications" />}
        </Panel>
      </div>
    </Page>
  );
}

export function LeadReports() {
  const role = useRole(); const base = apiBase(role) === "teamlead" ? "teamlead" : "manager";
  const { data, loading } = useApi<any>(`/api/${base}/analytics`);
  if (loading) return <Loading />;
  const d = data || {};
  return (
    <Page title="Reports" subtitle="Productivity and delivery across your people.">
      <Strip items={[["Active people", d.activeEmployees], ["Projects", d.activeProjects], ["Completion", `${d.completionRate ?? 0}%`], ["Productivity", `${d.avgProductivity ?? 0}%`]]} />
      <div className="grid gap-5 lg:grid-cols-2">
        <Panel title="Departments" pad={false}>
          <Table rows={arr(d.departmentStats)} empty="No data." art="tv-empty-analytics" cols={[{ head: "Department", cell: (r) => <b>{r.department}</b> }, { head: "People", cell: (r) => r.employee_count }, { head: "Projects", cell: (r) => r.project_count }, { head: "Progress", cell: (r) => <Bar value={Number(r.avg_progress || 0)} /> }]} />
        </Panel>
        <Panel title="People" pad={false}>
          <Table rows={arr(d.employeePerformance)} empty="No data." art="tv-empty-analytics" cols={[{ head: "Name", cell: (r) => <b>{r.name}</b> }, { head: "Done", cell: (r) => r.completedTasks }, { head: "Productivity", cell: (r) => <Bar value={Number(r.productivity || r.completionRate || 0)} /> }]} />
        </Panel>
      </div>
    </Page>
  );
}

// ---- admin ----
export function AdminDashboard() {
  const stats = useApi<any>("/api/admin/stats");
  const projects = useApi<any[]>("/api/admin/projects");
  if (stats.loading) return <Loading />;
  const s = stats.data || {};
  return (
    <Page title="Dashboard" subtitle="Your organisation at a glance.">
      <Strip items={[["Employees", s.totalEmployees], ["Active projects", s.activeProjects], ["Total tasks", s.totalTasks], ["Completed tasks", s.completedTasks]]} />
      <Panel title="Recent projects" pad={false}>
        <Table rows={arr(projects.data).slice(0, 8)} empty="No projects yet." art="tv-empty-projects" cols={[{ head: "Project", cell: (r) => <b>{r.name}</b> }, { head: "Owner", cell: (r) => r.owner_name || "-" }, { head: "Status", cell: (r) => <Badge>{r.status || "active"}</Badge> }, { head: "Progress", cell: (r) => <Bar value={Number(r.progress || 0)} /> }]} />
      </Panel>
    </Page>
  );
}

export function AdminEmployees() {
  const { data, loading, error, reload } = useApi<any[]>("/api/admin/employees");
  const [q, setQ] = useState("");
  const [open, setOpen] = useState(false);
  const [f, setF] = useState({ name: "", email: "", department: "", position: "", role: "employee", password: "" });
  const [msg, setMsg] = useState("");
  if (loading) return <Loading />;
  const needle = q.trim().toLowerCase();
  const rows = arr(data).filter((e) => `${e.name} ${e.email} ${e.department}`.toLowerCase().includes(needle));
  async function add(ev: React.FormEvent) {
    ev.preventDefault(); setMsg("");
    try { await api("/api/admin/employees", { body: f }); setOpen(false); setF({ name: "", email: "", department: "", position: "", role: "employee", password: "" }); reload(); } catch (err) { setMsg(err instanceof Error ? err.message : "Could not add"); }
  }
  async function remove(id: string, name: string) { if (confirm(`Remove ${name}?`)) { await api(`/api/admin/employees/${id}`, { method: "DELETE" }); reload(); } }
  return (
    <Page title="Employees" subtitle={`${arr(data).length} people`}
      actions={<><input className="dx-input w-56" type="search" placeholder="Search people" aria-label="Search people" value={q} onChange={(e) => setQ(e.target.value)} /><button className="dx-btn dx-primary" onClick={() => setOpen((o) => !o)}>{open ? "Close" : "Add employee"}</button></>}>
      {error && <Msg>{error}</Msg>}
      {open && (
        <Panel title="New employee">
          <form onSubmit={add} className="grid gap-3 sm:grid-cols-3">
            <Field label="Name"><input className="dx-input" required value={f.name} onChange={(e) => setF({ ...f, name: e.target.value })} /></Field>
            <Field label="Email"><input className="dx-input" type="email" required value={f.email} onChange={(e) => setF({ ...f, email: e.target.value })} /></Field>
            <Field label="Temporary password"><input className="dx-input" type="password" minLength={8} required value={f.password} onChange={(e) => setF({ ...f, password: e.target.value })} /></Field>
            <Field label="Department"><input className="dx-input" required value={f.department} onChange={(e) => setF({ ...f, department: e.target.value })} /></Field>
            <Field label="Designation"><input className="dx-input" required value={f.position} onChange={(e) => setF({ ...f, position: e.target.value })} /></Field>
            <Field label="Role"><select className="dx-input" value={f.role} onChange={(e) => setF({ ...f, role: e.target.value })}><option value="employee">Employee</option><option value="teamlead">Team lead</option><option value="manager">Manager</option><option value="hr">HR</option><option value="admin">Admin</option></select></Field>
            {msg && <div className="sm:col-span-3"><Msg>{msg}</Msg></div>}
            <div className="sm:col-span-3"><button className="dx-btn dx-primary">Add employee</button></div>
          </form>
        </Panel>
      )}
      <Panel pad={false}>
        <Table rows={rows} empty="No one matches." art="tv-empty-employees" cols={[
          { head: "Name", cell: (r) => <span className="flex items-center gap-2"><Avatar name={r.name} /><span><b className="block text-sm">{r.name}</b><span className="text-xs text-muted">{r.email}</span></span></span> },
          { head: "ID", cell: (r) => <span className="text-muted">{r.id}</span> }, { head: "Department", cell: (r) => r.department }, { head: "Role", cell: (r) => r.position || "-" },
          { head: "Joined", cell: (r) => <span className="whitespace-nowrap text-muted">{when(r.join_date)}</span> },
          { head: "", cell: (r) => <button className="dx-btn dx-danger min-h-8" onClick={() => remove(r.id, r.name)}>Remove</button> },
        ]} />
      </Panel>
    </Page>
  );
}

export function AdminSettings() {
  const { data, loading, reload } = useApi<any>("/api/admin/settings");
  const [msg, setMsg] = useState("");
  if (loading) return <Loading />;
  const s = data || {};
  const flags: [string, string][] = [["email_notifications", "Email notifications"], ["desktop_notifications", "Desktop notifications"], ["deadline_alerts", "Deadline alerts"], ["notify_project_updates", "Project update alerts"], ["notify_system_alerts", "System alerts"]];
  const isOn = (v: any) => String(v).toLowerCase() === "true";
  async function save(patch: Record<string, unknown>) { try { await api("/api/admin/settings", { method: "PUT", body: patch }); setMsg("Saved."); reload(); } catch (e) { setMsg(e instanceof Error ? e.message : "Could not save"); } }
  return (
    <Page title="Settings" subtitle="Organisation-wide preferences.">
      <Panel title="Organisation"><Field label="Company name"><input className="dx-input max-w-sm" defaultValue={s.company_name || ""} onBlur={(e) => save({ company_name: e.target.value })} /></Field></Panel>
      <Panel title="Notifications"><ul className="divide-y divide-line">{flags.map(([k, l]) => <li key={k} className="flex items-center justify-between py-2.5 text-sm"><span>{l}</span><input type="checkbox" className="size-4 accent-[#ea580c]" aria-label={l} checked={isOn(s[k])} onChange={(e) => save({ [k]: String(e.target.checked) })} /></li>)}</ul></Panel>
      {msg && <Msg ok>{msg}</Msg>}
    </Page>
  );
}
