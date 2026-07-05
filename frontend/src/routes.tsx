import { createBrowserRouter, RouterProvider, Navigate } from "react-router-dom";
import { lazy, Suspense } from "react";
import { MainLayout } from "@/components/layout/MainLayout";
import { LoginPage } from "@/pages/LoginPage";
import { DashboardPage } from "@/pages/DashboardPage";
import { NotFoundPage } from "@/pages/NotFoundPage";
import { Loader2 } from "lucide-react";

// ========== 同步加载（核心页面） ==========
// 登录页、首页、404 保持同步加载，避免白屏

// ========== 懒加载（业务页面） ==========
const CompaniesPage = lazy(() => import("@/pages/CompaniesPage"));
const CustomersPage = lazy(() => import("@/pages/CustomersPage"));
const ProductsPage = lazy(() => import("@/pages/ProductsPage"));
const InvoicesPage = lazy(() => import("@/pages/InvoicesPage"));
const BatchesPage = lazy(() => import("@/pages/BatchesPage"));
const WholeFishSalesPage = lazy(() => import("@/pages/SalesPage"));
const ProductionManagementPage = lazy(() => import("@/pages/ProductionManagementPage"));
const MaterialManagementPage = lazy(() => import("@/pages/MaterialManagementPage"));
const WarehousePage = lazy(() => import("@/pages/WarehousePage"));
const WarehouseV2Page = lazy(() => import("@/pages/WarehouseV2Page"));
const FinishedProductReportsPage = lazy(() => import("@/pages/FinishedProductReportsPage"));
const FinancePage = lazy(() => import("@/pages/FinancePage"));
const ReportsPage = lazy(() => import("@/pages/ReportsPage"));
const SettingsPage = lazy(() => import("@/pages/SettingsPage"));
const SalespersonPage = lazy(() => import("@/pages/SalespersonPage"));
const CommissionPage = lazy(() => import("@/pages/CommissionPage"));
const SuppliersPage = lazy(() => import("@/pages/SuppliersPage"));
const DailySlaughterPage = lazy(() => import("@/pages/DailySlaughterPage"));
const LossRecordsPage = lazy(() => import("@/pages/LossRecordsPage"));
const NotificationsPage = lazy(() => import("@/pages/NotificationsPage"));
const BankAccountsPage = lazy(() => import("@/pages/BankAccountsPage"));
const BrandsPage = lazy(() => import("@/pages/BrandsPage"));
const FinishedProductsPage = lazy(() => import("@/pages/FinishedProductsPage"));
const TraceabilityPage = lazy(() => import("@/pages/TraceabilityPage"));
const ReturnsPage = lazy(() => import("@/pages/ReturnsPage"));
const MaterialPurchasePage = lazy(() => import("@/pages/MaterialPurchasePage"));
const ProductSeriesPage = lazy(() => import("@/pages/ProductSeriesPage"));
const ProductTemplatePage = lazy(() => import("@/pages/ProductTemplatePage"));
const SkuPricingPage = lazy(() => import("@/pages/SkuPricingPage"));
const AuditLogsPage = lazy(() => import("@/pages/AuditLogsPage"));
const PurchaseOrderEntry = lazy(() => import("@/pages/PurchaseOrderEntry"));
const FinishedProductSales = lazy(() => import("@/pages/FinishedProductSales"));
const PurchaseReturnPage = lazy(() => import("@/components/purchase-returns/PurchaseReturnPage"));
const InboundRecordsPage = lazy(() => import("@/pages/InboundRecordsPage"));

// ========== 加载状态组件 ==========
function PageLoader() {
  return (
    <div className="flex h-screen items-center justify-center">
      <Loader2 className="h-8 w-8 animate-spin text-primary" />
    </div>
  );
}

// ========== 路由配置 ==========
const router = createBrowserRouter([
  {
    path: "/login",
    element: <LoginPage />,
  },
  {
    path: "/",
    element: <MainLayout />,
    children: [
      { index: true, element: <Navigate to="/dashboard" replace /> },
      { path: "dashboard", element: <DashboardPage /> },
      { path: "companies", element: <Suspense fallback={<PageLoader />}><CompaniesPage /></Suspense> },
      { path: "customers", element: <Suspense fallback={<PageLoader />}><CustomersPage /></Suspense> },
      { path: "products", element: <Suspense fallback={<PageLoader />}><ProductsPage /></Suspense> },
      { path: "finished-products", element: <Suspense fallback={<PageLoader />}><FinishedProductsPage /></Suspense> },
      { path: "traceability", element: <Suspense fallback={<PageLoader />}><TraceabilityPage /></Suspense> },
      { path: "returns", element: <Suspense fallback={<PageLoader />}><ReturnsPage /></Suspense> },
      { path: "brands", element: <Suspense fallback={<PageLoader />}><BrandsPage /></Suspense> },
      { path: "invoices", element: <Suspense fallback={<PageLoader />}><InvoicesPage /></Suspense> },
      { path: "batches", element: <Suspense fallback={<PageLoader />}><BatchesPage /></Suspense> },
      { path: "whole-fish-sales", element: <Suspense fallback={<PageLoader />}><WholeFishSalesPage /></Suspense> },
      { path: "finished-product-sales", element: <Suspense fallback={<PageLoader />}><FinishedProductSales /></Suspense> },
      { path: "made-to-order", element: <Suspense fallback={<PageLoader />}><FinishedProductSales key="made-to-order" /></Suspense> },
      { path: "production", element: <Suspense fallback={<PageLoader />}><ProductionManagementPage /></Suspense> },
      { path: "materials", element: <Suspense fallback={<PageLoader />}><MaterialManagementPage /></Suspense> },
      { path: "material-purchases", element: <Suspense fallback={<PageLoader />}><MaterialPurchasePage /></Suspense> },
      { path: "purchase-returns", element: <Suspense fallback={<PageLoader />}><PurchaseReturnPage /></Suspense> },
      { path: "warehouse", element: <Navigate to="/warehouse-v2" replace /> },
      { path: "warehouse-v2", element: <Suspense fallback={<PageLoader />}><WarehouseV2Page /></Suspense> },
      { path: "inbound-records", element: <Suspense fallback={<PageLoader />}><InboundRecordsPage /></Suspense> },
      { path: "purchase-orders", element: <Suspense fallback={<PageLoader />}><PurchaseOrderEntry /></Suspense> },
      { path: "finished-product-reports", element: <Suspense fallback={<PageLoader />}><FinishedProductReportsPage /></Suspense> },
      { path: "finance", element: <Suspense fallback={<PageLoader />}><FinancePage /></Suspense> },
      { path: "reports", element: <Suspense fallback={<PageLoader />}><ReportsPage /></Suspense> },
      { path: "reports/batches", element: <Suspense fallback={<PageLoader />}><ReportsPage /></Suspense> },
      { path: "reports/invoices", element: <Suspense fallback={<PageLoader />}><ReportsPage /></Suspense> },
      { path: "reports/receivable", element: <Suspense fallback={<PageLoader />}><ReportsPage /></Suspense> },
      { path: "reports/payable", element: <Suspense fallback={<PageLoader />}><ReportsPage /></Suspense> },
      { path: "reports/financial", element: <Suspense fallback={<PageLoader />}><ReportsPage /></Suspense> },
      { path: "reports/netting", element: <Suspense fallback={<PageLoader />}><ReportsPage /></Suspense> },
      { path: "settings", element: <Suspense fallback={<PageLoader />}><SettingsPage /></Suspense> },
      { path: "audit-logs", element: <Suspense fallback={<PageLoader />}><AuditLogsPage /></Suspense> },
      { path: "suppliers", element: <Suspense fallback={<PageLoader />}><SuppliersPage /></Suspense> },
      { path: "salespersons", element: <Suspense fallback={<PageLoader />}><SalespersonPage /></Suspense> },
      { path: "commissions", element: <Suspense fallback={<PageLoader />}><CommissionPage /></Suspense> },
      { path: "daily-slaughter", element: <Suspense fallback={<PageLoader />}><DailySlaughterPage /></Suspense> },
      { path: "loss-records", element: <Suspense fallback={<PageLoader />}><LossRecordsPage /></Suspense> },
      { path: "notifications", element: <Suspense fallback={<PageLoader />}><NotificationsPage /></Suspense> },
      { path: "bank-accounts", element: <Suspense fallback={<PageLoader />}><BankAccountsPage /></Suspense> },
      { path: "product-series", element: <Suspense fallback={<PageLoader />}><ProductSeriesPage /></Suspense> },
      { path: "product-templates", element: <Suspense fallback={<PageLoader />}><ProductTemplatePage /></Suspense> },
      { path: "sku-pricing", element: <Suspense fallback={<PageLoader />}><SkuPricingPage /></Suspense> },
      { path: "domestic-suppliers", element: <Navigate to="/suppliers" replace /> },
      { path: "*", element: <NotFoundPage /> },
    ],
  },
]);

export function AppRouter() {
  return <RouterProvider router={router} />;
}

export { router };
