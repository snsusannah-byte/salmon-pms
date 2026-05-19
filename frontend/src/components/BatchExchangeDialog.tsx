import { useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { toast } from "sonner";
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Checkbox } from "@/components/ui/checkbox";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { DollarSign, CheckCircle } from "lucide-react";

const fmtUSD = (v?: number | string | null) =>
  v != null ? `$${Number(v).toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}` : "-";

const fmt = (v?: number | string | null) =>
  v != null ? `¥${Number(v).toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}` : "-";

interface Invoice {
  id: number;
  invoice_no: string;
  total_amount_usd: number | string;
  batch_id?: number;
  batch_code?: string;
  batch_name?: string;
  exchange_status?: string;
}

interface BatchExchangeDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export function BatchExchangeDialog({ open, onOpenChange }: BatchExchangeDialogProps) {
  const queryClient = useQueryClient();
  const [selectedIds, setSelectedIds] = useState<Set<number>>(new Set());
  const [exchangeDate, setExchangeDate] = useState("");
  const [amountUsd, setAmountUsd] = useState("");
  const [exchangeRate, setExchangeRate] = useState("");
  const [amountCny, setAmountCny] = useState("");
  const [feeCny, setFeeCny] = useState("");

  // 获取所有未购汇/部分购汇的发票
  const { data: invoicesData, isLoading } = useQuery<Invoice[]>({
    queryKey: ["invoices-for-exchange"],
    queryFn: async () => {
      const res = await api.get("/v1/invoices?limit=500&exchange_status=not_exchanged,partial");
      return res.data?.items || [];
    },
    enabled: open,
  });

  const invoices = invoicesData || [];

  // 自动计算 CNY
  const autoCalcCny = () => {
    const usd = parseFloat(amountUsd) || 0;
    const rate = parseFloat(exchangeRate) || 0;
    if (usd && rate) {
      setAmountCny(String(Number((usd * rate).toFixed(2))));
    }
  };

  // 选中/取消选中发票
  const toggleInvoice = (id: number) => {
    const next = new Set(selectedIds);
    if (next.has(id)) {
      next.delete(id);
    } else {
      next.add(id);
    }
    setSelectedIds(next);

    // 自动计算选中合计
    const selectedInvoices = invoices.filter((inv) => next.has(inv.id));
    const total = selectedInvoices.reduce((sum, inv) => sum + Number(inv.total_amount_usd || 0), 0);
    setAmountUsd(String(Number(total.toFixed(2))));
    autoCalcCny();
  };

  // 全选/取消全选
  const toggleAll = () => {
    if (selectedIds.size === invoices.length) {
      setSelectedIds(new Set());
      setAmountUsd("");
    } else {
      const allIds = new Set(invoices.map((inv) => inv.id));
      setSelectedIds(allIds);
      const total = invoices.reduce((sum, inv) => sum + Number(inv.total_amount_usd || 0), 0);
      setAmountUsd(String(Number(total.toFixed(2))));
    }
    autoCalcCny();
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (selectedIds.size === 0) {
      toast.error("请至少选择一张发票");
      return;
    }
    if (!exchangeDate) {
      toast.error("请选择购汇日期");
      return;
    }
    if (!amountUsd || Number(amountUsd) <= 0) {
      toast.error("请输入购汇金额");
      return;
    }
    try {
      await api.post("/v1/finance/exchange", {
        related_invoice_ids: Array.from(selectedIds),
        exchange_date: exchangeDate,
        amount_usd: Number(amountUsd),
        exchange_rate: Number(exchangeRate),
        amount_cny: Number(amountCny),
        fee_cny: Number(feeCny) || 0,
        bank_account_id: null,
      });
      toast.success(`合并购汇成功，共 ${selectedIds.size} 张发票`);
      queryClient.invalidateQueries({ queryKey: ["exchange-records"] });
      queryClient.invalidateQueries({ queryKey: ["finance-summary"] });
      queryClient.invalidateQueries({ queryKey: ["invoices"] });
      queryClient.invalidateQueries({ queryKey: ["invoices-for-exchange"] });
      onOpenChange(false);
      setSelectedIds(new Set());
      setExchangeDate("");
      setAmountUsd("");
      setExchangeRate("");
      setAmountCny("");
      setFeeCny("");
    } catch (error: any) {
      toast.error(error.response?.data?.detail ?? "创建失败");
    }
  };

  // 选中发票合计
  const selectedInvoices = invoices.filter((inv) => selectedIds.has(inv.id));
  const selectedTotalUSD = selectedInvoices.reduce((sum, inv) => sum + Number(inv.total_amount_usd || 0), 0);

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-[720px] max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <DollarSign className="w-5 h-5" />
            合并购汇登记
          </DialogTitle>
        </DialogHeader>

        <form onSubmit={handleSubmit} className="space-y-5 py-2">
          {/* 发票多选列表 */}
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <Label className="text-sm font-medium">
                选择发票 <span className="text-red-500">*</span>
              </Label>
              <div className="flex items-center gap-3 text-xs text-muted-foreground">
                <span>已选 {selectedIds.size} 张</span>
                <button
                  type="button"
                  className="text-blue-600 hover:underline"
                  onClick={toggleAll}
                >
                  {selectedIds.size === invoices.length ? "取消全选" : "全选"}
                </button>
              </div>
            </div>

            {isLoading ? (
              <div className="text-sm text-muted-foreground py-4 text-center">加载中...</div>
            ) : invoices.length === 0 ? (
              <div className="text-sm text-muted-foreground py-4 text-center">暂无未购汇发票</div>
            ) : (
              <div className="border rounded-lg divide-y max-h-[300px] overflow-y-auto">
                {invoices.map((inv) => (
                  <div
                    key={inv.id}
                    className="flex items-center gap-3 px-3 py-2 hover:bg-muted/50 cursor-pointer"
                    onClick={() => toggleInvoice(inv.id)}
                  >
                    <Checkbox
                      checked={selectedIds.has(inv.id)}
                      onCheckedChange={() => toggleInvoice(inv.id)}
                    />
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 text-sm">
                        <span className="font-mono font-medium">{inv.invoice_no}</span>
                        <Badge variant="outline" className="text-xs">
                          {inv.batch_code || inv.batch_id || "—"}
                        </Badge>
                        {inv.batch_name && (
                          <span className="text-xs text-muted-foreground truncate">{inv.batch_name}</span>
                        )}
                      </div>
                    </div>
                    <div className="text-sm font-medium text-right whitespace-nowrap">
                      {fmtUSD(inv.total_amount_usd)}
                    </div>
                  </div>
                ))}
              </div>
            )}

            {selectedIds.size > 0 && (
              <Card className="bg-blue-50 border-blue-100">
                <CardContent className="p-3 text-sm">
                  <div className="flex justify-between items-center">
                    <span className="text-blue-700">选中发票合计 (USD)</span>
                    <span className="font-bold text-blue-600">{fmtUSD(selectedTotalUSD)}</span>
                  </div>
                </CardContent>
              </Card>
            )}
          </div>

          {/* 金额与汇率 */}
          <div className="grid grid-cols-[1fr_1fr_140px] gap-4">
            <div className="grid gap-2">
              <Label className="text-sm">USD金额</Label>
              <Input
                type="number"
                value={amountUsd}
                onChange={(e) => { setAmountUsd(e.target.value); autoCalcCny(); }}
                step="0.01"
                className="text-base"
              />
            </div>
            <div className="grid gap-2">
              <Label className="text-sm">汇率</Label>
              <Input
                type="number"
                value={exchangeRate}
                onChange={(e) => { setExchangeRate(e.target.value); autoCalcCny(); }}
                step="0.0001"
                placeholder="如 7.2345"
                className="text-base"
              />
            </div>
            <div className="grid gap-2">
              <Label className="text-sm">
                购汇日期 <span className="text-red-500">*</span>
              </Label>
              <Input
                type="date"
                value={exchangeDate}
                onChange={(e) => setExchangeDate(e.target.value)}
                className="text-base"
              />
            </div>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div className="grid gap-2">
              <Label className="text-sm text-muted-foreground">CNY金额（自动计算）</Label>
              <Input
                type="number"
                value={amountCny}
                onChange={(e) => setAmountCny(e.target.value)}
                step="0.01"
                className="bg-muted"
              />
            </div>
            <div className="grid gap-2">
              <Label className="text-sm">手续费 (¥)</Label>
              <Input
                type="number"
                value={feeCny}
                onChange={(e) => setFeeCny(e.target.value)}
                step="0.01"
                placeholder="0"
              />
            </div>
          </div>

          <div className="bg-muted p-3 rounded text-sm flex justify-between font-semibold">
            <span>购汇合计 (CNY)</span>
            <span>{fmt((parseFloat(amountCny) || 0) + (parseFloat(feeCny) || 0))}</span>
          </div>

          <DialogFooter>
            <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>
              取消
            </Button>
            <Button type="submit" disabled={selectedIds.size === 0}>
              <CheckCircle className="w-4 h-4 mr-1" />
              保存合并购汇
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
