import { Loader2, Printer } from "lucide-react";
import React, { useState } from "react";

import { Button } from "@/components/ui/button";
import { api } from "@/lib/api";

type ButtonProps = React.ComponentProps<typeof Button>;

export interface SalePrintItem {
  seq: number;
  product: string;
  spec: string;
  factory: string | null;
  slaughter_date: string | null;
  quantity: number;
  quantity_unit: string;
  weight: string | null;
  weight_unit: string | null;
  unit_price: number;
  price_unit: string;
  amount: number;
  remark: string | null;
}

export interface SalePrintData {
  sale_type: string;
  sale_type_label: string;
  sale_no: string;
  sale_date: string;
  customer: string;
  salesperson: string;
  items: SalePrintItem[];
  summary: {
    total_quantity: number;
    total_weight: string | null;
    total_amount: number;
    gross_amount: number;
    net_amount: number;
    paid_amount: number;
    unpaid_amount: number;
  };
  receipt_accounts: {
    account_name: string;
    bank_name: string;
    account_number: string;
    currency: string;
    notes: string;
  }[];
  remark: string;
}

interface SalePrintButtonProps extends Omit<ButtonProps, "onClick" | "children"> {
  saleType: "whole_fish" | "finished_product_v2";
  saleId: number | string;
  label?: string;
}

const fmt2 = (n: number | string | null | undefined) => {
  if (n === null || n === undefined || n === "") return "-";
  const num = typeof n === "string" ? parseFloat(n) : n;
  if (Number.isNaN(num)) return "-";
  return num.toLocaleString("zh-CN", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
};

const fmtQty = (n: number | string | null | undefined) => {
  if (n === null || n === undefined || n === "") return "-";
  const num = typeof n === "string" ? parseFloat(n) : n;
  if (Number.isNaN(num)) return "-";
  return Number.isInteger(num) ? String(num) : num.toLocaleString("zh-CN", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
};

const generatePrintHTML = (data: SalePrintData) => {
  const unitHeaders = (() => {
    if (data.sale_type === "whole_fish" || data.sale_type_label === "整鱼") {
      return { qty: "数量(箱)", weight: "重量(kg)", price: "单价(元/kg)" };
    }
    if (data.sale_type_label === "海鲜物料") {
      return {
        qty: `数量(${data.items[0]?.quantity_unit || "件"})`,
        weight: "重量",
        price: `单价(元/${data.items[0]?.quantity_unit || "件"})`,
      };
    }
    return { qty: "数量(份)", weight: "重量(kg)", price: "单价(元/份)" };
  })();

  const showFactory = data.sale_type === "whole_fish";

  const rows = data.items
    .map(
      (item) => {
        const factoryCell = showFactory
          ? `<td style="border:1px solid #e5e7eb;padding:8px 10px;vertical-align:middle;">${item.factory || "-"}</td>`
          : "";
        const slaughterCell = showFactory
          ? `<td style="border:1px solid #e5e7eb;padding:8px 10px;text-align:center;vertical-align:middle;">${item.slaughter_date || "-"}</td>`
          : "";
        return `
      <tr>
        <td style="border:1px solid #e5e7eb;padding:8px 10px;text-align:center;vertical-align:middle;">${item.seq}</td>
        <td style="border:1px solid #e5e7eb;padding:8px 10px;vertical-align:middle;">${item.product}</td>
        <td style="border:1px solid #e5e7eb;padding:8px 10px;vertical-align:middle;">${item.spec}</td>
        ${factoryCell}
        ${slaughterCell}
        <td style="border:1px solid #e5e7eb;padding:8px 10px;text-align:right;vertical-align:middle;">${fmtQty(item.quantity)}</td>
        <td style="border:1px solid #e5e7eb;padding:8px 10px;text-align:right;vertical-align:middle;">${item.weight ? fmt2(item.weight) : "-"}</td>
        <td style="border:1px solid #e5e7eb;padding:8px 10px;text-align:right;vertical-align:middle;">${fmt2(item.unit_price)}</td>
        <td style="border:1px solid #e5e7eb;padding:8px 10px;text-align:right;vertical-align:middle;font-weight:600;">${fmt2(item.amount)}</td>
        <td style="border:1px solid #e5e7eb;padding:8px 10px;vertical-align:middle;">${item.remark || "-"}</td>
      </tr>`;
      }
    )
    .join("");

  const bankBlocks = data.receipt_accounts
    .map(
      (acc, idx) => `
      <div class="bank" style="flex:1;min-width:0;margin-bottom:10px;">
        <div class="bank-title">收款信息 ${idx + 1}</div>
        <div class="bank-row"><span class="label">户名：</span><span class="value">${acc.account_name || "-"}</span></div>
        <div class="bank-row"><span class="label">账号：</span><span class="value">${acc.account_number || "-"}</span></div>
        <div class="bank-row"><span class="label">开户行：</span><span class="value">${acc.bank_name || "-"}</span></div>
        ${acc.notes ? `<div class="bank-row"><span class="label">备注：</span><span class="value">${acc.notes}</span></div>` : ""}
      </div>`
    )
    .join("");

  const bankSection = data.receipt_accounts.length > 0
    ? `<div class="bank-section" style="display:flex;gap:16px;align-items:flex-start;">${bankBlocks}</div>`
    : `
      <div class="bank">
        <div class="bank-title">收款信息</div>
        <div class="bank-row"><span class="label">户名：</span><span class="value">-</span></div>
        <div class="bank-row"><span class="label">账号：</span><span class="value">-</span></div>
        <div class="bank-row"><span class="label">开户行：</span><span class="value">-</span></div>
      </div>`;

  return `
    <!DOCTYPE html>
    <html>
      <head>
        <title>销售单 ${data.sale_no}</title>
        <style>
          @page { margin: 25mm; }
          * { box-sizing: border-box; }
          body { font-family: "Microsoft YaHei", "PingFang SC", "Helvetica Neue", Arial, sans-serif; margin: 0; padding: 20px; color: #1f2937; background: #fff; font-size: 13px; line-height: 1.5; }
          .page { width: 100%; margin: 0 auto; padding: 0; }
          .header { text-align: center; margin-bottom: 20px; padding-bottom: 12px; border-bottom: 2px solid #111827; }
          .header h1 { font-size: 26px; margin: 0; letter-spacing: 4px; font-weight: 700; }
          .info-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 8px 28px; font-size: 13px; margin-bottom: 18px; }
          .info-grid .row { display: flex; }
          .info-grid .label { color: #6b7280; min-width: 72px; }
          .info-grid .value { font-weight: 500; flex: 1; }
          .info-grid .full { grid-column: span 2; }
          table { width: 100%; border-collapse: collapse; font-size: 12px; margin-bottom: 14px; }
          th { background: #f3f4f6; font-weight: 600; color: #374151; border: 1px solid #e5e7eb; padding: 8px 10px; text-align: center; }
          td { border: 1px solid #e5e7eb; padding: 8px 10px; }
          tbody tr:nth-child(even) { background: #fafafa; }
          tfoot tr { background: #f3f4f6; font-weight: 700; color: #111827; }
          .summary { display: flex; justify-content: space-between; align-items: center; font-size: 14px; margin: 16px 0; padding: 10px 14px; background: #f9fafb; border: 1px solid #e5e7eb; border-radius: 4px; }
          .summary .total { font-size: 16px; font-weight: 700; color: #111827; }
          .bank { border: 1px solid #e5e7eb; border-radius: 4px; padding: 14px; background: #fafafa; }
          .bank-title { font-size: 14px; font-weight: 700; margin-bottom: 10px; color: #111827; border-bottom: 1px solid #e5e7eb; padding-bottom: 6px; }
          .bank-row { display: flex; margin: 5px 0; font-size: 13px; }
          .bank-row .label { color: #6b7280; min-width: 52px; }
          .bank-row .value { font-weight: 500; flex: 1; }
          .remark { font-size: 13px; color: #374151; margin-bottom: 14px; padding: 10px 14px; background: #fffbeb; border: 1px dashed #fcd34d; border-radius: 4px; }
          .no-print { text-align: right; margin-bottom: 16px; }
          .no-print button { background: #111827; color: #fff; border: none; padding: 8px 18px; border-radius: 4px; font-size: 13px; cursor: pointer; }
          .no-print button:hover { background: #374151; }
          @media print { .no-print { display: none; } body { padding: 0; } .page { padding: 0; } }
        </style>
      </head>
      <body>
        <div class="page">
          <div class="no-print">
            <button onclick="window.print()">打印</button>
          </div>

          <div class="header">
            <h1>销售单</h1>
          </div>

          <div class="info-grid">
            <div class="row"><span class="label">销售单号：</span><span class="value">${data.sale_no}</span></div>
            <div class="row"><span class="label">日期：</span><span class="value">${data.sale_date}</span></div>
            <div class="row"><span class="label">客户：</span><span class="value">${data.customer}</span></div>
            <div class="row"><span class="label">业务员：</span><span class="value">${data.salesperson}</span></div>
            <div class="row full"><span class="label">类型：</span><span class="value">${data.sale_type_label}</span></div>
          </div>

          <table>
            <thead>
              <tr>
                <th style="width:40px">序号</th>
                <th>产品</th>
                <th>规格</th>
                ${showFactory ? `<th>加工厂</th>
                <th style="width:70px">宰杀日期</th>` : ""}
                <th style="width:80px">${unitHeaders.qty}</th>
                <th style="width:80px">${unitHeaders.weight}</th>
                <th style="width:90px">${unitHeaders.price}</th>
                <th style="width:90px">金额</th>
                <th>备注</th>
              </tr>
            </thead>
            <tbody>${rows}</tbody>
            <tfoot>
              <tr>
                <td colspan="${showFactory ? 5 : 3}" style="text-align:right;">合计</td>
                <td style="text-align:right;">${fmtQty(data.summary.total_quantity)}</td>
                <td style="text-align:right;">${data.summary.total_weight ? fmt2(data.summary.total_weight) : "-"}</td>
                <td></td>
                <td style="text-align:right;">${fmt2(data.summary.total_amount)}</td>
                <td></td>
              </tr>
            </tfoot>
          </table>

          <div class="summary">
            <span>合计金额</span>
            <span class="total">¥${fmt2(data.summary.total_amount)}</span>
          </div>

          ${bankSection}

          ${data.remark ? `<div class="remark"><span style="font-weight:600;">备注：</span>${data.remark}</div>` : ""}

        </div>
      </body>
    </html>
  `;
};

export const SalePrintButton: React.FC<SalePrintButtonProps> = ({
  saleType,
  saleId,
  label = "打印",
  ...buttonProps
}) => {
  const [loading, setLoading] = useState(false);

  const handleClick = async () => {
    if (!saleId) return;
    setLoading(true);
    try {
      const res = await api.get(`/v1/print/sales/${saleType}/${saleId}`);
      const data = res.data as SalePrintData;
      const html = generatePrintHTML(data);
      const printWindow = window.open("", "_blank", "width=900,height=700,top=100,left=100");
      if (!printWindow) {
        alert("请允许浏览器弹出新窗口以进行打印");
        return;
      }
      printWindow.document.open();
      printWindow.document.write(html);
      printWindow.document.close();
    } catch (err: any) {
      const msg = err?.response?.data?.detail || err?.message || "打印失败";
      alert(msg);
    } finally {
      setLoading(false);
    }
  };

  return (
    <Button
      size="sm"
      variant="outline"
      onClick={handleClick}
      disabled={loading || !saleId}
      {...buttonProps}
    >
      {loading ? <Loader2 className="h-4 w-4 mr-1 animate-spin" /> : <Printer className="h-4 w-4 mr-1" />}
      {label}
    </Button>
  );
};

export default SalePrintButton;
