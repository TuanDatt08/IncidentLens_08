export type Role = "engineer" | "reviewer" | "admin";
export type User = { id: string; email: string; display_name: string; roles: Role[]; is_active: boolean; must_change_password: boolean };
export type AuthSession = { user: User; csrf_token: string };
export type Permission = "incident:read" | "incident:create" | "analysis:create" | "report:edit" | "report:submit" | "report:approve" | "report:reject" | "user:manage";
const permissions: Record<Role, Permission[]> = {
  engineer: ["incident:read", "incident:create", "analysis:create", "report:edit", "report:submit"],
  reviewer: ["incident:read", "report:approve", "report:reject"],
  admin: ["incident:read", "user:manage"],
};
export function hasPermission(user: User | undefined, permission: Permission) {
  return Boolean(user && !user.must_change_password && user.roles.some(role => permissions[role].includes(permission)));
}
