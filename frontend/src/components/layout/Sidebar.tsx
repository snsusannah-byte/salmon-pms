import { Link, useLocation } from "react-router-dom";
import { cn } from "@/lib/utils";
import {
  LayoutDashboard,
  Building2,
  Users,
  Package,
  FileText,
  Boxes,
  Fish,
  PackageCheck,
  DollarSign,
  BarChart3,
  Settings,
  UserCog,
  TrendingUp,
} from "lucide-react";

const navItems = [
  { icon: LayoutDashboard, label: "数据看板", path: "/dashboard" },
  { icon: FileText, label: "进口单证", path: "/invoices" },
  { icon: Boxes, label: "批次管理", path: "/batches" },
  { icon: Fish, label: "整鱼销售", path: "/whole-fish-sales" },
  { icon: PackageCheck, label: "成品销售", path: "/finished-product-sales" },
  { icon: DollarSign, label: "财务管理", path: "/finance" },
  { icon: BarChart3, label: "报表中心", path: "/reports" },
];

const bottomNavItems = [
  { icon: Building2, label: "主体管理", path: "/companies" },
  { icon: Users, label: "客户管理", path: "/customers" },
  { icon: Package, label: "产品管理", path: "/products" },
  { icon: UserCog, label: "业务员", path: "/salespersons" },
  { icon: TrendingUp, label: "提成管理", path: "/commissions" },
  { icon: Settings, label: "系统设置", path: "/settings" },
];

export function Sidebar() {
  const location = useLocation();

  return (
    <aside className="w-64 border-r bg-card flex flex-col">
      <div className="p-6 border-b">
        <h1 className="text-lg font-bold">三文鱼 PMS</h1>
        <p className="text-xs text-muted-foreground">V8.2</p>
      </div>
      <nav className="flex-1 p-4 space-y-1">
        {navItems.map((item) => {
          const Icon = item.icon;
          const isActive = location.pathname === item.path;
          return (
            <Link
              key={item.path}
              to={item.path}
              className={cn(
                "flex items-center gap-3 px-3 py-2 rounded-md text-sm transition-colors",
                isActive
                  ? "bg-primary text-primary-foreground"
                  : "text-muted-foreground hover:bg-muted hover:text-foreground"
              )}
            >
              <Icon className="h-4 w-4" />
              {item.label}
            </Link>
          );
        })}
        {/* 次要模块分隔 */}
        <div className="pt-4 mt-2 border-t">
          <p className="px-3 text-xs text-muted-foreground mb-2">其他</p>
          {bottomNavItems.map((item) => {
            const Icon = item.icon;
            const isActive = location.pathname === item.path;
            return (
              <Link
                key={item.path}
                to={item.path}
                className={cn(
                  "flex items-center gap-3 px-3 py-2 rounded-md text-sm transition-colors",
                  isActive
                    ? "bg-primary text-primary-foreground"
                    : "text-muted-foreground hover:bg-muted hover:text-foreground"
                )}
              >
                <Icon className="h-4 w-4" />
                {item.label}
              </Link>
            );
          })}
        </div>
      </nav>
    </aside>
  );
}
