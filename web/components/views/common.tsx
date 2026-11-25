"use client";
import { useState } from "react";
import { api, titleCase, when, type Role } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { apiBase } from "@/lib/nav";
import { Avatar, Badge, Bar, Empty, Field, Loading, Msg, Page, Panel, Table, useApi } from "@/components/kit";

export const useRole = (): Role => useAuth().user!.role;

export function NotificationsView() {
  const role = useRole(); const base = apiBase(role);
  const { data, loading, error, reload } = useApi<any[]>(`/api/${base}/notifications`);
  if (loading) return <Loading />;
  const list = Array.isArray(data) ? data : [];
  const mark = async (id: string) => { await api(`/api/${base}/notifications/${id}/read`, { method: "POST", body: {} }); reload(); };
  return (
    <Page title="Notifications" subtitle={`${list.filter((n) => !Number(n.is_read) && n.is_read !== "true").length} unread`}
      actions={<button className="dx-btn dx-ghost" onClick={async () => { await api(`/api/${base}/notifications/read-all`, { method: "POST", body: {} }); reload(); }}>Mark all read</button>}>
      {error && <Msg>{error}</Msg>}
      <Panel pad={false}>
        {list.length === 0 ? <Empty art="tv-empty-notifications" text="You are all caught up." /> : (
          <ul className="divide-y divide-line">{list.map((n) => {
            const unread = !(Number(n.is_read) === 1 || String(n.is_read).toLowerCase() === "true");
            return (
              <li key={n.id} className={`flex items-start justify-between gap-3 px-4 py-3 ${unread ? "bg-orange-soft/40" : ""}`}>
                <div className="min-w-0"><p className="text-sm font-semibold">{n.title}</p><p className="text-sm text-muted">{n.message}</p><p className="mt-0.5 text-xs text-muted">{when(n.created_at)}</p></div>
                {unread && <button className="dx-btn dx-ghost flex-none" onClick={() => mark(n.id)}>Mark read</button>}
              </li>
            );
          })}</ul>
        )}
      </Panel>
    </Page>
  );
}

export function ProfileView() {
  const { user, refresh } = useAuth();
  const { data, loading, reload } = useApi<any>(`/api/employee/${user!.id}`);
  const [f, setF] = useState<Record<string, string> | null>(null);
  const [pw, setPw] = useState({ current_password: "", new_password: "" });
  const [msg, setMsg] = useState<{ ok: boolean; text: string } | null>(null);
  const [pmsg, setPmsg] = useState<{ ok: boolean; text: string } | null>(null);
  if (loading) return <Loading />;
  const e = data?.employee || data || {};
  const form = f ?? { name: e.name || user!.name, phone: e.phone || "", location: e.location || "", position: e.position || "", skills: String(e.skills || "") };
  const set = (k: string, v: string) => setF({ ...form, [k]: v });

  async function save(ev: React.FormEvent) {
    ev.preventDefault(); setMsg(null);
    try { await api("/api/employee/profile/update", { body: form }); setMsg({ ok: true, text: "Profile saved." }); await refresh(); reload(); } catch (err) { setMsg({ ok: false, text: err instanceof Error ? err.message : "Could not save" }); }
  }
  async function changePw(ev: React.FormEvent) {
    ev.preventDefault(); setPmsg(null);
    try { await api("/api/employee/password/change", { body: pw }); setPw({ current_password: "", new_password: "" }); setPmsg({ ok: true, text: "Password updated." }); } catch (err) { setPmsg({ ok: false, text: err instanceof Error ? err.message : "Could not update" }); }
  }
  return (
    <Page title="Profile" subtitle={`${user!.email} · ${e.department || ""}`}>
      <div className="grid gap-5 lg:grid-cols-2">
        <Panel title="Your details">
          <form onSubmit={save} className="grid gap-3">
            <Field label="Full name"><input className="dx-input" required value={form.name} onChange={(x) => set("name", x.target.value)} /></Field>
            <div className="grid gap-3 sm:grid-cols-2">
              <Field label="Phone"><input className="dx-input" value={form.phone} onChange={(x) => set("phone", x.target.value)} /></Field>
              <Field label="Location"><input className="dx-input" value={form.location} onChange={(x) => set("location", x.target.value)} /></Field>
            </div>
            <Field label="Designation"><input className="dx-input" value={form.position} onChange={(x) => set("position", x.target.value)} /></Field>
            <Field label="Skills (comma separated)"><input className="dx-input" value={form.skills} onChange={(x) => set("skills", x.target.value)} /></Field>
            {msg && <Msg ok={msg.ok}>{msg.text}</Msg>}
            <button className="dx-btn dx-primary justify-self-start">Save changes</button>
          </form>
        </Panel>
        <Panel title="Change password">
          <form onSubmit={changePw} className="grid gap-3">
            <Field label="Current password"><input className="dx-input" type="password" autoComplete="current-password" required value={pw.current_password} onChange={(x) => setPw({ ...pw, current_password: x.target.value })} /></Field>
            <Field label="New password"><input className="dx-input" type="password" autoComplete="new-password" minLength={8} required value={pw.new_password} onChange={(x) => setPw({ ...pw, new_password: x.target.value })} /></Field>
            {pmsg && <Msg ok={pmsg.ok}>{pmsg.text}</Msg>}
            <button className="dx-btn dx-primary justify-self-start">Update password</button>
          </form>
        </Panel>
      </div>
    </Page>
  );
}

const norm = (p: any) => ({
  id: p.id, name: p.name, status: p.status || "active", progress: Number(p.progress || 0), start: p.startDate || p.start_date, end: p.endDate || p.end_date || p.deadline,
  owner: p.owner_name || p.team_name || "",
});
export function ProjectsView() {
  const role = useRole(); const base = apiBase(role);
  const { data, loading, error } = useApi<any[]>(`/api/${base}/projects`);
  if (loading) return <Loading />;
  const rows = (Array.isArray(data) ? data : []).map(norm);
  return (
    <Page title="Projects" subtitle={`${rows.length} projects`}>
      {error && <Msg>{error}</Msg>}
      <Panel pad={false}>
        <Table rows={rows} empty="No projects yet." art="tv-empty-projects" cols={[
          { head: "Project", cell: (r) => <span className="font-semibold">{r.name}</span> },
          { head: "Status", cell: (r) => <Badge>{r.status}</Badge> },
          { head: "Progress", cell: (r) => <Bar value={r.progress} /> },
          { head: "Owner", cell: (r) => r.owner || "-" },
          { head: "Dates", cell: (r) => <span className="whitespace-nowrap text-muted">{when(r.start)} to {when(r.end)}</span> },
        ]} />
      </Panel>
    </Page>
  );
}

export function TeamView() {
  const role = useRole(); const base = apiBase(role);
  const { data, loading, error } = useApi<any[]>(`/api/${base}/employees`);
  if (loading) return <Loading />;
  const rows = Array.isArray(data) ? data : [];
  return (
    <Page title={role === "hr" ? "People" : "Team"} subtitle={`${rows.length} people`}>
      {error && <Msg>{error}</Msg>}
      <Panel pad={false}>
        <Table rows={rows} empty="No people to show." art="tv-empty-employees" cols={[
          { head: "Name", cell: (r) => <span className="flex items-center gap-2"><Avatar name={r.name} /><span><b className="block text-sm">{r.name}</b><span className="text-xs text-muted">{r.email}</span></span></span> },
          { head: "Department", cell: (r) => r.department },
          { head: "Role", cell: (r) => r.position || "-" },
          { head: "Done", cell: (r) => r.completedTasks ?? "-" },
          { head: "Completion", cell: (r) => (r.completionRate != null ? <Bar value={Number(r.completionRate)} /> : "-") },
        ]} />
      </Panel>
    </Page>
  );
}

export function TasksView() {
  const role = useRole(); const base = apiBase(role);
  const canAssign = role !== "employee";
  const { data, loading, error, reload } = useApi<any[]>(`/api/${base}/tasks`);
  const people = useApi<any[]>(canAssign && role !== "admin" ? `/api/${base}/employees` : role === "admin" ? "/api/admin/employees" : null);
  const projects = useApi<any[]>(canAssign ? `/api/${base}/projects` : null);
  const [open, setOpen] = useState(false);
  const [f, setF] = useState({ title: "", description: "", assignee_id: "", project_id: "", priority: "medium", due_date: "" });
  const [msg, setMsg] = useState("");
  const [filter, setFilter] = useState("all");
  if (loading) return <Loading />;
  const all = Array.isArray(data) ? data : [];
  const rows = filter === "all" ? all : all.filter((t) => String(t.status).toLowerCase() === filter);
  const assignPath = role === "admin" ? "/api/admin/tasks" : `/api/${base}/tasks/assign`;

  async function create(ev: React.FormEvent) {
    ev.preventDefault(); setMsg("");
    try { await api(assignPath, { body: f }); setOpen(false); setF({ title: "", description: "", assignee_id: "", project_id: "", priority: "medium", due_date: "" }); reload(); } catch (err) { setMsg(err instanceof Error ? err.message : "Could not create the task"); }
  }
  async function setStatus(id: string, status: string) {
    if (role === "employee") await api("/api/employee/tasks/update-status", { body: { id, status } });
    else await api(role === "admin" ? `/api/admin/tasks/${id}` : `/api/${base}/tasks/${id}`, { method: "PUT", body: { status } });
    reload();
  }
  async function remove(id: string) {
    if (!confirm("Delete this task?")) return;
    await api(role === "admin" ? `/api/admin/tasks/${id}` : `/api/${base}/tasks/${id}`, { method: "DELETE" }); reload();
  }

  return (
    <Page title={role === "employee" ? "My tasks" : "Tasks"} subtitle={`${all.length} tasks`}
      actions={<>
        <select className="dx-input w-auto" aria-label="Filter by status" value={filter} onChange={(e) => setFilter(e.target.value)}>
          <option value="all">All</option><option value="todo">To do</option><option value="in-progress">In progress</option><option value="done">Done</option>
        </select>
        {canAssign && <button className="dx-btn dx-primary" onClick={() => setOpen((o) => !o)}>{open ? "Close" : "Assign a task"}</button>}
      </>}>
      {error && <Msg>{error}</Msg>}
      {open && (
        <Panel title="New task">
          <form onSubmit={create} className="grid gap-3 sm:grid-cols-2">
            <div className="sm:col-span-2"><Field label="Title"><input className="dx-input" required value={f.title} onChange={(e) => setF({ ...f, title: e.target.value })} /></Field></div>
            <div className="sm:col-span-2"><Field label="Description"><textarea className="dx-input" rows={2} value={f.description} onChange={(e) => setF({ ...f, description: e.target.value })} /></Field></div>
            <Field label="Assign to"><select className="dx-input" required value={f.assignee_id} onChange={(e) => setF({ ...f, assignee_id: e.target.value })}><option value="">Choose a person</option>{(people.data || []).map((p: any) => <option key={p.id} value={p.id}>{p.name}</option>)}</select></Field>
            <Field label="Project"><select className="dx-input" value={f.project_id} onChange={(e) => setF({ ...f, project_id: e.target.value })}><option value="">No project</option>{(projects.data || []).map((p: any) => <option key={p.id} value={p.id}>{p.name}</option>)}</select></Field>
            <Field label="Priority"><select className="dx-input" value={f.priority} onChange={(e) => setF({ ...f, priority: e.target.value })}><option>low</option><option>medium</option><option>high</option></select></Field>
            <Field label="Due date"><input className="dx-input" type="date" value={f.due_date} onChange={(e) => setF({ ...f, due_date: e.target.value })} /></Field>
            {msg && <div className="sm:col-span-2"><Msg>{msg}</Msg></div>}
            <div className="sm:col-span-2"><button className="dx-btn dx-primary">Create task</button></div>
          </form>
        </Panel>
      )}
      <Panel pad={false}>
        <Table rows={rows} empty="No tasks here." art="tv-empty-tasks" cols={[
          { head: "Task", cell: (t) => <span className="font-semibold">{t.title}</span> },
          ...(canAssign ? [{ head: "Assignee", cell: (t: any) => t.assignee_name || t.assignee_id || "-" }] : []),
          { head: "Priority", cell: (t) => <Badge>{t.priority || "medium"}</Badge> },
          { head: "Due", cell: (t) => <span className="whitespace-nowrap text-muted">{when(t.due_date)}</span> },
          { head: "Status", cell: (t) => (
            <select className="dx-input min-h-8 w-auto py-0.5 text-xs" aria-label={`Status of ${t.title}`} value={String(t.status).toLowerCase()} onChange={(e) => setStatus(t.id, e.target.value)}>
              <option value="todo">To do</option><option value="in-progress">In progress</option><option value="done">Done</option>
            </select>) },
          ...(role !== "employee" ? [{ head: "", cell: (t: any) => <button className="dx-btn dx-danger min-h-8" onClick={() => remove(t.id)}>Delete</button> }] : []),
        ]} />
      </Panel>
    </Page>
  );
}

export function LeaveView() {
  const role = useRole(); const isEmployee = role === "employee";
  const { data, loading, error, reload } = useApi<any[]>(isEmployee ? "/api/employee/leave" : "/api/manager/leave");
  const [f, setF] = useState({ type: "casual", startDate: "", endDate: "", reason: "" });
  const [msg, setMsg] = useState<{ ok: boolean; text: string } | null>(null);
  if (loading) return <Loading />;
  const rows = Array.isArray(data) ? data : [];

  async function apply(ev: React.FormEvent) {
    ev.preventDefault(); setMsg(null);
    try { await api("/api/employee/leave/apply", { body: f }); setF({ type: "casual", startDate: "", endDate: "", reason: "" }); setMsg({ ok: true, text: "Leave requested." }); reload(); } catch (err) { setMsg({ ok: false, text: err instanceof Error ? err.message : "Could not apply" }); }
  }
  const decide = async (id: string, status: string) => { await api("/api/manager/leave/update", { body: { id, status } }); reload(); };

  return (
    <Page title={isEmployee ? "Leave" : "Leave approvals"} subtitle={`${rows.length} requests`}>
      {error && <Msg>{error}</Msg>}
      {isEmployee && (
        <Panel title="Request leave">
          <form onSubmit={apply} className="grid gap-3 sm:grid-cols-4">
            <Field label="Type"><select className="dx-input" value={f.type} onChange={(e) => setF({ ...f, type: e.target.value })}><option value="casual">Casual</option><option value="sick">Sick</option><option value="annual">Annual</option><option value="unpaid">Unpaid</option></select></Field>
            <Field label="From"><input className="dx-input" type="date" required value={f.startDate} onChange={(e) => setF({ ...f, startDate: e.target.value })} /></Field>
            <Field label="To"><input className="dx-input" type="date" required min={f.startDate} value={f.endDate} onChange={(e) => setF({ ...f, endDate: e.target.value })} /></Field>
            <div className="flex items-end"><button className="dx-btn dx-primary w-full">Request</button></div>
            <div className="sm:col-span-4"><Field label="Reason"><input className="dx-input" required value={f.reason} onChange={(e) => setF({ ...f, reason: e.target.value })} /></Field></div>
            {msg && <div className="sm:col-span-4"><Msg ok={msg.ok}>{msg.text}</Msg></div>}
          </form>
        </Panel>
      )}
      <Panel pad={false}>
        <Table rows={rows} empty="No leave requests." art="tv-empty-leave" cols={[
          ...(!isEmployee ? [{ head: "Employee", cell: (r: any) => r.employee_name || r.employee_id }] : []),
          { head: "Type", cell: (r) => titleCase(r.type || "") },
          { head: "Dates", cell: (r) => <span className="whitespace-nowrap">{when(r.start_date)} to {when(r.end_date)}</span> },
          { head: "Reason", cell: (r) => <span className="text-muted">{r.reason}</span>, className: "max-w-xs truncate" },
          { head: "Status", cell: (r) => <Badge>{r.status}</Badge> },
          ...(!isEmployee ? [{ head: "", cell: (r: any) => String(r.status).toLowerCase() === "pending" ? <span className="flex gap-1.5"><button className="dx-btn dx-primary min-h-8" onClick={() => decide(r.id, "approved")}>Approve</button><button className="dx-btn dx-danger min-h-8" onClick={() => decide(r.id, "rejected")}>Reject</button></span> : null }] : []),
        ]} />
      </Panel>
    </Page>
  );
}
