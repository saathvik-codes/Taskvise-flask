import type { ComponentType } from "react";
import { LeaveView, NotificationsView, ProfileView, ProjectsView, TasksView, TeamView } from "./common";
import { AdminDashboard, AdminEmployees, AdminSettings, EmployeeOverview, EmployeeReports, EmployeeSettings, LeadOverview, LeadReports, WorkloadView } from "./roles";

const lead = { overview: LeadOverview, team: TeamView, projects: ProjectsView, tasks: TasksView, reports: LeadReports, notifications: NotificationsView, profile: ProfileView };

export const VIEWS: Record<string, Record<string, ComponentType>> = {
  employee: { overview: EmployeeOverview, tasks: TasksView, projects: ProjectsView, workload: WorkloadView, leave: LeaveView, reports: EmployeeReports, notifications: NotificationsView, profile: ProfileView, settings: EmployeeSettings },
  admin: { dashboard: AdminDashboard, employees: AdminEmployees, projects: ProjectsView, tasks: TasksView, settings: AdminSettings },
  manager: { ...lead, leave: LeaveView },
  hr: { ...lead, leave: LeaveView },
  teamlead: lead,
};
