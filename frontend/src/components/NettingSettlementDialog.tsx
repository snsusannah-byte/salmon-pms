import React, { useState, useMemo, useEffect } from "react";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { toast } from "sonner";
import { Loader2, Landmark, Search } from "lucide-react";

function fmt$(v: number | string | null | undefined) {
  const n = Number(v ?? 0);
  if (Number.isNaN(n)) return "¥0.00";
  return `¥${n.toLocaleString("zh-CN", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

function fmtDate(d: string | null | undefined) {
  if (!d) return "-";
  return new Date(d).toLocaleDateString("zh-CN");
}

interface NettingSettlementDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSuccess?: () => void;
}

export function NettingSettlementDialog({ open, onOpenChange, onSuccess }: NettingSettlementDialogProps) {
  const [selectedCompanyId, setSelectedCompanyId] = useState<string>("");
  const [companySearch, setCompanySearch] = useState("");
  const [selectedSaleIds, setSelectedSaleIds] = useState<number[]>([]);
  const [selectedPurchaseIds, setSelectedPurchaseIds] = useState<number[]>([]);
  const [selectedInboundIds, setSelectedInboundIds] = useState<number[]>([]);
  const [selectedBankAccountId, setSelectedBankAccountId] = useState<string>("");
  const [roundingAmount, setRoundingAmount] = useState<string>("0");
  const [actualAmount, setActualAmount] = useState<string>("");
  const [transactionDate, setTransactionDate] = useState<string>(new Date().toISOString().split("T")[0]);
  const [submitting, setSubmitting] = useState(false);

  // 重置状态当弹窗打开
  useEffect(() => {
    if (open) {
      setSelectedCompanyId("");
      setCompanySearch("");
      setSelectedSaleIds([]);
      setSelectedPurchaseIds([]);
      setSelectedInboundIds([]);
      setSelectedBankAccountId("");
      setRoundingAmount("0");
      setActualAmount("");
      setTransactionDate(new Date().toISOString().split("T")[0]);
    }
  }, [open]);

  // 查询公司
  const { data: companies } = useQuery({
    queryKey: ["netting-companies"],
    queryFn: async () => {
      const res = await api.get("/v1/companies/?limit=500");
      return (res.data?.items || []) as { id: number; name: string; type?: string; code?: string }[];
    },
    enabled: open,
  });

  // 过滤公司（支持搜索）
  const filteredCompanies = useMemo(() => {
    if (!companies) return [];
    if (!companySearch.trim()) return companies;
    return companies.filter(c =>
      c.name.toLowerCase().includes(companySearch.toLowerCase()) ||
      (c.code || "").toLowerCase().includes(companySearch.toLowerCase())
    );
  }, [companies, companySearch]);

  // 查询银行账号
  const { data: bankAccounts } = useQuery({
    queryKey: ["bank-accounts-list"],
    queryFn: async () => {
      const res = await api.get("/v1/finance/bank-accounts?limit=100");
      // API 直接返回数组，不是 {items: []}
      return (Array.isArray(res.data) ? res.data : res.data?.items || []) as { id: number; account_name: string; bank_name?: string; account_no?: string }[];
    },
    enabled: open,
  });

  // 查询未结清销售单
  const { data: unsettledSales } = useQuery({
    queryKey: ["netting-unsettled-sales", selectedCompanyId],
    queryFn: async () => {
      if (!selectedCompanyId) return [];
      const cid = Number(selectedCompanyId);
      const [wfRes, fpV2Res] = await Promise.all([
        api.get(`/v1/sales/whole-fish?customer_id=${cid}&limit=500`),
        api.get(`/v1/finished-product-sales?customer_id=${cid}&limit=500`),
      ]);
      const wfItems = (wfRes.data?.items || [])
        .filter((s: any) => (s.net_amount || s.total_amount || 0) - (s.paid_amount || 0) > 0.01)
        .map((s: any) => ({ ...s, _type: "whole_fish", _remaining: (s.net_amount || s.total_amount || 0) - (s.paid_amount || 0) }));
      const fpV2Items = (fpV2Res.data?.items || [])
        .filter((s: any) => (s.net_amount || s.total_amount || 0) - (s.paid_amount || 0) > 0.01)
        .map((s: any) => ({ ...s, _type: "finished_product", _remaining: (s.net_amount || s.total_amount || 0) - (s.paid_amount || 0) }));
      return [...wfItems, ...fpV2Items];
    },
    enabled: open && !!selectedCompanyId,
  });

  // 查询未结清采购单
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
        .map((p: any) => ({ ...p, _source: "material" as const, _remaining: (p.actual_total || p.total_amount || 0) - (p.paid_amount || 0) }));
      const inboundItems = (inboundRes.data?.items || [])
        .filter((p: any) => {
          const net = (p.total_amount || 0) - (p.after_sales_adjustment || 0);
          return net - (p.paid_amount || 0) > 0.01;
        })
        .map((p: any) => ({ ...p, _source: "inbound" as const, _remaining: (p.total_amount || 0) - (p.after_sales_adjustment || 0) - (p.paid_amount || 0) }));
      return [...matItems, ...inboundItems];
    },
    enabled: open && !!selectedCompanyId,
  });

  // 计算
  const preview = useMemo(() => {
    const selectedSales = (unsettledSales || []).filter((s: any) => selectedSaleIds.includes(s.id));
    const selectedMatPurchases = (unsettledPurchases || [])
      .filter((p: any) => p._source === "material" && selectedPurchaseIds.includes(p.id));
    const selectedInboundPurchases = (unsettledPurchases || [])
      .filter((p: any) => p._source === "inbound" && selectedInboundIds.includes(p.id));
    const saleTotal = selectedSales.reduce((sum: number, s: any) => sum + (s._remaining || 0), 0);
    const matTotal = selectedMatPurchases.reduce((sum: number, p: any) => sum + (p._remaining || 0), 0);
    const inboundTotal = selectedInboundPurchases.reduce((sum: number, p: any) => sum + (p._remaining || 0), 0);
    const purchaseTotal = matTotal + inboundTotal;
    const diff = Math.max(0, saleTotal - purchaseTotal);
    return {
      saleTotal, purchaseTotal, diff,
      saleCount: selectedSales.length,
      purchaseCount: selectedMatPurchases.length + selectedInboundPurchases.length,
    };
  }, [unsettledSales, unsettledPurchases, selectedSaleIds, selectedPurchaseIds, selectedInboundIds]);

  // 差额变化时，自动更新实付金额和抹零金额
  useEffect(() => {
    if (preview.diff > 0) {
      // 差额变化时：实付金额 = 差额，抹零 = 0
      setActualAmount(preview.diff.toFixed(2));
      setRoundingAmount("0");
    }
  }, [preview.diff]);

  // 手动修改实付金额时，自动计算抹零金额 = 差额 - 实付金额（抹零不能为负）
  const handleActualAmountChange = (value: string) => {
    setActualAmount(value);
    const actual = Number(value || 0);
    const rounding = Math.max(0, preview.diff - actual);
    setRoundingAmount(rounding.toFixed(2));
  };

  const handleSubmit = async () => {
    if (!selectedCompanyId) {
      toast.error("请选择主体");
      return;
    }
    const actual = Number(actualAmount || 0);
    if (actual <= 0) {
      toast.error("实付金额必须大于0");
      return;
    }
    setSubmitting(true);
    try {
      const companyName = companies?.find(c => String(c.id) === selectedCompanyId)?.name || "";
      const payload: any = {
        transaction_date: transactionDate,
        type: "income",
        category: "netting_settlement",
        amount: Number(actual.toFixed(2)),
        currency: "CNY",
        counterparty_id: Number(selectedCompanyId),
        counterparty_name: companyName,
        related_sale_ids: selectedSaleIds,
        related_purchase_ids: selectedPurchaseIds,
        related_purchase_inbound_ids: selectedInboundIds,
        description: `对冲结算：${preview.saleCount}个销售单 + ${preview.purchaseCount}个采购单`,
      };
      if (selectedBankAccountId) {
        payload.to_account_id = Number(selectedBankAccountId);
      }
      await api.post("/v1/finance/transactions", payload);
      toast.success("对冲结算已生成");
      onOpenChange(false);
      onSuccess?.();
    } catch (err: any) {
      toast.error(err.response?.data?.detail || "生成失败");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-[900px] max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Landmark className="h-5 w-5 text-blue-500" />
            生成对冲结算
          </DialogTitle>
        </DialogHeader>

        <div className="space-y-4">
          {/* 公司选择（支持搜索） */}
          <div>
            <Label className="text-xs text-muted-foreground">选择主体（既是客户又是供应商）</Label>
            <div className="relative mt-1">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
              <Input
                placeholder="搜索公司名称或代码..."
                value={companySearch}
                onChange={(e) => setCompanySearch(e.target.value)}
                className="pl-9"
              />
            </div>
            <div className="border rounded-md mt-1 max-h-[150px] overflow-y-auto">
              {filteredCompanies.length === 0 ? (
                <div className="text-xs text-muted-foreground text-center py-2">未找到匹配的公司</div>
              ) : (
                <div className="divide-y">
                  {filteredCompanies.map((c: any) => (
                    <div
                      key={c.id}
                      className={`flex items-center gap-2 p-2 cursor-pointer hover:bg-muted/30 ${selectedCompanyId === String(c.id) ? "bg-blue-50" : ""}`}
                      onClick={() => {
                        setSelectedCompanyId(String(c.id));
                        setSelectedSaleIds([]);
                        setSelectedPurchaseIds([]);
                        setSelectedInboundIds([]);
                      }}
                    >
                      <div className={`w-4 h-4 rounded-full border ${selectedCompanyId === String(c.id) ? "bg-blue-500 border-blue-500" : "border-gray-300"}`} />
                      <div className="flex-1 text-sm">
                        <div className="font-medium">{c.name}</div>
                        {c.code && <div className="text-xs text-muted-foreground">{c.code}</div>}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>

          {!selectedCompanyId ? (
            <div className="text-center text-muted-foreground py-8">请先选择公司</div>
          ) : (
            <>
              {/* 未结清销售单 */}
              <div className="space-y-2">
                <div className="font-medium text-sm flex items-center justify-between">
                  <span>未结清销售单</span>
                  <span className="text-xs text-muted-foreground">{(unsettledSales || []).length} 笔</span>
                </div>
                <div className="border rounded-md max-h-[200px] overflow-y-auto">
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
                              <span>应收 ¥{fmt$(s.net_amount || s.total_amount)}</span>
                              <span className="text-orange-600">待收 ¥{fmt$(s._remaining)}</span>
                            </div>
                          </div>
                        </label>
                      ))}
                    </div>
                  )}
                </div>
              </div>

              {/* 未结清采购单 */}
              <div className="space-y-2">
                <div className="font-medium text-sm flex items-center justify-between">
                  <span>未结清采购单</span>
                  <span className="text-xs text-muted-foreground">{(unsettledPurchases || []).length} 笔</span>
                </div>
                <div className="border rounded-md max-h-[200px] overflow-y-auto">
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

              {/* 预览区域 */}
              <div className="bg-muted/30 rounded-lg p-3">
                <div className="grid grid-cols-3 gap-4 text-sm text-center">
                  <div>
                    <div className="text-xs text-muted-foreground">选中销售待收</div>
                    <div className="font-medium text-red-600">{fmt$(preview.saleTotal)}</div>
                    <div className="text-xs text-muted-foreground">{preview.saleCount} 笔</div>
                  </div>
                  <div>
                    <div className="text-xs text-muted-foreground">选中采购待付</div>
                    <div className="font-medium text-green-600">{fmt$(preview.purchaseTotal)}</div>
                    <div className="text-xs text-muted-foreground">{preview.purchaseCount} 笔</div>
                  </div>
                  <div>
                    <div className="text-xs text-muted-foreground">差额</div>
                    <div className="font-bold text-lg text-blue-600">{fmt$(preview.diff)}</div>
                  </div>
                </div>
              </div>

              {/* 金额和银行 */}
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <Label className="text-xs text-muted-foreground">实付金额</Label>
                  <Input
                    type="number"
                    step="0.01"
                    value={actualAmount}
                    onChange={(e) => handleActualAmountChange(e.target.value)}
                    className="mt-1"
                  />
                </div>
                <div>
                  <Label className="text-xs text-muted-foreground">抹零金额</Label>
                  <Input
                    type="number"
                    step="0.01"
                    value={roundingAmount}
                    onChange={(e) => {
                      const rounding = Math.max(0, Number(e.target.value || 0));
                      setRoundingAmount(rounding.toFixed(2));
                      const newActual = preview.diff - rounding;
                      setActualAmount(newActual.toFixed(2));
                    }}
                    className="mt-1"
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <Label className="text-xs text-muted-foreground">付款日期</Label>
                  <Input
                    type="date"
                    value={transactionDate}
                    onChange={(e) => setTransactionDate(e.target.value)}
                    className="mt-1"
                  />
                </div>
                <div>
                  <Label className="text-xs text-muted-foreground">银行账号</Label>
                  <select
                    value={selectedBankAccountId}
                    onChange={(e) => setSelectedBankAccountId(e.target.value)}
                    className="w-full mt-1 px-3 py-2 border rounded-md text-sm"
                  >
                    <option value="">不指定银行账号</option>
                    {(bankAccounts || []).map((acc: any) => (
                      <option key={acc.id} value={acc.id}>
                        {acc.account_name} {acc.bank_name ? `(${acc.bank_name})` : ""}
                      </option>
                    ))}
                  </select>
                </div>
              </div>
            </>
          )}
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>取消</Button>
          <Button
            onClick={handleSubmit}
            disabled={submitting || !selectedCompanyId || Number(actualAmount || 0) <= 0}
            className="bg-blue-600 hover:bg-blue-700"
          >
            {submitting ? <Loader2 className="h-4 w-4 animate-spin mr-1" /> : null}
            确认生成对冲结算
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
