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
import { Loader2, Eye, Printer, Languages, Search } from "lucide-react";

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

// ==================== Tab 2: 单票财报 ====================

function InvoiceReportsTab() {
  const [page, setPage] = useState(0);
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");
  const [searchKey, setSearchKey] = useState("");
  const [detailId, setDetailId] = useState<number | null>(null);
  const [detailOpen, setDetailOpen] = useState(false);
  const [detailLang, setDetailLang] = useState<"zh" | "en">("zh");

  const { data, isLoading } = useQuery({
    queryKey: ["reports-invoices", page, startDate, endDate, searchKey],
    queryFn: async () => {
      const params = new URLSearchParams({
        skip: String(page * 30),
        limit: "30",
      });
      if (startDate) params.set("start_date", startDate);
      if (endDate) params.set("end_date", endDate);
      const res = await api.get(`/v1/reports/invoices?${params}`);
      return res.data as { total: number; items: any[]; skip: number; limit: number };
    },
  });

  const { data: detailData } = useQuery({
    queryKey: ["invoice-report-detail", detailId],
    queryFn: async () => {
      if (!detailId) return null;
      const res = await api.get(`/v1/reports/invoice/${detailId}`);
      return res.data;
    },
    enabled: !!detailId,
  });

  const filtered = useMemo(() => {
    if (!data) return [];
    if (!searchKey) return data.items;
    return data.items.filter((item) =>
      (item.invoice_no || "").toLowerCase().includes(searchKey.toLowerCase()) ||
      (item.supplier_name || "").toLowerCase().includes(searchKey.toLowerCase()) ||
      (item.exporter_name || "").toLowerCase().includes(searchKey.toLowerCase()) ||
      (item.processing_plant_name || "").toLowerCase().includes(searchKey.toLowerCase())
    );
  }, [data, searchKey]);

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap items-end gap-3">
        <DateFilter
          startDate={startDate}
          endDate={endDate}
          onStartChange={setStartDate}
          onEndChange={setEndDate}
          onSearch={() => setPage(0)}
        />
        <div className="ml-auto">
          <Input
            placeholder="搜索发票号/供应商"
            className="h-8 w-48"
            value={searchKey}
            onChange={(e) => { setSearchKey(e.target.value); setPage(0); }}
          />
        </div>
      </div>

      <Card>
        <CardContent className="p-0">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead className="text-xs">发票号</TableHead>
                <TableHead className="text-xs">日期</TableHead>
                <TableHead className="text-xs">供应商</TableHead>
                <TableHead className="text-xs">批次</TableHead>
                <TableHead className="text-xs text-right">采购金额(USD)</TableHead>
                <TableHead className="text-xs text-right">采购成本(CNY)</TableHead>
                <TableHead className="text-xs text-right">销售净额(CNY)</TableHead>
                <TableHead className="text-xs text-right">净利润(CNY)</TableHead>
                <TableHead className="text-xs text-right">利润率</TableHead>
                <TableHead className="text-xs text-center">操作</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {isLoading ? (
                <TableRow>
                  <TableCell colSpan={10} className="text-center py-8">
                    <Loader2 className="h-5 w-5 animate-spin mx-auto" />
                  </TableCell>
                </TableRow>
              ) : filtered.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={10} className="text-center text-muted-foreground py-8">
                    暂无数据
                  </TableCell>
                </TableRow>
              ) : (
                filtered.map((item) => (
                  <TableRow key={item.invoice_id}>
                    <TableCell className="text-xs font-medium">{item.invoice_no}</TableCell>
                    <TableCell className="text-xs">{fmtDate(item.invoice_date)}</TableCell>
                    <TableCell className="text-xs">{item.supplier_name || item.exporter_name || "-"}</TableCell>
                    <TableCell className="text-xs">{item.batch_code || "-"}</TableCell>
                    <TableCell className="text-xs text-right">${Number(item.total_amount_usd || 0).toLocaleString()}</TableCell>
                    <TableCell className="text-xs text-right">{fmt$(item.purchase_cost_cny)}</TableCell>
                    <TableCell className="text-xs text-right">{fmt$(item.sales_net)}</TableCell>
                    <TableCell className={cn("text-xs text-right font-medium", clsProfit(Number(item.net_profit)))}>
                      {fmt$(item.net_profit)}
                    </TableCell>
                    <TableCell className={cn("text-xs text-right", clsProfit(Number(item.profit_margin || 0)))}>
                      {item.profit_margin !== null && item.profit_margin !== undefined
                        ? `${Number(item.profit_margin).toFixed(1)}%`
                        : "-"}
                    </TableCell>
                    <TableCell className="text-center">
                      <Button variant="ghost" size="sm" className="h-7 px-2" onClick={() => { setDetailId(item.invoice_id); setDetailOpen(true); }}>
                        <Eye className="h-3.5 w-3.5" />
                      </Button>
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

      {/* 单票财报详情弹窗 — 提取到循环外部 */}
      <Dialog open={detailOpen} onOpenChange={(open) => { setDetailOpen(open); if (!open) setDetailId(null); }}>
        <DialogContent className="max-w-[750px] w-full p-4 sm:!max-w-[750px] max-h-[85vh] overflow-y-auto print:max-w-none print:w-full print:h-auto print:overflow-visible">
          <DialogHeader>
            <div className="flex items-center justify-between">
              <DialogTitle className="text-base">
                {detailLang === "zh" ? "单票财报详情" : "Invoice Financial Report"}
              </DialogTitle>
              <div className="flex items-center gap-2">
                <Button variant="ghost" size="sm" className="h-7 gap-1" onClick={() => setDetailLang(detailLang === "zh" ? "en" : "zh")}>
                  <Languages className="h-3.5 w-3.5" />
                  {detailLang === "zh" ? "EN" : "中"}
                </Button>
                <Button variant="ghost" size="sm" className="h-7 gap-1" onClick={() => window.print()}>
                  <Printer className="h-3.5 w-3.5" />
                  {detailLang === "zh" ? "打印" : "Print"}
                </Button>
              </div>
            </div>
          </DialogHeader>
          {detailData ? (
            <div className="space-y-3 text-sm">
              <style>{`
                @media print {
                  body * { visibility: hidden; }
                  [data-radix-dialog-content] *, [data-radix-dialog-content] { visibility: visible; }
                  [data-radix-dialog-content] { position: absolute; left: 0; top: 0; width: 100%; }
                  .print\:hidden { display: none !important; }
                }
              `}</style>

              {/* === 第一行：标题 === */}
              <div className="border-b pb-2 mb-2">
                <h2 className="text-lg font-bold text-slate-800">
                  {detailLang === "zh" ? "财务报告" : "Financial Report"} · {detailData.invoice_no}
                  <span className="text-sm font-normal text-slate-400 ml-3">{fmtDate(detailData.invoice_date)}</span>
                </h2>
              </div>

              {/* === 第二行：采购信息 + 进口费用（与批次财报模板一致） === */}
              <div className="grid grid-cols-2 gap-3">
                <div className="border rounded-lg p-2.5 space-y-1.5">
                  <p className="text-xs font-semibold text-blue-600">{detailLang === "zh" ? "采购信息" : "Purchase Info"}</p>
                  <div className="flex justify-between text-xs"><span className="text-muted-foreground">{detailLang === "zh" ? "采购金额(USD)" : "Amount(USD)"}</span><span>${Number(detailData.total_amount_usd || 0).toLocaleString()}</span></div>
                  <div className="flex justify-between text-xs"><span className="text-muted-foreground">{detailLang === "zh" ? "采购成本(CNY)" : "Cost(CNY)"}</span><span>{fmt$(detailData.purchase_cost_cny)}</span></div>
                  <div className="flex justify-between text-xs"><span className="text-muted-foreground">{detailLang === "zh" ? "重量" : "Weight"}</span><span>{Number(detailData.total_weight_kg || 0).toLocaleString()} kg</span></div>
                  <div className="flex justify-between text-xs"><span className="text-muted-foreground">{detailLang === "zh" ? "箱数" : "Boxes"}</span><span>{detailData.total_boxes || 0}</span></div>
                </div>
                <div className="border rounded-lg p-2.5 space-y-1.5">
                  <p className="text-xs font-semibold text-amber-600">{detailLang === "zh" ? "进口费用" : "Import Costs"}</p>
                  <div className="flex justify-between text-xs"><span className="text-muted-foreground">{detailLang === "zh" ? "进口关税" : "Import Duty"}</span><span>{fmt$(detailData.import_duty)}</span></div>
                  <div className="flex justify-between text-xs"><span className="text-muted-foreground">{detailLang === "zh" ? "进口增值税" : "Import VAT"}</span><span>{fmt$(detailData.import_vat)}</span></div>
                  <div className="flex justify-between text-xs font-medium border-t pt-1"><span>{detailLang === "zh" ? "税费合计" : "Total Taxes"}</span><span>{fmt$(detailData.total_taxes)}</span></div>
                  {(() => {
                    const cb = detailData.clearance_breakdown || {};
                    const hasClearance = Number(cb.clearance_fee || 0) > 0 || Number(cb.freight_fee || 0) > 0 || Number(cb.other_costs || 0) > 0 || Number(cb.inspection_fee || 0) > 0 || Number(cb.quarantine_fee || 0) > 0;
                    return (
                      <>
                        {Number(cb.clearance_fee || 0) > 0 && <div className="flex justify-between text-xs"><span className="text-muted-foreground">{detailLang === "zh" ? "提货费" : "Pickup Fee"}</span><span>{fmt$(cb.clearance_fee)}</span></div>}
                        {Number(cb.freight_fee || 0) > 0 && <div className="flex justify-between text-xs"><span className="text-muted-foreground">{detailLang === "zh" ? "运费" : "Freight"}</span><span>{fmt$(cb.freight_fee)}</span></div>}
                        {Number(cb.other_costs || 0) > 0 && <div className="flex justify-between text-xs"><span className="text-muted-foreground">{detailLang === "zh" ? "报关服务费" : "Customs Service"}</span><span>{fmt$(cb.other_costs)}</span></div>}
                        {Number(cb.inspection_fee || 0) > 0 && <div className="flex justify-between text-xs"><span className="text-muted-foreground">{detailLang === "zh" ? "目的地查验费" : "Inspection Fee"}</span><span>{fmt$(cb.inspection_fee)}</span></div>}
                        {Number(cb.quarantine_fee || 0) > 0 && <div className="flex justify-between text-xs"><span className="text-muted-foreground">{detailLang === "zh" ? "冷藏费" : "Cold Storage"}</span><span>{fmt$(cb.quarantine_fee)}</span></div>}
                        {hasClearance && <div className="flex justify-between text-xs font-medium border-t pt-1"><span>{detailLang === "zh" ? "清关费合计" : "Clearance Total"}</span><span>{fmt$(detailData.clearance_cost)}</span></div>}
                      </>
                    );
                  })()}
                  <div className="flex justify-between text-xs font-bold border-t-2 border-amber-200 pt-1"><span>{detailLang === "zh" ? "合计" : "Total"}</span><span className="text-amber-700">{fmt$(Number(detailData.total_taxes || 0) + Number(detailData.clearance_cost || 0))}</span></div>
                </div>
              </div>

              {/* === 第三行：购汇登记 + 损益分析 === */}
              <div className="grid grid-cols-2 gap-3">
                <div className="border rounded-lg p-2.5 space-y-1.5">
                  <p className="text-xs font-semibold text-green-600">{detailLang === "zh" ? "购汇登记" : "Exchange"}</p>
                  <div className="flex justify-between text-xs"><span className="text-muted-foreground">{detailLang === "zh" ? "汇率" : "Rate"}</span><span>{detailData.exchange_rate || "-"}</span></div>
                  <div className="flex justify-between text-xs"><span className="text-muted-foreground">{detailLang === "zh" ? "购汇金额" : "Payment"}</span><span>{fmt$(detailData.exchange_payment)}</span></div>
                  <div className="flex justify-between text-xs"><span className="text-muted-foreground">{detailLang === "zh" ? "手续费" : "Fee"}</span><span>{fmt$(detailData.exchange_fee)}</span></div>
                  <div className="flex justify-between text-xs font-medium border-t pt-1"><span>{detailLang === "zh" ? "购汇合计" : "Total"}</span><span>{fmt$(Number(detailData.exchange_payment || 0) + Number(detailData.exchange_fee || 0))}</span></div>
                </div>
                <div className="border rounded-lg p-2.5 space-y-1.5">
                  <p className="text-xs font-semibold text-purple-600">{detailLang === "zh" ? "损益分析" : "Profit/Loss"}</p>
                  
                  {/* 第一步：销售毛额 */}
                  <div className="flex justify-between text-xs"><span className="text-muted-foreground">{detailLang === "zh" ? "销售毛额" : "Gross Sales"}</span><span className="font-medium">{fmt$(detailData.total_sales_amount)}</span></div>
                  
                  {/* 第二步：扣减项 → 算出销售净额 */}
                  {Number(detailData.total_scan_fee || 0) !== 0 && (
                    <div className="flex justify-between text-xs"><span className="text-muted-foreground pl-2">{detailLang === "zh" ? "扫码费" : "Scan Fee"}</span><span className="text-red-500">-{fmt$(detailData.total_scan_fee)}</span></div>
                  )}
                  {Number(detailData.total_rounding || 0) !== 0 && (
                    <div className="flex justify-between text-xs"><span className="text-muted-foreground pl-2">{detailLang === "zh" ? "抹零" : "Rounding"}</span><span className="text-red-500">-{fmt$(detailData.total_rounding)}</span></div>
                  )}
                  {Number(detailData.total_after_sales || 0) !== 0 && (
                    <div className="flex justify-between text-xs"><span className="text-muted-foreground pl-2">{detailLang === "zh" ? "售后调整" : "After Sales"}</span><span className="text-red-500">-{fmt$(detailData.total_after_sales)}</span></div>
                  )}
                  {Number(detailData.total_discount || 0) !== 0 && (
                    <div className="flex justify-between text-xs"><span className="text-muted-foreground pl-2">{detailLang === "zh" ? "折扣" : "Discount"}</span><span className="text-red-500">-{fmt$(detailData.total_discount)}</span></div>
                  )}
                  <div className="flex justify-between text-xs font-medium border-t border-dashed pt-1">
                    <span className="text-muted-foreground">{detailLang === "zh" ? "销售净额" : "Net Sales"}</span>
                    <span className="font-medium">{fmt$(detailData.total_sales_net)}</span>
                  </div>
                  
                  {/* 第三步：继续扣减 → 成本费用 */}
                  {Number(detailData.total_commission || 0) !== 0 && (
                    <div className="flex justify-between text-xs"><span className="text-muted-foreground pl-2">{detailLang === "zh" ? "业务员提成" : "Commission"}</span><span className="text-red-500">-{fmt$(detailData.total_commission)}</span></div>
                  )}
                  {Number(detailData.shrinkage || 0) !== 0 && (
                    <div className="flex justify-between text-xs">
                      <span className="text-muted-foreground pl-2">{detailLang === "zh" ? `账面损耗(采购${Number(detailData.total_weight_kg || 0).toLocaleString()}kg - 销售${Number(detailData.sales_weight || 0).toLocaleString()}kg = ${Number((detailData.total_weight_kg || 0) - (detailData.sales_weight || 0)).toLocaleString()}kg)` : "Shrinkage"}</span>
                      <span className="text-red-500">-{fmt$(detailData.shrinkage)}</span>
                    </div>
                  )}
                  <div className="flex justify-between text-xs">
                    <span className="text-muted-foreground pl-2">{detailLang === "zh" ? "购汇合计" : "Exchange Total"}</span>
                    <span className="text-red-500">-{fmt$(Number(detailData.exchange_payment || 0) + Number(detailData.exchange_fee || 0))}</span>
                  </div>
                  <div className="flex justify-between text-xs">
                    <span className="text-muted-foreground pl-2">{detailLang === "zh" ? "进口费用合计" : "Import Cost Total"}</span>
                    <span className="text-red-500">-{fmt$(Number(detailData.total_taxes || 0) + Number(detailData.clearance_cost || 0))}</span>
                  </div>
                  
                  {/* 第四步：净利润 */}
                  <div className="flex justify-between text-xs font-medium border-t pt-1">
                    <span className={clsProfit(Number(detailData.net_profit))}>{detailLang === "zh" ? "净利润" : "Net Profit"}</span>
                    <span className={clsProfit(Number(detailData.net_profit))}>{fmt$(detailData.net_profit)}</span>
                  </div>
                </div>
              </div>

              {/* === 利润汇总行（单票） === */}
              <div className="bg-slate-100 border rounded-lg p-3 space-y-2">
                <p className="text-xs font-semibold text-slate-700">{detailLang === "zh" ? "利润汇总" : "Profit Summary"}</p>
                <div className="grid grid-cols-3 gap-4 text-xs">
                  <div className="text-center">
                    <div className="text-muted-foreground mb-0.5">{detailLang === "zh" ? "期初净利润留存" : "Opening Profit"}</div>
                    <div className="font-semibold">{fmt$(Number(detailData.cumulative_profit || 0) - Number(detailData.net_profit || 0))}</div>
                  </div>
                  <div className="text-center">
                    <div className="text-muted-foreground mb-0.5">{detailLang === "zh" ? "本期经营净利润" : "Current Profit"}</div>
                    <div className={clsProfit(Number(detailData.net_profit))}>{fmt$(detailData.net_profit)}</div>
                  </div>
                  <div className="text-center">
                    <div className="text-muted-foreground mb-0.5">{detailLang === "zh" ? "累计净利润总额" : "Cumulative Profit"}</div>
                    <div className="font-semibold">{fmt$(detailData.cumulative_profit)}</div>
                  </div>
                </div>
              </div>

              {/* === 产品明细（单票独有） === */}
              {(detailData.products && detailData.products.length > 0) && (
                <div className="border rounded-lg overflow-hidden">
                  <p className="text-xs font-semibold px-2.5 py-1.5 bg-muted/50">{detailLang === "zh" ? "产品明细" : "Products"}</p>
                  <Table>
                    <TableHeader>
                      <TableRow className="bg-muted/50">
                        <TableHead className="text-xs py-1">{detailLang === "zh" ? "产品" : "Product"}</TableHead>
                        <TableHead className="text-xs py-1">{detailLang === "zh" ? "规格" : "Spec"}</TableHead>
                        <TableHead className="text-xs py-1 text-right">{detailLang === "zh" ? "箱数" : "Boxes"}</TableHead>
                        <TableHead className="text-xs py-1 text-right">{detailLang === "zh" ? "净重(kg)" : "Weight"}</TableHead>
                        <TableHead className="text-xs py-1 text-right">{detailLang === "zh" ? "单价" : "Price"}</TableHead>
                        <TableHead className="text-xs py-1 text-right">{detailLang === "zh" ? "金额" : "Amount"}</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {detailData.products.map((p: any, idx: number) => (
                        <TableRow key={idx}>
                          <TableCell className="text-xs py-1">{p.product_name || "-"}</TableCell>
                          <TableCell className="text-xs py-1">{p.product_spec || "-"}</TableCell>
                          <TableCell className="text-xs py-1 text-right">{p.box_count || 0}</TableCell>
                          <TableCell className="text-xs py-1 text-right">{Number(p.net_weight_kg || 0).toLocaleString()}</TableCell>
                          <TableCell className="text-xs py-1 text-right">${p.unit_price || 0}</TableCell>
                          <TableCell className="text-xs py-1 text-right font-medium">${p.total_amount || 0}</TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </div>
              )}

              {/* === 第四行：销售明细 === */}
              {(detailData.sales && detailData.sales.length > 0) && (
                <div className="border rounded-lg overflow-hidden">
                  <p className="text-xs font-semibold px-2.5 py-1.5 bg-muted/50">{detailLang === "zh" ? "销售明细" : "Sales Details"}</p>
                  <Table>
                    <TableHeader>
                      <TableRow className="bg-muted/50">
                        <TableHead className="text-xs py-1">{detailLang === "zh" ? "日期" : "Date"}</TableHead>
                        <TableHead className="text-xs py-1">{detailLang === "zh" ? "客户" : "Customer"}</TableHead>
                        <TableHead className="text-xs py-1">{detailLang === "zh" ? "规格" : "Spec"}</TableHead>
                        <TableHead className="text-xs py-1 text-right">{detailLang === "zh" ? "箱数" : "Boxes"}</TableHead>
                        <TableHead className="text-xs py-1 text-right">{detailLang === "zh" ? "重量" : "Weight"}</TableHead>
                        <TableHead className="text-xs py-1 text-right">{detailLang === "zh" ? "单价" : "Price"}</TableHead>
                        <TableHead className="text-xs py-1 text-right">{detailLang === "zh" ? "净额" : "Net"}</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {detailData.sales.map((sale: any, idx: number) => (
                        <TableRow key={idx}>
                          <TableCell className="text-xs py-1">{fmtDate(sale.sale_date)}</TableCell>
                          <TableCell className="text-xs py-1">{sale.customer_name || "-"}</TableCell>
                          <TableCell className="text-xs py-1">{sale.spec || "-"}</TableCell>
                          <TableCell className="text-xs py-1 text-right">{sale.box_count || 0}</TableCell>
                          <TableCell className="text-xs py-1 text-right">{Number(sale.weight_kg || 0).toLocaleString()}</TableCell>
                          <TableCell className="text-xs py-1 text-right">{fmt$(sale.unit_price)}</TableCell>
                          <TableCell className="text-xs py-1 text-right font-medium">{fmt$(sale.net_amount)}</TableCell>
                        </TableRow>
                      ))}
                      {/* 汇总行 */}
                      <TableRow className="border-t-2 font-medium bg-muted/30">
                        <TableCell className="text-xs py-1" colSpan={3}>{detailLang === "zh" ? "合计" : "Total"}</TableCell>
                        <TableCell className="text-xs py-1 text-right">{detailData.sales.reduce((sum: number, s: any) => sum + (s.box_count || 0), 0)}</TableCell>
                        <TableCell className="text-xs py-1 text-right">{Number(detailData.total_sales_weight || 0).toLocaleString()} kg</TableCell>
                        <TableCell className="text-xs py-1 text-right">—</TableCell>
                        <TableCell className="text-xs py-1 text-right font-bold">{fmt$(detailData.total_sales_net)}</TableCell>
                      </TableRow>
                    </TableBody>
                  </Table>
                </div>
              )}

              {/* === 第五行：溯源信息 === */}
              <div className="border rounded-lg p-2.5">
                <p className="text-xs font-semibold text-indigo-600 mb-2">{detailLang === "zh" ? "溯源信息" : "Traceability"}</p>
                <div className="grid grid-cols-4 gap-4 text-center text-xs">
                  <div>
                    <div className="text-lg mb-0.5">🏭</div>
                    <div className="text-muted-foreground">{detailLang === "zh" ? "加工厂" : "Plant"}</div>
                    <div className="font-medium">{detailData.processing_plant_name || "-"}</div>
                  </div>
                  <div>
                    <div className="text-lg mb-0.5">📍</div>
                    <div className="text-muted-foreground">{detailLang === "zh" ? "养殖场" : "Farm"}</div>
                    <div className="font-medium">{detailData.fish_farm_name || "-"}</div>
                  </div>
                  <div>
                    <div className="text-lg mb-0.5">🚢</div>
                    <div className="text-muted-foreground">{detailLang === "zh" ? "出口商" : "Exporter"}</div>
                    <div className="font-medium">{detailData.exporter_name || "-"}</div>
                  </div>
                  <div>
                    <div className="text-lg mb-0.5">💰</div>
                    <div className="text-muted-foreground">{detailLang === "zh" ? "供应商" : "Supplier"}</div>
                    <div className="font-medium">{detailData.supplier_name || "-"}</div>
                  </div>
                </div>
                <div className="text-xs text-muted-foreground flex flex-wrap gap-x-3 gap-y-0.5 pt-2 mt-2 border-t">
                  {detailData.processing_plant_eu_code && (
                    <span>EU注册号：{detailData.processing_plant_eu_code}</span>
                  )}
                  {detailData.processing_plant_customs_code && (
                    <span>CN海关准入：{detailData.processing_plant_customs_code}</span>
                  )}
                  {detailData.fish_farm_ggn && (
                    <span>养殖GGN：{detailData.fish_farm_ggn}</span>
                  )}
                  {detailData.fish_farm_coc_no && (
                    <span>监管链COC：{detailData.fish_farm_coc_no}</span>
                  )}
                  {detailData.processing_plant_coc_no && (
                    <span>监管链COC(加工厂)：{detailData.processing_plant_coc_no}</span>
                  )}
                  {detailData.fish_farm_area && (
                    <span>养殖区：{detailData.fish_farm_area}</span>
                  )}
                </div>
              </div>

              {/* 底部汇总已删除 */}
            </div>
          ) : (
            <div className="py-8 text-center">
              <Loader2 className="h-5 w-5 animate-spin mx-auto" />
            </div>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
}
