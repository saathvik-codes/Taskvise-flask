"use client";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useState } from "react";
import { BarChart3, Bell, Calendar, CheckSquare, Folder, LayoutGrid, LogOut, Menu, Scale, Settings, User, Users, X } from "lucide-react";
import { useAuth } from "@/lib/auth";
import { NAV, ROLE_LABEL } from "@/lib/nav";
import type { Role } from "@/lib/api";

const ICONS: Record<string, React.ComponentType<{ className?: string }>> = {
  layout: LayoutGrid, check: CheckSquare, folder: Folder, scale: Scale, calendar: Calendar, chart: BarChart3, bell: Bell, user: User, cog: Settings, users: Users,
};

export default function Shell({ role, children }: { role: Role; children: React.ReactNode }) {
  const { user, logout } = useAuth();
  const path = usePathname();
  const router = useRouter();
  const [open, setOpen] = useState(false);
  const items = NAV[role];
  const groups = [...new Set(items.map((i) => i.group || ""))];

  const rail = (
    <div className="flex h-full flex-col gap-4 overflow-y-auto p-3">
      <div className="flex items-center gap-2.5 px-2 pt-1">
        <img src="/icon-192.png" alt="" width={32} height={32} className="size-8 rounded-lg" />
        <span className="font-[family-name:var(--font-head)] text-lg font-bold">TaskVise</span>
      </div>
      <div className="flex items-center gap-2.5 rounded-xl border border-line bg-white p-2.5">
        <span className="grid size-9 flex-none place-items-center rounded-lg bg-orange text-sm font-bold text-white">{(user?.name || "?").charAt(0).toUpperCase()}</span>
        <div className="min-w-0"><p className="truncate text-sm font-semibold">{user?.name}</p><p className="text-xs text-muted">{ROLE_LABEL[role]}</p></div>
      </div>
      <nav aria-label="Sections" className="grid gap-4">
        {groups.map((g) => (
          <div key={g || "main"} className="grid gap-0.5">
            {g && <p className="px-2.5 pb-1 text-[11px] font-bold uppercase tracking-wide text-muted">{g}</p>}
            {items.filter((i) => (i.group || "") === g).map((i) => {
              const Icon = ICONS[i.icon] || LayoutGrid;
              const href = `/${role}/${i.view}`;
              const active = path === href;
              return (
                <Link key={i.view} href={href} onClick={() => setOpen(false)} aria-current={active ? "page" : undefined}
                  className={`flex min-h-9 items-center gap-2.5 rounded-lg px-2.5 text-sm font-medium ${active ? "bg-orange-soft text-orange-dark" : "text-slate hover:bg-[#f1efe9]"}`}>
                  <Icon className={`size-4 flex-none ${active ? "text-orange" : "text-muted"}`} />{i.label}
                </Link>
              );
            })}
          </div>
        ))}
      </nav>
      <button onClick={async () => { await logout(); router.replace("/login"); }} className="mt-auto flex min-h-9 items-center gap-2.5 rounded-lg px-2.5 text-sm font-medium text-slate hover:bg-[#f1efe9]"><LogOut className="size-4 text-muted" />Sign out</button>
    </div>
  );

  return (
    <div className="min-h-dvh lg:grid lg:grid-cols-[16rem_minmax(0,1fr)]">
      <aside className="sticky top-0 hidden h-dvh border-r border-line bg-rail lg:block">{rail}</aside>
      <div className="min-w-0">
        <header className="sticky top-0 z-20 flex h-14 items-center gap-3 border-b border-line bg-white/95 px-4 lg:hidden">
          <button aria-label="Open menu" onClick={() => setOpen(true)} className="grid size-9 place-items-center rounded-lg border border-line"><Menu className="size-5" /></button>
          <img src="/icon-192.png" alt="" width={28} height={28} className="size-7 rounded-md" /><span className="font-[family-name:var(--font-head)] font-bold">TaskVise</span>
        </header>
        <main className="mx-auto w-full max-w-6xl px-4 pb-16 pt-5 sm:px-6 lg:px-8 lg:pt-8">{children}</main>
      </div>
      {open && (
        <div className="fixed inset-0 z-40 lg:hidden" role="dialog" aria-modal="true">
          <button aria-label="Close menu" className="absolute inset-0 bg-black/30" onClick={() => setOpen(false)} />
          <aside className="absolute inset-y-0 left-0 w-72 max-w-[85vw] bg-rail shadow-xl">
            <button aria-label="Close menu" onClick={() => setOpen(false)} className="absolute right-2 top-2 grid size-8 place-items-center rounded-lg"><X className="size-5" /></button>
            {rail}
          </aside>
        </div>
      )}
    </div>
  );
}
