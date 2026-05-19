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
import { Loader2, Eye, ChevronLeft, ChevronRight, Search, Download, Printer, X } from "lucide-react";

function fmt$(v: number | string | null | undefined) {
  const n = Number(v ?? 0);
  if (Number.isNaN(n)) return "¥0.00";
  return `¥${n.toLocaleString("zh-CN", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

function fmtDate(d: string | null | undefined) {
  if (!d) return "-";
  return new Date(d).toLocaleDateString("zh-CN");
}

// ==================== Tab 3: 应收对账单 (Inline 展示模式) ====================

export function ReceivableStatementsTab() {
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");
  const [customerSearch, setCustomerSearch] = useState("");
  const [selectedCustomerId, setSelectedCustomerId] = useState<string>("");
  const [doSearch, setDoSearch] = useState(false);
  const customerDropdownRef = useRef<HTMLDivElement>(null);

  // 点击外部关闭客户下拉框
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (customerDropdownRef.current && !customerDropdownRef.current.contains(event.target as Node)) {
        const target = event.target as HTMLElement;
        if (!target.closest('input[placeholder="搜索客户..."]')) {
          setCustomerSearch("");
        }
      }
    };
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  // 客户列表
  const { data: customers } = useQuery({
    queryKey: ["customers-list"],
    queryFn: async () => {
      const res = await api.get("/v1/companies/?limit=500");
      return (res.data?.items || []) as { id: number; name: string; code?: string }[];
    },
  });

  const filteredCustomers = useMemo(() => {
    if (!customers) return [];
    if (!customerSearch.trim()) return customers;
    return customers.filter(c =>
      c.name.toLowerCase().includes(customerSearch.toLowerCase()) ||
      (c.code || "").toLowerCase().includes(customerSearch.toLowerCase())
    );
  }, [customers, customerSearch]);

  const { data, isLoading } = useQuery({
    queryKey: ["reports-receivable", startDate, endDate, doSearch],
    queryFn: async () => {
      const params = new URLSearchParams({ skip: "0", limit: "500" });
      if (startDate) params.set("start_date", startDate);
      if (endDate) params.set("end_date", endDate);
      const res = await api.get(`/v1/reports/receivable-statements?${params}`);
      return res.data as {
        total: number;
        items: any[];
        total_receivable: number;
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
    if (selectedCustomerId) params.set("customer_id", selectedCustomerId);
    const url = `/api/v1/reports/receivable-statements/export?${params}`;
    window.open(url, "_blank");
    toast.success("正在导出...");
  };

  const periodText = `${startDate || "全部"} ~ ${endDate || "全部"}`;

  const activeItem = useMemo(() => {
    if (!data?.items?.length) return null;
    if (selectedCustomerId) {
      return data.items.find(i => String(i.customer_id) === selectedCustomerId) || null;
    }
    return null;
  }, [data, selectedCustomerId]);

  return (
    <>
      <style>{`
        @media print {
          nav, aside, .sidebar, [role="navigation"] { display: none !important; }
          body { -webkit-print-color-adjust: exact; print-color-adjust: exact; }
          .print-content { width: 100% !important; margin: 0 !important; padding: 0 !important; }
          .print-content table { font-size: 9px; width: 100%; border-collapse: collapse; }
          .print-content th, .print-content td { padding: 1px 3px !important; border: 1px solid #ccc !important; }
          .print-content h4 { font-size: 10px; margin: 4px 0 2px 0; }
          .print-empty { display: none !important; }
          .print-hide-note { display: none !important; }
          .print-content .grid { gap: 2px !important; }
          .print-content .rounded-lg { border: 1px solid #ccc !important; padding: 4px !important; }
        }
      `}</style>
      <div className="space-y-4">
        {/* 查询条件 */}
        <Card className="print-hidden-query">
          <CardHeader className="pb-3">
            <CardTitle className="text-base flex items-center gap-2">
              <FileText className="h-5 w-5 text-blue-500" />
              应收对账单
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
              <div className="space-y-1 relative" ref={customerDropdownRef}>
                <Label className="text-xs text-muted-foreground">客户（留空=全部）</Label>
                <div className="relative">
                  <Input
                    value={customerSearch || (selectedCustomerId && customers?.find(c => String(c.id) === selectedCustomerId)?.name || "")}
                    onChange={e => { setCustomerSearch(e.target.value); setSelectedCustomerId(""); }}
                    placeholder="搜索客户..."
                    className="pr-8"
                  />
                  {selectedCustomerId && (
                    <button
                      className="absolute right-2 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600"
                      onClick={() => { setSelectedCustomerId(""); setCustomerSearch(""); }}
                    >
                      <X className="h-4 w-4" />
                    </button>
                  )}
                </div>
                {customerSearch && filteredCustomers.length > 0 && (
                  <div className="absolute z-50 w-full bg-white border rounded shadow-lg mt-1 max-h-48 overflow-auto">
                    {filteredCustomers.map(c => (
                      <div
                        key={c.id}
                        className="px-3 py-2 hover:bg-gray-100 cursor-pointer text-sm"
                        onClick={() => { setSelectedCustomerId(String(c.id)); setCustomerSearch(c.name); }}
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
                不选日期则查询全部；不选客户则查询全部客户。
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
                      <h2 className="text-xl font-bold">{activeItem.customer_name}对账单</h2>
                      <p className="text-sm">对账周期：{periodText}</p>
                    </div>

                    {/* 屏幕汇总 */}
                    <div className="bg-muted/30 rounded-lg p-4 space-y-2 print:hidden">
                      <div className="flex items-center justify-between">
                        <div className="text-lg font-semibold">{activeItem.customer_name}</div>
                        <div className="text-sm text-muted-foreground">对账周期：{periodText}</div>
                      </div>
                      <div className="grid grid-cols-5 gap-4 text-sm text-center">
                        <div>
                          <div className="text-xs text-muted-foreground">期初欠款</div>
                          <div className="font-medium">{fmt$(activeItem.opening_balance)}</div>
                        </div>
                        <div>
                          <div className="text-xs text-muted-foreground">本期销售</div>
                          <div className="font-medium text-green-600">{fmt$(activeItem.current_sales)}</div>
                        </div>
                        <div>
                          <div className="text-xs text-muted-foreground">本期净额</div>
                          <div className="font-medium">{fmt$(activeItem.current_net_sales || 0)}</div>
                        </div>
                        <div>
                          <div className="text-xs text-muted-foreground">本期收支</div>
                          <div className="font-medium text-blue-600">{fmt$(activeItem.current_receipts)}</div>
                        </div>
                        <div>
                          <div className="text-xs text-muted-foreground">期末欠款</div>
                          <div className={cn("font-medium", Number(activeItem.closing_balance) > 0 ? "text-red-600" : "text-green-600")}>
                            {fmt$(activeItem.closing_balance)}
                          </div>
                        </div>
                      </div>
                    </div>

                    {/* 打印汇总 */}
                    <div className="hidden print:block border-t border-b border-gray-300 py-2 mb-4">
                      <div className="grid grid-cols-5 gap-2 text-center text-sm">
                        <div><div className="text-xs text-gray-600">期初欠款</div><div className="font-medium">{fmt$(activeItem.opening_balance)}</div></div>
                        <div><div className="text-xs text-gray-600">本期销售</div><div className="font-medium">{fmt$(activeItem.current_sales)}</div></div>
                        <div><div className="text-xs text-gray-600">本期净额</div><div className="font-medium">{fmt$(activeItem.current_net_sales || 0)}</div></div>
                        <div><div className="text-xs text-gray-600">本期收支</div><div className="font-medium">{fmt$(activeItem.current_receipts)}</div></div>
                        <div><div className="text-xs text-gray-600">期末欠款</div><div className="font-medium">{fmt$(activeItem.closing_balance)}</div></div>
                      </div>
                    </div>

                    {/* 销售明细 */}
                    <div className="space-y-1">
                      <h4 className="text-sm font-medium">销售明细</h4>
                      <div className="border rounded-md">
                        <Table>
                          <TableHeader>
                            <TableRow className="bg-muted/20">
                              <TableHead className="text-xs py-1.5">日期</TableHead>
                              <TableHead className="text-xs py-1.5">销售单号</TableHead>
                              <TableHead className="text-xs py-1.5">规格</TableHead>
                              <TableHead className="text-xs py-1.5 text-right">数量</TableHead>
                              <TableHead className="text-xs py-1.5 text-right">重量(kg)</TableHead>
                              <TableHead className="text-xs py-1.5 text-right">单价</TableHead>
                              <TableHead className="text-xs py-1.5 text-right">金额</TableHead>
                              <TableHead className="text-xs py-1.5 text-right">净额</TableHead>
                            </TableRow>
                          </TableHeader>
                          <TableBody>
                            {(activeItem.sale_details || []).length === 0 ? (
                              <TableRow className="print-empty">
                                <TableCell colSpan={8} className="text-xs text-center text-muted-foreground py-2">无销售明细</TableCell>
                              </TableRow>
                            ) : (
                              (activeItem.sale_details || []).map((d: any, idx: number) => (
                                <TableRow key={idx}>
                                  <TableCell className="text-xs py-1.5">{fmtDate(d.date)}</TableCell>
                                  <TableCell className="text-xs py-1.5">{d.sale_no}</TableCell>
                                  <TableCell className="text-xs py-1.5">{d.spec || "-"}</TableCell>
                                  <TableCell className="text-xs py-1.5 text-right">{d.quantity != null ? d.quantity : "-"}</TableCell>
                                  <TableCell className="text-xs py-1.5 text-right">{d.weight_kg ? Number(d.weight_kg).toFixed(2) : "-"}</TableCell>
                                  <TableCell className="text-xs py-1.5 text-right">{d.unit_price ? fmt$(d.unit_price) : "-"}</TableCell>
                                  <TableCell className="text-xs py-1.5 text-right">{fmt$(d.gross_amount)}</TableCell>
                                  <TableCell className="text-xs py-1.5 text-right">{fmt$(d.net_amount)}</TableCell>
                                </TableRow>
                              ))
                            )}
                            <TableRow className="bg-muted/30 font-medium">
                              <TableCell className="text-xs py-1.5" colSpan={3}>销售合计</TableCell>
                              <TableCell className="text-xs py-1.5 text-right">{(activeItem.sale_details || []).reduce((sum: number, d: any) => sum + (Number(d.quantity) || 0), 0)}</TableCell>
                              <TableCell className="text-xs py-1.5 text-right">{(activeItem.sale_details || []).reduce((sum: number, d: any) => sum + (Number(d.weight_kg) || 0), 0).toFixed(2)}</TableCell>
                              <TableCell className="text-xs py-1.5"></TableCell>
                              <TableCell className="text-xs py-1.5 text-right">{fmt$((activeItem.sale_details || []).reduce((sum: number, d: any) => sum + (Number(d.gross_amount) || 0), 0))}</TableCell>
                              <TableCell className="text-xs py-1.5 text-right">{fmt$((activeItem.sale_details || []).reduce((sum: number, d: any) => sum + (Number(d.net_amount) || 0), 0))}</TableCell>
                            </TableRow>
                          </TableBody>
                        </Table>
                      </div>
                    </div>

                    {/* 折扣明细 */}
                    <div className="space-y-1">
                      <h4 className="text-sm font-medium">折扣明细</h4>
                      <div className="border rounded-md">
                        <Table>
                          <TableHeader>
                            <TableRow className="bg-muted/20">
                              <TableHead className="text-xs py-1.5">日期</TableHead>
                              <TableHead className="text-xs py-1.5">销售单号</TableHead>
                              <TableHead className="text-xs py-1.5 text-right">折扣金额</TableHead>
                              <TableHead className="text-xs py-1.5">原因</TableHead>
                            </TableRow>
                          </TableHeader>
                          <TableBody>
                            {(activeItem.discount_details || []).length === 0 ? (
                              <TableRow className="print-empty">
                                <TableCell colSpan={4} className="text-xs text-center text-muted-foreground py-2">无折扣明细</TableCell>
                              </TableRow>
                            ) : (
                              (activeItem.discount_details || []).map((d: any, idx: number) => (
                                <TableRow key={idx}>
                                  <TableCell className="text-xs py-1.5">{fmtDate(d.date)}</TableCell>
                                  <TableCell className="text-xs py-1.5">{d.sale_no}</TableCell>
                                  <TableCell className="text-xs py-1.5 text-right">{fmt$(d.discount_amount)}</TableCell>
                                  <TableCell className="text-xs py-1.5">{d.reason || "-"}</TableCell>
                                </TableRow>
                              ))
                            )}
                            <TableRow className="bg-muted/30 font-medium">
                              <TableCell className="text-xs py-1.5" colSpan={2}>折扣合计</TableCell>
                              <TableCell className="text-xs py-1.5 text-right">{fmt$((activeItem.discount_details || []).reduce((sum: number, d: any) => sum + (Number(d.discount_amount) || 0), 0))}</TableCell>
                              <TableCell className="text-xs py-1.5"></TableCell>
                            </TableRow>
                          </TableBody>
                        </Table>
                      </div>
                    </div>

                    {/* 售后明细 */}
                    <div className="space-y-1">
                      <h4 className="text-sm font-medium">售后明细</h4>
                      <div className="border rounded-md">
                        <Table>
                          <TableHeader>
                            <TableRow className="bg-muted/20">
                              <TableHead className="text-xs py-1.5">日期</TableHead>
                              <TableHead className="text-xs py-1.5">销售单号</TableHead>
                              <TableHead className="text-xs py-1.5">退货单号</TableHead>
                              <TableHead className="text-xs py-1.5 text-right">重量</TableHead>
                              <TableHead className="text-xs py-1.5 text-right">单价</TableHead>
                              <TableHead className="text-xs py-1.5 text-right">金额</TableHead>
                              <TableHead className="text-xs py-1.5">原因</TableHead>
                              <TableHead className="text-xs py-1.5">退款方式</TableHead>
                            </TableRow>
                          </TableHeader>
                          <TableBody>
                            {(activeItem.aftersales_details || []).length === 0 ? (
                              <TableRow className="print-empty">
                                <TableCell colSpan={8} className="text-xs text-center text-muted-foreground py-2">无售后明细</TableCell>
                              </TableRow>
                            ) : (
                              (activeItem.aftersales_details || []).map((d: any, idx: number) => (
                                <TableRow key={idx}>
                                  <TableCell className="text-xs py-1.5">{fmtDate(d.date)}</TableCell>
                                  <TableCell className="text-xs py-1.5">{d.sale_no || "-"}</TableCell>
                                  <TableCell className="text-xs py-1.5">{d.return_no || "-"}</TableCell>
                                  <TableCell className="text-xs py-1.5 text-right">{d.quantity != null ? `${d.quantity} kg` : "-"}</TableCell>
                                  <TableCell className="text-xs py-1.5 text-right">{d.unit_price != null ? `¥${Number(d.unit_price).toFixed(2)}` : "-"}</TableCell>
                                  <TableCell className="text-xs py-1.5 text-right">{fmt$(d.amount)}</TableCell>
                                  <TableCell className="text-xs py-1.5">{d.reason || "-"}</TableCell>
                                  <TableCell className="text-xs py-1.5">
                                    {d.refund_method === 'direct_refund' ? '直接退款' :
                                     d.refund_method === 'balance_deduction' ? '抵扣货款' :
                                     d.refund_method === 'prepayment' ? '转为预付款' :
                                     d.refund_method === 'deferred' ? '挂账/延期' :
                                     d.refund_method || '-'}
                                  </TableCell>
                                </TableRow>
                              ))
                            )}
                            <TableRow className="bg-muted/30 font-medium">
                              <TableCell className="text-xs py-1.5" colSpan={3}>售后合计</TableCell>
                              <TableCell className="text-xs py-1.5 text-right">{(activeItem.aftersales_details || []).reduce((sum: number, d: any) => sum + (Number(d.quantity) || 0), 0).toFixed(2)} kg</TableCell>
                              <TableCell className="text-xs py-1.5"></TableCell>
                              <TableCell className="text-xs py-1.5 text-right">{fmt$((activeItem.aftersales_details || []).reduce((sum: number, d: any) => sum + (Number(d.amount) || 0), 0))}</TableCell>
                              <TableCell className="text-xs py-1.5"></TableCell>
                              <TableCell className="text-xs py-1.5"></TableCell>
                            </TableRow>
                          </TableBody>
                        </Table>
                      </div>
                    </div>

                    {/* 收支明细 */}
                    <div className="space-y-1">
                      <h4 className="text-sm font-medium">收支明细</h4>
                      <div className="border rounded-md">
                        <Table>
                          <TableHeader>
                            <TableRow className="bg-muted/20">
                              <TableHead className="text-xs py-1.5">日期</TableHead>
                              <TableHead className="text-xs py-1.5 text-right">金额</TableHead>
                              <TableHead className="text-xs py-1.5">类型</TableHead>
                              <TableHead className="text-xs py-1.5 print-hide-note">备注</TableHead>
                            </TableRow>
                          </TableHeader>
                          <TableBody>
                            {(activeItem.receipt_details || []).length === 0 ? (
                              <TableRow className="print-empty">
                                <TableCell colSpan={4} className="text-xs text-center text-muted-foreground py-2">无收支明细</TableCell>
                              </TableRow>
                            ) : (
                              (activeItem.receipt_details || []).map((d: any, idx: number) => (
                                <TableRow key={idx}>
                                  <TableCell className="text-xs py-1.5">{fmtDate(d.date)}</TableCell>
                                  <TableCell className={cn("text-xs py-1.5 text-right", Number(d.amount) < 0 ? "text-red-600" : "")}>
                                    {Number(d.amount) < 0 ? `-${fmt$(Math.abs(Number(d.amount)))}` : fmt$(d.amount)}
                                  </TableCell>
                                  <TableCell className="text-xs py-1.5">
                                    {d.payment_method === 'bank_transfer' ? '银行转账' :
                                     d.payment_method === 'transfer' ? '银行转账' :
                                     d.payment_method === 'prepayment' ? '客户预付款' :
                                     d.payment_method === 'sales_refund' ? '售后退款' :
                                     d.payment_method === 'balance' ? '余额抵扣' :
                                     d.payment_method === 'cash' ? '现金' :
                                     d.payment_method === 'wechat_pay' ? '微信支付' :
                                     d.payment_method === 'alipay' ? '支付宝' :
                                     d.payment_method === 'check' ? '支票' :
                                     d.payment_method === 'card' ? '刷卡' :
                                     d.payment_method || '-'}
                                  </TableCell>
                                  <TableCell className="text-xs py-1.5 print-hide-note">{d.reference_no || "-"}</TableCell>
                                </TableRow>
                              ))
                            )}
                            <TableRow className="bg-muted/30 font-medium">
                              <TableCell className="text-xs py-1.5" colSpan={1}>收支合计</TableCell>
                              <TableCell className="text-xs py-1.5 text-right">{fmt$((activeItem.receipt_details || []).reduce((sum: number, d: any) => sum + (Number(d.amount) || 0), 0))}</TableCell>
                              <TableCell className="text-xs py-1.5"></TableCell>
                              <TableCell className="text-xs py-1.5 print-hide-note"></TableCell>
                            </TableRow>
                          </TableBody>
                        </Table>
                      </div>
                    </div>
                  </div>
                ) : (
                  /* 没选客户 → 显示客户汇总列表 */
                  <div className="space-y-2">
                    <div className="flex items-center justify-between">
                      <span className="text-sm text-muted-foreground">
                        周期: {data?.start_date || "全部"} ~ {data?.end_date || "全部"} · 共 {data?.items?.length || 0} 位客户
                      </span>
                      {data && (
                        <span className="text-sm font-medium text-red-600">
                          总应收: {fmt$(data.total_receivable)}
                        </span>
                      )}
                    </div>
                    <div className="space-y-3">
                      {data.items.map((item: any) => (
                        <Card key={item.customer_id} className="overflow-hidden cursor-pointer hover:bg-muted/50" onClick={() => setSelectedCustomerId(String(item.customer_id))}>
                          <div className="px-4 py-2 bg-muted/30 border-b">
                            <div className="font-medium text-sm">{item.customer_name} {item.customer_code ? `(${item.customer_code})` : ""}</div>
                          </div>
                          <div className="grid grid-cols-5 gap-4 px-4 py-3 text-sm text-center items-center">
                            <div>
                              <div className="text-xs text-muted-foreground">期初欠款</div>
                              <div className="font-medium">{fmt$(item.opening_balance)}</div>
                            </div>
                            <div>
                              <div className="text-xs text-muted-foreground">本期销售</div>
                              <div className="font-medium text-green-600">{fmt$(item.current_sales)}</div>
                            </div>
                            <div>
                              <div className="text-xs text-muted-foreground">本期净额</div>
                              <div className="font-medium">{fmt$(item.current_net_sales || 0)}</div>
                            </div>
                            <div>
                              <div className="text-xs text-muted-foreground">本期收支</div>
                              <div className="font-medium text-blue-600">{fmt$(item.current_receipts)}</div>
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
