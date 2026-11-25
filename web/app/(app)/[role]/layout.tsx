"use client";
import { useParams, useRouter } from "next/navigation";
import { useEffect } from "react";
import Shell from "@/components/Shell";
import { Loading } from "@/components/kit";
import { roleHome, type Role } from "@/lib/api";
import { useAuth } from "@/lib/auth";

const ROLES = ["admin", "manager", "hr", "teamlead", "employee"];

export default function RoleLayout({ children }: { children: React.ReactNode }) {
  const { role } = useParams<{ role: string }>();
  const { user, loading } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (loading) return;
    if (!user) router.replace("/login");
    else if (!ROLES.includes(role) || user.role !== role) router.replace(roleHome[user.role] || "/login");
  }, [user, loading, role, router]);

  if (loading || !user || user.role !== role) return <div className="mx-auto max-w-5xl p-6"><Loading /></div>;
  return <Shell role={user.role}>{children}</Shell>;
}
