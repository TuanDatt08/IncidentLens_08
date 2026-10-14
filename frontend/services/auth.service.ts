import { apiRequest } from "@/lib/api-client";
import type { AuthSession } from "@/types/auth";

export const getSession = () => apiRequest<AuthSession>("/auth/me");
export const login = (email: string, password: string) => apiRequest<AuthSession>("/auth/login", { method: "POST", body: JSON.stringify({ email, password }) });
export const logout = () => apiRequest<void>("/auth/logout", { method: "POST" });
export const changePassword = (current_password: string, new_password: string) => apiRequest<void>("/auth/change-password", { method: "POST", body: JSON.stringify({ current_password, new_password }) });
