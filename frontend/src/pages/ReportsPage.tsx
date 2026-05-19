import { useLocation } from "react-router-dom";
import { BatchReportsTab } from "./BatchReportsTab";
import { InvoiceReportsTab } from "./InvoiceReportsTab";
import { ReceivableStatementsTab } from "./ReceivableStatementsTab";
import { PayableStatementsTab } from "./PayableStatementsTab";
import { FinancialStatementsTab } from "./FinancialStatementsTab";

export function ReportsPage() {
  const { pathname } = useLocation();
  return (
    <div className="space-y-4">
      <div className="print:hidden">
        <h1 className="text-2xl font-bold">报表中心</h1>
        <p className="text-sm text-muted-foreground">
          批次财报、单票财报、应收/应付对账单、三大财务报表
        </p>
      </div>
      <div className="mt-4">
        {pathname === "/reports/invoices" ? (
          <InvoiceReportsTab />
        ) : pathname === "/reports/receivable" ? (
          <ReceivableStatementsTab />
        ) : pathname === "/reports/payable" ? (
          <PayableStatementsTab />
        ) : pathname === "/reports/financial" ? (
          <FinancialStatementsTab />
        ) : (
          <BatchReportsTab />
        )}
      </div>
    </div>
  );
}
