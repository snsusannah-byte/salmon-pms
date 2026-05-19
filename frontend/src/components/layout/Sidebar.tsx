import { Link, useLocation } from "react-router-dom";
import { cn } from "@/lib/utils";
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
} from "lucide-react";

const navItems = [
  { icon: LayoutDashboard, label: "数据看板", path: "/dashboard" },
  { icon: FileCheck, label: "进口单证", path: "/invoices" },
  { icon: Container, label: "批次管理", path: "/batches" },
  { icon: Fish, label: "整鱼销售", path: "/whole-fish-sales" },
];

const reportItems = [
  { icon: Package, label: "批次财报", path: "/reports/batches" },
  { icon: FileText, label: "单票财报", path: "/reports/invoices" },
  { icon: ArrowDownLeft, label: "应收对账", path: "/reports/receivable" },
  { icon: ArrowUpRight, label: "应付对账", path: "/reports/payable" },
  { icon: BarChart3, label: "三大报表", path: "/reports/financial" },
];

const financeItems = [
  { icon: Ship, label: "进口费用", path: "/finance?tab=import" },
  { icon: DollarSign, label: "购汇登记", path: "/finance?tab=exchange" },
  { icon: List, label: "交易流水", path: "/finance?tab=transactions" },
];

const finishedProductItems = [
  { icon: PackageCheck, label: "成品销售", path: "/finished-product-sales" },
  { icon: Factory, label: "生产管理", path: "/production" },
  { icon: Warehouse, label: "成品仓库", path: "/warehouse" },
  { icon: Archive, label: "仓库管理V2", path: "/warehouse-v2" },
  { icon: Package, label: "采购入库", path: "/purchase-orders" },
  { icon: FileSpreadsheet, label: "成品报表", path: "/finished-product-reports" },
];

const afterSalesItems = [
  { icon: ArrowLeftRight, label: "退货管理", path: "/returns" },
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

        {/* 报表中心分组 */}
        <div className="pt-4 mt-2 border-t">
          <p className="px-3 text-xs text-muted-foreground mb-2">报表中心</p>
          {reportItems.map((item) => {
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

        {/* 财务管理分组 */}
        <div className="pt-4 mt-2 border-t">
          <p className="px-3 text-xs text-muted-foreground mb-2">财务管理</p>
          {financeItems.map((item) => {
            const Icon = item.icon;
            const fullPath = location.pathname + location.search;
            const isActive = fullPath === item.path;
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

        {/* 成品管理分组 */}
        <div className="pt-4 mt-2 border-t">
          <p className="px-3 text-xs text-muted-foreground mb-2">成品管理</p>
          {finishedProductItems.map((item) => {
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

        {/* 售后管理分组 */}
        <div className="pt-4 mt-2 border-t">
          <p className="px-3 text-xs text-muted-foreground mb-2">售后管理</p>
          {afterSalesItems.map((item) => {
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

        {/* 其他分组 */}
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
