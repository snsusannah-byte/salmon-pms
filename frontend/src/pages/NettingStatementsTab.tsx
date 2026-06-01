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
import { Loader2, Search, Download, Printer, X, FileText, ArrowLeftRight } from "lucide-react";

function fmt$(v: number | string | null | undefined) {
  const n = Number(v ?? 0);
  if (Number.isNaN(n)) return "¥0.00";
  return `¥${n.toLocaleString("zh-CN", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

export function NettingStatementsTab() {
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");
  const [companySearch, setCompanySearch] = useState("");
  const [selectedCompanyId, setSelectedCompanyId] = useState<string>("");
  const [doSearch, setDoSearch] = useState(false);
  const companyDropdownRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (companyDropdownRef.current && !companyDropdownRef.current.contains(event.target as Node)) {
        const target = event.target as HTMLElement;
        if (!target.closest('input[placeholder="搜索公司..."]')) {
          setCompanySearch("");
        }
      }
    };
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  const { data: companies } = useQuery({
    queryKey: ["companies-list"],
    queryFn: async () => {
      const res = await api.get("/v1/companies/?limit=500");
      return (res.data?.items || []) as { id: number; name: string; code?: string; type?: string }[];
    },
  });

  const filteredCompanies = useMemo(() => {
    if (!companies) return [];
    if (!companySearch.trim()) return companies;
    return companies.filter(c =>
      c.name.toLowerCase().includes(companySearch.toLowerCase()) ||
      (c.code || "").toLowerCase().includes(companySearch.toLowerCase())
    );
  }, [companies, companySearch]);

  const { data, isLoading } = useQuery({
    queryKey: ["reports-netting", startDate, endDate, doSearch],
    queryFn: async () => {
      const params = new URLSearchParams({ skip: "0", limit: "500" });
      if (startDate) params.set("start_date", startDate);
      if (endDate) params.set("end_date", endDate);
      const res = await api.get(`/v1/reports/netting-statements?${params}`);
      return res.data as {
        total: number;
        items: any[];
        total_net_receivable: number;
        total_net_payable: number;
        start_date: string;
        end_date: string;
      };
    },
    enabled: doSearch,
  });

  const handleSearch = () => setDoSearch(true);

  const exportCSV = () => {
    if (!data) return;
    const params = new URLSearchParams();
    if (startDate) params.set("start_date", startDate);
    if (endDate) params.set("end_date", endDate);
    if (selectedCompanyId) params.set("company_id", selectedCompanyId);
    const url = `/api/v1/reports/netting-statements/export?${params}`;
    window.open(url, "_blank");
    toast.success("正在导出...");
  };

  const periodText = `${startDate || "全部"} ~ ${endDate || "全部"}`;

  const activeItem = useMemo(() => {
    if (!data?.items?.length) return null;
    if (selectedCompanyId) {
      return data.items.find(i => String(i.company_id) === selectedCompanyId) || null;
    }
    return null;
  }, [data, selectedCompanyId]);

  return (
    <>
      <style>{`
        @media print {
          nav, aside, .sidebar, [role="navigation"] { display: none !important; }
          .print-hidden-query { display: none !important; }
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
              <ArrowLeftRight className="h-5 w-5 text-blue-500" />
              往来对账单
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
              <div className="space-y-1 relative" ref={companyDropdownRef}>
                <Label className="text-xs text-muted-foreground">公司（留空=全部）</Label>
                <div className="relative">
                  <Input
                    value={companySearch || (selectedCompanyId && companies?.find(c => String(c.id) === selectedCompanyId)?.name || "")}
                    onChange={e => { setCompanySearch(e.target.value); setSelectedCompanyId(""); }}
                    placeholder="搜索公司..."
                    className="pr-8"
                  />
                  {selectedCompanyId && (
                    <button
                      className="absolute right-2 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600"
                      onClick={() => { setSelectedCompanyId(""); setCompanySearch(""); }}
                    >
                      <X className="h-4 w-4" />
                    </button>
                  )}
                </div>
                    {companySearch && filteredCompanies.length > 0 && (
                  <div className="absolute z-50 w-full bg-white border rounded shadow-lg mt-1 max-h-48 overflow-auto">
                    {filteredCompanies.map(c => (
                      <div
                        key={c.id}
                        className="px-3 py-2 hover:bg-gray-100 cursor-pointer text-sm"
                        onClick={() => { setSelectedCompanyId(String(c.id)); setCompanySearch(c.name); }}
                      >
                        <div className="flex items-center justify-between">
                          <span>{c.name}</span>
                          <span className="text-xs text-muted-foreground">ID:{c.id}</span>
                        </div>
                        <div className="text-xs text-muted-foreground mt-0.5">
                          {c.code ? `编码:${c.code} · ` : ''}类型:{c.type || '未知'}
                        </div>
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
                不选日期则查询全部；不选公司则查询全部有交易的公司。
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
                      <h2 className="text-xl font-bold">{activeItem.company_name} 往来对账单</h2>
                      <p className="text-sm">对账周期：{periodText}</p>
                    </div>

                    {/* 屏幕汇总 */}
                    <div className="bg-muted/30 rounded-lg p-4 space-y-2 print:hidden">
                      <div className="flex items-center justify-between">
                        <div className="text-lg font-semibold">{activeItem.company_name}</div>
                        <div className="text-sm text-muted-foreground">对账周期：{periodText}</div>
                      </div>
                      <div className="grid grid-cols-3 gap-4 text-sm text-center">
                        <div className="border-r">
                          <div className="text-xs text-muted-foreground mb-1">应收端</div>
                          <div className="space-y-1">
                            <div><span className="text-xs text-muted-foreground">期初欠款</span> <span className="font-medium">{fmt$(activeItem.receivable_opening)}</span></div>
                            <div><span className="text-xs text-muted-foreground">本期销售净额</span> <span className="font-medium text-green-600">{fmt$(activeItem.receivable_current_sales)}</span></div>
                            <div><span className="text-xs text-muted-foreground">本期收款</span> <span className="font-medium text-blue-600">{fmt$(activeItem.receivable_current_receipts)}</span></div>
                            <div><span className="text-xs text-muted-foreground">期末应收</span> <span className="font-medium text-red-600">{fmt$(activeItem.receivable_closing)}</span></div>
                          </div>
                        </div>
                        <div className="border-r">
                          <div className="text-xs text-muted-foreground mb-1">应付端</div>
                          <div className="space-y-1">
                            <div><span className="text-xs text-muted-foreground">期初欠款</span> <span className="font-medium">{fmt$(activeItem.payable_opening)}</span></div>
                            <div><span className="text-xs text-muted-foreground">本期采购</span> <span className="font-medium text-orange-600">{fmt$(activeItem.payable_current_purchase)}</span></div>
                            <div><span className="text-xs text-muted-foreground">本期付款</span> <span className="font-medium text-green-600">{fmt$(activeItem.payable_current_payments)}</span></div>
                            <div><span className="text-xs text-muted-foreground">期末应付</span> <span className="font-medium text-red-600">{fmt$(activeItem.payable_closing)}</span></div>
                          </div>
                        </div>
                        <div>
                          <div className="text-xs text-muted-foreground mb-1">往来净额</div>
                          <div className="space-y-1">
                            <div><span className="text-xs text-muted-foreground">期初净额</span> <span className="font-medium">{fmt$(activeItem.netting_opening)}</span></div>
                            <div><span className="text-xs text-muted-foreground">期末净额</span> <span className={cn("font-bold text-lg", activeItem.netting_closing > 0 ? "text-red-600" : activeItem.netting_closing < 0 ? "text-green-600" : "text-gray-600")}>{fmt$(Math.abs(activeItem.netting_closing))}</span></div>
                            <div><span className="text-xs text-muted-foreground">方向</span> <span className="font-bold">{activeItem.netting_direction === "应收" ? "对方欠我" : activeItem.netting_direction === "应付" ? "我欠对方" : "平"}</span></div>
                          </div>
                        </div>
                      </div>
                    </div>

                    {/* 应收明细 */}
                    {activeItem.sale_details?.length > 0 && (
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
                              </TableRow>
                            </TableHeader>
                            <TableBody>
                              {activeItem.sale_details.map((d: any, idx: number) => (
                                <TableRow key={idx}>
                                  <TableCell className="text-xs py-1.5">{d.date}</TableCell>
                                  <TableCell className="text-xs py-1.5">{d.sale_no}</TableCell>
                                  <TableCell className="text-xs py-1.5">{d.spec || "-"}</TableCell>
                                  <TableCell className="text-xs py-1.5 text-right">{d.quantity != null ? d.quantity : "-"}</TableCell>
                                  <TableCell className="text-xs py-1.5 text-right">{d.weight_kg ? Number(d.weight_kg).toFixed(2) : "-"}</TableCell>
                                  <TableCell className="text-xs py-1.5 text-right">{d.unit_price ? fmt$(d.unit_price) : "-"}</TableCell>
                                  <TableCell className="text-xs py-1.5 text-right">{fmt$(d.gross_amount)}</TableCell>
                                </TableRow>
                              ))}
                            </TableBody>
                          </Table>
                        </div>
                      </div>
                    )}

                    {/* 应付明细 */}
                    {activeItem.purchase_details?.length > 0 && (
                      <div className="space-y-1">
                        <h4 className="text-sm font-medium">采购明细</h4>
                        <div className="border rounded-md">
                          <Table>
                            <TableHeader>
                              <TableRow className="bg-muted/20">
                                <TableHead className="text-xs py-1.5">日期</TableHead>
                                <TableHead className="text-xs py-1.5">单号</TableHead>
                                <TableHead className="text-xs py-1.5 text-right">金额(USD)</TableHead>
                                <TableHead className="text-xs py-1.5 text-right">汇率</TableHead>
                                <TableHead className="text-xs py-1.5 text-right">金额(CNY)</TableHead>
                              </TableRow>
                            </TableHeader>
                            <TableBody>
                              {activeItem.purchase_details.map((d: any, idx: number) => (
                                <TableRow key={idx}>
                                  <TableCell className="text-xs py-1.5">{d.date}</TableCell>
                                  <TableCell className="text-xs py-1.5">{d.invoice_no || "-"}</TableCell>
                                  <TableCell className="text-xs py-1.5 text-right">{d.amount_usd ? `$${Number(d.amount_usd).toFixed(2)}` : "-"}</TableCell>
                                  <TableCell className="text-xs py-1.5 text-right">{d.exchange_rate || "-"}</TableCell>
                                  <TableCell className="text-xs py-1.5 text-right">{fmt$(d.amount_cny)}</TableCell>
                                </TableRow>
                              ))}
                            </TableBody>
                          </Table>
                        </div>
                      </div>
                    )}

                    {/* 付款明细 */}
                    {activeItem.payment_details?.length > 0 && (
                      <div className="space-y-1">
                        <h4 className="text-sm font-medium">付款明细</h4>
                        <div className="border rounded-md">
                          <Table>
                            <TableHeader>
                              <TableRow className="bg-muted/20">
                                <TableHead className="text-xs py-1.5">日期</TableHead>
                                <TableHead className="text-xs py-1.5">付款类型</TableHead>
                                <TableHead className="text-xs py-1.5 text-right">付款金额</TableHead>
                                <TableHead className="text-xs py-1.5">备注</TableHead>
                              </TableRow>
                            </TableHeader>
                            <TableBody>
                              {activeItem.payment_details.map((d: any, idx: number) => (
                                <TableRow key={idx}>
                                  <TableCell className="text-xs py-1.5">{d.date}</TableCell>
                                  <TableCell className="text-xs py-1.5">{d.payment_type || "-"}</TableCell>
                                  <TableCell className="text-xs py-1.5 text-right">{fmt$(d.amount)}</TableCell>
                                  <TableCell className="text-xs py-1.5">{d.reference_no || "-"}</TableCell>
                                </TableRow>
                              ))}
                            </TableBody>
                          </Table>
                        </div>
                      </div>
                    )}
                  </div>
                ) : (
                  /* 没选公司 → 显示公司汇总列表 */
                  <div className="space-y-2">
                    <div className="flex items-center justify-between">
                      <span className="text-sm text-muted-foreground">
                        周期: {data?.start_date || "全部"} ~ {data?.end_date || "全部"} · 共 {data?.items?.length || 0} 家公司
                      </span>
                      <div className="flex gap-4 text-sm">
                        <span className="font-medium text-red-600">总净应收: {fmt$(data?.total_net_receivable)}</span>
                        <span className="font-medium text-green-600">总净应付: {fmt$(data?.total_net_payable)}</span>
                      </div>
                    </div>
                    <div className="space-y-3">
                      {data.items.map((item: any) => (
                        <Card key={item.company_id} className="overflow-hidden cursor-pointer hover:bg-muted/50" onClick={() => setSelectedCompanyId(String(item.company_id))}>
                          <div className="px-4 py-2 bg-muted/30 border-b flex items-center justify-between">
                            <div className="font-medium text-sm">{item.company_name} {item.company_code ? `(${item.company_code})` : ""}</div>
                            <div className="text-xs">
                              {item.company_type === "both" && (
                                <span className="bg-blue-100 text-blue-700 px-2 py-0.5 rounded">既是客户又是供应商</span>
                              )}
                              {item.company_type === "customer" && (
                                <span className="bg-green-100 text-green-700 px-2 py-0.5 rounded">仅客户</span>
                              )}
                              {item.company_type === "supplier" && (
                                <span className="bg-orange-100 text-orange-700 px-2 py-0.5 rounded">仅供应商</span>
                              )}
                            </div>
                          </div>
                          <div className="grid grid-cols-6 gap-4 px-4 py-3 text-sm text-center items-center">
                            <div>
                              <div className="text-xs text-muted-foreground">期初应收</div>
                              <div className="font-medium">{fmt$(item.receivable_opening)}</div>
                            </div>
                            <div>
                              <div className="text-xs text-muted-foreground">期末应收</div>
                              <div className="font-medium text-red-600">{fmt$(item.receivable_closing)}</div>
                            </div>
                            <div>
                              <div className="text-xs text-muted-foreground">期初应付</div>
                              <div className="font-medium">{fmt$(item.payable_opening)}</div>
                            </div>
                            <div>
                              <div className="text-xs text-muted-foreground">期末应付</div>
                              <div className="font-medium text-orange-600">{fmt$(item.payable_closing)}</div>
                            </div>
                            <div>
                              <div className="text-xs text-muted-foreground">往来净额</div>
                              <div className={cn("font-bold", item.netting_closing > 0 ? "text-red-600" : item.netting_closing < 0 ? "text-green-600" : "text-gray-600")}>
                                {fmt$(Math.abs(item.netting_closing))}
                              </div>
                            </div>
                            <div>
                              <div className="text-xs text-muted-foreground">方向</div>
                              <div className={cn("font-medium", item.netting_direction === "应收" ? "text-red-600" : item.netting_direction === "应付" ? "text-green-600" : "text-gray-600")}>
                                {item.netting_direction === "应收" ? "对方欠我" : item.netting_direction === "应付" ? "我欠对方" : "平"}
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
