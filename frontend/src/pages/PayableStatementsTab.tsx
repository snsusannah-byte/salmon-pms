import { useState, useMemo, useRef, useEffect } from "react";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { toast } from "sonner";
import { Loader2, Eye, ChevronLeft, ChevronRight, Search, Download, Printer, X, FileText } from "lucide-react";

function fmt$(v: number | string | null | undefined) {
  const n = Number(v ?? 0);
  if (Number.isNaN(n)) return "¥0.00";
  return `¥${n.toLocaleString("zh-CN", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

function fmtDate(d: string | null | undefined) {
  if (!d) return "-";
  return new Date(d).toLocaleDateString("zh-CN");
}

// ==================== Tab 4: 应付对账单 (Inline 展示模式) ====================

export function PayableStatementsTab() {
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");
  const [supplierSearch, setSupplierSearch] = useState("");
  const [selectedSupplierId, setSelectedSupplierId] = useState<string>("");
  const [doSearch, setDoSearch] = useState(false);
  const supplierDropdownRef = useRef<HTMLDivElement>(null);

  // 点击外部关闭供应商下拉框
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (supplierDropdownRef.current && !supplierDropdownRef.current.contains(event.target as Node)) {
        const target = event.target as HTMLElement;
        if (!target.closest('input[placeholder="搜索供应商/报关行..."]')) {
          setSupplierSearch("");
        }
      }
    };
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  // 供应商列表
  const { data: suppliers } = useQuery({
    queryKey: ["suppliers-list"],
    queryFn: async () => {
      const res = await api.get("/v1/companies/?limit=500");
      return (res.data?.items || []) as { id: number; name: string; code?: string }[];
    },
  });

  const filteredSuppliers = useMemo(() => {
    if (!suppliers) return [];
    if (!supplierSearch.trim()) return suppliers;
    return suppliers.filter(c =>
      c.name.toLowerCase().includes(supplierSearch.toLowerCase()) ||
      (c.code || "").toLowerCase().includes(supplierSearch.toLowerCase())
    );
  }, [suppliers, supplierSearch]);

  const { data, isLoading } = useQuery({
    queryKey: ["reports-payable", startDate, endDate, doSearch],
    queryFn: async () => {
      const params = new URLSearchParams({ skip: "0", limit: "500" });
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
    enabled: doSearch,
  });

  const handleSearch = () => {
    setDoSearch(true);
  };

  const exportCSV = () => {
    if (!data) return;
    const params = new URLSearchParams();
    if (startDate) params.set("start_date", startDate);
    if (endDate) params.set("end_date", endDate);
    if (selectedSupplierId) params.set("supplier_id", selectedSupplierId);
    const url = `/api/v1/reports/payable-statements/export?${params}`;
    window.open(url, "_blank");
    toast.success("正在导出...");
  };

  const periodText = `${startDate || "全部"} ~ ${endDate || "全部"}`;

  const activeItem = useMemo(() => {
    if (!data?.items?.length) return null;
    if (selectedSupplierId) {
      return data.items.find(i => String(i.supplier_id) === selectedSupplierId) || null;
    }
    return null;
  }, [data, selectedSupplierId]);

  return (
    <>
      <style>{`
        @media print {
          nav, aside, .sidebar, [role="navigation"] { display: none !important; }
          body { -webkit-print-color-adjust: exact; print-color-adjust: exact; }
          .print-content { display: block !important; width: 100% !important; margin: 0 !important; padding: 0 !important; }
          .print-content table { font-size: 9px; width: 100%; border-collapse: collapse; }
          .print-content th, .print-content td { padding: 1px 3px !important; border: 1px solid #ccc !important; }
          .print-content h4 { font-size: 10px; margin: 4px 0 2px 0; }
          .print-empty { display: none !important; }
          .print-content .grid { gap: 2px !important; }
          .print-content .rounded-lg { border: 1px solid #ccc !important; padding: 4px !important; }
        }
      `}</style>
      <div className="space-y-4">
        {/* 查询条件 */}
        <Card className="print-hidden-query print:hidden">
          <CardHeader className="pb-3">
            <CardTitle className="text-base flex items-center gap-2">
              <FileText className="h-5 w-5 text-blue-500" />
              应付对账单
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid grid-cols-3 gap-4">
              <div className="space-y-1">
                <Label className="text-xs text-muted-foreground">对账周期（开始）</Label>
                <Input type="date" value={startDate} onChange={e => setStartDate(e.target.value)} />
              </div>
              <div className="space-y-1">
                <Label className="text-xs text-muted-foreground">对账周期（结束）</Label>
                <Input type="date" value={endDate} onChange={e => setEndDate(e.target.value)} />
              </div>
              <div className="space-y-1 relative" ref={supplierDropdownRef}>
                <Label className="text-xs text-muted-foreground">供应商/报关行（留空=全部）</Label>
                <div className="relative">
                  <Input
                    value={supplierSearch || (selectedSupplierId && suppliers?.find(c => String(c.id) === selectedSupplierId)?.name || "")}
                    onChange={e => { setSupplierSearch(e.target.value); setSelectedSupplierId(""); }}
                    placeholder="搜索供应商/报关行..."
                    className="pr-8"
                  />
                  {selectedSupplierId && (
                    <button
                      className="absolute right-2 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600"
                      onClick={() => { setSelectedSupplierId(""); setSupplierSearch(""); }}
                    >
                      <X className="h-4 w-4" />
                    </button>
                  )}
                </div>
                {supplierSearch && filteredSuppliers.length > 0 && (
                  <div className="absolute z-50 w-full bg-white border rounded shadow-lg mt-1 max-h-48 overflow-auto">
                    {filteredSuppliers.map(c => (
                      <div
                        key={c.id}
                        className="px-3 py-2 hover:bg-gray-100 cursor-pointer text-sm"
                        onClick={() => { setSelectedSupplierId(String(c.id)); setSupplierSearch(c.name); }}
                      >
                        {c.name} {c.code ? `(${c.code})` : ""}
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
            <div className="flex items-center gap-2">
              <Button onClick={handleSearch} className="bg-blue-600 hover:bg-blue-700">
                <Search className="h-4 w-4 mr-1" /> 查询
              </Button>
              <Button variant="outline" onClick={exportCSV} disabled={!data?.items?.length}>
                <Download className="h-4 w-4 mr-1" /> 导出CSV
              </Button>
              <Button variant="outline" onClick={() => window.print()} disabled={!activeItem}>
                <Printer className="h-4 w-4 mr-1" /> 打印对账单
              </Button>
              <span className="text-xs text-muted-foreground ml-2">
                不选日期则查询全部；不选供应商则查询全部。
              </span>
            </div>
          </CardContent>
        </Card>

        {/* 查询结果 */}
        {doSearch && (
          <>
            {isLoading ? (
              <div className="text-center py-8">
                <Loader2 className="h-5 w-5 animate-spin mx-auto" />
              </div>
            ) : !data || data.items.length === 0 ? (
              <div className="text-center text-muted-foreground py-8">
                暂无数据
              </div>
            ) : (
              <>
                {activeItem ? (
                  <div className="space-y-4 print-content">
                    {/* 打印标题 */}
                    <div className="hidden print:block text-center space-y-1 mb-4">
                      <h2 className="text-xl font-bold">{activeItem.supplier_name}对账单</h2>
                      <p className="text-sm">对账周期：{periodText}</p>
                    </div>

                    {/* 屏幕汇总 */}
                    <div className="bg-muted/30 rounded-lg p-4 space-y-2 print:hidden">
                      <div className="flex items-center justify-between">
                        <div className="text-lg font-semibold">{activeItem.supplier_name}</div>
                        <div className="text-sm text-muted-foreground">对账周期：{periodText}</div>
                      </div>
                      {activeItem.supplier_type === "customs_broker" ? (
                        <div className="grid grid-cols-4 gap-4 text-sm text-center">
                          <div><div className="text-xs text-muted-foreground">期初欠款</div><div className="font-medium">{fmt$(activeItem.opening_balance)}</div></div>
                          <div><div className="text-xs text-muted-foreground">本期费用</div><div className="font-medium text-orange-600">{fmt$(activeItem.current_expenses || 0)}</div></div>
                          <div><div className="text-xs text-muted-foreground">本期付款</div><div className="font-medium text-green-600">{fmt$(activeItem.current_payments)}</div></div>
                          <div><div className="text-xs text-muted-foreground">期末欠款</div><div className={cn("font-medium", Number(activeItem.closing_balance) > 0 ? "text-red-600" : "text-green-600")}>{fmt$(activeItem.closing_balance)}</div></div>
                        </div>
                      ) : (
                        <div className="grid grid-cols-5 gap-4 text-sm text-center">
                          <div><div className="text-xs text-muted-foreground">期初欠款</div><div className="font-medium">{fmt$(activeItem.opening_balance)}</div></div>
                          <div><div className="text-xs text-muted-foreground">本期采购</div><div className="font-medium text-red-600">{fmt$(activeItem.current_purchase)}</div></div>
                          <div><div className="text-xs text-muted-foreground">本期费用</div><div className="font-medium text-orange-600">{fmt$(activeItem.current_expenses || 0)}</div></div>
                          <div><div className="text-xs text-muted-foreground">本期付款</div><div className="font-medium text-green-600">{fmt$(activeItem.current_payments)}</div></div>
                          <div><div className="text-xs text-muted-foreground">期末欠款</div><div className={cn("font-medium", Number(activeItem.closing_balance) > 0 ? "text-red-600" : "text-green-600")}>{fmt$(activeItem.closing_balance)}</div></div>
                        </div>
                      )}
                    </div>

                    {/* 采购明细（报关行不显示） */}
                    {(activeItem.supplier_type || '') !== "customs_broker" && (
                    <div className="space-y-1">
                      <h4 className="text-sm font-medium">采购明细</h4>
                      <div className="border rounded-md">
                        <Table>
                          <TableHeader>
                            <TableRow className="bg-muted/20">
                              <TableHead className="text-xs py-1.5">日期</TableHead>
                              <TableHead className="text-xs py-1.5">发票号</TableHead>
                              <TableHead className="text-xs py-1.5 text-right">金额(USD)</TableHead>
                              <TableHead className="text-xs py-1.5 text-right">汇率</TableHead>
                              <TableHead className="text-xs py-1.5 text-right">金额(CNY)</TableHead>
                            </TableRow>
                          </TableHeader>
                          <TableBody>
                            {(activeItem.purchase_details || []).length === 0 ? (
                              <TableRow className="print-empty"><TableCell colSpan={5} className="text-xs text-center text-muted-foreground py-2">无采购明细</TableCell></TableRow>
                            ) : (
                              (activeItem.purchase_details || []).map((d: any, idx: number) => (
                                <TableRow key={idx}>
                                  <TableCell className="text-xs py-1.5">{fmtDate(d.date)}</TableCell>
                                  <TableCell className="text-xs py-1.5">{d.invoice_no || "-"}</TableCell>
                                  <TableCell className="text-xs py-1.5 text-right">${Number(d.amount_usd || 0).toLocaleString("en-US", {minimumFractionDigits: 2})}</TableCell>
                                  <TableCell className="text-xs py-1.5 text-right">{d.exchange_rate || "-"}</TableCell>
                                  <TableCell className="text-xs py-1.5 text-right">{fmt$(d.amount_cny)}</TableCell>
                                </TableRow>
                              ))
                            )}
                            <TableRow className="bg-muted/30 font-medium">
                              <TableCell className="text-xs py-1.5" colSpan={2}>采购合计</TableCell>
                              <TableCell className="text-xs py-1.5 text-right">${(activeItem.purchase_details || []).reduce((sum: number, d: any) => sum + (Number(d.amount_usd) || 0), 0).toLocaleString("en-US", {minimumFractionDigits: 2})}</TableCell>
                              <TableCell className="text-xs py-1.5"></TableCell>
                              <TableCell className="text-xs py-1.5 text-right">{fmt$((activeItem.purchase_details || []).reduce((sum: number, d: any) => sum + (Number(d.amount_cny) || 0), 0))}</TableCell>
                            </TableRow>
                          </TableBody>
                        </Table>
                      </div>
                    </div>
                    )}

                    {/* 费用明细 */}
                    <div className="space-y-1">
                      <h4 className="text-sm font-medium">费用明细</h4>
                      <div className="border rounded-md">
                        <Table>
                          <TableHeader>
                            <TableRow className="bg-muted/20">
                              <TableHead className="text-xs py-1.5">日期</TableHead>
                              <TableHead className="text-xs py-1.5">发票号</TableHead>
                              {activeItem.supplier_type === "customs_broker" ? (
                                <>
                                  <TableHead className="text-xs py-1.5 text-right">出关毛重(kg)</TableHead>
                                  <TableHead className="text-xs py-1.5 text-right">运费</TableHead>
                                  <TableHead className="text-xs py-1.5 text-right">目的地查验费</TableHead>
                                  <TableHead className="text-xs py-1.5 text-right">冷藏费</TableHead>
                                  <TableHead className="text-xs py-1.5 text-right">其他费用</TableHead>
                                  <TableHead className="text-xs py-1.5 text-right">清关费</TableHead>
                                </>
                              ) : (
                                <>
                                  <TableHead className="text-xs py-1.5">费用类型</TableHead>
                                  <TableHead className="text-xs py-1.5">说明</TableHead>
                                </>
                              )}
                              <TableHead className="text-xs py-1.5 text-right">金额</TableHead>
                            </TableRow>
                          </TableHeader>
                          <TableBody>
                            {(activeItem.expense_details || []).length === 0 ? (
                              <TableRow className="print-empty"><TableCell colSpan={activeItem.supplier_type === "customs_broker" ? 9 : 5} className="text-xs text-center text-muted-foreground py-2">无费用明细</TableCell></TableRow>
                            ) : (
                              (activeItem.expense_details || []).map((d: any, idx: number) => (
                                <TableRow key={idx}>
                                  <TableCell className="text-xs py-1.5">{fmtDate(d.date)}</TableCell>
                                  <TableCell className="text-xs py-1.5">{d.invoice_no || "-"}</TableCell>
                                  {activeItem.supplier_type === "customs_broker" ? (
                                    <>
                                      <TableCell className="text-xs py-1.5 text-right">{d.gross_weight_kg != null ? Number(d.gross_weight_kg).toFixed(2) : "-"}</TableCell>
                                      <TableCell className="text-xs py-1.5 text-right">{d.freight_fee != null ? fmt$(d.freight_fee) : "-"}</TableCell>
                                      <TableCell className="text-xs py-1.5 text-right">{d.inspection_fee != null ? fmt$(d.inspection_fee) : "-"}</TableCell>
                                      <TableCell className="text-xs py-1.5 text-right">{d.quarantine_fee != null ? fmt$(d.quarantine_fee) : "-"}</TableCell>
                                      <TableCell className="text-xs py-1.5 text-right">{d.other_costs != null ? fmt$(d.other_costs) : "-"}</TableCell>
                                      <TableCell className="text-xs py-1.5 text-right">{d.clearance_fee != null ? fmt$(d.clearance_fee) : "-"}</TableCell>
                                    </>
                                  ) : (
                                    <>
                                      <TableCell className="text-xs py-1.5">
                                        {d.expense_type === "import_duty" ? "进口关税" : d.expense_type === "import_vat" ? "进口增值税" : d.expense_type === "clearance_fee" ? "清关费" : d.expense_type || "-"}
                                      </TableCell>
                                      <TableCell className="text-xs py-1.5">{d.description || "-"}</TableCell>
                                    </>
                                  )}
                                  <TableCell className="text-xs py-1.5 text-right">{fmt$(d.amount)}</TableCell>
                                </TableRow>
                              ))
                            )}
                            <TableRow className="bg-muted/30 font-medium">
                              <TableCell className="text-xs py-1.5" colSpan={activeItem.supplier_type === "customs_broker" ? 8 : 4}>费用合计</TableCell>
                              <TableCell className="text-xs py-1.5 text-right">{fmt$((activeItem.expense_details || []).reduce((sum: number, d: any) => sum + (Number(d.amount) || 0), 0))}</TableCell>
                            </TableRow>
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
                            <TableRow className="bg-muted/20">
                              <TableHead className="text-xs py-1.5">日期</TableHead>
                              <TableHead className="text-xs py-1.5">付款类型</TableHead>
                              <TableHead className="text-xs py-1.5 text-right">付款金额</TableHead>
                              <TableHead className="text-xs py-1.5 ">备注</TableHead>
                            </TableRow>
                          </TableHeader>
                          <TableBody>
                            {(activeItem.payment_details || []).length === 0 ? (
                              <TableRow className="print-empty"><TableCell colSpan={4} className="text-xs text-center text-muted-foreground py-2">无付款明细</TableCell></TableRow>
                            ) : (
                              (activeItem.payment_details || []).map((d: any, idx: number) => (
                                <TableRow key={idx}>
                                  <TableCell className="text-xs py-1.5">{fmtDate(d.date)}</TableCell>
                                  <TableCell className="text-xs py-1.5">
                                    {d.payment_type === "exchange" ? "购汇付款" : d.payment_type === "clearance_payment" ? "清关费付款" : d.payment_type || "-"}
                                  </TableCell>
                                  <TableCell className="text-xs py-1.5 text-right">{fmt$(d.amount)}</TableCell>
                                  <TableCell className="text-xs py-1.5 ">{d.description || d.reference_no || "-"}</TableCell>
                                </TableRow>
                              ))
                            )}
                            <TableRow className="bg-muted/30 font-medium">
                              <TableCell className="text-xs py-1.5" colSpan={1}>付款合计</TableCell>
                              <TableCell className="text-xs py-1.5 text-right">{fmt$((activeItem.payment_details || []).reduce((sum: number, d: any) => sum + (Number(d.amount) || 0), 0))}</TableCell>
                              <TableCell className="text-xs py-1.5 "></TableCell>
                            </TableRow>
                          </TableBody>
                        </Table>
                      </div>
                    </div>
                  </div>
                ) : (
                  /* 没选供应商 → 显示供应商汇总列表 */
                  <div className="space-y-2">
                    <div className="flex items-center justify-between">
                      <span className="text-sm text-muted-foreground">
                        周期: {data?.start_date || "全部"} ~ {data?.end_date || "全部"} · 共 {data?.items?.length || 0} 位供应商
                      </span>
                      {data && (
                        <span className="text-sm font-medium text-red-600">
                          总应付: {fmt$(data.total_payable)}
                        </span>
                      )}
                    </div>
                    <div className="space-y-3">
                      {data.items.map((item: any) => (
                        <Card key={item.supplier_id} className="overflow-hidden cursor-pointer hover:bg-muted/50" onClick={() => setSelectedSupplierId(String(item.supplier_id))}>
                          <div className="px-4 py-2 bg-muted/30 border-b">
                            <div className="font-medium text-sm">{item.supplier_name} {item.supplier_code ? `(${item.supplier_code})` : ""}</div>
                          </div>
                          <div className="grid grid-cols-5 gap-4 px-4 py-3 text-sm text-center items-center">
                            <div>
                              <div className="text-xs text-muted-foreground">期初欠款</div>
                              <div className="font-medium">{fmt$(item.opening_balance)}</div>
                            </div>
                            <div>
                              <div className="text-xs text-muted-foreground">本期采购</div>
                              <div className="font-medium text-red-600">{fmt$(item.current_purchase)}</div>
                            </div>
                            <div>
                              <div className="text-xs text-muted-foreground">本期费用</div>
                              <div className="font-medium text-orange-600">{fmt$(item.current_expenses || 0)}</div>
                            </div>
                            <div>
                              <div className="text-xs text-muted-foreground">本期付款</div>
                              <div className="font-medium text-green-600">{fmt$(item.current_payments)}</div>
                            </div>
                            <div>
                              <div className="text-xs text-muted-foreground">期末欠款</div>
                              <div className={cn("font-medium", Number(item.closing_balance) > 0 ? "text-red-600" : "text-green-600")}>
                                {fmt$(item.closing_balance)}
                              </div>
                            </div>
                          </div>
                        </Card>
                      ))}
                    </div>
                  </div>
                )}
              </>
            )}
          </>
        )}
      </div>
    </>
  );
}
