import { apiRequest } from "@/api/client";
import type { AdminNotification, AdminNotificationList, RefreshRun, RefreshRunList, SourceCheckResponse, SourceFile, SourceFileDownloadResponse, SourceFileList, SourceMonitorStatus } from "@/api/types";

export function getSourceMonitorStatus() {
  return apiRequest<SourceMonitorStatus>("/admin/source-monitor/status");
}

export function runSourceCheck() {
  return apiRequest<SourceCheckResponse>("/admin/source-monitor/check", { method: "POST" });
}

export function listSourceFiles(params: { limit?: number; offset?: number } = {}) {
  return apiRequest<SourceFileList>("/admin/source-files", { params });
}

export function getSourceFile(sourceFileId: string) {
  return apiRequest<SourceFile>(`/admin/source-files/${sourceFileId}`);
}

export function downloadSourceFile(sourceFileId: string) {
  return apiRequest<SourceFileDownloadResponse>(`/admin/source-files/${sourceFileId}/download`, { method: "POST" });
}

export function importSourceFile(sourceFileId: string) {
  return apiRequest<RefreshRun>(`/admin/source-files/${sourceFileId}/import`, { method: "POST" });
}

export function listRefreshRuns(params: { limit?: number; offset?: number } = {}) {
  return apiRequest<RefreshRunList>("/admin/refresh-runs", { params });
}

export function getRefreshRun(refreshRunId: string) {
  return apiRequest<RefreshRun>(`/admin/refresh-runs/${refreshRunId}`);
}

export function listAdminNotifications(params: { notification_status?: "unread" | "read" | "resolved"; limit?: number; offset?: number } = {}) {
  return apiRequest<AdminNotificationList>("/admin/notifications", { params });
}

export function markNotificationRead(notificationId: string) {
  return apiRequest<AdminNotification>(`/admin/notifications/${notificationId}/read`, { method: "POST" });
}

export function resolveNotification(notificationId: string) {
  return apiRequest<AdminNotification>(`/admin/notifications/${notificationId}/resolve`, { method: "POST" });
}
