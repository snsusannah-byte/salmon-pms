import { createBrowserRouter, RouterProvider, Navigate } from "react-router-dom";
import { MainLayout } from "@/components/layout/MainLayout";
import { LoginPage } from "@/pages/LoginPage";
import { DashboardPage } from "@/pages/DashboardPage";
import { CompaniesPage } from "@/pages/CompaniesPage";
import { CustomersPage } from "@/pages/CustomersPage";
import ProductsPage from "@/pages/ProductsPage";
import { InvoicesPage } from "@/pages/InvoicesPage";
import { BatchesPage } from "@/pages/BatchesPage";
import { SalesPage as WholeFishSalesPage } from "@/pages/SalesPage";
import { ProductionManagementPage } from "@/pages/ProductionManagementPage";
import { MaterialManagementPage } from "@/pages/MaterialManagementPage";
import { WarehousePage } from "@/pages/WarehousePage";
import { WarehouseV2Page } from "@/pages/WarehouseV2Page";
import { FinishedProductReportsPage } from "@/pages/FinishedProductReportsPage";
import { FinancePage } from "@/pages/FinancePage";
import { ReportsPage } from "@/pages/ReportsPage";
import { SettingsPage } from "@/pages/SettingsPage";
import { SalespersonPage } from "@/pages/SalespersonPage";
import { CommissionPage } from "@/pages/CommissionPage";
import { SuppliersPage } from "@/pages/SuppliersPage";
import { DailySlaughterPage } from "@/pages/DailySlaughterPage";
import { LossRecordsPage } from "@/pages/LossRecordsPage";
import NotificationsPage from "@/pages/NotificationsPage";
import { BankAccountsPage } from "@/pages/BankAccountsPage";
import { BrandsPage } from "@/pages/BrandsPage";
import { FinishedProductsPage } from "@/pages/FinishedProductsPage";
import { TraceabilityPage } from "@/pages/TraceabilityPage";
import ReturnsPage from "@/pages/ReturnsPage";
import { NotFoundPage } from "@/pages/NotFoundPage";

// V4 迁移页面 (salmon-finance-v4)
import { PurchaseOrderEntry } from "@/pages/PurchaseOrderEntry";
import { FinishedProductSales } from "@/pages/FinishedProductSales";

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
      { path: "companies", element: <CompaniesPage /> },
      { path: "customers", element: <CustomersPage /> },
      { path: "products", element: <ProductsPage /> },
      { path: "finished-products", element: <FinishedProductsPage /> },
      { path: "traceability", element: <TraceabilityPage /> },
      { path: "returns", element: <ReturnsPage /> },
      { path: "brands", element: <BrandsPage /> },
      { path: "invoices", element: <InvoicesPage /> },
      { path: "batches", element: <BatchesPage /> },
      { path: "whole-fish-sales", element: <WholeFishSalesPage /> },
      { path: "finished-product-sales", element: <FinishedProductSales /> },
      { path: "production", element: <ProductionManagementPage /> },
      { path: "materials", element: <MaterialManagementPage /> },
      { path: "warehouse", element: <WarehousePage /> },
      { path: "warehouse-v2", element: <WarehouseV2Page /> },
      { path: "purchase-orders", element: <PurchaseOrderEntry /> },
      { path: "finished-product-reports", element: <FinishedProductReportsPage /> },
      { path: "finance", element: <FinancePage /> },
      { path: "reports", element: <ReportsPage /> },
      { path: "reports/batches", element: <ReportsPage /> },
      { path: "reports/invoices", element: <ReportsPage /> },
      { path: "reports/receivable", element: <ReportsPage /> },
      { path: "reports/payable", element: <ReportsPage /> },
      { path: "reports/financial", element: <ReportsPage /> },
      { path: "settings", element: <SettingsPage /> },
      { path: "suppliers", element: <SuppliersPage /> },
      { path: "salespersons", element: <SalespersonPage /> },
      { path: "commissions", element: <CommissionPage /> },
      { path: "daily-slaughter", element: <DailySlaughterPage /> },
      { path: "loss-records", element: <LossRecordsPage /> },
      { path: "notifications", element: <NotificationsPage /> },
      { path: "bank-accounts", element: <BankAccountsPage /> },
      // V4 迁移路由
      { path: "domestic-suppliers", element: <Navigate to="/suppliers" replace /> },
      { path: "*", element: <NotFoundPage /> },
    ],
  },
]);

export function AppRouter() {
  return <RouterProvider router={router} />;
}

export { router };
