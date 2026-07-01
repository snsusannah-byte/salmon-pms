import { Link, useLocation } from "react-router-dom";
import { cn } from "@/lib/utils";
import { getCachedUser, filterNavByRole, MENU_MODULE_MAP } from "@/lib/permissions";
import type { UserRole } from "@/lib/permissions";
import {
  LayoutDashboard,
  Building2,
  Banknote,
  Users,
  Boxes,
  FileCheck,
  Container,
  Fish,
  PackageCheck,
  Package,
  Landmark,
  BarChart3,
  Settings,
  UserCog,
  Percent,
  Warehouse,
  Factory,
  Layers,
  Store,
  Tag,
  FileSpreadsheet,
  Wrench,
  Archive,
  ArrowLeftRight,
  Ship,
  DollarSign,
  List,
  FileText,
  TrendingUp,
  ArrowDownLeft,
  ArrowUpRight,
  Shield,
} from "lucide-react";
import { useMemo } from "react";

const navItems = [
  { icon: LayoutDashboard, label: "数据看板", path: "/dashboard" },
  { icon: FileCheck, label: "进口单证", path: "/invoices" },
  { icon: Container, label: "批次管理", path: "/batches" },
  { icon: Ship, label: "进口销售", path: "/whole-fish-sales" },
];

const reportItems = [
  { icon: Package, label: "批次财报", path: "/reports/batches" },
  { icon: FileText, label: "单票财报", path: "/reports/invoices" },
  { icon: ArrowDownLeft, label: "应收对账", path: "/reports/receivable" },
  { icon: ArrowUpRight, label: "应付对账", path: "/reports/payable" },
  { icon: ArrowLeftRight, label: "往来对账", path: "/reports/netting" },
  { icon: BarChart3, label: "三大报表", path: "/reports/financial" },
];

const financeItems = [
  { icon: Ship, label: "进口费用", path: "/finance?tab=import" },
  { icon: DollarSign, label: "购汇登记", path: "/finance?tab=exchange" },
  { icon: List, label: "交易流水", path: "/finance?tab=transactions" },
];

const finishedProductItems = [
  { icon: TrendingUp, label: "以销定采", path: "/made-to-order" },
  { icon: PackageCheck, label: "预包装销售", path: "/finished-product-sales" },
  { icon: Factory, label: "生产管理", path: "/production" },
  { icon: Warehouse, label: "仓库管理", path: "/warehouse-v2" },
  { icon: Package, label: "采购入库", path: "/purchase-orders" },
  { icon: Archive, label: "辅料采购", path: "/material-purchases" },
  { icon: FileSpreadsheet, label: "成品报表", path: "/finished-product-reports" },
];

const afterSalesItems = [
  { icon: ArrowLeftRight, label: "退货管理", path: "/returns" },
  { icon: Package, label: "采购售后", path: "/purchase-returns" },
];

const productDefinitionItems = [
  { icon: Layers, label: "系列管理", path: "/product-series" },
  { icon: Boxes, label: "SPU与规格", path: "/product-templates" },
  { icon: Tag, label: "SKU价格配置", path: "/sku-pricing" },
];

const bottomNavItems = [
  { icon: Boxes, label: "原料规格", path: "/products" },
  { icon: Tag, label: "品牌管理", path: "/brands" },
  { icon: Layers, label: "成品定义", path: "/finished-products" },
  { icon: ArrowLeftRight, label: "追溯查询", path: "/traceability" },
  { icon: Wrench, label: "物料管理", path: "/materials" },
  { icon: Building2, label: "主体管理", path: "/companies" },
  { icon: Users, label: "客户管理", path: "/customers" },
  { icon: Store, label: "供应商管理", path: "/suppliers" },
  { icon: UserCog, label: "业务员", path: "/salespersons" },
  { icon: Percent, label: "提成管理", path: "/commissions" },
  { icon: Banknote, label: "银行账户", path: "/bank-accounts" },
  { icon: Shield, label: "审计日志", path: "/audit-logs" },
  { icon: Settings, label: "系统设置", path: "/settings" },
];

function useUserRole(): UserRole {
  const user = getCachedUser();
  return user?.role ?? "user";
}

interface SectionProps {
  title: string;
  items: { icon: React.ElementType; label: string; path: string }[];
  role: UserRole;
}

function NavSection({ title, items, role }: SectionProps) {
  const location = useLocation();
  const filtered = useMemo(() => filterNavByRole(items, role), [items, role]);
  if (filtered.length === 0) return null;

  return (
    <div className="pt-4 mt-2 border-t">
      <p className="px-3 text-xs text-muted-foreground mb-2">{title}</p>
      {filtered.map((item) => {
        const Icon = item.icon;
        const isActive =
          location.pathname === item.path ||
          (item.path.includes("?") && location.pathname + location.search === item.path);
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
  );
}

export function Sidebar() {
  const role = useUserRole();

  return (
    <aside className="w-64 border-r bg-card flex flex-col h-screen">
      <div className="p-6 border-b shrink-0">
        <h1 className="text-lg font-bold">三文鱼 PMS</h1>
        <p className="text-xs text-muted-foreground">V8.2</p>
        {role !== "admin" && (
          <p className="text-xs text-primary mt-1">角色: {role}</p>
        )}
      </div>
      <nav className="flex-1 p-4 space-y-1 overflow-y-auto">
        {/* 主导航 — 默认全部可见 */}
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

        <NavSection title="报表中心" items={reportItems} role={role} />
        <NavSection title="财务管理" items={financeItems} role={role} />
        <NavSection title="内销管理" items={finishedProductItems} role={role} />
        <NavSection title="售后管理" items={afterSalesItems} role={role} />
        <NavSection title="产品定义" items={productDefinitionItems} role={role} />
        <NavSection title="其他" items={bottomNavItems} role={role} />
      </nav>
    </aside>
  );
}
