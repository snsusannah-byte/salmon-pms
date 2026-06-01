/**
 * 前端权限工具
 * 与后端 permissions.py 对应
 */

import { useState, useEffect } from "react";

export type UserRole = "admin" | "finance" | "sales" | "warehouse" | "user";

export interface UserInfo {
  id: number;
  username: string;
  email: string;
  full_name?: string;
  role: UserRole;
  is_active: boolean;
}

// ========== 权限矩阵 ==========

const MODULE_PERMISSIONS: Record<string, UserRole[]> = {
  finance: ["admin", "finance"],
  reports: ["admin", "finance"],
  sales: ["admin", "sales"],
  customers: ["admin", "sales"],
  receivable: ["admin", "sales", "finance"],
  warehouse: ["admin", "warehouse"],
  materials: ["admin", "warehouse"],
  batches: ["admin", "warehouse", "sales"],
  purchase: ["admin", "warehouse", "sales"],
  suppliers: ["admin", "warehouse", "sales"],
  production: ["admin", "warehouse"],
  system: ["admin"],
  users: ["admin"],
};

/**
 * 检查角色是否有模块权限
 * user 角色默认可查看所有模块（后端控制写入权限）
 */
export function canAccessModule(role: UserRole, module: string): boolean {
  const allowed = MODULE_PERMISSIONS[module];
  if (!allowed) return true; // 未定义权限的模块默认开放
  return role === "admin" || role === "user" || allowed.includes(role);
}

/**
 * 检查角色是否可以执行敏感操作
 */
export function canPerformAction(
  role: UserRole,
  action: "delete" | "lock" | "unlock" | "batch_import" | "approve"
): boolean {
  const map: Record<string, UserRole[]> = {
    delete: ["admin"],
    unlock: ["admin"],
    lock: ["admin", "warehouse", "finance"],
    batch_import: ["admin", "finance"],
    approve: ["admin", "finance"],
  };
  const allowed = map[action] || ["admin"];
  return role === "admin" || allowed.includes(role);
}

// ========== React Hook ==========

export function useAuth(): { user: UserInfo | null; role: UserRole; isAdmin: boolean; loading: boolean } {
  const [user, setUser] = useState<UserInfo | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const cached = getCachedUser();
    setUser(cached);
    setLoading(false);
  }, []);

  const role = user?.role ?? "user";
  return { user, role, isAdmin: role === "admin", loading };
}

// ========== 菜单权限配置 ==========

export interface NavItem {
  icon: string; // lucide icon name
  label: string;
  path: string;
  module: string;
  requireAdmin?: boolean;
}

/** 各分组对应的模块 */
export const MENU_MODULE_MAP: Record<string, string> = {
  "/reports/financial": "reports",
  "/reports/batches": "reports",
  "/reports/invoices": "reports",
  "/reports/receivable": "receivable",
  "/reports/payable": "finance",
  "/reports/netting": "finance",
  "/finance": "finance",
  "/bank-accounts": "finance",
  "/warehouse-v2": "warehouse",
  "/purchase-orders": "warehouse",
  "/materials": "warehouse",
  "/production": "production",
  "/finished-product-sales": "sales",
  "/made-to-order": "sales",
  "/returns": "sales",
  "/customers": "sales",
  "/salespersons": "sales",
  "/commissions": "sales",
  "/companies": "system",
  "/suppliers": "purchase",
  "/settings": "system",
};

/**
 * 根据角色过滤菜单项
 */
export function filterNavByRole<T extends { path: string }>(
  items: T[],
  role: UserRole
): T[] {
  if (role === "admin") return items;
  return items.filter((item) => {
    const module = MENU_MODULE_MAP[item.path] || "system";
    return canAccessModule(role, module);
  });
}

/**
 * 从 localStorage 读取缓存的用户信息
 */
export function getCachedUser(): UserInfo | null {
  try {
    const raw = localStorage.getItem("salmon_user");
    return raw ? (JSON.parse(raw) as UserInfo) : null;
  } catch {
    return null;
  }
}

export function setCachedUser(user: UserInfo | null): void {
  if (user) {
    localStorage.setItem("salmon_user", JSON.stringify(user));
  } else {
    localStorage.removeItem("salmon_user");
  }
}
