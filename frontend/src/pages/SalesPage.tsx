
import React, { useState, useRef, useEffect } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from "@/components/ui/table";
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter, DialogDescription,
} from "@/components/ui/dialog";
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from "@/components/ui/select";
import { Badge } from "@/components/ui/badge";
import { Checkbox } from "@/components/ui/checkbox";
import { Card, CardContent } from "@/components/ui/card";
import {
  Plus, Search, Eye, Pencil, Trash2, X, DollarSign, Receipt, AlertTriangle, Trash, Lock, Unlock, Banknote, SlidersHorizontal,
} from "lucide-react";
import { toast } from "sonner";
import { BatchImportButton } from "@/components/BatchImportButton";

const statusMap: Record<string, { label: string; color: string }> = {
  pending: { label: "待收款", color: "bg-red-100 text-red-800" },
  partial_paid: { label: "部分收款", color: "bg-yellow-100 text-yellow-800" },
  fully_paid: { label: "全部收款", color: "bg-green-100 text-green-800" },
  after_sales: { label: "售后中", color: "bg-purple-100 text-purple-800" },
};

interface WholeFishSaleItem {
  id?: number;
  sale_id?: number;
  spec: string;
  box_count: number;
  weight_kg: string;
  unit_price: string;
  amount: string;
}

interface Sale {
  id: number;
  sale_no: string | null;
  batch_id: number;
  batch_name: string | null;
  batch_code: string | null;
  sale_date: string;
  customer_id: number;
  customer_name: string | null;
  spec: string | null;
  box_count: number | null;
  weight_kg: string;
  unit_price: string;
  gross_amount: string;
  scan_fee: string;
  rounding_adjustment: string;
  after_sales_adjustment: string;
  discount: string;
  commission: string;
  net_amount: string;
  paid_amount: string;
  status: string;
  salesperson_id: number | null;
  salesperson_name: string | null;
  notes: string | null;
  is_locked: boolean;
  receipts: Receipt[];
  aftersales: Aftersales[];
  items?: WholeFishSaleItem[];
}

interface Receipt {
  id: number;
  sale_id: number;
  receipt_date: string;
  amount: string;
  payment_method: string;
  bank_account_id?: number | null;
  reference_no: string | null;
  notes: string | null;
  transaction_id?: number | null;
}

interface Aftersales {
  id: number;
  sale_id: number;
  record_date: string;
  type: string;
  amount: string;
  reason: string | null;
  status: string;
  notes: string | null;
}

interface SaleListResponse {
  total: number;
  items: Sale[];
  skip: number;
  limit: number;
}

const PAGE_SIZE = 30;

// ==================== 页面主组件 ====================

export function SalesPage() {
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState<string>("all");
  const [page, setPage] = useState(1);
  const [formOpen, setFormOpen] = useState(false);
  const [editingSale, setEditingSale] = useState<Sale | null>(null);
  const [detailOpen, setDetailOpen] = useState(false);
  const [detailSale, setDetailSale] = useState<Sale | null>(null);
  const [selectedIds, setSelectedIds] = useState<Set<number>>(new Set());
  const [batchDeleteDialogOpen, setBatchDeleteDialogOpen] = useState(false);
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [deleteSale, setDeleteSale] = useState<Sale | null>(null);
  const [deleteMutationPending, setDeleteMutationPending] = useState(false);
  const [adjustDialogOpen, setAdjustDialogOpen] = useState(false);
  const [adjustSale, setAdjustSale] = useState<Sale | null>(null);
  const [receiptSale, setReceiptSale] = useState<Sale | null>(null);
  const [receiptDialogOpen, setReceiptDialogOpen] = useState(false);
  const [receiptAmount, setReceiptAmount] = useState("");
  const [receiptRounding, setReceiptRounding] = useState("0");
  const [receiptBankAccountId, setReceiptBankAccountId] = useState("");
  const [receiptDate, setReceiptDate] = useState(new Date().toISOString().split("T")[0]);
  const [receiptDescription, setReceiptDescription] = useState("");
  const [adjRounding, setAdjRounding] = useState("0");
  const [adjAfterSales, setAdjAfterSales] = useState("0");
  const [adjAfterSalesIssue, setAdjAfterSalesIssue] = useState("");
  const [adjDiscount, setAdjDiscount] = useState("0");
  const [adjCommission, setAdjCommission] = useState("0");
  const [adjCommissionType, setAdjCommissionType] = useState<"fixed" | "per_kg">("fixed");
  const [adjPaidAmount, setAdjPaidAmount] = useState("0");
  const queryClient = useQueryClient();

  const { data, isLoading } = useQuery<SaleListResponse>({
    queryKey: ["sales", statusFilter, page, search],
    queryFn: async () => {
      const params = new URLSearchParams();
      if (statusFilter && statusFilter !== "all") params.append("status", statusFilter);
      if (search.trim()) params.append("search", search.trim());
      params.append("skip", String((page - 1) * PAGE_SIZE));
      params.append("limit", String(PAGE_SIZE));
      const res = await api.get(`/v1/sales/whole-fish?${params.toString()}`);
      return res.data;
    },
  });

  const totalPages = data ? Math.ceil(data.total / PAGE_SIZE) : 0;

  // 全局汇总查询（不分页，获取所有匹配数据）
  const { data: allSalesData } = useQuery<SaleListResponse>({
    queryKey: ["sales-all", statusFilter, search],
    queryFn: async () => {
      const params = new URLSearchParams();
      if (statusFilter && statusFilter !== "all") params.append("status", statusFilter);
      if (search.trim()) params.append("search", search.trim());
      params.append("skip", "0");
      params.append("limit", "500");
      const res = await api.get(`/v1/sales/whole-fish?${params.toString()}`);
      return res.data;
    },
    enabled: data !== undefined, // 等分页数据加载后再加载汇总
  });

  const summary = {
    totalCount: allSalesData?.items?.length || 0,
    totalBoxes: allSalesData?.items?.reduce((sum, s) => sum + Number(s.box_count || 0), 0) || 0,
    totalWeight: allSalesData?.items?.reduce((sum, s) => sum + Number(s.weight_kg || 0), 0) || 0,
    totalNetAmount: allSalesData?.items?.reduce((sum, s) => sum + Number(s.net_amount || 0), 0) || 0,
    totalPaid: allSalesData?.items?.reduce((sum, s) => sum + Number(s.paid_amount || 0), 0) || 0,
    totalUnpaid: allSalesData?.items?.reduce((sum, s) => sum + (Number(s.net_amount || 0) - Number(s.paid_amount || 0)), 0) || 0,
    totalAfterSales: allSalesData?.items?.reduce((sum, s) => sum + Number(s.after_sales_adjustment || 0), 0) || 0,
  };

  const toggleSelectAll = () => {
    if (!data?.items) return;
    if (selectedIds.size === data.items.length) {
      setSelectedIds(new Set());
    } else {
      setSelectedIds(new Set(data.items.map((s) => s.id)));
    }
  };

  const toggleSelect = (id: number, checked: boolean | "indeterminate") => {
    if (checked === "indeterminate") return;
    const newSet = new Set(selectedIds);
    if (checked) newSet.add(id);
    else newSet.delete(id);
    setSelectedIds(newSet);
  };

  const batchDeleteMutation = useMutation({
    mutationFn: async (ids: number[]) => {
      const res = await api.post("/v1/sales/whole-fish/batch-delete", { ids });
      return res.data;
    },
    onSuccess: (result: any) => {
      toast.success(`批量删除成功：删除 ${result.deleted || 0} 条`);
      queryClient.invalidateQueries({ queryKey: ["sales"] });
      setSelectedIds(new Set());
      setBatchDeleteDialogOpen(false);
    },
    onError: (err: any) => toast.error(err.response?.data?.detail || "批量删除失败"),
  });

  const handleBatchUnlock = async () => {
    if (selectedIds.size === 0) { toast.error("请先选择要解锁的记录"); return; }
    try {
      const ids = Array.from(selectedIds);
      const res = await api.post("/v1/sales/whole-fish/batch-unlock", { ids });
      toast.success(`批量解锁成功：${res.data.unlocked || 0} 条已解锁，${res.data.skipped || 0} 条跳过`);
      queryClient.invalidateQueries({ queryKey: ["sales"] });
      setSelectedIds(new Set());
    } catch (err: any) {
      toast.error(err.response?.data?.detail || "批量解锁失败");
    }
  };

  const handleBatchDelete = () => {
    if (selectedIds.size === 0) { toast.error("请先选择要删除的记录"); return; }
    setBatchDeleteDialogOpen(true);
  };

  const handleBatchLock = async () => {
    if (selectedIds.size === 0) { toast.error("请先选择要锁定的记录"); return; }
    try {
      const ids = Array.from(selectedIds);
      const res = await api.post("/v1/sales/whole-fish/batch-lock", { ids });
      toast.success(`批量锁定成功：${res.data.locked || 0} 条已锁定，${res.data.skipped || 0} 条跳过`);
      queryClient.invalidateQueries({ queryKey: ["sales"] });
      setSelectedIds(new Set());
    } catch (err: any) {
      toast.error(err.response?.data?.detail || "批量锁定失败");
    }
  };

  const handleDelete = async (sale: Sale) => {
    if (sale.is_locked) { toast.error("销售记录已锁定，不能删除"); return; }
    setDeleteSale(sale);
    setDeleteDialogOpen(true);
  };

  const handleLockToggle = async (sale: Sale) => {
    try {
      if (sale.is_locked) {
        await api.post(`/v1/sales/whole-fish/${sale.id}/unlock`);
        toast.success("销售记录已解锁");
      } else {
        await api.post(`/v1/sales/whole-fish/${sale.id}/lock`);
        toast.success("销售记录已锁定");
      }
      queryClient.invalidateQueries({ queryKey: ["sales"] });
    } catch (err: any) {
      toast.error(err.response?.data?.detail || "操作失败");
    }
  };

  const confirmDelete = async () => {
    if (!deleteSale) return;
    setDeleteMutationPending(true);
    try {
      await api.delete(`/v1/sales/whole-fish/${deleteSale.id}`);
      toast.success("销售记录已删除");
      queryClient.invalidateQueries({ queryKey: ["sales"] });
      setDeleteDialogOpen(false);
      setDeleteSale(null);
    } catch (error: any) {
      toast.error(error.response?.data?.detail ?? "删除失败");
    } finally {
      setDeleteMutationPending(false);
    }
  };

  const [adjBankAccountId, setAdjBankAccountId] = useState("");
  const [adjReceiptDate, setAdjReceiptDate] = useState("");

  // 银行账户列表
  const { data: bankAccountsData } = useQuery({
    queryKey: ["bank-accounts"],
    queryFn: async () => {
      const res = await api.get("/v1/finance/bank-accounts");
      return res.data;
    },
  });
  const bankAccounts = bankAccountsData || [];

  const handleOpenAdjust = (sale: Sale) => {
    if (sale.is_locked) { toast.error("销售记录已锁定，不能调整"); return; }
    setAdjustSale(sale);
    const afterSales = String(sale.after_sales_adjustment ?? 0);
    const discount = String(sale.discount ?? 0);
    setAdjAfterSales(afterSales);
    setAdjAfterSalesIssue(sale.notes ?? "");
    setAdjDiscount(discount);
    setAdjRounding(String(sale.rounding_adjustment ?? 0));
    setAdjCommission(String(sale.commission ?? 0));
    setAdjBankAccountId("");
    setAdjReceiptDate(new Date().toISOString().split("T")[0]);
    setAdjustDialogOpen(true);
  };

  const openReceipt = (sale: Sale) => {
    if (sale.is_locked) { toast.error("销售记录已锁定，不能收款"); return; }
    setReceiptSale(sale);
    const receivable = Math.max(0, Number(sale.net_amount || 0) - Number(sale.paid_amount || 0));
    setReceiptAmount(receivable > 0 ? receivable.toFixed(2) : "");
    setReceiptRounding("0"); // 默认抹零为0（实收=应收）
    setReceiptBankAccountId("");
    setReceiptDate(new Date().toISOString().split("T")[0]);
    setReceiptDescription("");
    setReceiptDialogOpen(true);
  };

  // 当实收金额变化时，实时计算抹零 = 应收 - 实收
  const handleReceiptAmountChange = (value: string) => {
    setReceiptAmount(value);
    if (!receiptSale) return;
    const receivable = Math.max(0, Number(receiptSale.net_amount || 0) - Number(receiptSale.paid_amount || 0));
    const actual = Number(value) || 0;
    const rounding = Math.max(0, receivable - actual);
    setReceiptRounding(rounding > 0 ? rounding.toFixed(2) : "0");
  };

  const handleSaveReceipt = async () => {
    if (!receiptSale) return;
    const amount = Number(receiptAmount);
    if (amount <= 0) {
      toast.error("收款金额必须大于0");
      return;
    }
    // 收款金额允许略大于应收（实际业务中客户可能凑整多转）
    const receivable = Math.max(0, Number(receiptSale.net_amount || 0) - Number(receiptSale.paid_amount || 0));
    if (amount > receivable) {
      // 多收场景：仅做提示，不拦截
      console.log(`本次实收 ¥${amount.toFixed(2)} 超过应收余额 ¥${receivable.toFixed(2)}，多收 ¥${(amount - receivable).toFixed(2)}`);
    }
    try {
      // 收款时传 rounding_adjustment（用户手动控制抹零）
      await api.post(`/v1/sales/whole-fish/${receiptSale.id}/receipts`, {
        receipt_date: receiptDate,
        amount: amount,
        payment_method: "bank_transfer",
        bank_account_id: receiptBankAccountId ? Number(receiptBankAccountId) : null,
        rounding_adjustment: Number(receiptRounding || 0),
        notes: receiptDescription.trim() || undefined,
      });
      toast.success("收款成功");
      queryClient.invalidateQueries({ queryKey: ["sales"] });
      setReceiptDialogOpen(false);
      setReceiptSale(null);
    } catch (err: any) {
      toast.error(err.response?.data?.detail || "收款失败");
    }
  };

  const adjustMutation = useMutation({
    mutationFn: async ({ id, body }: { id: number; body: any }) => {
      const res = await api.put(`/v1/sales/whole-fish/${id}`, body);
      return res.data;
    },
    onSuccess: () => {
      toast.success("调整已保存");
      queryClient.invalidateQueries({ queryKey: ["sales"] });
      setAdjustDialogOpen(false);
      setAdjustSale(null);
    },
    onError: (err: any) => toast.error(err.response?.data?.detail || "调整失败"),
  });

  const handleSaveAdjust = async () => {
    if (!adjustSale) return;

    try {
      // 保存所有调整项
      await api.put(`/v1/sales/whole-fish/${adjustSale.id}`, {
        after_sales_adjustment: Number(adjAfterSales || 0),
        discount: Number(adjDiscount || 0),
        rounding_adjustment: Number(adjRounding || 0),
        commission: Number(adjCommission || 0),
        notes: adjAfterSalesIssue.trim() || undefined,
      });

      toast.success("调整已保存");
      queryClient.invalidateQueries({ queryKey: ["sales"] });
      setAdjustDialogOpen(false);
      setAdjustSale(null);
    } catch (err: any) {
      toast.error(err.response?.data?.detail || "调整失败");
    }
  };

  return (
    <div className="space-y-6">
      <SaleFormDialog open={formOpen} onOpenChange={setFormOpen} initialData={editingSale}
        onSuccess={() => { queryClient.invalidateQueries({ queryKey: ["sales"] }); setEditingSale(null); }} />

      {/* 批量删除确认弹窗 */}
      <Dialog open={batchDeleteDialogOpen} onOpenChange={setBatchDeleteDialogOpen}>
        <DialogContent className="max-w-sm">
          <DialogHeader>
            <DialogTitle>确认批量删除</DialogTitle>
          </DialogHeader>
          <p className="text-sm text-muted-foreground">
            确定删除选中的 {selectedIds.size} 条销售记录吗？此操作不可撤销。
          </p>
          <DialogFooter>
            <Button variant="outline" onClick={() => setBatchDeleteDialogOpen(false)}>取消</Button>
            <Button variant="destructive" onClick={() => batchDeleteMutation.mutate(Array.from(selectedIds))} disabled={batchDeleteMutation.isPending}>
              {batchDeleteMutation.isPending ? "删除中..." : "确认删除"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* 单条删除确认弹窗 */}
      <Dialog open={deleteDialogOpen} onOpenChange={setDeleteDialogOpen}>
        <DialogContent className="max-w-sm">
          <DialogHeader>
            <DialogTitle>确认删除</DialogTitle>
          </DialogHeader>
          <p className="text-sm text-muted-foreground">
            确定要删除销售记录 <span className="font-mono font-medium">{deleteSale?.sale_no ?? `#${deleteSale?.id}`}</span> 吗？<br/>客户: {deleteSale?.customer_name ?? "-"}<br/>此操作不可撤销。
          </p>
          <DialogFooter>
            <Button variant="outline" onClick={() => { setDeleteDialogOpen(false); setDeleteSale(null); }}>取消</Button>
            <Button variant="destructive" onClick={confirmDelete} disabled={deleteMutationPending}>
              {deleteMutationPending ? "删除中..." : "确认删除"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* 调整项弹窗 */}
      <Dialog open={adjustDialogOpen} onOpenChange={setAdjustDialogOpen}>
        <DialogContent className="max-w-[480px]">
          <DialogHeader>
            <DialogTitle>🔧 销售调整</DialogTitle>
            <DialogDescription className="text-sm">
              {adjustSale ? `销售单: ${adjustSale.sale_no ?? `#${adjustSale.id}`} · 客户: ${adjustSale.customer_name ?? "-"}` : ""}
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-2">
            {/* 金额明细 */}
            <div className="bg-muted/50 rounded-md p-3 text-sm space-y-1">
              <div className="flex justify-between">
                <span className="text-muted-foreground">销售金额</span>
                <span className="font-medium tabular-nums">¥{adjustSale ? Number(adjustSale.gross_amount).toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 }) : "0"}</span>
              </div>
              {adjustSale && Number(adjustSale.scan_fee) !== 0 && (
                <div className="flex justify-between text-orange-600">
                  <span>扫码手续费</span>
                  <span className="tabular-nums">-¥{Number(adjustSale.scan_fee).toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</span>
                </div>
              )}
              {adjustSale && Number(adjustSale.rounding_adjustment || adjRounding) !== 0 && (
                <div className="flex justify-between text-orange-600">
                  <span>抹零调整</span>
                  <span className="tabular-nums">-¥{Number(adjRounding || adjustSale.rounding_adjustment || 0).toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</span>
                </div>
              )}
              {adjustSale && (Number(adjustSale.after_sales_adjustment || adjAfterSales) !== 0) && (
                <div className="flex justify-between text-orange-600">
                  <span>售后调整</span>
                  <span className="tabular-nums">-¥{Number(adjAfterSales || adjustSale.after_sales_adjustment || 0).toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</span>
                </div>
              )}
              {adjustSale && (Number(adjustSale.discount || adjDiscount) !== 0) && (
                <div className="flex justify-between text-orange-600">
                  <span>折扣</span>
                  <span className="tabular-nums">-¥{Number(adjDiscount || adjustSale.discount || 0).toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</span>
                </div>
              )}
              {adjustSale && (Number(adjustSale.commission || adjCommission) !== 0) && (
                <div className="flex justify-between text-orange-600">
                  <span>提成</span>
                  <span className="tabular-nums">-¥{Number(adjCommission || adjustSale.commission || 0).toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</span>
                </div>
              )}
              <div className="flex justify-between font-semibold border-t border-dashed pt-2 mt-1">
                <span>净金额</span>
                <span className="text-blue-600 tabular-nums">
                  ¥{(() => {
                    if (!adjustSale) return "0.00";
                    const net = Math.max(0, Number(adjustSale.gross_amount || 0) - Number(adjustSale.scan_fee || 0) - Number(adjRounding || adjustSale.rounding_adjustment || 0) - Number(adjAfterSales || adjustSale.after_sales_adjustment || 0) - Number(adjDiscount || adjustSale.discount || 0) - Number(adjCommission || adjustSale.commission || 0));
                    return net.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
                  })()}
                </span>
              </div>
              <div className="flex justify-between text-green-600">
                <span>已收金额</span>
                <span className="tabular-nums">¥{adjustSale ? Number(adjustSale.paid_amount).toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 }) : "0"}</span>
              </div>
              <div className="flex justify-between font-semibold border-t border-dashed pt-2 mt-1">
                <span>未付余额</span>
                <span className={(() => {
                  if (!adjustSale) return "text-gray-400";
                  const net = Math.max(0, Number(adjustSale.gross_amount || 0) - Number(adjustSale.scan_fee || 0) - Number(adjRounding || adjustSale.rounding_adjustment || 0) - Number(adjAfterSales || adjustSale.after_sales_adjustment || 0) - Number(adjDiscount || adjustSale.discount || 0) - Number(adjCommission || adjustSale.commission || 0));
                  const remaining = net - Number(adjustSale.paid_amount || 0);
                  return remaining <= 0 ? "text-green-600" : "text-orange-600";
                })()}>
                  ¥{(() => {
                    if (!adjustSale) return "0.00";
                    const net = Math.max(0, Number(adjustSale.gross_amount || 0) - Number(adjustSale.scan_fee || 0) - Number(adjRounding || adjustSale.rounding_adjustment || 0) - Number(adjAfterSales || adjustSale.after_sales_adjustment || 0) - Number(adjDiscount || adjustSale.discount || 0) - Number(adjCommission || adjustSale.commission || 0));
                    const remaining = Math.max(0, net - Number(adjustSale.paid_amount || 0));
                    return remaining.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
                  })()}
                </span>
              </div>
            </div>

            {/* 调整输入 */}
            <div className="space-y-3">
              <div className="space-y-1">
                <Label className="text-xs">抹零调整 <span className="text-muted-foreground font-normal">（尾差减免）</span></Label>
                <Input inputMode="decimal" value={adjRounding} onChange={(e) => setAdjRounding(e.target.value)} placeholder="0" />
                <p className="text-xs text-muted-foreground">用于减免未付尾差，如 0.94 元直接抹零</p>
              </div>

              <div className="space-y-1">
                <Label className="text-xs">折扣</Label>
                <Input inputMode="decimal" value={adjDiscount} onChange={(e) => setAdjDiscount(e.target.value)} placeholder="0" />
              </div>

              <div className="space-y-1">
                <Label className="text-xs">售后调整</Label>
                <div className="flex gap-2">
                  <Input inputMode="decimal" value={adjAfterSales} onChange={(e) => setAdjAfterSales(e.target.value)} placeholder="0" className="w-32" />
                  <Input value={adjAfterSalesIssue} onChange={(e) => setAdjAfterSalesIssue(e.target.value)} placeholder="售后问题描述" />
                </div>
              </div>

              <div className="space-y-1">
                <Label className="text-xs">提成</Label>
                <Input inputMode="decimal" value={adjCommission} onChange={(e) => setAdjCommission(e.target.value)} placeholder="0" />
              </div>
            </div>

            {/* 调整提示 */}
            {(() => {
              if (!adjustSale) return null;
              const net = Math.max(0, Number(adjustSale.gross_amount || 0) - Number(adjustSale.scan_fee || 0) - Number(adjRounding || 0) - Number(adjAfterSales || 0) - Number(adjDiscount || 0) - Number(adjCommission || 0));
              const remaining = net - Number(adjustSale.paid_amount || 0);
              if (remaining <= 0 && Number(adjustSale.paid_amount || 0) > 0) {
                return (
                  <div className="flex items-center gap-2 text-xs text-green-600 bg-green-50 rounded-md p-2">
                    <span>✓</span>
                    <span>调整后已付清，状态将变为「已结清」</span>
                  </div>
                );
              }
              if (remaining > 0 && Number(adjustSale.paid_amount || 0) > 0) {
                return (
                  <div className="flex items-center gap-2 text-xs text-orange-600 bg-orange-50 rounded-md p-2">
                    <span>⚠</span>
                    <span>调整后仍有未付 ¥{remaining.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}，需继续收款</span>
                  </div>
                );
              }
              return null;
            })()}
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setAdjustDialogOpen(false)}>取消</Button>
            <Button onClick={handleSaveAdjust} disabled={adjustMutation.isPending}>
              {adjustMutation.isPending ? "保存中..." : "保存调整"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* 收款弹窗 */}
      <Dialog open={receiptDialogOpen} onOpenChange={setReceiptDialogOpen}>
        <DialogContent className="max-w-[450px]">
          <DialogHeader>
            <DialogTitle>💰 销售收款</DialogTitle>
            <DialogDescription>
              {receiptSale ? `销售单: ${receiptSale.sale_no ?? `#${receiptSale.id}`} · 客户: ${receiptSale.customer_name ?? "-"}` : ""}
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-2">
            {/* 金额明细 */}
            <div className="bg-muted/50 rounded-md p-3 text-sm space-y-1">
              <div className="flex justify-between">
                <span className="text-muted-foreground">销售金额</span>
                <span className="font-medium tabular-nums">¥{receiptSale ? Number(receiptSale.gross_amount).toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 }) : "0"}</span>
              </div>
              {/* 调整项（有值才显示） */}
              {receiptSale && Number(receiptSale.rounding_adjustment) !== 0 && (
                <div className="flex justify-between text-orange-600">
                  <span>抹零调整</span>
                  <span className="tabular-nums">-¥{Number(receiptSale.rounding_adjustment).toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</span>
                </div>
              )}
              {receiptSale && Number(receiptSale.after_sales_adjustment) !== 0 && (
                <div className="flex justify-between text-orange-600">
                  <span>售后调整</span>
                  <span className="tabular-nums">-¥{Number(receiptSale.after_sales_adjustment).toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</span>
                </div>
              )}
              {receiptSale && Number(receiptSale.discount) !== 0 && (
                <div className="flex justify-between text-orange-600">
                  <span>折扣</span>
                  <span className="tabular-nums">-¥{Number(receiptSale.discount).toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</span>
                </div>
              )}
              {receiptSale && Number(receiptSale.commission) !== 0 && (
                <div className="flex justify-between text-orange-600">
                  <span>提成</span>
                  <span className="tabular-nums">-¥{Number(receiptSale.commission).toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</span>
                </div>
              )}
              {receiptSale && Number(receiptSale.scan_fee) !== 0 && (
                <div className="flex justify-between text-orange-600">
                  <span>扫码手续费</span>
                  <span className="tabular-nums">-¥{Number(receiptSale.scan_fee).toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</span>
                </div>
              )}
              <div className="flex justify-between">
                <span className="text-muted-foreground">已收金额</span>
                <span className="font-medium tabular-nums">¥{receiptSale ? Number(receiptSale.paid_amount).toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 }) : "0"}</span>
              </div>
              <div className="flex justify-between font-semibold border-t border-dashed pt-2 mt-1">
                <span>应收金额</span>
                <span className="text-blue-600 text-base tabular-nums">
                  ¥{receiptSale ? Math.max(0, Number(receiptSale.net_amount) - Number(receiptSale.paid_amount)).toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 }) : "0"}
                </span>
              </div>
            </div>

            <div className="space-y-2">
              <Label>本次实收金额</Label>
              <Input
                inputMode="decimal"
                value={receiptAmount}
                onChange={(e) => handleReceiptAmountChange(e.target.value)}
                placeholder="输入实际收款金额"
                className="text-lg"
              />
            </div>

            <div className="space-y-2">
              <Label className="text-xs">抹零调整</Label>
              <Input
                inputMode="decimal"
                value={receiptRounding}
                onChange={(e) => setReceiptRounding(e.target.value)}
                placeholder="0"
                className="text-sm"
              />
              <p className="text-xs text-muted-foreground">本次收款时减免的尾差金额，默认0</p>
            </div>

            {/* 动态抹零/多收标签 */}
            {(() => {
              if (!receiptSale || !receiptAmount) return null;
              const receivable = Math.max(0, Number(receiptSale.net_amount) - Number(receiptSale.paid_amount));
              const actual = Number(receiptAmount) || 0;
              const rounding = Number(receiptRounding) || 0;
              const diff = receivable - actual - rounding;
              if (diff === 0) {
                return (
                  <div className="flex justify-end items-center mt-1.5 animate-in fade-in slide-in-from-top-1 duration-300">
                    <span className="text-xs text-green-600 font-medium">已付清 ✓</span>
                  </div>
                );
              }
              if (diff > 0) {
                return (
                  <div className="flex justify-end items-center gap-2 mt-1.5 animate-in fade-in slide-in-from-top-1 duration-300">
                    <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-medium bg-orange-50 text-orange-600 border border-orange-200">
                      未付余额
                    </span>
                    <span className="text-sm font-semibold text-orange-600 tabular-nums">¥{diff.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</span>
                  </div>
                );
              }
              return (
                <div className="flex justify-end items-center gap-2 mt-1.5 animate-in fade-in slide-in-from-top-1 duration-300">
                  <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-medium bg-green-50 text-green-600 border border-green-200">
                    ↑ 多收
                  </span>
                  <span className="text-sm font-semibold text-green-600 tabular-nums">¥{Math.abs(diff).toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</span>
                </div>
              );
            })()}
            {/* 计算公式提示 */}
            {(() => {
              if (!receiptSale || !receiptAmount) return null;
              const receivable = Math.max(0, Number(receiptSale.net_amount) - Number(receiptSale.paid_amount));
              const actual = Number(receiptAmount) || 0;
              const rounding = Number(receiptRounding) || 0;
              const diff = receivable - actual - rounding;
              if (diff === 0) return null;
              return (
                <div className="flex justify-end mt-0.5">
                  <span className="text-xs text-muted-foreground">
                    应收 ¥{receivable.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })} - 实收 ¥{actual.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })} {rounding > 0 ? `- 抹零 ¥${rounding.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}` : ""} = {diff > 0 ? `未付 ¥${diff.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}` : `多收 ¥${Math.abs(diff).toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`}
                  </span>
                </div>
              );
            })()}

            <div className="space-y-1">
              <Label className="text-xs">收款银行</Label>
              <Select value={receiptBankAccountId} onValueChange={(v) => setReceiptBankAccountId(v ?? "")}>
                <SelectTrigger className="h-8 text-xs">
                  <SelectValue placeholder="选择银行">
                    {(() => {
                      const b = bankAccounts.find((ba: any) => String(ba.id) === receiptBankAccountId);
                      return b ? `${b.bank_name} ···${b.account_number?.slice(-4)}` : "选择银行";
                    })()}
                  </SelectValue>
                </SelectTrigger>
                <SelectContent>
                  {bankAccounts.map((b: any) => (
                    <SelectItem key={b.id} value={String(b.id)} className="text-xs">{b.bank_name} ···{b.account_number?.slice(-4)}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-1">
              <Label className="text-xs">收款日期</Label>
              <Input type="date" value={receiptDate} onChange={(e) => setReceiptDate(e.target.value)} className="h-8 text-xs" />
            </div>
            <div className="space-y-1">
              <Label className="text-xs">收款描述</Label>
              <Input
                value={receiptDescription}
                onChange={(e) => setReceiptDescription(e.target.value)}
                placeholder="如：张三转账/微信收款/尾款等"
                className="h-8 text-xs"
              />
              <p className="text-xs text-muted-foreground">描述会同步显示在交易流水中</p>
            </div>

            {/* 本次收款后未付 */}
            <div className="border-t pt-3">
              <div className="flex justify-between items-center">
                <span className="text-sm font-medium">本次收款后未付</span>
                <span className={`text-lg font-bold tabular-nums ${(() => {
                  if (!receiptSale) return "text-gray-400";
                  const remaining = Math.max(0, Number(receiptSale.net_amount) - Number(receiptSale.paid_amount));
                  if (!receiptAmount) {
                    return remaining <= 0 ? "text-green-600" : "text-orange-600";
                  }
                  const actual = Number(receiptAmount) || 0;
                  const rounding = Number(receiptRounding) || 0;
                  const afterPay = Math.max(0, remaining - actual - rounding);
                  return afterPay <= 0 ? "text-green-600" : "text-orange-600";
                })()}`}>
                  ¥{(() => {
                    if (!receiptSale) return "0.00";
                    const remaining = Math.max(0, Number(receiptSale.net_amount) - Number(receiptSale.paid_amount));
                    if (!receiptAmount) {
                      return remaining.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
                    }
                    const actual = Number(receiptAmount) || 0;
                    const rounding = Number(receiptRounding) || 0;
                    const afterPay = Math.max(0, remaining - actual - rounding);
                    return afterPay.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
                  })()}
                </span>
              </div>
              {receiptAmount && Number(receiptAmount) > 0 && (() => {
                const receivable = Math.max(0, Number(receiptSale?.net_amount || 0) - Number(receiptSale?.paid_amount || 0));
                const actual = Number(receiptAmount) || 0;
                const rounding = Number(receiptRounding) || 0;
                const afterPay = receivable - actual - rounding;
                if (afterPay > 0) {
                  return (
                    <div className="flex justify-end mt-1">
                      <span className="text-xs text-muted-foreground">应收 ¥{receivable.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })} - 实收 ¥{actual.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })} - 抹零 ¥{rounding.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })} = 未付 ¥{afterPay.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</span>
                    </div>
                  );
                }
                if (afterPay <= 0) {
                  return (
                    <div className="flex justify-end mt-1">
                      <span className="text-xs text-muted-foreground">应收 ¥{receivable.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })} - 实收 ¥{actual.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })} {rounding > 0 ? `- 抹零 ¥${rounding.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}` : ""} = 已结清</span>
                    </div>
                  );
                }
                return null;
              })()}
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setReceiptDialogOpen(false)}>取消</Button>
            <Button onClick={handleSaveReceipt} className="bg-green-600 hover:bg-green-700">确认收款</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* 详情弹窗 */}
      <Dialog open={detailOpen} onOpenChange={setDetailOpen}>
        <DialogContent className="max-w-[700px] max-h-[90vh] overflow-y-auto">
          <DialogHeader className="pb-4 border-b flex flex-row items-center justify-between">
            <div>
              <DialogTitle>销售详情</DialogTitle>
              <DialogDescription>销售 #{detailSale?.id} · {detailSale?.customer_name}</DialogDescription>
            </div>
            <Button variant="ghost" size="icon" className="h-8 w-8" onClick={() => setDetailOpen(false)}>
              <X className="h-4 w-4" />
            </Button>
          </DialogHeader>
          {detailSale && <SaleDetailDialog sale={detailSale} onClose={() => setDetailOpen(false)} />}
        </DialogContent>
      </Dialog>

      {/* 标题栏 */}
      <div className="flex items-center justify-between">
        <div><h1 className="text-2xl font-bold">整鱼销售</h1><p className="text-sm text-muted-foreground">共 {data?.total ?? 0} 条销售记录</p></div>
        <div className="flex gap-2"><BatchImportButton type="sales" />
          <Button onClick={() => { setEditingSale(null); setFormOpen(true); }}><Plus className="h-4 w-4 mr-2" />新增销售</Button></div>
      </div>

      {/* 筛选栏 */}
      <div className="flex gap-4">
        <div className="relative flex-1 max-w-sm">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <Input placeholder="搜索客户、批次名称、编号..." value={search} onChange={(e) => { setSearch(e.target.value); setPage(1); }} className="pl-9" />
        </div>
        <Select value={statusFilter} onValueChange={(v) => { setStatusFilter(v ?? "all"); setPage(1); }}>
          <SelectTrigger className="w-[160px]">
            <SelectValue>
              {statusFilter === "all" ? "全部状态" : statusMap[statusFilter]?.label || statusFilter}
            </SelectValue>
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">全部状态</SelectItem>
            {Object.entries(statusMap).map(([key, { label }]) => (
              <SelectItem key={key} value={key}>{label}</SelectItem>
            ))}
          </SelectContent>
        </Select>
        {selectedIds.size > 0 && (
          <>
            <Button variant="outline" size="sm" onClick={handleBatchLock}><Lock className="h-4 w-4 mr-1" />批量锁定 ({selectedIds.size})</Button>
            <Button variant="outline" size="sm" onClick={handleBatchUnlock}><Unlock className="h-4 w-4 mr-1" />批量解锁 ({selectedIds.size})</Button>
            <Button variant="destructive" size="sm" onClick={handleBatchDelete}><Trash className="h-4 w-4 mr-1" />批量删除 ({selectedIds.size})</Button>
          </>
        )}
      </div>

      {/* 汇总行 */}
      {data?.items && data.items.length > 0 && (
        <div className="flex flex-wrap gap-2">
          <Card className="flex-shrink-0"><CardContent className="p-2 text-sm whitespace-nowrap"><p className="text-muted-foreground text-xs">记录条数</p><p className="text-xl font-bold">{summary.totalCount.toLocaleString()}</p></CardContent></Card>
          <Card className="flex-shrink-0"><CardContent className="p-2 text-sm whitespace-nowrap"><p className="text-muted-foreground text-xs">总箱数</p><p className="text-xl font-bold">{summary.totalBoxes.toLocaleString()}</p></CardContent></Card>
          <Card className="flex-shrink-0"><CardContent className="p-2 text-sm whitespace-nowrap"><p className="text-muted-foreground text-xs">总重量</p><p className="text-xl font-bold">{summary.totalWeight.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })} kg</p></CardContent></Card>
          <Card className="flex-shrink-0"><CardContent className="p-2 text-sm whitespace-nowrap"><p className="text-muted-foreground text-xs">总销售金额</p><p className="text-xl font-bold">¥{summary.totalNetAmount.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</p></CardContent></Card>
          <Card className="flex-shrink-0"><CardContent className="p-2 text-sm whitespace-nowrap"><p className="text-muted-foreground text-xs">净金额</p><p className="text-xl font-bold text-blue-600">¥{summary.totalNetAmount.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</p></CardContent></Card>
          <Card className="flex-shrink-0"><CardContent className="p-2 text-sm whitespace-nowrap"><p className="text-muted-foreground text-xs">售后金额</p><p className="text-xl font-bold text-red-500">¥{summary.totalAfterSales.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</p></CardContent></Card>
          <Card className="flex-shrink-0"><CardContent className="p-2 text-sm whitespace-nowrap"><p className="text-muted-foreground text-xs">已收金额</p><p className="text-xl font-bold text-green-600">¥{summary.totalPaid.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</p></CardContent></Card>
        </div>
      )}

      {/* 数据表格 */}
      <div className="border rounded-lg">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead className="w-[40px]"><Checkbox checked={data?.items ? selectedIds.size === data.items.length && data.items.length > 0 : false} onCheckedChange={toggleSelectAll} /></TableHead>
              <TableHead>销售单号</TableHead>
              <TableHead>日期</TableHead>
              <TableHead>客户</TableHead>
              <TableHead>业务员</TableHead>
              <TableHead>批次编号</TableHead>
              <TableHead>批次名称</TableHead>
              <TableHead>规格</TableHead>
              <TableHead className="text-right">箱数</TableHead>
              <TableHead className="text-right">重量(kg)</TableHead>
              <TableHead className="text-right">销售金额</TableHead>
              <TableHead className="text-right">净金额</TableHead>
              <TableHead className="text-right">已收</TableHead>
              <TableHead className="text-right">售后</TableHead>
              <TableHead>付款状态</TableHead>
              <TableHead className="w-[120px]">操作</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {isLoading ? <TableRow><TableCell colSpan={16} className="text-center py-8">加载中...</TableCell></TableRow>
             : (data?.items?.length ?? 0) === 0 ? <TableRow><TableCell colSpan={16} className="text-center py-8">暂无数据</TableCell></TableRow>
             : <>
                {data?.items.map((sale) => {
                  const statusInfo = statusMap[sale.status] ?? { label: sale.status, color: "" };
                  const unpaid = Number(sale.net_amount) - Number(sale.paid_amount);
                  return (
                    <TableRow key={sale.id}>
                      <TableCell><Checkbox checked={selectedIds.has(sale.id)} onCheckedChange={(checked) => toggleSelect(sale.id, checked)} /></TableCell>
                      <TableCell className="font-medium relative">
                        {sale.is_locked && <span className="text-orange-500 mr-1">🔒</span>}
                        {sale.sale_no ?? `#${sale.id}`}
                        {sale.aftersales && sale.aftersales.length > 0 && (
                          <span className="ml-1 inline-flex items-center justify-center w-4 h-4 rounded-full bg-red-500 text-white text-[10px] font-bold" title={`售后 ${sale.aftersales.length} 条`}>
                            {sale.aftersales.length}
                          </span>
                        )}
                      </TableCell>
                      <TableCell>{sale.sale_date}</TableCell>
                      <TableCell>{sale.customer_name ?? "-"}</TableCell>
                      <TableCell>{sale.salesperson_name ?? "-"}</TableCell>
                      <TableCell>{sale.batch_code ?? sale.batch_name ?? "-"}</TableCell>
                      <TableCell>{sale.batch_name ?? "-"}</TableCell>
                      <TableCell>{sale.spec ?? "-"}</TableCell>
                      <TableCell className="text-right">{sale.box_count ?? "-"}</TableCell>
                      <TableCell className="text-right">{Number(sale.weight_kg).toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</TableCell>
                      <TableCell className="text-right">¥{Number(sale.gross_amount).toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</TableCell>
                      <TableCell className="text-right">
                        ¥{Number(sale.net_amount).toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                      </TableCell>
                      <TableCell className="text-right text-green-600">¥{Number(sale.paid_amount).toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</TableCell>
                      <TableCell className="text-right">
                        {Number(sale.after_sales_adjustment) > 0 ? (
                          <span className="text-red-500 font-medium">-¥{Number(sale.after_sales_adjustment).toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</span>
                        ) : (
                          <span className="text-muted-foreground">-</span>
                        )}
                      </TableCell>
                      <TableCell><Badge variant="secondary" className={statusInfo.color}>{statusInfo.label}</Badge></TableCell>
                      <TableCell>
                        <div className="flex gap-1">
                          <Button variant="ghost" size="icon" className="h-8 w-8" onClick={() => { setDetailSale(sale); setDetailOpen(true); }}><Eye className="h-4 w-4" /></Button>
                          <Button variant="ghost" size="icon" className="h-8 w-8" onClick={() => { setEditingSale(sale); setFormOpen(true); }} disabled={sale.is_locked}><Pencil className={cn("h-4 w-4", sale.is_locked && "text-muted-foreground")} /></Button>
                          <Button variant="ghost" size="icon" className="h-8 w-8 text-green-600" onClick={() => openReceipt(sale)} title="收款" disabled={sale.is_locked}><Banknote className={cn("h-4 w-4", sale.is_locked && "text-muted-foreground")} /></Button>
                          <Button variant="ghost" size="icon" className="h-8 w-8" onClick={() => handleOpenAdjust(sale)} title="调整" disabled={sale.is_locked}><SlidersHorizontal className={cn("h-4 w-4", sale.is_locked && "text-muted-foreground")} /></Button>
                          <Button variant="ghost" size="icon" className="h-8 w-8" onClick={() => handleLockToggle(sale)} title={sale.is_locked ? "解锁" : "锁定"}>
                            {sale.is_locked ? <Unlock className="h-4 w-4 text-orange-500" /> : <Lock className="h-4 w-4 text-muted-foreground" />}
                          </Button>
                          <Button variant="ghost" size="icon" className="h-8 w-8 text-red-500" onClick={() => handleDelete(sale)} disabled={sale.is_locked}><Trash2 className={cn("h-4 w-4", sale.is_locked && "text-muted-foreground")} /></Button>
                        </div>
                      </TableCell>
                    </TableRow>
                  );
                })}
                {/* 页汇总行 */}
                {data?.items && data.items.length > 0 && (
                  <TableRow className="bg-muted/50 font-medium border-t-2">
                    <TableCell colSpan={8} className="text-right">本页合计:</TableCell>
                    <TableCell className="text-right">
                      {data.items.reduce((s, it) => s + (Number(it.box_count) || 0), 0)}
                    </TableCell>
                    <TableCell className="text-right">
                      {data.items.reduce((s, it) => s + Number(it.weight_kg || 0), 0).toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })} kg
                    </TableCell>
                    <TableCell className="text-right">
                      ¥{data.items.reduce((s, it) => s + Number(it.gross_amount || 0), 0).toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                    </TableCell>
                    <TableCell className="text-right">
                      ¥{data.items.reduce((s, it) => s + Number(it.net_amount || 0), 0).toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                    </TableCell>
                    <TableCell className="text-right text-green-600">
                      ¥{data.items.reduce((s, it) => s + Number(it.paid_amount || 0), 0).toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                    </TableCell>
                    <TableCell className="text-right text-red-500">
                      {(() => {
                        const totalAfterSales = data.items.reduce((s, it) => s + Number(it.after_sales_adjustment || 0), 0);
                        return totalAfterSales > 0 ? `-¥${totalAfterSales.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}` : "-";
                      })()}
                    </TableCell>
                    <TableCell colSpan={2} />
                  </TableRow>
                )}
              </>}
          </TableBody>
        </Table>
      </div>

      {totalPages > 1 && (
        <div className="flex items-center justify-between">
          <div className="text-sm text-muted-foreground">显示 {(page - 1) * PAGE_SIZE + 1} - {Math.min(page * PAGE_SIZE, data?.total ?? 0)} / 共 {data?.total ?? 0} 条</div>
          <div className="flex items-center gap-2">
            <Button variant="outline" size="sm" onClick={() => setPage(page - 1)} disabled={page <= 1}>上一页</Button>
            <span className="text-sm">{page} / {totalPages}</span>
            <Button variant="outline" size="sm" onClick={() => setPage(page + 1)} disabled={page >= totalPages}>下一页</Button>
          </div>
        </div>
      )}
    </div>
  );
}

// ==================== 规格明细行 ====================

interface SpecItem {
  spec: string;
  box_count: string;
  weight_kg: string;
  unit_price: string;
}

// ==================== 销售表单弹窗 ====================

function SaleFormDialog({ open, onOpenChange, initialData, onSuccess }: {
  open: boolean; onOpenChange: (open: boolean) => void; initialData: Sale | null; onSuccess: () => void;
}) {
  const queryClient = useQueryClient();
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [previewSaleNo, setPreviewSaleNo] = useState("");

  const [saleDate, setSaleDate] = useState("");
  const [batchId, setBatchId] = useState("");
  const [customerId, setCustomerId] = useState("");
  const [salespersonId, setSalespersonId] = useState("");
  const [notes, setNotes] = useState("");
  const [specItems, setSpecItems] = useState<SpecItem[]>([{ spec: "", box_count: "", weight_kg: "", unit_price: "" }]);

  React.useEffect(() => {
    if (open && saleDate) {
      const d = new Date(saleDate);
      if (!isNaN(d.getTime())) {
        const prefix = `XS${d.getFullYear()}${String(d.getMonth()+1).padStart(2,"0")}${String(d.getDate()).padStart(2,"0")}`;
        setPreviewSaleNo(`${prefix}-001（预览）`);
      }
    }
  }, [open, saleDate]);

  React.useEffect(() => {
    if (open) resetForm();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open, initialData?.id]);

  const resetForm = () => {
    if (initialData) {
      setSaleDate(initialData.sale_date);
      setBatchId(String(initialData.batch_id));
      setCustomerId(String(initialData.customer_id));
      setSalespersonId(initialData.salesperson_id ? String(initialData.salesperson_id) : "");
      if (initialData.items && initialData.items.length > 0) {
        setSpecItems(initialData.items.map(it => ({
          spec: it.spec ?? "",
          box_count: it.box_count ? String(it.box_count) : "",
          weight_kg: String(it.weight_kg),
          unit_price: String(it.unit_price),
        })));
      } else {
        setSpecItems([{ spec: initialData.spec ?? "", box_count: initialData.box_count ? String(initialData.box_count) : "", weight_kg: String(initialData.weight_kg), unit_price: String(initialData.unit_price) }]);
      }
      setNotes(initialData.notes ?? "");
    } else {
      setSaleDate(new Date().toISOString().split("T")[0]);
      setBatchId(""); setCustomerId(""); setSalespersonId("");
      setSpecItems([{ spec: "", box_count: "", weight_kg: "", unit_price: "" }]);
      setNotes("");
    }
  };

  const { data: batchesData } = useQuery({
    queryKey: ["batches-for-sale"], queryFn: async () => { const res = await api.get("/v1/batches/?status=open&limit=500"); return res.data; }, enabled: open,
  });
  const availableBatches = (batchesData?.items || []).filter((b: any) => (b.remaining_boxes || 0) > 0);
  const { data: customersData } = useQuery({
    queryKey: ["customers-for-sale"], queryFn: async () => { const res = await api.get("/v1/companies/?type=customer&limit=500"); return res.data; }, enabled: open,
  });
  const { data: salespersonsData } = useQuery({
    queryKey: ["salespersons-for-sale"], queryFn: async () => { const res = await api.get("/v1/salespersons/?limit=500"); return res.data; }, enabled: open,
  });
  const { data: importSpecsData } = useQuery({
    queryKey: ["import-specs-for-sale"], queryFn: async () => { const res = await api.get("/v1/products/?categories=WHOLE_FISH,FILLET&limit=500"); return res.data; }, enabled: open,
  });

  const importSpecs = importSpecsData?.items || [];

  const addSpecItem = () => setSpecItems([...specItems, { spec: "", box_count: "", weight_kg: "", unit_price: "" }]);
  const updateSpecItem = (index: number, field: keyof SpecItem, value: string) => {
    const newItems = [...specItems];
    newItems[index] = { ...newItems[index], [field]: value };
    setSpecItems(newItems);
  };
  const removeSpecItem = (index: number) => setSpecItems(specItems.filter((_, i) => i !== index));

  const totalAmount = specItems.reduce((sum, it) => sum + (Number(it.weight_kg) || 0) * (Number(it.unit_price) || 0), 0);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!saleDate || !batchId || !customerId) { toast.error("请填写必填字段"); return; }
    const validItems = specItems.filter(it => it.weight_kg && it.unit_price);
    if (validItems.length === 0) { toast.error("请至少填写一条规格明细"); return; }

    setIsSubmitting(true);
    try {
      const firstItem = validItems[0];
      const totalWeight = validItems.reduce((s, it) => s + (Number(it.weight_kg) || 0), 0);
      const totalGross = validItems.reduce((s, it) => s + (Number(it.weight_kg) || 0) * (Number(it.unit_price) || 0), 0);
      const totalBoxCount = validItems.reduce((s, it) => s + (Number(it.box_count) || 0), 0);

      // 构建 items 数组
      const itemsPayload = validItems.map((it, idx) => ({
        spec: it.spec || "",
        box_count: Number(it.box_count) || 0,
        weight_kg: Number(it.weight_kg),
        unit_price: Number(it.unit_price),
        sort_order: idx,
      }));

      const payload: any = {
        sale_date: saleDate,
        batch_id: Number(batchId),
        customer_id: Number(customerId),
        salesperson_id: salespersonId ? Number(salespersonId) : null,
        spec: firstItem.spec || undefined,
        box_count: totalBoxCount || undefined,
        weight_kg: Number(totalWeight),
        unit_price: totalWeight > 0 ? totalGross / totalWeight : 0,
        gross_amount: totalGross,
        notes: notes.trim() || undefined,
        items: itemsPayload,
      };

      if (!initialData) {
        // 新建时才传 net_amount（初始等于 gross）
        payload.net_amount = totalGross;
      }

      if (initialData) {
        await api.put(`/v1/sales/whole-fish/${initialData.id}`, payload);
        toast.success("销售记录更新成功");
      } else {
        await api.post("/v1/sales/whole-fish", payload);
        toast.success("销售记录创建成功");
      }
      onSuccess();
      onOpenChange(false);
    } catch (error: any) {
      toast.error(error.response?.data?.detail ?? "操作失败");
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={(v) => { if (!v) { onOpenChange(false); resetForm(); } }}>
      <DialogContent className="!w-[480px] !max-w-[95vw] max-h-[90vh] overflow-y-auto p-5">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-3">
            {initialData ? "编辑销售记录" : "新增销售记录"}
            {previewSaleNo && (
              <Badge variant="outline" className="text-sm font-mono text-muted-foreground">
                {previewSaleNo}
              </Badge>
            )}
          </DialogTitle>
        </DialogHeader>
        <form onSubmit={handleSubmit} className="space-y-5">
          {/* 第一行：销售日期 + 批号 */}
          <div className="grid grid-cols-2 gap-5">
            <div className="space-y-2">
              <Label>销售日期 <span className="text-red-500">*</span></Label>
              <Input type="date" value={saleDate} onChange={(e) => setSaleDate(e.target.value)} className="h-10" />
            </div>
            <div className="space-y-2">
              <Label>批号 <span className="text-red-500">*</span></Label>
              <Select value={batchId} onValueChange={(v) => setBatchId(v ?? "")}>
                <SelectTrigger className="h-10">
                  <SelectValue placeholder="选择批号">
                    {batchesData?.items?.find((b: any) => String(b.id) === batchId)?.batch_name ?? <span className="text-muted-foreground">选择批号</span>}
                  </SelectValue>
                </SelectTrigger>
                <SelectContent>{availableBatches.map((b: any) => <SelectItem key={b.id} value={String(b.id)}>{b.batch_name} <span className="text-muted-foreground text-xs">({b.batch_code})</span></SelectItem>)}</SelectContent>
              </Select>
            </div>
          </div>

          {/* 第二行：客户 + 业务员 */}
          <div className="grid grid-cols-2 gap-5">
            <div className="space-y-2">
              <Label>客户 <span className="text-red-500">*</span></Label>
              <CustomerSearchSelect
                customers={customersData?.items || []}
                value={customerId}
                onChange={setCustomerId}
                placeholder="选择客户"
              />
            </div>
            <div className="space-y-2">
              <Label>业务员</Label>
              <Select value={salespersonId} onValueChange={(v) => setSalespersonId(v ?? "")}>
                <SelectTrigger className="h-10">
                  <SelectValue>
                    {(() => {
                      const s = salespersonsData?.items?.find((s: any) => String(s.id) === salespersonId);
                      return s ? (s.full_name ?? s.name) : "选择业务员";
                    })()}
                  </SelectValue>
                </SelectTrigger>
                <SelectContent>{salespersonsData?.items?.map((s: any) => <SelectItem key={s.id} value={String(s.id)}>{s.full_name ?? s.name}</SelectItem>)}</SelectContent>
              </Select>
            </div>
          </div>

          {/* 产品明细 */}
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <Label>产品明细</Label>
              <Button type="button" variant="outline" size="sm" onClick={addSpecItem}><Plus className="h-4 w-4 mr-1" />添加产品</Button>
            </div>
            <div className="space-y-2">
              {specItems.map((item, idx) => {
                const amount = (Number(item.weight_kg) || 0) * (Number(item.unit_price) || 0);
                const selectedProduct = importSpecs.find((p: any) => (p.spec || p.name) === item.spec);
                return (
                  <div key={idx} className="grid grid-cols-[70px_1fr_50px_65px_65px_60px_26px] gap-2 items-center">
                    <div className="text-xs font-medium truncate min-w-0" title={selectedProduct?.name}>
                      {selectedProduct?.name || <span className="text-muted-foreground">产品</span>}
                    </div>
                    <Select value={item.spec} onValueChange={(v) => updateSpecItem(idx, "spec", v ?? "")}>
                      <SelectTrigger className="h-8 text-xs px-2"><SelectValue placeholder="规格" /></SelectTrigger>
                      <SelectContent>
                        {importSpecs.map((p: any) => (
                          <SelectItem key={p.id} value={p.spec || p.name} className="text-xs">{p.spec || p.name}</SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                    <Input inputMode="decimal" value={item.box_count} onChange={(e) => updateSpecItem(idx, "box_count", e.target.value)} className="h-8 text-center text-xs px-1" placeholder="箱" />
                    <Input inputMode="decimal" value={item.weight_kg} onChange={(e) => updateSpecItem(idx, "weight_kg", e.target.value)} className="h-8 text-center text-xs px-1" placeholder="kg" />
                    <Input inputMode="decimal" value={item.unit_price} onChange={(e) => updateSpecItem(idx, "unit_price", e.target.value)} className="h-8 text-center text-xs px-1" placeholder="单价" />
                    <div className="text-right text-xs font-medium tabular-nums">¥{amount.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</div>
                    <Button type="button" variant="ghost" size="icon" className="h-7 w-7 text-red-500 shrink-0" onClick={() => removeSpecItem(idx)} disabled={specItems.length <= 1}>
                      <X className="h-3.5 w-3.5" />
                    </Button>
                  </div>
                );
              })}
            </div>
            <div className="flex justify-end items-center gap-3 text-xs pt-1 border-t">
              <span className="text-muted-foreground">总箱数: <span className="font-medium text-foreground">{specItems.reduce((s, it) => s + (Number(it.box_count) || 0), 0)}</span></span>
              <span className="text-muted-foreground">总重量: <span className="font-medium text-foreground">{specItems.reduce((s, it) => s + (Number(it.weight_kg) || 0), 0).toFixed(2)} kg</span></span>
              <span className="text-muted-foreground">总金额: <span className="font-bold text-green-600">¥{totalAmount.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</span></span>
            </div>
          </div>

          {/* 备注 */}
          <div className="space-y-2">
            <Label>备注</Label>
            <Input value={notes} onChange={(e) => setNotes(e.target.value)} placeholder="其他备注信息" />
          </div>

          <DialogFooter>
            <Button type="button" variant="outline" onClick={() => onOpenChange(false)}><X className="h-4 w-4 mr-1" />取消</Button>
            <Button type="submit" disabled={isSubmitting}><Receipt className="h-4 w-4 mr-1" />{isSubmitting ? "保存中..." : (initialData ? "保存" : "保存")}</Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}

// ==================== 可搜索客户选择组件 ====================

function CustomerSearchSelect({ customers, value, onChange, placeholder }: { customers: any[]; value: string; onChange: (v: string) => void; placeholder: string }) {
  const [open, setOpen] = useState(false);
  const [search, setSearch] = useState("");
  const ref = useRef<HTMLDivElement>(null);

  const selected = customers.find((c: any) => String(c.id) === value);
  const filtered = search.trim()
    ? customers.filter((c: any) => c.name?.toLowerCase().includes(search.trim().toLowerCase()))
    : customers;

  useEffect(() => {
    function handleClick(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) {
        setOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClick);
    return () => document.removeEventListener("mousedown", handleClick);
  }, []);

  return (
    <div ref={ref} className="relative">
      <button
        type="button"
        onClick={() => setOpen(!open)}
        className={cn(
          "w-full flex items-center justify-between h-10 px-3 py-2 border rounded-md text-sm bg-background",
          "hover:border-ring focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2",
          !selected && "text-muted-foreground"
        )}
      >
        <span className="truncate">{selected?.name || placeholder}</span>
        <svg className={cn("h-4 w-4 shrink-0 transition-transform", open && "rotate-180")} xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><polyline points="6 9 12 15 18 9"/></svg>
      </button>
      {open && (
        <div className="absolute z-50 w-full mt-1 bg-popover border rounded-md shadow-md overflow-hidden">
          <div className="p-2 border-b">
            <div className="relative">
              <Search className="absolute left-2 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-muted-foreground" />
              <Input
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                placeholder="搜索客户..."
                className="pl-7 h-8 text-sm"
                autoFocus
              />
            </div>
          </div>
          <div className="max-h-[200px] overflow-y-auto">
            {filtered.length === 0 ? (
              <div className="p-3 text-sm text-muted-foreground text-center">未找到客户</div>
            ) : (
              filtered.map((c: any) => (
                <div
                  key={c.id}
                  onClick={() => { onChange(String(c.id)); setOpen(false); setSearch(""); }}
                  className={cn(
                    "px-3 py-2 text-sm cursor-pointer hover:bg-accent",
                    String(c.id) === value && "bg-accent font-medium"
                  )}
                >
                  {c.name}
                </div>
              ))
            )}
          </div>
        </div>
      )}
    </div>
  );
}

// ==================== 详情弹窗组件 ====================

function SaleDetailDialog({ sale, onClose }: { sale: Sale; onClose: () => void }) {
  const [activeTab, setActiveTab] = useState("info");
  const queryClient = useQueryClient();

  const paymentMethodMap: Record<string, string> = {
    bank_transfer: "银行转账",
    cash: "现金",
    check: "支票",
    wechat: "微信",
    alipay: "支付宝",
    balance: "余额抵扣",
    other: "其他",
  };

  const [receiptFormOpen, setReceiptFormOpen] = useState(false);
  const [receiptDate, setReceiptDate] = useState("");
  const [receiptAmount, setReceiptAmount] = useState("");
  const [receiptMethod, setReceiptMethod] = useState("bank_transfer");
  const [receiptBankAccountId, setReceiptBankAccountId] = useState("");
  const [receiptRef, setReceiptRef] = useState("");
  const [receiptNotes, setReceiptNotes] = useState("");

  const [aftersalesFormOpen, setAftersalesFormOpen] = useState(false);
  const [aftersalesDate, setAftersalesDate] = useState("");
  const [aftersalesType, setAftersalesType] = useState("refund");
  const [aftersalesAmount, setAftersalesAmount] = useState("");
  const [aftersalesReason, setAftersalesReason] = useState("");
  const [aftersalesStatus, setAftersalesStatus] = useState("pending");
  const [aftersalesNotes, setAftersalesNotes] = useState("");

  // 银行账户列表
  const { data: bankAccountsData } = useQuery({
    queryKey: ["bank-accounts"],
    queryFn: async () => {
      const res = await api.get("/v1/finance/bank-accounts");
      return res.data;
    },
  });
  const bankAccounts = bankAccountsData || [];

  const createReceiptMutation = useMutation({
    mutationFn: async (payload: any) => {
      const res = await api.post(`/v1/sales/whole-fish/${sale.id}/receipts`, payload);
      return res.data;
    },
    onSuccess: () => {
      toast.success("收款记录添加成功");
      queryClient.invalidateQueries({ queryKey: ["sales"] });
      setReceiptFormOpen(false);
      resetReceiptForm();
    },
    onError: (err: any) => toast.error(err.response?.data?.detail || "添加失败"),
  });

  const resetReceiptForm = () => {
    setReceiptDate("");
    setReceiptAmount("");
    setReceiptMethod("bank_transfer");
    setReceiptBankAccountId("");
    setReceiptRef("");
    setReceiptNotes("");
  };

  const unpaid = Number(sale.net_amount) - Number(sale.paid_amount);

  return (
    <div className="py-4">
      <div className="flex gap-2 mb-4">
        <Button variant={activeTab === "info" ? "default" : "outline"} size="sm" onClick={() => setActiveTab("info")}>基本信息</Button>
        <Button variant={activeTab === "receipts" ? "default" : "outline"} size="sm" onClick={() => setActiveTab("receipts")}>收款记录 ({sale.receipts.length})</Button>
        <Button variant={activeTab === "aftersales" ? "default" : "outline"} size="sm" onClick={() => setActiveTab("aftersales")}>售后记录 ({sale.aftersales.length + (Number(sale.after_sales_adjustment) > 0 ? 1 : 0)})</Button>
      </div>

      {activeTab === "info" && (
        <div className="space-y-4">
          <div className="grid grid-cols-2 gap-3 text-sm">
            <div><span className="text-muted-foreground">销售单号:</span> <span className="ml-1 font-mono">{sale.sale_no ?? "-"}</span></div>
            <div><span className="text-muted-foreground">批次:</span> <span className="ml-1">{sale.batch_code ?? sale.batch_name ?? "-"}</span></div>
            <div><span className="text-muted-foreground">日期:</span> <span className="ml-1">{sale.sale_date}</span></div>
            <div><span className="text-muted-foreground">客户:</span> <span className="ml-1">{sale.customer_name ?? "-"}</span></div>
          </div>

          {/* 规格明细 */}
          {sale.items && sale.items.length > 0 && (
            <div className="border rounded-md overflow-hidden">
              <div className="bg-muted/50 px-3 py-2 text-xs font-medium">规格明细</div>
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead className="text-xs">规格</TableHead>
                    <TableHead className="text-xs text-right">箱数</TableHead>
                    <TableHead className="text-xs text-right">重量(kg)</TableHead>
                    <TableHead className="text-xs text-right">单价</TableHead>
                    <TableHead className="text-xs text-right">金额</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {sale.items.map((item) => (
                    <TableRow key={item.id ?? `${item.spec}-${item.weight_kg}`}>
                      <TableCell className="text-sm">{item.spec ?? "-"}</TableCell>
                      <TableCell className="text-sm text-right">{item.box_count ?? "-"}</TableCell>
                      <TableCell className="text-sm text-right">{Number(item.weight_kg).toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</TableCell>
                      <TableCell className="text-sm text-right">{Number(item.unit_price).toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</TableCell>
                      <TableCell className="text-sm text-right">¥{Number(item.amount).toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</TableCell>
                    </TableRow>
                  ))}
                  <TableRow className="bg-muted/50 font-medium text-sm">
                    <TableCell colSpan={2} className="text-right">合计:</TableCell>
                    <TableCell className="text-right">{sale.items.reduce((s, it) => s + Number(it.weight_kg || 0), 0).toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })} kg</TableCell>
                    <TableCell />
                    <TableCell className="text-right">${sale.items.reduce((s, it) => s + Number(it.amount || 0), 0).toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</TableCell>
                  </TableRow>
                </TableBody>
              </Table>
            </div>
          )}

          {/* 汇总金额 */}
          <div className="bg-muted p-3 rounded-md space-y-2 text-sm">
            <div className="flex justify-between"><span>毛金额</span><span>¥{Number(sale.gross_amount).toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</span></div>
            {Number(sale.rounding_adjustment) > 0 && <div className="flex justify-between text-red-500"><span>抹零调整</span><span>-¥{Number(sale.rounding_adjustment).toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</span></div>}
            {Number(sale.after_sales_adjustment) > 0 && <div className="flex justify-between text-red-500"><span>售后调整</span><span>-¥{Number(sale.after_sales_adjustment).toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</span></div>}
            {Number(sale.discount) > 0 && <div className="flex justify-between text-red-500"><span>折扣</span><span>-¥{Number(sale.discount).toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</span></div>}
            {Number(sale.commission) > 0 && <div className="flex justify-between text-red-500"><span>提成</span><span>-¥{Number(sale.commission).toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</span></div>}
            <div className="flex justify-between font-semibold border-t pt-1"><span>净金额</span><span>¥{Number(sale.net_amount).toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</span></div>
            <div className="flex justify-between text-green-600"><span>已付</span><span>¥{Number(sale.paid_amount).toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</span></div>
            {unpaid > 0 ? (
              <div className="flex justify-between text-orange-600 font-medium"><span>未付</span><span>¥{unpaid.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</span></div>
            ) : unpaid < 0 ? (
              <div className="flex justify-between text-blue-600 font-medium"><span>应退</span><span>¥{Math.abs(unpaid).toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</span></div>
            ) : (
              <div className="flex justify-between text-green-600 font-medium"><span>已结清</span><span>¥0.00</span></div>
            )}
          </div>
        </div>
      )}

      {activeTab === "receipts" && (
        <div className="space-y-4">
          <div className="bg-muted/50 rounded-lg p-4 space-y-3">
            <div className="flex items-center justify-between">
              <h4 className="text-sm font-medium">{receiptFormOpen ? "添加收款" : "收款操作"}</h4>
              {!receiptFormOpen && <Button size="sm" onClick={() => setReceiptFormOpen(true)} disabled={sale.is_locked}><Plus className="h-3 w-3 mr-1" />添加收款</Button>}
            </div>
            {receiptFormOpen && (
              <form onSubmit={(e) => { e.preventDefault(); if (!receiptDate || !receiptAmount) { toast.error("请填写日期和金额"); return; } createReceiptMutation.mutate({ receipt_date: receiptDate, amount: Number(receiptAmount), payment_method: receiptMethod, bank_account_id: receiptBankAccountId ? Number(receiptBankAccountId) : null, reference_no: receiptRef.trim() || null, notes: receiptNotes.trim() || null }); }} className="space-y-3">
                <div className="grid grid-cols-2 gap-3">
                  <div className="space-y-1"><Label className="text-xs">收款日期 *</Label><Input type="date" value={receiptDate} onChange={(e) => setReceiptDate(e.target.value)} /></div>
                  <div className="space-y-1"><Label className="text-xs">金额 *</Label><Input type="number" step="0.01" value={receiptAmount} onChange={(e) => setReceiptAmount(e.target.value)} /></div>
                </div>
                <div className="grid grid-cols-2 gap-3">
                  <div className="space-y-1">
                    <Label className="text-xs">收款方式</Label>
                    <Select value={receiptMethod} onValueChange={(v) => { setReceiptMethod(v ?? ""); if (v === "balance") setReceiptBankAccountId(""); }}>
                      <SelectTrigger className="h-8 text-xs"><SelectValue /></SelectTrigger>
                      <SelectContent>
                        <SelectItem value="bank_transfer">银行转账</SelectItem>
                        <SelectItem value="cash">现金</SelectItem>
                        <SelectItem value="check">支票</SelectItem>
                        <SelectItem value="scan">扫码</SelectItem>
                        <SelectItem value="balance">余额抵扣</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                  {receiptMethod !== "balance" ? (
                  <div className="space-y-1">
                    <Label className="text-xs">收款银行</Label>
                    <Select value={receiptBankAccountId} onValueChange={(v) => setReceiptBankAccountId(v ?? "")}>
                      <SelectTrigger className="h-8 text-xs">
                        <SelectValue placeholder="选择银行">
                          {(() => {
                            const b = bankAccounts.find((ba: any) => String(ba.id) === receiptBankAccountId);
                            return b ? `${b.bank_name} ···${b.account_number?.slice(-4)}` : "选择银行";
                          })()}
                        </SelectValue>
                      </SelectTrigger>
                      <SelectContent>
                        {bankAccounts.map((b: any) => (
                          <SelectItem key={b.id} value={String(b.id)} className="text-xs">{b.bank_name} ···{b.account_number?.slice(-4)}</SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                  ) : (
                  <div className="space-y-1">
                    <Label className="text-xs">客户余额</Label>
                    <div className="h-8 flex items-center px-3 rounded-md border bg-muted/30 text-xs">
                      {(() => {
                        const c = (customersData?.items || []).find((c: any) => c.id === receiptSale?.customer_id);
                        const bal = Number(c?.prepaid_balance || 0);
                        return (
                          <span className={bal > 0 ? "text-green-600 font-medium" : "text-muted-foreground"}>
                            {c ? `¥${bal.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}` : "—"}
                          </span>
                        );
                      })()}
                    </div>
                  </div>
                  )}
                </div>
                <div className="space-y-1">
                  <Label className="text-xs">参考号</Label>
                  <Input value={receiptRef} onChange={(e) => setReceiptRef(e.target.value)} placeholder="转账单号等" className="h-8 text-xs" />
                </div>
                <div className="flex gap-2 justify-end">
                  <Button type="button" variant="ghost" size="sm" onClick={() => { setReceiptFormOpen(false); resetReceiptForm(); }}>取消</Button>
                  <Button type="submit" size="sm" disabled={createReceiptMutation.isPending}>{createReceiptMutation.isPending ? "保存中..." : "保存"}</Button>
                </div>
              </form>
            )}
          </div>
          {sale.receipts && sale.receipts.length > 0 ? (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead className="text-xs">日期</TableHead>
                  <TableHead className="text-xs">方式</TableHead>
                  <TableHead className="text-xs">银行</TableHead>
                  <TableHead className="text-xs text-right">金额</TableHead>
                  <TableHead className="text-xs">备注</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {sale.receipts.map((r) => (
                  <TableRow key={r.id}>
                    <TableCell className="text-sm">{r.receipt_date}</TableCell>
                    <TableCell className="text-sm">{paymentMethodMap[r.payment_method] || r.payment_method}</TableCell>
                    <TableCell className="text-sm">{(() => {
                      const b = bankAccounts.find((ba: any) => ba.id === r.bank_account_id);
                      return b ? `${b.bank_name} ${b.account_number?.slice(-4)}` : "-";
                    })()}</TableCell>
                    <TableCell className="text-sm text-right">¥{Number(r.amount).toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</TableCell>
                    <TableCell className="text-sm">{r.notes ?? "-"}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          ) : <div className="text-sm text-muted-foreground text-center py-8">暂无收款记录</div>}
        </div>
      )}

      {activeTab === "aftersales" && (
        <div>
          {sale.aftersales && sale.aftersales.length > 0 || Number(sale.after_sales_adjustment) > 0 ? (
            <Table>
              <TableHeader><TableRow><TableHead className="text-xs">日期</TableHead><TableHead className="text-xs">类型</TableHead><TableHead className="text-xs text-right">金额</TableHead><TableHead className="text-xs">状态</TableHead></TableRow></TableHeader>
              <TableBody>
                {Number(sale.after_sales_adjustment) > 0 && (
                  <TableRow>
                    <TableCell className="text-sm">{sale.sale_date}</TableCell>
                    <TableCell className="text-sm">售后调整</TableCell>
                    <TableCell className="text-sm text-right text-red-500">-¥{Number(sale.after_sales_adjustment).toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</TableCell>
                    <TableCell className="text-sm">已扣减</TableCell>
                  </TableRow>
                )}
                {sale.aftersales.map((a) => (
                  <TableRow key={a.id}><TableCell className="text-sm">{a.record_date}</TableCell><TableCell className="text-sm">{a.type}</TableCell><TableCell className="text-sm text-right">¥{Number(a.amount).toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</TableCell><TableCell className="text-sm">{a.status}</TableCell></TableRow>
                ))}
              </TableBody>
            </Table>
          ) : <div className="text-sm text-muted-foreground text-center py-8">暂无售后记录</div>}
        </div>
      )}
    </div>
  );
}
