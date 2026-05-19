import { Outlet } from "react-router-dom";
import { Sidebar } from "./Sidebar";
import { Header } from "./Header";

export function MainLayout() {
  return (
    <div className="flex h-screen bg-background">
      <div className="print:hidden">
        <Sidebar />
      </div>
      <div className="flex-1 flex flex-col overflow-hidden">
        <div className="print:hidden">
          <Header />
        </div>
        <main className="flex-1 overflow-auto p-6 print:p-0">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
