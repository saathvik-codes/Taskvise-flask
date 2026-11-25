export type Role = "admin" | "manager" | "hr" | "teamlead" | "employee";
export type User = { id: string; name: string; email: string; role: Role };

export class ApiError extends Error {
  constructor(message: string, public status: number) { super(message); }
}

// Same-origin calls; Next proxies /api to Flask and the session cookie rides along.
export async function api<T = any>(path: string, opts: { method?: string; body?: unknown } = {}): Promise<T> {
  const res = await fetch(path, {
    method: opts.method || (opts.body !== undefined ? "POST" : "GET"),
    headers: opts.body !== undefined ? { "Content-Type": "application/json" } : undefined,
    body: opts.body !== undefined ? JSON.stringify(opts.body) : undefined,
    credentials: "same-origin",
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new ApiError((data && (data.error || data.message)) || `Request failed (${res.status})`, res.status);
  return data as T;
}

export const when = (s?: string) => {
  if (!s) return "";
  const d = new Date(s.includes("T") ? s : s.replace(" ", "T"));
  return Number.isNaN(+d) ? s : d.toLocaleDateString("en-IN", { day: "numeric", month: "short", year: "numeric" });
};
export const money = (n: number | string | undefined) => new Intl.NumberFormat("en-IN", { style: "currency", currency: "INR", maximumFractionDigits: 0 }).format(Number(n || 0));
export const titleCase = (s: string) => s.replace(/[-_]/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
export const roleHome: Record<Role, string> = { admin: "/admin/dashboard", manager: "/manager/overview", hr: "/hr/overview", teamlead: "/teamlead/overview", employee: "/employee/overview" };
