import { apiRequest } from "@/lib/api-client";
import type { Role, User } from "@/types/auth";

export const listUsers = (offset = 0) => apiRequest<{ items: User[]; total: number; limit: number; offset: number }>(`/admin/users?limit=20&offset=${offset}`);
export const createUser = (data: { email: string; display_name: string; roles: Role[]; temporary_password: string }) => apiRequest<{ user: User }>("/admin/users", { method: "POST", body: JSON.stringify(data) });
export const updateUser = (id: string, data: { display_name?: string; roles?: Role[]; is_active?: boolean }) => apiRequest<{ user: User }>(`/admin/users/${encodeURIComponent(id)}`, { method: "PATCH", body: JSON.stringify(data) });
export const resetPassword = (id: string, temporary_password: string) => apiRequest<void>(`/admin/users/${encodeURIComponent(id)}/reset-password`, { method: "POST", body: JSON.stringify({ temporary_password }) });
