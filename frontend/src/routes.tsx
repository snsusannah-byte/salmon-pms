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
import { FinishedProductSalesPage } from "@/pages/FinishedProductSalesPage";
import { ProductionManagementPage } from "@/pages/ProductionManagementPage";
import { MaterialManagementPage } from "@/pages/MaterialManagementPage";
import { WarehousePage } from "@/pages/WarehousePage";
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
import { NotFoundPage } from "@/pages/NotFoundPage";

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
      { path: "invoices", element: <InvoicesPage /> },
      { path: "batches", element: <BatchesPage /> },
      { path: "whole-fish-sales", element: <WholeFishSalesPage /> },
      { path: "finished-product-sales", element: <FinishedProductSalesPage /> },
      { path: "production", element: <ProductionManagementPage /> },
      { path: "materials", element: <MaterialManagementPage /> },
      { path: "warehouse", element: <WarehousePage /> },
      { path: "finished-product-reports", element: <FinishedProductReportsPage /> },
      { path: "finance", element: <FinancePage /> },
      { path: "reports", element: <ReportsPage /> },
      { path: "settings", element: <SettingsPage /> },
      { path: "suppliers", element: <SuppliersPage /> },
      { path: "salespersons", element: <SalespersonPage /> },
      { path: "commissions", element: <CommissionPage /> },
      { path: "daily-slaughter", element: <DailySlaughterPage /> },
      { path: "loss-records", element: <LossRecordsPage /> },
      { path: "notifications", element: <NotificationsPage /> },
      { path: "*", element: <NotFoundPage /> },
    ],
  },
]);

export function AppRouter() {
  return <RouterProvider router={router} />;
}
