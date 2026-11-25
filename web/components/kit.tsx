"use client";
import { useCallback, useEffect, useState } from "react";
import { api } from "@/lib/api";

// Fetches JSON from the Flask API and lets a view reload after a change.
export function useApi<T = any>(path: string | null) {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const load = useCallback(async () => {
    if (!path) return;
    try { setData(await api<T>(path)); setError(""); } catch (e) { setError(e instanceof Error ? e.message : "Could not load"); } finally { setLoading(false); }
  }, [path]);
  useEffect(() => { void load(); }, [load]);
  return { data, error, loading, reload: load };
}

export function Page({ title, subtitle, actions, children }: { title: string; subtitle?: string; actions?: React.ReactNode; children: React.ReactNode }) {
  return (
    <div className="grid gap-5">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div className="min-w-0"><h1 className="font-[family-name:var(--font-head)] text-2xl font-bold tracking-tight">{title}</h1>{subtitle && <p className="mt-0.5 text-sm text-muted">{subtitle}</p>}</div>
        {actions && <div className="flex flex-wrap items-center gap-2">{actions}</div>}
      </div>
      {children}
    </div>
  );
}

export function Strip({ items }: { items: [string, string | number | undefined][] }) {
  return (
    <dl className="grid grid-cols-2 gap-px overflow-hidden rounded-xl border border-line bg-line md:grid-cols-4">
      {items.map(([l, v]) => (
        <div key={l} className="bg-white px-4 py-3.5"><dt className="text-xs font-medium text-muted">{l}</dt><dd className="mt-1 font-[family-name:var(--font-head)] text-2xl font-bold">{v ?? 0}</dd></div>
      ))}
    </dl>
  );
}

export function Panel({ title, actions, children, pad = true }: { title?: string; actions?: React.ReactNode; children: React.ReactNode; pad?: boolean }) {
  return (
    <section className="dx-card min-w-0 overflow-hidden">
      {(title || actions) && <div className="flex items-center justify-between gap-3 border-b border-line px-4 py-3"><h2 className="font-[family-name:var(--font-head)] text-base font-bold">{title}</h2>{actions}</div>}
      <div className={pad ? "p-4" : ""}>{children}</div>
    </section>
  );
}

export function Table<T>({ rows, cols, empty, art }: { rows: T[]; cols: { head: string; cell: (r: T) => React.ReactNode; className?: string }[]; empty: string; art?: string }) {
  if (!rows.length) return <Empty text={empty} art={art} />;
  return (
    <div className="overflow-x-auto">
      <table className="w-full min-w-[34rem] border-collapse">
        <thead className="border-b border-line bg-[#fbfaf7]"><tr>{cols.map((c) => <th key={c.head} className="dx-th">{c.head}</th>)}</tr></thead>
        <tbody>{rows.map((r, i) => <tr key={i} className="border-b border-line last:border-0 hover:bg-[#fbfaf7]">{cols.map((c) => <td key={c.head} className={`dx-td ${c.className || ""}`}>{c.cell(r)}</td>)}</tr>)}</tbody>
      </table>
    </div>
  );
}

export function Empty({ text, art }: { text: string; art?: string }) {
  return (
    <div className="grid justify-items-center gap-2 px-4 py-10 text-center">
      {art && <img src={`/art/${art}.webp`} alt="" width={160} height={120} className="h-auto w-36" />}
      <p className="text-sm text-muted">{text}</p>
    </div>
  );
}

const tones: Record<string, string> = {
  done: "bg-green-100 text-green-800", completed: "bg-green-100 text-green-800", approved: "bg-green-100 text-green-800", active: "bg-green-100 text-green-800",
  "in-progress": "bg-blue-100 text-blue-800", "in progress": "bg-blue-100 text-blue-800", pending: "bg-amber-100 text-amber-800", planning: "bg-amber-100 text-amber-800",
  high: "bg-red-100 text-red-800", rejected: "bg-red-100 text-red-800", overdue: "bg-red-100 text-red-800", medium: "bg-amber-100 text-amber-800", low: "bg-slate-100 text-slate-700", todo: "bg-slate-100 text-slate-700",
};
export const Badge = ({ children }: { children: string }) => (
  <span className={`inline-block whitespace-nowrap rounded-md px-2 py-0.5 text-xs font-semibold capitalize ${tones[String(children).toLowerCase()] || "bg-slate-100 text-slate-700"}`}>{String(children).replace(/[-_]/g, " ")}</span>
);

export const Bar = ({ value }: { value: number }) => (
  <div className="flex items-center gap-2"><div className="h-1.5 w-24 overflow-hidden rounded-full bg-[#ebe9e3]"><div className="h-full rounded-full bg-orange" style={{ width: `${Math.max(0, Math.min(100, value))}%` }} /></div><span className="text-xs text-muted">{Math.round(value)}%</span></div>
);

export const Field = ({ label, children }: { label: string; children: React.ReactNode }) => <label className="block"><span className="dx-label">{label}</span>{children}</label>;
export const Msg = ({ ok, children }: { ok?: boolean; children: React.ReactNode }) => <p role={ok ? "status" : "alert"} className={`rounded-lg px-3 py-2 text-sm ${ok ? "bg-green-50 text-green-800" : "bg-red-50 text-red-700"}`}>{children}</p>;
export const Loading = () => <div className="grid gap-3"><div className="h-20 animate-pulse rounded-xl bg-[#efece4]" /><div className="h-48 animate-pulse rounded-xl bg-[#efece4]" /></div>;
export const Avatar = ({ name }: { name: string }) => <span className="grid size-8 flex-none place-items-center rounded-lg bg-orange-soft text-xs font-bold text-orange-dark">{(name || "?").split(" ").map((p) => p[0]).slice(0, 2).join("").toUpperCase()}</span>;
