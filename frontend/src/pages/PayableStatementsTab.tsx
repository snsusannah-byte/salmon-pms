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
import { Loader2, Eye, Search } from "lucide-react";

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

function DateFilter({ startDate, endDate, onStartChange, onEndChange, onSearch }: {
  startDate: string; endDate: string;
  onStartChange: (v: string) => void; onEndChange: (v: string) => void; onSearch: () => void;
}) {
  return (
    <div className="flex items-end gap-3">
      <div className="space-y-1">
        <Label className="text-xs text-muted-foreground">开始日期</Label>
        <Input type="date" value={startDate} onChange={(e) => onStartChange(e.target.value)} className="h-8" />
      </div>
      <div className="space-y-1">
        <Label className="text-xs text-muted-foreground">结束日期</Label>
        <Input type="date" value={endDate} onChange={(e) => onEndChange(e.target.value)} className="h-8" />
      </div>
      <Button size="sm" className="h-8" onClick={onSearch}>查询</Button>
    </div>
  );
}

// ==================== Tab 4: 应付对账单 ====================

function PayableStatementsTab() {
  const [page, setPage] = useState(0);
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");

  const { data, isLoading } = useQuery({
    queryKey: ["reports-payable", page, startDate, endDate],
    queryFn: async () => {
      const params = new URLSearchParams({
        skip: String(page * 30),
        limit: "30",
      });
      if (startDate) params.set("start_date", startDate);
      if (endDate) params.set("end_date", endDate);
      const res = await api.get(`/v1/reports/payable-statements?${params}`);
      return res.data as {
        total: number;
        items: any[];
        total_payable: number;
        start_date: string;
        end_date: string;
      };
    },
  });

  return (
    <div className="space-y-3">
      <DateFilter
        startDate={startDate}
        endDate={endDate}
        onStartChange={setStartDate}
        onEndChange={setEndDate}
        onSearch={() => setPage(0)}
      />

      {data && (
        <div className="flex gap-4 text-xs text-muted-foreground">
          <span>周期: {data.start_date || "全部"} ~ {data.end_date || "全部"}</span>
          <span className="font-medium text-foreground">总应付: {fmt$(data.total_payable)}</span>
        </div>
      )}

      <Card>
        <CardContent className="p-0">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead className="text-xs">供应商名称</TableHead>
                <TableHead className="text-xs">类型</TableHead>
                <TableHead className="text-xs text-right">期初欠款(CNY)</TableHead>
                <TableHead className="text-xs text-right">本期采购(CNY)</TableHead>
                <TableHead className="text-xs text-right">本期费用(CNY)</TableHead>
                <TableHead className="text-xs text-right">本期付款(CNY)</TableHead>
                <TableHead className="text-xs text-right">期末欠款(CNY)</TableHead>
                <TableHead className="text-xs text-center">操作</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {isLoading ? (
                <TableRow>
                  <TableCell colSpan={8} className="text-center py-8">
                    <Loader2 className="h-5 w-5 animate-spin mx-auto" />
                  </TableCell>
                </TableRow>
              ) : !data || data.items.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={8} className="text-center text-muted-foreground py-8">
                    暂无数据
                  </TableCell>
                </TableRow>
              ) : (
                data.items.map((item) => (
                  <TableRow key={item.supplier_id}>
                    <TableCell className="text-xs font-medium">{item.supplier_name}</TableCell>
                    <TableCell className="text-xs">
                      {item.supplier_type === "processing_plant" ? "加工厂" : item.supplier_type === "exporter" ? "出口商" : item.supplier_type === "customs_broker" ? "报关行" : item.supplier_type}
                    </TableCell>
                    <TableCell className="text-xs text-right">{fmt$(item.opening_balance)}</TableCell>
                    <TableCell className="text-xs text-right text-red-600">+{fmt$(item.current_purchase)}</TableCell>
                    <TableCell className="text-xs text-right text-red-600">+{fmt$(item.current_expenses)}</TableCell>
                    <TableCell className="text-xs text-right text-green-600">-{fmt$(item.current_payments)}</TableCell>
                    <TableCell className={cn("text-xs text-right font-medium", Number(item.closing_balance) > 0 ? "text-red-600" : "text-green-600")}>
                      {fmt$(item.closing_balance)}
                    </TableCell>
                    <TableCell className="text-center">
                      <Dialog>
                        <DialogTrigger>
                          <Button variant="ghost" size="sm" className="h-7 px-2">
                            <Eye className="h-3.5 w-3.5" />
                          </Button>
                        </DialogTrigger>
                        <DialogContent className="max-w-[800px] max-h-[85vh] overflow-y-auto">
                          <DialogHeader>
                            <DialogTitle className="text-base">应付对账明细 - {item.supplier_name} {item.supplier_type === "customs_broker" ? "(报关行)" : ""}</DialogTitle>
                          </DialogHeader>
                          <div className="space-y-3 text-sm">
                            <div className={cn("grid gap-3 text-xs bg-muted/50 p-3 rounded-lg", item.supplier_type === "customs_broker" ? "grid-cols-3" : "grid-cols-5")}>
                              {item.supplier_type !== "customs_broker" && <div><span className="text-muted-foreground">期初:</span> {fmt$(item.opening_balance)}</div>}
                              {item.supplier_type !== "customs_broker" && <div><span className="text-muted-foreground">采购:</span> +{fmt$(item.current_purchase)}</div>}
                              <div><span className="text-muted-foreground">费用:</span> +{fmt$(item.current_expenses)}</div>
                              {item.supplier_type !== "customs_broker" && <div><span className="text-muted-foreground">付款:</span> -{fmt$(item.current_payments)}</div>}
                              <div className={cn("font-medium", Number(item.closing_balance) > 0 ? "text-red-600" : "text-green-600")}>
                                期末: {fmt$(item.closing_balance)}
                              </div>
                            </div>
                            <div className="border rounded-lg overflow-hidden">
                              <Table>
                                <TableHeader>
                                  <TableRow className="bg-muted/50">
                                    <TableHead className="text-xs">日期</TableHead>
                                    <TableHead className="text-xs">类型</TableHead>
                                    <TableHead className="text-xs">发票号</TableHead>
                                    <TableHead className="text-xs">说明</TableHead>
                                    <TableHead className="text-xs text-right">借方(+)</TableHead>
                                    <TableHead className="text-xs text-right">贷方(-)</TableHead>
                                    <TableHead className="text-xs text-right">余额</TableHead>
                                  </TableRow>
                                </TableHeader>
                                <TableBody>
                                  {(item.details || []).map((d: any, idx: number) => (
                                    <TableRow key={idx}>
                                      <TableCell className="text-xs">{fmtDate(d.date)}</TableCell>
                                      <TableCell className="text-xs">
                                        {d.type === "invoice" ? "采购" : d.type === "exchange" ? "付款" : "期初"}
                                      </TableCell>
                                      <TableCell className="text-xs">{d.invoice_no || "-"}</TableCell>
                                      <TableCell className="text-xs">{d.description || "-"}</TableCell>
                                      <TableCell className="text-xs text-right text-red-600">
                                        {Number(d.debit || 0) > 0 ? fmt$(d.debit) : ""}
                                      </TableCell>
                                      <TableCell className="text-xs text-right text-green-600">
                                        {Number(d.credit || 0) > 0 ? fmt$(d.credit) : ""}
                                      </TableCell>
                                      <TableCell className={cn("text-xs text-right font-medium", Number(d.balance) > 0 ? "text-red-600" : "")}>
                                        {fmt$(d.balance)}
                                      </TableCell>
                                    </TableRow>
                                  ))}
                                </TableBody>
                              </Table>
                            </div>
                            {/* 采购明细 */}
                            <div className="space-y-1">
                              <h4 className="text-sm font-medium">采购明细</h4>
                              <div className="border rounded-md">
                                <Table>
                                  <TableHeader>
                                    <TableRow className="bg-muted/50">
                                      <TableHead className="text-xs">日期</TableHead>
                                      <TableHead className="text-xs">发票号</TableHead>
                                      <TableHead className="text-xs text-right">金额(USD)</TableHead>
                                      <TableHead className="text-xs text-right">汇率</TableHead>
                                      <TableHead className="text-xs text-right">金额(CNY)</TableHead>
                                    </TableRow>
                                  </TableHeader>
                                  <TableBody>
                                    {(item.purchase_details || []).length === 0 ? (
                                      <TableRow><TableCell colSpan={5} className="text-xs text-center py-2">无采购明细</TableCell></TableRow>
                                    ) : (
                                      (item.purchase_details || []).map((d: any, idx: number) => (
                                        <TableRow key={idx}>
                                          <TableCell className="text-xs">{fmtDate(d.date)}</TableCell>
                                          <TableCell className="text-xs">{d.invoice_no || "-"}</TableCell>
                                          <TableCell className="text-xs text-right">${Number(d.amount_usd || 0).toLocaleString("en-US", {minimumFractionDigits: 2})}</TableCell>
                                          <TableCell className="text-xs text-right">{d.exchange_rate || "-"}</TableCell>
                                          <TableCell className="text-xs text-right">{fmt$(d.amount_cny)}</TableCell>
                                        </TableRow>
                                      ))
                                    )}
                                  </TableBody>
                                </Table>
                              </div>
                            </div>
                            {/* 费用明细 */}
                            <div className="space-y-1">
                              <h4 className="text-sm font-medium">费用明细</h4>
                              <div className="border rounded-md">
                                <Table>
                                  <TableHeader>
                                    <TableRow className="bg-muted/50">
                                      <TableHead className="text-xs">日期</TableHead>
                                      <TableHead className="text-xs">发票号</TableHead>
                                      <TableHead className="text-xs">费用类型</TableHead>
                                      <TableHead className="text-xs">说明</TableHead>
                                      <TableHead className="text-xs text-right">金额</TableHead>
                                    </TableRow>
                                  </TableHeader>
                                  <TableBody>
                                    {(item.expense_details || []).length === 0 ? (
                                      <TableRow><TableCell colSpan={5} className="text-xs text-center py-2">无费用明细</TableCell></TableRow>
                                    ) : (
                                      (item.expense_details || []).map((d: any, idx: number) => (
                                        <TableRow key={idx}>
                                          <TableCell className="text-xs">{fmtDate(d.date)}</TableCell>
                                          <TableCell className="text-xs">{d.invoice_no || "-"}</TableCell>
                                          <TableCell className="text-xs">
                                            {d.expense_type === "import_duty" ? "进口关税" : d.expense_type === "import_vat" ? "进口增值税" : d.expense_type === "clearance_fee" ? "清关费" : d.expense_type || "-"}
                                          </TableCell>
                                          <TableCell className="text-xs">{d.description || "-"}</TableCell>
                                          <TableCell className="text-xs text-right">{fmt$(d.amount)}</TableCell>
                                        </TableRow>
                                      ))
                                    )}
                                  </TableBody>
                                </Table>
                              </div>
                            </div>
                            {/* 付款明细 */}
                            <div className="space-y-1">
                              <h4 className="text-sm font-medium">付款明细</h4>
                              <div className="border rounded-md">
                                <Table>
                                  <TableHeader>
                                    <TableRow className="bg-muted/50">
                                      <TableHead className="text-xs">日期</TableHead>
                                      <TableHead className="text-xs">付款类型</TableHead>
                                      <TableHead className="text-xs text-right">付款金额</TableHead>
                                      <TableHead className="text-xs">备注</TableHead>
                                    </TableRow>
                                  </TableHeader>
                                  <TableBody>
                                    {(item.payment_details || []).length === 0 ? (
                                      <TableRow><TableCell colSpan={4} className="text-xs text-center py-2">无付款明细</TableCell></TableRow>
                                    ) : (
                                      (item.payment_details || []).map((d: any, idx: number) => (
                                        <TableRow key={idx}>
                                          <TableCell className="text-xs">{fmtDate(d.date)}</TableCell>
                                          <TableCell className="text-xs">
                                            {d.payment_type === "exchange" ? "购汇付款" : d.payment_type === "clearance_payment" ? "清关费付款" : d.payment_type || "-"}
                                          </TableCell>
                                          <TableCell className="text-xs text-right">{fmt$(d.amount)}</TableCell>
                                          <TableCell className="text-xs">{d.description || d.reference_no || "-"}</TableCell>
                                        </TableRow>
                                      ))
                                    )}
                                  </TableBody>
                                </Table>
                              </div>
                            </div>
                          </div>
                        </DialogContent>
                      </Dialog>
                    </TableCell>
                  </TableRow>
                ))
              )}
            </TableBody>
          </Table>
          <SimplePagination
            current={page}
            total={data?.total || 0}
            pageSize={30}
            onChange={setPage}
          />
        </CardContent>
      </Card>
    </div>
  );
}
