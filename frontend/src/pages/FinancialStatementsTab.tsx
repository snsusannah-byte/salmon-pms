import { useState, useMemo, useRef, useEffect } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { toast } from "sonner";
import { Loader2, Printer, Search } from "lucide-react";

function fmt$(v: number | string | null | undefined) {
  const n = Number(v ?? 0);
  if (Number.isNaN(n)) return "¥0.00";
  return `¥${n.toLocaleString("zh-CN", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

function fmtDate(d: string | null | undefined) {
  if (!d) return "-";
  return new Date(d).toLocaleDateString("zh-CN");
}

function clsProfit(v: number) {
  return v >= 0 ? "text-green-600" : "text-red-600";
}

function SimplePagination({ current, total, pageSize, onChange }: {
  current: number; total: number; pageSize: number; onChange: (page: number) => void;
}) {
  const totalPages = Math.max(1, Math.ceil(total / pageSize));
  if (totalPages <= 1) return null;
  return (
    <div className="flex items-center justify-between px-2 py-3">
      <span className="text-xs text-muted-foreground">
        第 {current + 1} / {totalPages} 页，共 {total} 条
      </span>
      <div className="flex gap-1">
        <Button variant="outline" size="sm" disabled={current === 0} onClick={() => onChange(current - 1)}>
          <ChevronLeft className="h-3 w-3" />
        </Button>
        <Button variant="outline" size="sm" disabled={current >= totalPages - 1} onClick={() => onChange(current + 1)}>
          <ChevronRight className="h-3 w-3" />
        </Button>
      </div>
    </div>
  );
}

// ==================== Tab 5: 三大报表 ====================

export function FinancialStatementsTab() {
  const [periodType, setPeriodType] = useState("current_quarter");
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");
  const [retailRevenue, setRetailRevenue] = useState("");
  const [retailCost, setRetailCost] = useState("");

  const { data, isLoading } = useQuery({
    queryKey: ["financial-statements", periodType, startDate, endDate, retailRevenue, retailCost],
    queryFn: async () => {
      const params = new URLSearchParams({ period_type: periodType });
      if (periodType === "custom") {
        if (startDate) params.set("start_date", startDate);
        if (endDate) params.set("end_date", endDate);
      }
      if (retailRevenue) params.set("retail_revenue", retailRevenue);
      if (retailCost) params.set("retail_cost", retailCost);
      const res = await api.get(`/v1/reports/financial-statements?${params}`);
      return res.data as any;
    },
  });

  const periodOptions = [
    { value: "current_quarter", label: "本季度" },
    { value: "last_quarter", label: "上季度" },
    { value: "first_half", label: "上半年" },
    { value: "second_half", label: "下半年" },
    { value: "current_year", label: "本年度" },
    { value: "last_year", label: "上年度" },
    { value: "custom", label: "自定义" },
  ];

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-end gap-3">
        <div className="grid gap-1">
          <Label className="text-xs">报表周期</Label>
          <select
            className="h-8 w-32 rounded-md border border-input bg-background px-2 text-xs"
            value={periodType}
            onChange={(e) => setPeriodType(e.target.value)}
          >
            {periodOptions.map((o) => (
              <option key={o.value} value={o.value}>{o.label}</option>
            ))}
          </select>
        </div>
        {periodType === "custom" && (
          <>
            <div className="grid gap-1">
              <Label className="text-xs">开始日期</Label>
              <Input type="date" className="h-8 w-40" value={startDate} onChange={(e) => setStartDate(e.target.value)} />
            </div>
            <div className="grid gap-1">
              <Label className="text-xs">结束日期</Label>
              <Input type="date" className="h-8 w-40" value={endDate} onChange={(e) => setEndDate(e.target.value)} />
            </div>
          </>
        )}
        <div className="grid gap-1">
          <Label className="text-xs">零售收入(可选)</Label>
          <Input type="number" className="h-8 w-32" placeholder="0" value={retailRevenue} onChange={(e) => setRetailRevenue(e.target.value)} />
        </div>
        <div className="grid gap-1">
          <Label className="text-xs">零售成本(可选)</Label>
          <Input type="number" className="h-8 w-32" placeholder="0" value={retailCost} onChange={(e) => setRetailCost(e.target.value)} />
        </div>
      </div>

      {data?.meta && (
        <div className="text-xs text-muted-foreground flex items-center gap-2">
          <span className="font-medium text-foreground">{data.meta.company_name}</span>
          <span>|</span>
          <span>{data.meta.period_label}</span>
          <span>|</span>
          <span>生成时间: {data.meta.generated_at}</span>
          <Button variant="ghost" size="sm" className="h-6 ml-auto" onClick={() => window.print()}>
            <Printer className="h-3 w-3 mr-1" /> 打印
          </Button>
        </div>
      )}

      {isLoading ? (
        <div className="py-12 text-center">
          <Loader2 className="h-6 w-6 animate-spin mx-auto" />
          <p className="text-sm text-muted-foreground mt-2">正在计算财务报表...</p>
        </div>
      ) : data ? (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 print:grid-cols-1">
          {/* 利润表 */}
          <Card className="print:shadow-none print:border-black">
            <CardHeader className="pb-2">
              <CardTitle className="text-base text-center">{data.income_statement.title}</CardTitle>
              <p className="text-xs text-center text-muted-foreground">{data.income_statement.subtitle}</p>
            </CardHeader>
            <CardContent className="pt-0">
              <Table>
                <TableBody>
                  {(data.income_statement.items || []).map((item: any, idx: number) => (
                    <TableRow key={idx} className={cn(
                      "border-0",
                      item.is_spacer ? "h-2" : "",
                      item.is_total ? "border-t-2 border-black font-bold" : "",
                      item.is_highlight ? "bg-yellow-50 font-semibold" : "",
                      item.is_section ? "border-t border-gray-300" : ""
                    )}>
                      <TableCell className={cn(
                        "text-xs py-1",
                        item.is_header ? "font-semibold" : "",
                        item.is_deduction ? "text-red-600" : "",
                        item.indent === 1 ? "pl-6" : item.indent === 2 ? "pl-10" : ""
                      )}>
                        {item.label}
                        {item.note && <span className="text-[10px] text-muted-foreground ml-1">({item.note})</span>}
                      </TableCell>
                      <TableCell className={cn(
                        "text-xs text-right py-1 font-mono",
                        item.is_deduction ? "text-red-600" : "",
                        item.is_total ? "font-bold" : ""
                      )}>
                        {item.amount !== null && item.amount !== undefined ? fmt$(item.amount) : ""}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
              <div className="mt-3 text-xs text-muted-foreground text-center">
                利润率: {data.income_statement.summary?.profit_margin || 0}%
              </div>
            </CardContent>
          </Card>

          {/* 资产负债表 */}
          <Card className="print:shadow-none print:border-black">
            <CardHeader className="pb-2">
              <CardTitle className="text-base text-center">{data.balance_sheet.title}</CardTitle>
              <p className="text-xs text-center text-muted-foreground">{data.balance_sheet.subtitle}</p>
            </CardHeader>
            <CardContent className="pt-0">
              <Table>
                <TableBody>
                  {(data.balance_sheet.items || []).map((item: any, idx: number) => (
                    <TableRow key={idx} className={cn(
                      "border-0",
                      item.is_spacer ? "h-2" : "",
                      item.is_total ? "border-t-2 border-black font-bold" : "",
                      item.is_highlight ? "bg-yellow-50 font-semibold" : "",
                      item.is_section ? "border-t border-gray-300" : ""
                    )}>
                      <TableCell className={cn(
                        "text-xs py-1",
                        item.is_header ? "font-semibold" : "",
                        item.is_deduction ? "text-red-600" : "",
                        item.indent === 1 ? "pl-6" : ""
                      )}>
                        {item.label}
                        {item.note && <span className="text-[10px] text-muted-foreground ml-1">({item.note})</span>}
                      </TableCell>
                      <TableCell className={cn(
                        "text-xs text-right py-1 font-mono",
                        item.is_deduction ? "text-red-600" : "",
                        item.is_total ? "font-bold" : ""
                      )}>
                        {item.amount !== null && item.amount !== undefined ? fmt$(item.amount) : ""}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
              {data.balance_sheet.customer_debts && data.balance_sheet.customer_debts.length > 0 && (
                <div className="mt-3">
                  <p className="text-xs font-medium mb-1">TOP 5 欠款客户</p>
                  <div className="text-xs space-y-0.5">
                    {data.balance_sheet.customer_debts.map((c: any) => (
                      <div key={c.customer_id} className="flex justify-between">
                        <span>{c.customer_name}</span>
                        <span className="text-red-600">{fmt$(c.unpaid)}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </CardContent>
          </Card>

          {/* 现金流量表 */}
          <Card className="print:shadow-none print:border-black">
            <CardHeader className="pb-2">
              <CardTitle className="text-base text-center">{data.cash_flow.title}</CardTitle>
              <p className="text-xs text-center text-muted-foreground">{data.cash_flow.subtitle}</p>
            </CardHeader>
            <CardContent className="pt-0">
              <Table>
                <TableBody>
                  {(data.cash_flow.items || []).map((item: any, idx: number) => (
                    <TableRow key={idx} className={cn(
                      "border-0",
                      item.is_spacer ? "h-2" : "",
                      item.is_total ? "border-t-2 border-black font-bold" : "",
                      item.is_highlight ? "bg-yellow-50 font-semibold" : "",
                      item.is_section ? "border-t border-gray-300" : ""
                    )}>
                      <TableCell className={cn(
                        "text-xs py-1",
                        item.is_header ? "font-semibold" : "",
                        item.is_deduction ? "text-red-600" : "",
                        item.indent === 1 ? "pl-6" : ""
                      )}>
                        {item.label}
                      </TableCell>
                      <TableCell className={cn(
                        "text-xs text-right py-1 font-mono",
                        item.is_deduction ? "text-red-600" : "",
                        item.is_total ? "font-bold" : ""
                      )}>
                        {item.amount !== null && item.amount !== undefined ? fmt$(item.amount) : ""}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </CardContent>
          </Card>
        </div>
      ) : null}
    </div>
  );
}

// ==================== 主页面 ====================
