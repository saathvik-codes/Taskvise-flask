import type { Role } from "./api";

export type NavItem = { view: string; label: string; icon: string; group?: string };

// icon names resolve to lucide components in Shell
export const NAV: Record<Role, NavItem[]> = {
  employee: [
    { view: "overview", label: "Overview", icon: "layout" }, { view: "tasks", label: "My tasks", icon: "check" }, { view: "projects", label: "My projects", icon: "folder" },
    { view: "workload", label: "Workload and help", icon: "scale" }, { view: "leave", label: "Leave", icon: "calendar" }, { view: "reports", label: "Reports", icon: "chart" },
    { view: "notifications", label: "Notifications", icon: "bell", group: "Account" }, { view: "profile", label: "Profile", icon: "user", group: "Account" }, { view: "settings", label: "Settings", icon: "cog", group: "Account" },
  ],
  admin: [
    { view: "dashboard", label: "Dashboard", icon: "layout" }, { view: "employees", label: "Employees", icon: "users" }, { view: "projects", label: "Projects", icon: "folder" },
    { view: "tasks", label: "Tasks", icon: "check" }, { view: "settings", label: "Settings", icon: "cog", group: "Account" },
  ],
  manager: [
    { view: "overview", label: "Overview", icon: "layout" }, { view: "team", label: "Team", icon: "users" }, { view: "projects", label: "Projects", icon: "folder" }, { view: "tasks", label: "Tasks", icon: "check" },
    { view: "leave", label: "Leave approvals", icon: "calendar" }, { view: "reports", label: "Reports", icon: "chart" },
    { view: "notifications", label: "Notifications", icon: "bell", group: "Account" }, { view: "profile", label: "Profile", icon: "user", group: "Account" },
  ],
  hr: [
    { view: "overview", label: "Overview", icon: "layout" }, { view: "team", label: "People", icon: "users" }, { view: "projects", label: "Projects", icon: "folder" }, { view: "tasks", label: "Tasks", icon: "check" },
    { view: "leave", label: "Leave", icon: "calendar" }, { view: "reports", label: "Reports", icon: "chart" },
    { view: "notifications", label: "Notifications", icon: "bell", group: "Account" }, { view: "profile", label: "Profile", icon: "user", group: "Account" },
  ],
  teamlead: [
    { view: "overview", label: "Overview", icon: "layout" }, { view: "team", label: "Team", icon: "users" }, { view: "projects", label: "Projects", icon: "folder" }, { view: "tasks", label: "Tasks", icon: "check" },
    { view: "reports", label: "Reports", icon: "chart" },
    { view: "notifications", label: "Notifications", icon: "bell", group: "Account" }, { view: "profile", label: "Profile", icon: "user", group: "Account" },
  ],
};

export const ROLE_LABEL: Record<Role, string> = { admin: "Administrator", manager: "Manager", hr: "HR", teamlead: "Team lead", employee: "Employee" };
// HR uses the manager endpoints
export const apiBase = (role: Role) => (role === "hr" ? "manager" : role);
