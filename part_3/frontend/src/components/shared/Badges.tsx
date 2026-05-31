import type { RegistrationStatus, Role, SubmissionStatus } from "@/api/types";

export function StatusBadge({ status }: { status: SubmissionStatus | RegistrationStatus }) {
  return <span className={`badge badge-${status.replace("_", "-")}`}>{status.replace("_", " ")}</span>;
}

export function RoleBadge({ role }: { role: Role }) {
  return <span className={`badge role-${role}`}>{role}</span>;
}

export function ActiveBadge({ active }: { active: boolean }) {
  return <span className={`badge ${active ? "badge-active" : "badge-inactive"}`}>{active ? "active" : "inactive"}</span>;
}
