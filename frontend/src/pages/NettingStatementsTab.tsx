import { useState, useMemo, useRef, useEffect } from "react";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter } from "@/components/ui/dialog";
import { toast } from "sonner";
import { Loader2, Search, Download, Printer, X, ChevronDown, ChevronUp, ArrowLeftRight, Landmark, FileSpreadsheet, Receipt } from "lucide-react";

function fmt$(v: number | string | null | undefined) {
  const n = Number(v ?? 0);
  if (Number.isNaN(n)) return "¥0.00";
  return `¥${n.toLocaleString("zh-CN", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

function fmtDate(d: string | null | undefined) {
  if (!d) return "-";
  return new Date(d).toLocaleDateString("zh-CN");
}

function paymentDescLabel(desc: string | null | undefined) {
  const map: Record<string, string> = {
    main_business_income: "主营业务收入",
    main_business_revenue: "主营业务收入",
    netting_settlement: "对冲结算",
    customer_deposit: "客户预付款",
    goods_payment: "采购付款",
    other_income: "其他收入",
    other_expense: "其他支出",
    scan_fee: "扫码费",
    import_payment: "进口付款",
    sales_refund: "销售退款",
    balance_deduction: "余额抵扣",
  };
  return map[desc || ""] || desc || "-";
}

// 数字金额转人民币大写
function numberToChinese(n: number | string | null | undefined) {
  const num = Math.abs(Number(n ?? 0));
  const cnNums = ["零", "壹", "贰", "叁", "肆", "伍", "陆", "柒", "捌", "玖"];
  const cnIntUnits = ["", "拾", "佰", "仟"];
  const cnBigUnits = ["", "万", "亿", "兆"];

  if (num === 0) return "零元整";

  const integer = Math.floor(num);
  const decimal = Math.round((num - integer) * 100);

  let intStr = "";
  let zero = false;
  let unitPos = 0;
  let g = integer;
  while (g > 0) {
    const p = g % 10;
    const c = p === 0 && !zero ? "零" : cnNums[p] + (p === 0 ? "" : cnIntUnits[unitPos % 4]);
    intStr = c + intStr;
    if (p === 0) zero = true; else zero = false;
    g = Math.floor(g / 10);
    unitPos++;
    if (unitPos % 4 === 0 && g > 0) intStr = cnBigUnits[unitPos / 4] + intStr;
  }

  intStr = intStr.replace(/零+/g, "零").replace(/^零|零$/g, "");
  if (!intStr) intStr = "零";
  intStr += "元";

  let decStr = "";
  if (decimal > 0) {
    const jiao = Math.floor(decimal / 10);
    const fen = decimal % 10;
    if (jiao > 0) decStr += cnNums[jiao] + "角";
    if (fen > 0) decStr += cnNums[fen] + "分";
  } else {
    decStr += "整";
  }

  return intStr + decStr;
}

export function NettingStatementsTab() {
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");
  const [companySearch, setCompanySearch] = useState("");
  const [selectedCompanyId, setSelectedCompanyId] = useState<string>("");
  const [doSearch, setDoSearch] = useState(false);
  const companyDropdownRef = useRef<HTMLDivElement>(null);

  // 对冲结算弹窗状态
  const [isNettingOpen, setIsNettingOpen] = useState(false);
  const [selectedSaleIds, setSelectedSaleIds] = useState<number[]>([]);
  const [selectedPurchaseIds, setSelectedPurchaseIds] = useState<number[]>([]);
  const [selectedInboundIds, setSelectedInboundIds] = useState<number[]>([]);
  const [selectedBankAccountId, setSelectedBankAccountId] = useState<string>("");
  const [nettingSubmitting, setNettingSubmitting] = useState(false);

  // 明细折叠状态
  const [showSaleDetails, setShowSaleDetails] = useState(false);
  const [showDiscountDetails, setShowDiscountDetails] = useState(false);
  const [showAftersalesDetails, setShowAftersalesDetails] = useState(false);
  const [showPurchaseDetails, setShowPurchaseDetails] = useState(false);
  const [showPurchaseReturnDetails, setShowPurchaseReturnDetails] = useState(false);

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

  const { data: bankAccounts } = useQuery({
    queryKey: ["bank-accounts-list"],
    queryFn: async () => {
      const res = await api.get("/v1/finance/bank-accounts?limit=100");
      return (res.data?.items || []) as { id: number; account_name: string; bank_name?: string; account_no?: string }[];
    },
    enabled: isNettingOpen,
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

  const handleNettingSubmit = async () => {
    if (!selectedCompanyId || nettingPreview.nettingAmount <= 0) return;
    setNettingSubmitting(true);
    try {
      const companyName = companies?.find(c => String(c.id) === selectedCompanyId)?.name || "";
      const payload: any = {
        transaction_date: new Date().toISOString().split("T")[0],
        type: "income",
        category: "netting_settlement",
        amount: Number(nettingPreview.nettingAmount.toFixed(2)),
        currency: "CNY",
        counterparty_id: Number(selectedCompanyId),
        counterparty: companyName,
        related_sale_ids: selectedSaleIds,
        related_purchase_ids: selectedPurchaseIds,
        related_purchase_inbound_ids: selectedInboundIds,
        description: `对冲结算：${nettingPreview.saleCount}个销售单 + ${nettingPreview.purchaseCount}个采购单`,
      };
      if (selectedBankAccountId) {
        payload.to_account_id = Number(selectedBankAccountId);
      }
      const res = await api.post("/v1/finance/transactions", payload);
      toast.success("对冲结算已生成");
      setIsNettingOpen(false);
      setSelectedSaleIds([]);
      setSelectedPurchaseIds([]);
      setSelectedInboundIds([]);
      setSelectedBankAccountId("");
      // 刷新数据
      setDoSearch(true);
    } catch (err: any) {
      toast.error(err.response?.data?.detail || "生成失败");
    } finally {
      setNettingSubmitting(false);
    }
  };

  const activeItem = useMemo(() => {
    if (!data?.items?.length) return null;
    if (selectedCompanyId) {
      return data.items.find(i => String(i.company_id) === selectedCompanyId) || null;
    }
    return null;
  }, [data, selectedCompanyId]);

  // 查询未结清销售单（进口整鱼 + 成品/以销定采）
  const { data: unsettledSales } = useQuery({
    queryKey: ["netting-unsettled-sales", selectedCompanyId],
    queryFn: async () => {
      if (!selectedCompanyId) return [];
      const cid = Number(selectedCompanyId);
      // 1. 进口整鱼销售
      const wfRes = await api.get(`/v1/sales/whole-fish?customer_id=${cid}&limit=500`);
      const wfItems = (wfRes.data?.items || []).filter((s: any) => (s.net_amount || s.total_amount || 0) - (s.paid_amount || 0) > 0.01);
      // 2. 成品/以销定采销售
      const fpRes = await api.get(`/v1/finished-product-sales?customer_id=${cid}&limit=500`);
      const fpItems = (fpRes.data?.items || []).filter((s: any) => (s.net_amount || s.total_amount || 0) - (s.paid_amount || 0) > 0.01);
      // 合并并标记类型
      return [
        ...wfItems.map((s: any) => ({ ...s, _type: "whole_fish", _remaining: (s.net_amount || s.total_amount || 0) - (s.paid_amount || 0) })),
        ...fpItems.map((s: any) => ({ ...s, _type: "finished_product", _remaining: (s.net_amount || s.total_amount || 0) - (s.paid_amount || 0) })),
      ];
    },
    enabled: isNettingOpen && !!selectedCompanyId,
  });

  // 查询未结清采购单（辅料采购 + 采购入库）
  const { data: unsettledPurchases } = useQuery({
    queryKey: ["netting-unsettled-purchases", selectedCompanyId],
    queryFn: async () => {
      if (!selectedCompanyId) return [];
      const cid = Number(selectedCompanyId);
      const [matRes, inboundRes] = await Promise.all([
        api.get(`/v1/material-purchases?supplier_id=${cid}&limit=500`),
        api.get(`/v1/import-inbound?supplier_id=${cid}&limit=500`),
      ]);
      const matItems = (matRes.data?.items || [])
        .filter((p: any) => (p.actual_total || p.total_amount || 0) - (p.paid_amount || 0) > 0.01)
        .map((p: any) => ({
          ...p,
          _source: "material" as const,
          _remaining: (p.actual_total || p.total_amount || 0) - (p.paid_amount || 0),
        }));
      const inboundItems = (inboundRes.data?.items || [])
        .filter((p: any) => {
          const net = (p.total_amount || 0) - (p.after_sales_adjustment || 0);
          return net - (p.paid_amount || 0) > 0.01;
        })
        .map((p: any) => ({
          ...p,
          _source: "inbound" as const,
          _remaining: (p.total_amount || 0) - (p.after_sales_adjustment || 0) - (p.paid_amount || 0),
        }));
      return [...matItems, ...inboundItems];
    },
    enabled: isNettingOpen && !!selectedCompanyId,
  });

  // 预览计算（差额模式：销售待收 - 采购待付）
  const nettingPreview = useMemo(() => {
    const selectedSales = (unsettledSales || []).filter((s: any) => selectedSaleIds.includes(s.id));
    const selectedMatPurchases = (unsettledPurchases || [])
      .filter((p: any) => p._source === "material" && selectedPurchaseIds.includes(p.id));
    const selectedInboundPurchases = (unsettledPurchases || [])
      .filter((p: any) => p._source === "inbound" && selectedInboundIds.includes(p.id));
    const saleTotal = selectedSales.reduce((sum: number, s: any) => sum + (s._remaining || 0), 0);
    const matTotal = selectedMatPurchases.reduce((sum: number, p: any) => sum + (p._remaining || 0), 0);
    const inboundTotal = selectedInboundPurchases.reduce((sum: number, p: any) => sum + (p._remaining || 0), 0);
    const purchaseTotal = matTotal + inboundTotal;
    // 差额模式：对冲金额 = 销售待收 - 采购待付（客户还需付的差额）
    const nettingAmount = Math.max(0, saleTotal - purchaseTotal);
    return {
      saleTotal, purchaseTotal, nettingAmount,
      saleCount: selectedSales.length,
      purchaseCount: selectedMatPurchases.length + selectedInboundPurchases.length,
    };
  }, [unsettledSales, unsettledPurchases, selectedSaleIds, selectedPurchaseIds, selectedInboundIds]);

  return (
    <>
      <style>{`
        @media print {
          nav, aside, .sidebar, [role="navigation"] { display: none !important; }
          .print-hidden-query { display: none !important; }
          body { -webkit-print-color-adjust: exact; print-color-adjust: exact; }
          .print-content { display: block !important; width: 100% !important; margin: 0 !important; padding: 0 !important; }
          .print-content table { font-size: 9px; width: 100%; border-collapse: collapse; }
          .print-content th, .print-content td { padding: 2px 4px !important; border: 1px solid #ccc !important; }
          .print-content h4 { font-size: 10px; margin: 4px 0 2px 0; }
          .print-empty { display: none !important; }
          .print-content .grid { gap: 2px !important; }
          .print-content .rounded-lg { border: 1px solid #ccc !important; padding: 4px !important; }
          .print-sign-area { display: block !important; }
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
                    {/* 屏幕汇总 - 重新设计为专业对账单头部 */}
                    <div className="bg-white border rounded-lg shadow-sm print:shadow-none print:border-0 print:rounded-none print:hidden">
                      <div className="px-4 py-3 border-b flex items-center justify-between">
                        <div>
                          <div className="text-lg font-bold">{activeItem.company_name}</div>
                          <div className="text-xs text-muted-foreground mt-0.5">对账周期：{periodText}</div>
                        </div>
                        <div className="flex items-center gap-2">
                          <Button variant="outline" size="sm" onClick={() => window.print()}>
                            <Printer className="h-4 w-4 mr-1" /> 打印
                          </Button>
                        </div>
                      </div>
                      <div className="grid grid-cols-5 gap-0 divide-x text-center text-sm">
                        <div className="p-3">
                          <div className="text-xs text-muted-foreground mb-1">期初余额</div>
                          <div className={cn("font-bold", activeItem.netting_opening > 0 ? "text-red-600" : activeItem.netting_opening < 0 ? "text-green-600" : "text-gray-600")}>
                            {activeItem.netting_opening > 0 ? `应收 ${fmt$(activeItem.netting_opening)}` : activeItem.netting_opening < 0 ? `应付 ${fmt$(Math.abs(activeItem.netting_opening))}` : "平"}
                          </div>
                        </div>
                        <div className="p-3">
                          <div className="text-xs text-muted-foreground mb-1">本期应收增加</div>
                          <div className="font-medium text-red-600">{fmt$(activeItem.receivable_current_sales)}</div>
                          <div className="text-xs text-muted-foreground mt-0.5">销售净额</div>
                        </div>
                        <div className="p-3">
                          <div className="text-xs text-muted-foreground mb-1">本期应付增加</div>
                          <div className="font-medium text-green-600">{fmt$(activeItem.payable_current_purchase)}</div>
                          <div className="text-xs text-muted-foreground mt-0.5">采购净额</div>
                        </div>
                        <div className="p-3">
                          <div className="text-xs text-muted-foreground mb-1">本期结算差额</div>
                          <div className={cn("font-medium", (activeItem.receivable_current_sales - activeItem.payable_current_purchase) > 0 ? "text-red-600" : (activeItem.receivable_current_sales - activeItem.payable_current_purchase) < 0 ? "text-green-600" : "text-gray-600")}>
                            {fmt$(activeItem.receivable_current_sales - activeItem.payable_current_purchase)}
                          </div>
                          <div className="text-xs text-muted-foreground mt-0.5">
                            {(activeItem.receivable_current_sales - activeItem.payable_current_purchase) > 0 ? "应收" : (activeItem.receivable_current_sales - activeItem.payable_current_purchase) < 0 ? "应付" : "平"}
                          </div>
                        </div>
                        <div className="p-3">
                          <div className="text-xs text-muted-foreground mb-1">期末余额</div>
                          <div className={cn("font-bold text-lg", activeItem.netting_closing > 0 ? "text-red-600" : activeItem.netting_closing < 0 ? "text-green-600" : "text-gray-600")}>
                            {activeItem.netting_closing > 0 ? `应收 ${fmt$(activeItem.netting_closing)}` : activeItem.netting_closing < 0 ? `应付 ${fmt$(Math.abs(activeItem.netting_closing))}` : "平"}
                          </div>
                          <div className="text-xs text-muted-foreground mt-0.5">
                            {activeItem.netting_direction === "应收" ? "对方欠我方" : activeItem.netting_direction === "应付" ? "我方欠对方" : "无欠款"}
                          </div>
                        </div>
                      </div>
                    </div>

                    {/* 打印专用标题 */}
                    <div className="hidden print:block mb-6">
                      <h1 className="text-2xl font-bold text-center mb-4">往来对账单</h1>
                      <div className="flex justify-between text-sm">
                        <div className="space-y-1">
                          <div>致：{activeItem.company_name}</div>
                          <div>货币单位：人民币（元）</div>
                        </div>
                        <div className="space-y-1 text-right">
                          <div>对账周期：{periodText}</div>
                          <div>制表日期：{new Date().toLocaleDateString("zh-CN", { year: "numeric", month: "long", day: "numeric" })}</div>
                        </div>
                      </div>
                    </div>

                    

                    {/* 打印汇总 */}
                    <div className="hidden print:block mb-6 text-sm">
                      <table className="w-full border-collapse border border-gray-300">
                        <thead>
                          <tr className="bg-gray-50">
                            <th className="border border-gray-300 px-3 py-2 text-center">期初余额</th>
                            <th className="border border-gray-300 px-3 py-2 text-center">本期应收增加</th>
                            <th className="border border-gray-300 px-3 py-2 text-center">本期应付增加</th>
                            <th className="border border-gray-300 px-3 py-2 text-center">本期结算差额</th>
                            <th className="border border-gray-300 px-3 py-2 text-center">期末余额</th>
                          </tr>
                        </thead>
                        <tbody>
                          <tr>
                            <td className={cn("border border-gray-300 px-3 py-2 text-center", activeItem.netting_opening > 0 ? "text-red-600" : activeItem.netting_opening < 0 ? "text-green-600" : "text-gray-600")}>
                              {fmt$(activeItem.netting_opening)}
                            </td>
                            <td className="border border-gray-300 px-3 py-2 text-center text-red-600">{fmt$(activeItem.receivable_current_sales)}</td>
                            <td className="border border-gray-300 px-3 py-2 text-center text-green-600">{fmt$(activeItem.payable_current_purchase)}</td>
                            <td className="border border-gray-300 px-3 py-2 text-center font-medium">
                              {(() => {
                                const diff = (Number(activeItem.receivable_current_sales) || 0) - (Number(activeItem.payable_current_purchase) || 0);
                                if (diff > 0) return <span className="text-red-600">应收 {fmt$(diff)}</span>;
                                if (diff < 0) return <span className="text-green-600">应付 {fmt$(Math.abs(diff))}</span>;
                                return <span className="text-gray-600">平</span>;
                              })()}
                            </td>
                            <td className={cn("border border-gray-300 px-3 py-2 text-center font-bold", activeItem.netting_closing > 0 ? "text-red-600" : activeItem.netting_closing < 0 ? "text-green-600" : "text-gray-600")}>
                              {activeItem.netting_closing > 0 ? `应收 ${fmt$(activeItem.netting_closing)}` : activeItem.netting_closing < 0 ? `应付 ${fmt$(Math.abs(activeItem.netting_closing))}` : "平"}
                            </td>
                          </tr>
                        </tbody>
                      </table>
                    </div>

                    {/* 销售明细 - 可折叠 */}
                    <div className="space-y-1">
                      <button
                        className="flex items-center gap-1.5 text-sm font-medium hover:text-blue-600 transition-colors print:hidden"
                        onClick={() => setShowSaleDetails(!showSaleDetails)}
                      >
                        {showSaleDetails ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
                        <FileSpreadsheet className="h-4 w-4 text-orange-500" />
                        销售明细（参考）
                        <span className="text-xs text-muted-foreground font-normal">{(activeItem.sale_details || []).length} 笔</span>
                      </button>
                      {showSaleDetails && (
                        <div className="border rounded-md">
                          <Table>
                            <TableHeader>
                              <TableRow className="bg-muted/20">
                                <TableHead className="text-xs py-1.5">日期</TableHead>
                                <TableHead className="text-xs py-1.5">销售单号</TableHead>
                                <TableHead className="text-xs py-1.5">批次名称</TableHead>
                                <TableHead className="text-xs py-1.5">宰杀日期</TableHead>
                                <TableHead className="text-xs py-1.5">加工厂(EU)</TableHead>
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
                                <TableRow>
                                  <TableCell colSpan={11} className="text-xs text-center text-muted-foreground py-2">无销售明细</TableCell>
                                </TableRow>
                              ) : (
                                (activeItem.sale_details || []).map((d: any, idx: number) => (
                                  <TableRow key={idx}>
                                    <TableCell className="text-xs py-1.5">{fmtDate(d.date)}</TableCell>
                                    <TableCell className="text-xs py-1.5">{d.sale_no}</TableCell>
                                    <TableCell className="text-xs py-1.5">{d.batch_name || "-"}</TableCell>
                                    <TableCell className="text-xs py-1.5">{d.slaughter_date ? fmtDate(d.slaughter_date) : "-"}</TableCell>
                                    <TableCell className="text-xs py-1.5">{d.processing_plant_code || "-"}</TableCell>
                                    <TableCell className="text-xs py-1.5">{d.spec || "-"}</TableCell>
                                    <TableCell className="text-xs py-1.5 text-right">{d.quantity != null ? d.quantity : "-"}</TableCell>
                                    <TableCell className="text-xs py-1.5 text-right">{d.weight_kg ? Number(d.weight_kg).toFixed(2) : "-"}</TableCell>
                                    <TableCell className="text-xs py-1.5 text-right">{d.unit_price ? fmt$(d.unit_price) : "-"}</TableCell>
                                    <TableCell className="text-xs py-1.5 text-right">{fmt$(d.gross_amount)}</TableCell>
                                    <TableCell className="text-xs py-1.5 text-right font-medium">{fmt$(d.net_amount)}</TableCell>
                                  </TableRow>
                                ))
                              )}
                              <TableRow className="bg-muted/30 font-medium">
                                <TableCell className="text-xs py-1.5" colSpan={6}>销售合计</TableCell>
                                <TableCell className="text-xs py-1.5 text-right">{(activeItem.sale_details || []).reduce((sum: number, d: any) => sum + (Number(d.quantity) || 0), 0)}</TableCell>
                                <TableCell className="text-xs py-1.5 text-right">{(activeItem.sale_details || []).reduce((sum: number, d: any) => sum + (Number(d.weight_kg) || 0), 0).toFixed(2)}</TableCell>
                                <TableCell className="text-xs py-1.5"></TableCell>
                                <TableCell className="text-xs py-1.5 text-right">{fmt$((activeItem.sale_details || []).reduce((sum: number, d: any) => sum + (Number(d.gross_amount) || 0), 0))}</TableCell>
                                <TableCell className="text-xs py-1.5 text-right">{fmt$((activeItem.sale_details || []).reduce((sum: number, d: any) => sum + (Number(d.net_amount) || 0), 0))}</TableCell>
                              </TableRow>
                            </TableBody>
                          </Table>
                        </div>
                      )}
                    </div>

                    {/* 销售折扣明细 - 可折叠 */}
                    <div className="space-y-1">
                      <button
                        className="flex items-center gap-1.5 text-sm font-medium hover:text-blue-600 transition-colors"
                        onClick={() => setShowDiscountDetails(!showDiscountDetails)}
                      >
                        {showDiscountDetails ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
                        <FileSpreadsheet className="h-4 w-4 text-orange-400" />
                        销售折扣明细
                        <span className="text-xs text-muted-foreground font-normal">{(activeItem.discount_details || []).length} 笔</span>
                      </button>
                      {showDiscountDetails && (
                        <div className="border rounded-md">
                          <Table>
                            <TableHeader>
                              <TableRow className="bg-muted/20">
                                <TableHead className="text-xs py-1.5">日期</TableHead>
                                <TableHead className="text-xs py-1.5">销售单号</TableHead>
                                <TableHead className="text-xs py-1.5 text-right">折扣金额</TableHead>
                              </TableRow>
                            </TableHeader>
                            <TableBody>
                              {(activeItem.discount_details || []).length === 0 ? (
                                <TableRow>
                                  <TableCell colSpan={3} className="text-xs text-center text-muted-foreground py-2">无折扣记录</TableCell>
                                </TableRow>
                              ) : (
                                (activeItem.discount_details || []).map((d: any, idx: number) => (
                                  <TableRow key={idx}>
                                    <TableCell className="text-xs py-1.5">{fmtDate(d.date)}</TableCell>
                                    <TableCell className="text-xs py-1.5">{d.sale_no}</TableCell>
                                    <TableCell className="text-xs py-1.5 text-right text-orange-600">-{fmt$(d.discount_amount)}</TableCell>
                                  </TableRow>
                                ))
                              )}
                              <TableRow className="bg-muted/30 font-medium">
                                <TableCell className="text-xs py-1.5" colSpan={2}>折扣合计</TableCell>
                                <TableCell className="text-xs py-1.5 text-right text-orange-600">
                                  -{fmt$((activeItem.discount_details || []).reduce((sum: number, d: any) => sum + (Number(d.discount_amount) || 0), 0))}
                                </TableCell>
                              </TableRow>
                            </TableBody>
                          </Table>
                        </div>
                      )}
                    </div>

                    {/* 销售售后明细 - 可折叠 */}
                    <div className="space-y-1">
                      <button
                        className="flex items-center gap-1.5 text-sm font-medium hover:text-blue-600 transition-colors"
                        onClick={() => setShowAftersalesDetails(!showAftersalesDetails)}
                      >
                        {showAftersalesDetails ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
                        <FileSpreadsheet className="h-4 w-4 text-red-400" />
                        销售售后明细
                        <span className="text-xs text-muted-foreground font-normal">
                          {(activeItem.aftersales_details || []).length} 笔
                        </span>
                      </button>
                      {showAftersalesDetails && (
                        <div className="border rounded-md">
                          <Table>
                            <TableHeader>
                              <TableRow className="bg-muted/20">
                                <TableHead className="text-xs py-1.5">日期</TableHead>
                                <TableHead className="text-xs py-1.5">来源</TableHead>
                                <TableHead className="text-xs py-1.5">单号</TableHead>
                                <TableHead className="text-xs py-1.5 text-right">售后金额</TableHead>
                                <TableHead className="text-xs py-1.5">备注</TableHead>
                              </TableRow>
                            </TableHeader>
                            <TableBody>
                              {(activeItem.aftersales_details || []).length === 0 ? (
                                <TableRow>
                                  <TableCell colSpan={5} className="text-xs text-center text-muted-foreground py-2">无销售售后记录</TableCell>
                                </TableRow>
                              ) : (
                                (activeItem.aftersales_details || []).map((d: any, idx: number) => (
                                  <TableRow key={idx}>
                                    <TableCell className="text-xs py-1.5">{fmtDate(d.date)}</TableCell>
                                    <TableCell className="text-xs py-1.5">
                                      <span className="text-blue-600">退货单</span>
                                    </TableCell>
                                    <TableCell className="text-xs py-1.5">{d.return_no || d.sale_no || "-"}</TableCell>
                                    <TableCell className="text-xs py-1.5 text-right text-red-600">-{fmt$(d.amount)}</TableCell>
                                    <TableCell className="text-xs py-1.5">{d.reason || "-"}</TableCell>
                                  </TableRow>
                                ))
                              )}
                              <TableRow className="bg-muted/30 font-medium">
                                <TableCell className="text-xs py-1.5" colSpan={3}>售后合计</TableCell>
                                <TableCell className="text-xs py-1.5 text-right text-red-600">
                                  -{fmt$((activeItem.aftersales_details || []).reduce((sum: number, d: any) => sum + (Number(d.amount) || 0), 0))}
                                </TableCell>
                                <TableCell className="text-xs py-1.5"></TableCell>
                              </TableRow>
                            </TableBody>
                          </Table>
                        </div>
                      )}
                    </div>

                    {/* 采购明细 - 可折叠 */}
                    <div className="space-y-1">
                      <button
                        className="flex items-center gap-1.5 text-sm font-medium hover:text-blue-600 transition-colors"
                        onClick={() => setShowPurchaseDetails(!showPurchaseDetails)}
                      >
                        {showPurchaseDetails ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
                        <FileSpreadsheet className="h-4 w-4 text-green-500" />
                        采购明细（参考）
                        <span className="text-xs text-muted-foreground font-normal">{(activeItem.purchase_details || []).length} 笔</span>
                      </button>
                      {showPurchaseDetails && (
                        <div className="border rounded-md">
                          <Table>
                            <TableHeader>
                              <TableRow className="bg-muted/20">
                                <TableHead className="text-xs py-1.5">日期</TableHead>
                                <TableHead className="text-xs py-1.5">单号</TableHead>
                                <TableHead className="text-xs py-1.5">批次</TableHead>
                                <TableHead className="text-xs py-1.5">规格</TableHead>
                                <TableHead className="text-xs py-1.5 text-right">数量</TableHead>
                                <TableHead className="text-xs py-1.5 text-right">重量(kg)</TableHead>
                                <TableHead className="text-xs py-1.5 text-right">单价</TableHead>
                                <TableHead className="text-xs py-1.5 text-right">金额</TableHead>
                                <TableHead className="text-xs py-1.5 text-right">净额</TableHead>
                              </TableRow>
                            </TableHeader>
                            <TableBody>
                              {(activeItem.purchase_details || []).length === 0 ? (
                                <TableRow>
                                  <TableCell colSpan={9} className="text-xs text-center text-muted-foreground py-2">无采购明细</TableCell>
                                </TableRow>
                              ) : (
                                (activeItem.purchase_details || []).map((d: any, idx: number) => (
                                  <TableRow key={idx}>
                                    <TableCell className="text-xs py-1.5">{d.date}</TableCell>
                                    <TableCell className="text-xs py-1.5">{d.invoice_no || "-"}</TableCell>
                                    <TableCell className="text-xs py-1.5">{d.batch_no || "-"}</TableCell>
                                    <TableCell className="text-xs py-1.5">{d.spec || "-"}</TableCell>
                                    <TableCell className="text-xs py-1.5 text-right">{d.quantity != null ? d.quantity : "-"}</TableCell>
                                    <TableCell className="text-xs py-1.5 text-right">{d.weight_kg ? Number(d.weight_kg).toFixed(2) : "-"}</TableCell>
                                    <TableCell className="text-xs py-1.5 text-right">{d.unit_price ? fmt$(d.unit_price) : "-"}</TableCell>
                                    <TableCell className="text-xs py-1.5 text-right">{fmt$(d.amount_cny)}</TableCell>
                                    <TableCell className="text-xs py-1.5 text-right font-medium">
                                      {fmt$((Number(d.amount_cny) || 0) - (Number(d.after_sales_adjustment) || 0))}
                                    </TableCell>
                                  </TableRow>
                                ))
                              )}
                              <TableRow className="bg-muted/30 font-medium">
                                <TableCell className="text-xs py-1.5" colSpan={4}>采购合计</TableCell>
                                <TableCell className="text-xs py-1.5 text-right">{(activeItem.purchase_details || []).reduce((sum: number, d: any) => sum + (Number(d.quantity) || 0), 0)}</TableCell>
                                <TableCell className="text-xs py-1.5 text-right">{(activeItem.purchase_details || []).reduce((sum: number, d: any) => sum + (Number(d.weight_kg) || 0), 0).toFixed(2)}</TableCell>
                                <TableCell className="text-xs py-1.5"></TableCell>
                                <TableCell className="text-xs py-1.5 text-right">
                                  {fmt$((activeItem.purchase_details || []).reduce((sum: number, d: any) => sum + (Number(d.amount_cny) || 0), 0))}
                                </TableCell>
                                <TableCell className="text-xs py-1.5 text-right">
                                  {fmt$((activeItem.purchase_details || []).reduce((sum: number, d: any) => sum + (Number(d.amount_cny) || 0) - (Number(d.after_sales_adjustment) || 0), 0))}
                                </TableCell>
                              </TableRow>
                            </TableBody>
                          </Table>
                        </div>
                      )}
                    </div>

                    {/* 采购售后明细 - 可折叠 */}
                    <div className="space-y-1">
                      <button
                        className="flex items-center gap-1.5 text-sm font-medium hover:text-blue-600 transition-colors"
                        onClick={() => setShowPurchaseReturnDetails(!showPurchaseReturnDetails)}
                      >
                        {showPurchaseReturnDetails ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
                        <FileSpreadsheet className="h-4 w-4 text-red-400" />
                        采购售后明细
                        <span className="text-xs text-muted-foreground font-normal">{(activeItem.purchase_return_details || []).length} 笔</span>
                      </button>
                      {showPurchaseReturnDetails && (
                        <div className="border rounded-md">
                          <Table>
                            <TableHeader>
                              <TableRow className="bg-muted/20">
                                <TableHead className="text-xs py-1.5">日期</TableHead>
                                <TableHead className="text-xs py-1.5">售后单号</TableHead>
                                <TableHead className="text-xs py-1.5 text-right">退款金额</TableHead>
                                <TableHead className="text-xs py-1.5">退款方式</TableHead>
                                <TableHead className="text-xs py-1.5">原因</TableHead>
                              </TableRow>
                            </TableHeader>
                            <TableBody>
                              {(activeItem.purchase_return_details || []).length === 0 ? (
                                <TableRow>
                                  <TableCell colSpan={5} className="text-xs text-center text-muted-foreground py-2">无采购售后记录</TableCell>
                                </TableRow>
                              ) : (
                                (activeItem.purchase_return_details || []).map((d: any, idx: number) => (
                                  <TableRow key={idx}>
                                    <TableCell className="text-xs py-1.5">{fmtDate(d.date)}</TableCell>
                                    <TableCell className="text-xs py-1.5">{d.return_no || "-"}</TableCell>
                                    <TableCell className="text-xs py-1.5 text-right text-red-600">-{fmt$(d.amount)}</TableCell>
                                    <TableCell className="text-xs py-1.5">{d.refund_method || "-"}</TableCell>
                                    <TableCell className="text-xs py-1.5">{d.reason || "-"}</TableCell>
                                  </TableRow>
                                ))
                              )}
                              <TableRow className="bg-muted/30 font-medium">
                                <TableCell className="text-xs py-1.5" colSpan={2}>采购售后合计</TableCell>
                                <TableCell className="text-xs py-1.5 text-right text-red-600">
                                  -{fmt$((activeItem.purchase_return_details || []).reduce((sum: number, d: any) => sum + (Number(d.amount) || 0), 0))}
                                </TableCell>
                                <TableCell className="text-xs py-1.5" colSpan={2}></TableCell>
                              </TableRow>
                            </TableBody>
                          </Table>
                        </div>
                      )}
                    </div>

{/* 往来结算汇总说明 */}
                    <div className="hidden print:block mb-6 text-sm">
                      <div className="text-base font-bold mb-3">本期往来结算汇总</div>
                      <table className="w-full border-collapse border border-gray-300 mb-4">
                        <tbody>
                          <tr>
                            <td className="border border-gray-300 px-3 py-2 font-medium bg-gray-50 w-32">本期应收贵公司款项</td>
                            <td className="border border-gray-300 px-3 py-2 text-right">
                              {fmt$(activeItem.receivable_current_sales)}
                            </td>
                          </tr>
                          <tr>
                            <td className="border border-gray-300 px-3 py-2 font-medium bg-gray-50">本期应付贵公司款项</td>
                            <td className="border border-gray-300 px-3 py-2 text-right">
                              {fmt$(activeItem.payable_current_purchase)}
                            </td>
                          </tr>
                          <tr>
                            <td className="border border-gray-300 px-3 py-2 font-medium bg-gray-50">本期结算</td>
                            <td className="border border-gray-300 px-3 py-2 text-right font-medium">
                              {(() => {
                                const diff = (Number(activeItem.receivable_current_sales) || 0) - (Number(activeItem.payable_current_purchase) || 0);
                                if (diff > 0) return <span>应收 {fmt$(diff)}</span>;
                                if (diff < 0) return <span>应付 {fmt$(Math.abs(diff))}</span>;
                                return <span>平</span>;
                              })()}
                            </td>
                          </tr>
                        </tbody>
                      </table>
                    </div>

{/* 收付款流水明细 - 核心对账内容 */}
                    <div className="space-y-2">
                      <div className="flex items-center justify-between">
                        <h4 className="text-sm font-bold flex items-center gap-1.5">
                          <Receipt className="h-4 w-4 text-blue-600" />
                          收付款流水明细
                        </h4>
                        <span className="text-xs text-muted-foreground">共 {(activeItem.payment_details || []).length} 笔</span>
                      </div>
                      <div className="border rounded-md overflow-hidden">
                        <Table>
                          <TableHeader>
                            <TableRow className="bg-slate-50">
                              <TableHead className="text-xs py-2 w-24">日期</TableHead>
                              <TableHead className="text-xs py-2">摘要</TableHead>
                              <TableHead className="text-xs py-2 w-28">分类</TableHead>
                              <TableHead className="text-xs py-2 text-right w-24">收入</TableHead>
                              <TableHead className="text-xs py-2 text-right w-24">支出</TableHead>
                              <TableHead className="text-xs py-2 text-right w-24">余额</TableHead>
                              <TableHead className="text-xs py-2 w-32">备注</TableHead>
                            </TableRow>
                          </TableHeader>
                          <TableBody>
                            {/* 期初余额行 */}
                            <TableRow className="bg-amber-50/50">
                              <TableCell className="text-xs py-1.5 text-muted-foreground">{startDate || "期初"}</TableCell>
                              <TableCell className="text-xs py-1.5 font-medium">上期结转 / 期初余额</TableCell>
                              <TableCell className="text-xs py-1.5">-</TableCell>
                              <TableCell className="text-xs py-1.5 text-right">-</TableCell>
                              <TableCell className="text-xs py-1.5 text-right">-</TableCell>
                              <TableCell className="text-xs py-1.5 text-right font-medium">
                                <span className={activeItem.netting_opening > 0 ? "text-red-600" : activeItem.netting_opening < 0 ? "text-green-600" : "text-gray-600"}>
                                  {fmt$(activeItem.netting_opening)}
                                </span>
                              </TableCell>
                              <TableCell className="text-xs py-1.5">-</TableCell>
                            </TableRow>
                            {(activeItem.payment_details || []).length === 0 ? (
                              <TableRow>
                                <TableCell colSpan={7} className="text-xs text-center text-muted-foreground py-3">本期无收付款记录</TableCell>
                              </TableRow>
                            ) : (
                              (() => {
                                let runningBalance = Number(activeItem.netting_opening);
                                const sortedDetails = [...(activeItem.payment_details || [])].sort((a: any, b: any) => {
                                  return new Date(a.date).getTime() - new Date(b.date).getTime();
                                });
                                return sortedDetails.map((d: any, idx: number) => {
                                  const isReceipt = d.type === "receipt";
                                  const amount = Number(d.amount) || 0;
                                  if (isReceipt) {
                                    runningBalance += amount;
                                  } else {
                                    runningBalance -= amount;
                                  }
                                  return (
                                    <TableRow key={idx}>
                                      <TableCell className="text-xs py-1.5">{fmtDate(d.date)}</TableCell>
                                      <TableCell className="text-xs py-1.5">
                                        <span className={isReceipt ? "text-green-700" : "text-red-700"}>
                                          {paymentDescLabel(d.description)}
                                        </span>
                                      </TableCell>
                                      <TableCell className="text-xs py-1.5">
                                        <span className={cn(
                                          "px-1.5 py-0.5 rounded text-xs",
                                          isReceipt ? "bg-green-50 text-green-700" : "bg-red-50 text-red-700"
                                        )}>
                                          {isReceipt ? "收款" : "付款"}
                                        </span>
                                      </TableCell>
                                      <TableCell className="text-xs py-1.5 text-right">
                                        {isReceipt ? <span className="text-green-600">{fmt$(amount)}</span> : "-"}
                                      </TableCell>
                                      <TableCell className="text-xs py-1.5 text-right">
                                        {!isReceipt ? <span className="text-red-600">{fmt$(amount)}</span> : "-"}
                                      </TableCell>
                                      <TableCell className="text-xs py-1.5 text-right font-medium">
                                        <span className={runningBalance > 0 ? "text-red-600" : runningBalance < 0 ? "text-green-600" : "text-gray-600"}>
                                          {fmt$(runningBalance)}
                                        </span>
                                      </TableCell>
                                      <TableCell className="text-xs py-1.5 text-muted-foreground">{d.notes || "-"}</TableCell>
                                    </TableRow>
                                  );
                                });
                              })()
                            )}
                            {/* 期末余额行 */}
                            {(activeItem.payment_details || []).length > 0 && (
                              <TableRow className="bg-slate-50 font-medium border-t-2">
                                <TableCell className="text-xs py-2" colSpan={3}>本期合计 / 期末余额</TableCell>
                                <TableCell className="text-xs py-2 text-right text-green-600">
                                  {fmt$((activeItem.payment_details || []).filter((d: any) => d.type === "receipt").reduce((sum: number, d: any) => sum + (Number(d.amount) || 0), 0))}
                                </TableCell>
                                <TableCell className="text-xs py-2 text-right text-red-600">
                                  {fmt$((activeItem.payment_details || []).filter((d: any) => d.type === "payment").reduce((sum: number, d: any) => sum + (Number(d.amount) || 0), 0))}
                                </TableCell>
                                <TableCell className="text-xs py-2 text-right">
                                  <span className={activeItem.netting_closing > 0 ? "text-red-600" : activeItem.netting_closing < 0 ? "text-green-600" : "text-gray-600"}>
                                    {fmt$(activeItem.netting_closing)}
                                  </span>
                                </TableCell>
                                <TableCell className="text-xs py-2">-</TableCell>
                              </TableRow>
                            )}
                          </TableBody>
                        </Table>
                      </div>
                    </div>

                    {/* 结算说明与收款账户 */}
                    <div className="hidden print:block mt-8 text-sm">
<div className="mb-4 leading-relaxed text-sm">
                        {(() => {
                          const diff = (Number(activeItem.receivable_current_sales) || 0) - (Number(activeItem.payable_current_purchase) || 0);
                          const closing = Number(activeItem.netting_closing) || 0;
                          if (closing > 0) {
                            return (
                              <div className="space-y-1">
                                <div>
                                  综上所述，本期结算为贵公司应付我公司人民币<strong className="mx-1">{numberToChinese(diff)}</strong>（小写：{fmt$(diff)}）。
                                  截至本期期末，贵公司累计应付我公司人民币<strong className="mx-1">{numberToChinese(closing)}</strong>（小写：{fmt$(closing)}）。
                                </div>
                                <div>请贵公司核对无误后，将上述款项支付至我公司以下账户：</div>
                              </div>
                            );
                          }
                          if (closing < 0) {
                            return (
                              <div className="space-y-1">
                                <div>
                                  综上所述，本期结算为我公司应付贵公司人民币<strong className="mx-1">{numberToChinese(Math.abs(diff))}</strong>（小写：{fmt$(Math.abs(diff))}）。
                                  截至本期期末，我公司累计应付贵公司人民币<strong className="mx-1">{numberToChinese(Math.abs(closing))}</strong>（小写：{fmt$(Math.abs(closing))}）。
                                </div>
                                <div>请贵公司核对无误后，我公司将上述款项支付至贵公司指定账户。</div>
                              </div>
                            );
                          }
                          return <div>综上所述，双方往来款项已结清。</div>;
                        })()}
                      </div>

                      <div className="border border-gray-300 rounded overflow-hidden">
                        <table className="w-full text-sm border-collapse">
                          <tbody>
                            <tr className="border-b border-gray-300">
                              <td className="border-r border-gray-300 px-3 py-2 font-medium bg-gray-50 w-28">收款方</td>
                              <td className="px-3 py-2">绍兴中挪食品有限公司</td>
                            </tr>
                            <tr className="border-b border-gray-300">
                              <td className="border-r border-gray-300 px-3 py-2 font-medium bg-gray-50">银行账户</td>
                              <td className="px-3 py-2">330604106000219512</td>
                            </tr>
                            <tr>
                              <td className="border-r border-gray-300 px-3 py-2 font-medium bg-gray-50">开户行地址</td>
                              <td className="px-3 py-2">杭州银行绍兴分行营业部</td>
                            </tr>
                          </tbody>
                        </table>
                      </div>
                    </div>                  </div>
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
        {/* 对冲结算弹窗 */}
        <Dialog open={isNettingOpen} onOpenChange={setIsNettingOpen}>
          <DialogContent className="max-w-4xl max-h-[90vh] overflow-y-auto">
            <DialogHeader>
              <DialogTitle>生成对冲结算</DialogTitle>
              <DialogDescription>
                选择要对冲的销售单和采购单，系统自动计算对冲金额。对冲金额 = min(选中销售待收合计, 选中采购待付合计)
              </DialogDescription>
            </DialogHeader>

            <div className="grid grid-cols-2 gap-4 mt-4">
              {/* 左侧：未结清销售单 */}
              <div className="space-y-2">
                <div className="font-medium text-sm flex items-center justify-between">
                  <span>未结清销售单</span>
                  <span className="text-xs text-muted-foreground">{(unsettledSales || []).length} 笔</span>
                </div>
                <div className="border rounded-md max-h-[300px] overflow-y-auto">
                  {(unsettledSales || []).length === 0 ? (
                    <div className="text-xs text-muted-foreground text-center py-4">暂无未结清销售单</div>
                  ) : (
                    <div className="divide-y">
                      {(unsettledSales || []).map((s: any) => (
                        <label key={s.id} className="flex items-start gap-2 p-2 hover:bg-muted/30 cursor-pointer">
                          <input
                            type="checkbox"
                            checked={selectedSaleIds.includes(s.id)}
                            onChange={(e) => {
                              if (e.target.checked) {
                                setSelectedSaleIds(prev => [...prev, s.id]);
                              } else {
                                setSelectedSaleIds(prev => prev.filter(id => id !== s.id));
                              }
                            }}
                            className="mt-0.5"
                          />
                          <div className="flex-1 text-xs">
                            <div className="font-medium">{s.sale_no || `#${s.id}`}</div>
                            <div className="text-muted-foreground">{fmtDate(s.sale_date || s.date)} · {s._type === "whole_fish" ? "进口整鱼" : "成品/以销定采"}</div>
                            <div className="flex justify-between mt-0.5">
                              <span>应付 ¥{fmt$(s.net_amount || s.total_amount)}</span>
                              <span className="text-orange-600">待收 ¥{fmt$(s._remaining)}</span>
                            </div>
                          </div>
                        </label>
                      ))}
                    </div>
                  )}
                </div>
              </div>

              {/* 右侧：未结清采购单 */}
              <div className="space-y-2">
                <div className="font-medium text-sm flex items-center justify-between">
                  <span>未结清采购单</span>
                  <span className="text-xs text-muted-foreground">{(unsettledPurchases || []).length} 笔</span>
                </div>
                <div className="border rounded-md max-h-[300px] overflow-y-auto">
                  {(unsettledPurchases || []).length === 0 ? (
                    <div className="text-xs text-muted-foreground text-center py-4">暂无未结清采购单</div>
                  ) : (
                    <div className="divide-y">
                      {(unsettledPurchases || []).map((p: any) => (
                        <label key={`${p._source}-${p.id}`} className="flex items-start gap-2 p-2 hover:bg-muted/30 cursor-pointer">
                          <input
                            type="checkbox"
                            checked={p._source === "inbound" ? selectedInboundIds.includes(p.id) : selectedPurchaseIds.includes(p.id)}
                            onChange={(e) => {
                              if (p._source === "inbound") {
                                if (e.target.checked) {
                                  setSelectedInboundIds(prev => [...prev, p.id]);
                                } else {
                                  setSelectedInboundIds(prev => prev.filter(id => id !== p.id));
                                }
                              } else {
                                if (e.target.checked) {
                                  setSelectedPurchaseIds(prev => [...prev, p.id]);
                                } else {
                                  setSelectedPurchaseIds(prev => prev.filter(id => id !== p.id));
                                }
                              }
                            }}
                            className="mt-0.5"
                          />
                          <div className="flex-1 text-xs">
                            <div className="font-medium">{p.order_no || p.purchase_no || `#${p.id}`}</div>
                            <div className="text-muted-foreground">{fmtDate(p.order_date || p.purchase_date)} · {p._source === "inbound" ? "采购入库" : "辅料采购"}</div>
                            <div className="flex justify-between mt-0.5">
                              <span>总额 ¥{fmt$(p.actual_total || p.total_amount)}</span>
                              <span className="text-orange-600">待付 ¥{fmt$(p._remaining)}</span>
                            </div>
                          </div>
                        </label>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            </div>

            {/* 预览区域 */}
            <div className="bg-muted/30 rounded-lg p-3 mt-4">
              <div className="grid grid-cols-3 gap-4 text-sm text-center">
                <div>
                  <div className="text-xs text-muted-foreground">选中销售待收</div>
                  <div className="font-medium text-red-600">{fmt$(nettingPreview.saleTotal)}</div>
                  <div className="text-xs text-muted-foreground">{nettingPreview.saleCount} 笔</div>
                </div>
                <div>
                  <div className="text-xs text-muted-foreground">选中采购待付</div>
                  <div className="font-medium text-green-600">{fmt$(nettingPreview.purchaseTotal)}</div>
                  <div className="text-xs text-muted-foreground">{nettingPreview.purchaseCount} 笔</div>
                </div>
                <div>
                  <div className="text-xs text-muted-foreground">对冲金额</div>
                  <div className="font-bold text-lg text-blue-600">{fmt$(nettingPreview.nettingAmount)}</div>
                  <div className="text-xs text-muted-foreground">
                    {nettingPreview.saleTotal > nettingPreview.purchaseTotal ? `销售多 ¥${(nettingPreview.saleTotal - nettingPreview.nettingAmount).toLocaleString("zh-CN", { minimumFractionDigits: 2 })}` : `采购多 ¥${(nettingPreview.purchaseTotal - nettingPreview.nettingAmount).toLocaleString("zh-CN", { minimumFractionDigits: 2 })}`}
                  </div>
                </div>
              </div>
            </div>

            {/* 银行账号选择 */}
            <div className="mt-4">
              <Label className="text-xs text-muted-foreground">收款银行账号（可选）</Label>
              <select
                value={selectedBankAccountId}
                onChange={(e) => setSelectedBankAccountId(e.target.value)}
                className="w-full mt-1 px-3 py-2 border rounded-md text-sm"
              >
                <option value="">不指定银行账号</option>
                {(bankAccounts || []).map((acc: any) => (
                  <option key={acc.id} value={acc.id}>
                    {acc.account_name} {acc.bank_name ? `(${acc.bank_name})` : ""} {acc.account_no ? `- ${acc.account_no}` : ""}
                  </option>
                ))}
              </select>
            </div>

            <DialogFooter>
              <Button variant="outline" onClick={() => setIsNettingOpen(false)}>取消</Button>
              <Button
                onClick={handleNettingSubmit}
                disabled={nettingSubmitting || nettingPreview.nettingAmount <= 0}
                className="bg-blue-600 hover:bg-blue-700"
              >
                {nettingSubmitting ? <Loader2 className="h-4 w-4 animate-spin mr-1" /> : null}
                确认生成对冲结算
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </div>
    </>
  );
}
