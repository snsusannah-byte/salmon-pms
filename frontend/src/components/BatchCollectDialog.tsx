import React, { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter,
} from "@/components/ui/dialog";
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from "@/components/ui/select";
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";
import { Banknote, Loader2 } from "lucide-react";
import { toast } from "sonner";

interface Sale {
  id: number;
  sale_no: string;
  customer_name?: string | null;
  net_amount: number;
  paid_amount: number;
}

interface BankAccount {
  id: number;
  account_name: string;
  bank_name: string;
}

interface BatchCollectDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  sales: Sale[];
}

export function BatchCollectDialog({ open, onOpenChange, sales }: BatchCollectDialogProps) {
  const queryClient = useQueryClient();
  const [bankAccountId, setBankAccountId] = useState("");
  const [collectDate, setCollectDate] = useState(() => new Date().toISOString().split("T")[0]);
  const [collectAmount, setCollectAmount] = useState("");

  const { data: bankAccounts } = useQuery({
    queryKey: ["bank-accounts"],
    queryFn: async () => {
      const res = await api.get("/v1/finance/bank-accounts?limit=100");
      // API 返回数组，不是 {items: [...]}
      return Array.isArray(res.data) ? res.data : (res.data?.items || []);
    },
    enabled: open,
  });

  const collectMutation = useMutation({
    mutationFn: async () => {
      const saleIds = sales.map((s) => s.id);
      const payload: any = {
        sale_ids: saleIds,
        bank_account_id: Number(bankAccountId),
        collect_date: collectDate,
      };
      const amt = Number(collectAmount);
      if (amt > 0 && amt !== totalAmount) {
        payload.amount = amt;
      }
      const res = await api.post("/v1/sales/whole-fish/batch-collect", payload);
      return res.data;
    },
    onSuccess: (data) => {
      toast.success(`合并收款成功，总金额 ¥${data.total_amount?.toLocaleString("zh-CN") || ""}`);
      onOpenChange(false);
      // 修正缓存失效 key，匹配 SalesPage 中的 queryKey
      queryClient.invalidateQueries({ queryKey: ["sales"] });
      queryClient.invalidateQueries({ queryKey: ["sales-all"] });
      queryClient.invalidateQueries({ queryKey: ["customer-receivables"] });
      queryClient.invalidateQueries({ queryKey: ["finance-summary"] });
      queryClient.invalidateQueries({ queryKey: ["transactions"] });
    },
    onError: (err: any) => {
      toast.error(err.response?.data?.detail || "合并收款失败");
    },
  });

  // 计算各销售单应收金额
  const saleDetails = sales.map((sale) => {
    const receivable = Math.max(0, Number(sale.net_amount) - Number(sale.paid_amount));
    return { ...sale, receivable };
  });

  const totalAmount = saleDetails.reduce((sum, s) => sum + s.receivable, 0);

  // 弹窗打开时重置/同步 collectAmount
  React.useEffect(() => {
    if (open) {
      setCollectAmount(totalAmount > 0 ? totalAmount.toFixed(2) : "");
      setBankAccountId("");
    }
  }, [open, totalAmount]);

  const handleSubmit = () => {
    if (!bankAccountId) {
      toast.error("请选择收款账户");
      return;
    }
    const amt = Number(collectAmount);
    if (!amt || amt <= 0) {
      toast.error("收款金额必须大于0");
      return;
    }
    collectMutation.mutate();
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-lg">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Banknote className="h-5 w-5 text-green-600" />
            合并收款
          </DialogTitle>
        </DialogHeader>

        <div className="space-y-4">
          {/* 选中销售单列表 */}
          <div className="border rounded-md">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>销售单号</TableHead>
                  <TableHead>客户</TableHead>
                  <TableHead className="text-right">净金额</TableHead>
                  <TableHead className="text-right">已收</TableHead>
                  <TableHead className="text-right">本次应收</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {saleDetails.map((sale) => (
                  <TableRow key={sale.id}>
                    <TableCell className="font-medium">{sale.sale_no}</TableCell>
                    <TableCell>{sale.customer_name || "-"}</TableCell>
                    <TableCell className="text-right">¥{Number(sale.net_amount).toLocaleString("zh-CN", { minimumFractionDigits: 2 })}</TableCell>
                    <TableCell className="text-right text-green-600">¥{Number(sale.paid_amount).toLocaleString("zh-CN", { minimumFractionDigits: 2 })}</TableCell>
                    <TableCell className="text-right font-medium">
                      {sale.receivable > 0 ? (
                        <span className="text-blue-600">¥{sale.receivable.toLocaleString("zh-CN", { minimumFractionDigits: 2 })}</span>
                      ) : (
                        <Badge variant="secondary">已收齐</Badge>
                      )}
                    </TableCell>
                  </TableRow>
                ))}
                <TableRow className="bg-muted/50 font-medium">
                  <TableCell colSpan={4} className="text-right">合计应收:</TableCell>
                  <TableCell className="text-right text-lg font-bold text-green-700">
                    ¥{totalAmount.toLocaleString("zh-CN", { minimumFractionDigits: 2 })}
                  </TableCell>
                </TableRow>
              </TableBody>
            </Table>
          </div>

          {/* 收款信息 */}
          <div className="space-y-3">
            <div className="space-y-2">
              <Label>收款账户 *</Label>
              <Select value={bankAccountId} onValueChange={setBankAccountId}>
                <SelectTrigger>
                  <SelectValue placeholder="选择银行账户" />
                </SelectTrigger>
                <SelectContent>
                  {bankAccounts?.map((acc: BankAccount) => (
                    <SelectItem key={acc.id} value={String(acc.id)}>
                      {acc.bank_name} - {acc.account_name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-2">
              <Label>本次实收金额</Label>
              <Input
                type="number"
                step="0.01"
                value={collectAmount}
                onChange={(e) => setCollectAmount(e.target.value)}
                placeholder={`应收合计 ¥${totalAmount.toLocaleString("zh-CN", { minimumFractionDigits: 2 })}`}
                className="text-lg font-medium"
              />
              {Number(collectAmount) !== totalAmount && (
                <div className="text-xs space-y-1">
                  {Number(collectAmount) < totalAmount && (
                    <p className="text-orange-600">
                      本次少收 ¥{(totalAmount - Number(collectAmount)).toLocaleString("zh-CN", { minimumFractionDigits: 2 })}，剩余应收将留待下次收取
                    </p>
                  )}
                  {Number(collectAmount) > totalAmount && (
                    <p className="text-blue-600">
                      本次多收 ¥{(Number(collectAmount) - totalAmount).toLocaleString("zh-CN", { minimumFractionDigits: 2 })}，超出部分将优先填入较早的销售单
                    </p>
                  )}
                </div>
              )}
            </div>

            <div className="space-y-2">
              <Label>收款日期</Label>
              <Input
                type="date"
                value={collectDate}
                onChange={(e) => setCollectDate(e.target.value)}
              />
            </div>
          </div>
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            取消
          </Button>
          <Button
            onClick={handleSubmit}
            disabled={collectMutation.isPending || !bankAccountId || Number(collectAmount) <= 0}
          >
            {collectMutation.isPending && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
            确认收款 ¥{Number(collectAmount || 0).toLocaleString("zh-CN", { minimumFractionDigits: 2 })}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
