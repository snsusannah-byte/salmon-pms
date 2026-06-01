import { useEffect } from "react";
import { useNavigate, useLocation } from "react-router-dom";
import { getCachedUser, canAccessModule, MENU_MODULE_MAP } from "@/lib/permissions";
import { toast } from "sonner";

/**
 * 路由守卫 Hook — 在路由切换时检查权限
 * 
 * 用法：在 MainLayout 或需要守卫的组件中调用
 */
export function useRouteGuard() {
  const navigate = useNavigate();
  const location = useLocation();

  useEffect(() => {
    const user = getCachedUser();
    if (!user) return; // 未登录，由登录逻辑处理

    const role = user.role;
    if (role === "admin") return; // admin 全通

    const path = location.pathname;
    const module = MENU_MODULE_MAP[path] || "system";

    if (!canAccessModule(role, module)) {
      toast.error("权限不足，无法访问该页面");
      navigate("/dashboard", { replace: true });
    }
  }, [location.pathname, navigate]);
}
