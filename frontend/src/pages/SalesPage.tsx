
import React, { useState } from "react";
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
  Plus, Search, Eye, Pencil, Trash2, X, DollarSign, Receipt, AlertTriangle, Trash,
} from "lucide-react";
import { toast } from "sonner";
import { BatchImportButton } from "@/components/BatchImportButton";

const statusMap: Record<string, { label: string; color: string }> = {
  pending: { label: "待收款", color: "bg-red-100 text-red-800" },
  partial_paid: { label: "部分收款", color: "bg-yellow-100 text-yellow-800" },
  fully_paid: { label: "全部收款", color: "bg-green-100 text-green-800" },
  after_sales: { label: "售后中", color: "bg-purple-100 text-purple-800" },
};

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
}

interface Receipt {
  id: number;
  sale_id: number;
  receipt_date: string;
  amount: string;
  payment_method: string;
  reference_no: string | null;
  notes: string | null;
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

  const handleBatchDelete = () => {
    if (selectedIds.size === 0) { toast.error("请先选择要删除的记录"); return; }
    setBatchDeleteDialogOpen(true);
  };

  const handleDelete = async (sale: Sale) => {
    if (sale.is_locked) { toast.error("销售记录已锁定，不能删除"); return; }
    setDeleteSale(sale);
    setDeleteDialogOpen(true);
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

  const handleOpenAdjust = (sale: Sale) => {
    setAdjustSale(sale);
    setAdjRounding(String(sale.rounding_adjustment ?? 0));
    setAdjAfterSales(String(sale.after_sales_adjustment ?? 0));
    setAdjAfterSalesIssue(sale.notes ?? "");
    setAdjDiscount(String(sale.discount ?? 0));
    setAdjCommission(String(sale.commission ?? 0));
    // 默认收款 = 应收金额（毛金额 - 折扣 - 售后调整）
    const gross = Number(sale.gross_amount || 0);
    const discount = Number(sale.discount || 0);
    const afterSales = Number(sale.after_sales_adjustment || 0);
    const net = Math.max(0, gross - discount - afterSales);
    setAdjPaidAmount(String(net));
    setAdjustDialogOpen(true);
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

  const handleSaveAdjust = () => {
    if (!adjustSale) return;
    const gross = Number(adjustSale.gross_amount);
    const net = Math.max(0, gross - Number(adjRounding || 0) - Number(adjAfterSales || 0) - Number(adjDiscount || 0));
    adjustMutation.mutate({
      id: adjustSale.id,
      body: {
        rounding_adjustment: Number(adjRounding || 0),
        after_sales_adjustment: Number(adjAfterSales || 0),
        discount: Number(adjDiscount || 0),
        net_amount: net,
        paid_amount: Number(adjPaidAmount || 0),
        notes: adjAfterSalesIssue.trim() || undefined,
      },
    });
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
            <DialogTitle>销售调整 #{adjustSale?.id}</DialogTitle>
            <DialogDescription className="text-sm">
              销售单号: <span className="font-mono">{adjustSale?.sale_no}</span> · 客户: {adjustSale?.customer_name}
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-4">
            {/* 毛金额 */}
            <div className="bg-muted/50 rounded-md p-3 text-sm space-y-1">
              <div className="flex justify-between">
                <span className="text-muted-foreground">毛金额</span>
                <span className="font-medium">${adjustSale ? Number(adjustSale.gross_amount).toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 }) : "0"}</span>
              </div>
              {adjustSale && Number(adjustSale.weight_kg) > 0 && (
                <div className="text-xs text-muted-foreground">
                  {Number(adjustSale.weight_kg).toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })} kg × {Number(adjustSale.unit_price).toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}/kg
                </div>
              )}
            </div>

              {/* 调整项 */}
              <div className="space-y-3">
                <div className="grid grid-cols-2 gap-3">
                  <div className="space-y-1">
                    <Label className="text-xs">抹零</Label>
                    <Input inputMode="decimal" value={adjRounding} onChange={(e) => setAdjRounding(e.target.value)} placeholder="0" />
                  </div>
                  <div className="space-y-1">
                    <Label className="text-xs">折扣</Label>
                    <Input inputMode="decimal" value={adjDiscount} onChange={(e) => setAdjDiscount(e.target.value)} placeholder="0" />
                  </div>
                </div>

                <div className="space-y-1">
                  <Label className="text-xs">售后调整</Label>
                  <div className="flex gap-2">
                    <Input inputMode="decimal" value={adjAfterSales} onChange={(e) => setAdjAfterSales(e.target.value)} placeholder="0" className="w-32" />
                    <Input value={adjAfterSalesIssue} onChange={(e) => setAdjAfterSalesIssue(e.target.value)} placeholder="售后问题描述" />
                  </div>
                </div>

                {/* 本次收款 - 核心区域 */}
                <div className="space-y-2 border-t pt-3 mt-3">
                  <Label className="text-sm font-medium text-green-700">💰 本次收款</Label>
                  <div className="flex gap-2 items-center">
                    <Input
                      inputMode="decimal"
                      value={adjPaidAmount}
                      onChange={(e) => {
                        const val = e.target.value;
                        setAdjPaidAmount(val);
                        // 自动计算抹零
                        const paid = Number(val || 0);
                        const gross = Number(adjustSale?.gross_amount || 0);
                        const discount = Number(adjDiscount || 0);
                        const afterSales = Number(adjAfterSales || 0);
                        const net = Math.max(0, gross - discount - afterSales);
                        if (paid > 0 && paid <= net) {
                          setAdjRounding(String((net - paid).toFixed(2)));
                        } else if (paid >= net) {
                          setAdjRounding("0");
                        }
                      }}
                      placeholder="输入实收金额"
                      className="text-lg"
                    />
                    <span className="text-sm text-muted-foreground whitespace-nowrap">
                      应收: ${adjustSale ? Math.max(0, Number(adjustSale.gross_amount) - Number(adjDiscount || 0) - Number(adjAfterSales || 0)).toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 }) : "0"}
                    </span>
                  </div>
                  {Number(adjRounding) > 0 && (
                    <div className="text-xs text-orange-600">
                      自动抹零: ${Number(adjRounding).toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                    </div>
                  )}
                </div>
              </div>

              {/* 计算结果 */}
              <div className="bg-muted/50 rounded-md p-3 text-sm space-y-2">
                <div className="flex justify-between">
                  <span className="text-muted-foreground">毛金额</span>
                  <span>${adjustSale ? Number(adjustSale.gross_amount).toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 }) : "0"}</span>
                </div>
                {Number(adjDiscount) > 0 && (
                  <div className="flex justify-between text-orange-600">
                    <span>折扣</span>
                    <span>-${Number(adjDiscount).toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</span>
                  </div>
                )}
                {Number(adjAfterSales) > 0 && (
                  <div className="flex justify-between text-orange-600">
                    <span>售后调整</span>
                    <span>-${Number(adjAfterSales).toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</span>
                  </div>
                )}
                {Number(adjRounding) > 0 && (
                  <div className="flex justify-between text-orange-600">
                    <span>抹零</span>
                    <span>-${Number(adjRounding).toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</span>
                  </div>
                )}
                <div className="flex justify-between font-medium border-t pt-1">
                  <span>净金额</span>
                  <span>${adjustSale ? Math.max(0, Number(adjustSale.gross_amount) - Number(adjRounding || 0) - Number(adjAfterSales || 0) - Number(adjDiscount || 0)).toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 }) : "0"}</span>
                </div>
                <div className="flex justify-between text-green-600">
                  <span>本次收款</span>
                  <span>+${Number(adjPaidAmount || 0).toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</span>
                </div>
                <div className="flex justify-between font-medium border-t pt-1">
                  <span>未付余额</span>
                  <span className={adjustSale && (Number(adjustSale.gross_amount) - Number(adjRounding || 0) - Number(adjAfterSales || 0) - Number(adjDiscount || 0) - Number(adjPaidAmount || 0)) <= 0 ? "text-green-600" : "text-orange-600"}>
                    ${adjustSale ? Math.max(0, Number(adjustSale.gross_amount) - Number(adjRounding || 0) - Number(adjAfterSales || 0) - Number(adjDiscount || 0) - Number(adjPaidAmount || 0)).toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 }) : "0"}
                  </span>
                </div>
              </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setAdjustDialogOpen(false)}>取消</Button>
            <Button onClick={handleSaveAdjust} disabled={adjustMutation.isPending}>
              {adjustMutation.isPending ? "保存中..." : "保存收款"}
            </Button>
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
          <SelectTrigger className="w-[160px]"><SelectValue placeholder="收款状态" /></SelectTrigger>
          <SelectContent>
            <SelectItem value="all">全部状态</SelectItem>
            {Object.entries(statusMap).map(([key, { label }]) => (
              <SelectItem key={key} value={key}>{label}</SelectItem>
            ))}
          </SelectContent>
        </Select>
        {selectedIds.size > 0 && (
          <Button variant="destructive" size="sm" onClick={handleBatchDelete}><Trash className="h-4 w-4 mr-1" />批量删除 ({selectedIds.size})</Button>
        )}
      </div>

      {/* 汇总行 */}
      {data?.items && data.items.length > 0 && (
        <div className="grid grid-cols-6 gap-4">
          <Card><CardContent className="p-3 text-sm"><p className="text-muted-foreground">记录条数</p><p className="text-2xl font-bold">{summary.totalCount.toLocaleString()}</p></CardContent></Card>
          <Card><CardContent className="p-3 text-sm"><p className="text-muted-foreground">总箱数</p><p className="text-2xl font-bold">{summary.totalBoxes.toLocaleString()}</p></CardContent></Card>
          <Card><CardContent className="p-3 text-sm"><p className="text-muted-foreground">总重量</p><p className="text-2xl font-bold">{summary.totalWeight.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })} kg</p></CardContent></Card>
          <Card><CardContent className="p-3 text-sm"><p className="text-muted-foreground">总销售金额</p><p className="text-2xl font-bold">${summary.totalNetAmount.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</p></CardContent></Card>
          <Card><CardContent className="p-3 text-sm"><p className="text-muted-foreground">已收金额</p><p className="text-2xl font-bold text-green-600">${summary.totalPaid.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</p></CardContent></Card>
          <Card><CardContent className="p-3 text-sm"><p className="text-muted-foreground">未收金额</p><p className="text-2xl font-bold text-orange-600">${summary.totalUnpaid.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</p></CardContent></Card>
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
              <TableHead>批次编号</TableHead>
              <TableHead>批次名称</TableHead>
              <TableHead>规格</TableHead>
              <TableHead className="text-right">箱数</TableHead>
              <TableHead className="text-right">重量(kg)</TableHead>
              <TableHead className="text-right">销售金额</TableHead>
              <TableHead>付款状态</TableHead>
              <TableHead className="w-[120px]">操作</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {isLoading ? <TableRow><TableCell colSpan={12} className="text-center py-8">加载中...</TableCell></TableRow>
             : (data?.items?.length ?? 0) === 0 ? <TableRow><TableCell colSpan={12} className="text-center py-8">暂无数据</TableCell></TableRow>
             : <>
                {data?.items.map((sale) => {
                  const statusInfo = statusMap[sale.status] ?? { label: sale.status, color: "" };
                  const unpaid = Number(sale.net_amount) - Number(sale.paid_amount);
                  return (
                    <TableRow key={sale.id}>
                      <TableCell><Checkbox checked={selectedIds.has(sale.id)} onCheckedChange={(checked) => toggleSelect(sale.id, checked)} /></TableCell>
                      <TableCell className="font-medium">{sale.is_locked && <span className="text-orange-500 mr-1">🔒</span>}{sale.sale_no ?? `#${sale.id}`}</TableCell>
                      <TableCell>{sale.sale_date}</TableCell>
                      <TableCell>{sale.customer_name ?? "-"}</TableCell>
                      <TableCell>{sale.batch_code ?? sale.batch_name ?? "-"}</TableCell>
                      <TableCell>{sale.batch_name ?? "-"}</TableCell>
                      <TableCell>{sale.spec ?? "-"}</TableCell>
                      <TableCell className="text-right">{sale.box_count ?? "-"}</TableCell>
                      <TableCell className="text-right">{Number(sale.weight_kg).toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</TableCell>
                      <TableCell className="text-right">
                        <div>${Number(sale.net_amount).toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</div>
                        {unpaid > 0 && <div className="text-xs text-orange-500">未付 ${unpaid.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</div>}
                      </TableCell>
                      <TableCell><Badge variant="secondary" className={statusInfo.color}>{statusInfo.label}</Badge></TableCell>
                      <TableCell>
                        <div className="flex gap-1">
                          <Button variant="ghost" size="icon" className="h-8 w-8" onClick={() => { setDetailSale(sale); setDetailOpen(true); }}><Eye className="h-4 w-4" /></Button>
                          <Button variant="ghost" size="icon" className="h-8 w-8" onClick={() => { setEditingSale(sale); setFormOpen(true); }} disabled={sale.is_locked}><Pencil className={cn("h-4 w-4", sale.is_locked && "text-muted-foreground")} /></Button>
                          <Button variant="ghost" size="icon" className="h-8 w-8" onClick={() => handleOpenAdjust(sale)} title="调整" disabled={sale.is_locked}><DollarSign className={cn("h-4 w-4", sale.is_locked && "text-muted-foreground")} /></Button>
                          <Button variant="ghost" size="icon" className="h-8 w-8 text-red-500" onClick={() => handleDelete(sale)} disabled={sale.is_locked}><Trash2 className={cn("h-4 w-4", sale.is_locked && "text-muted-foreground")} /></Button>
                        </div>
                      </TableCell>
                    </TableRow>
                  );
                })}
                {/* 页汇总行 */}
                {data?.items && data.items.length > 0 && (
                  <TableRow className="bg-muted/50 font-medium border-t-2">
                    <TableCell colSpan={7} className="text-right">本页合计:</TableCell>
                    <TableCell className="text-right">
                      {data.items.reduce((s, it) => s + (Number(it.box_count) || 0), 0)}
                    </TableCell>
                    <TableCell className="text-right">
                      {data.items.reduce((s, it) => s + Number(it.weight_kg || 0), 0).toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })} kg
                    </TableCell>
                    <TableCell className="text-right">
                      ${data.items.reduce((s, it) => s + Number(it.net_amount || 0), 0).toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
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
      setSpecItems([{ spec: initialData.spec ?? "", box_count: initialData.box_count ? String(initialData.box_count) : "", weight_kg: String(initialData.weight_kg), unit_price: String(initialData.unit_price) }]);
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
      const payload = {
        sale_date: saleDate,
        batch_id: Number(batchId),
        customer_id: Number(customerId),
        salesperson_id: salespersonId ? Number(salespersonId) : undefined,
        spec: firstItem.spec || undefined,
        box_count: Number(firstItem.box_count) || undefined,
        weight_kg: Number(totalWeight),
        unit_price: totalWeight > 0 ? totalGross / totalWeight : 0,
        gross_amount: totalGross,
        net_amount: totalGross,
        notes: notes.trim() || undefined,
      };
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
      <DialogContent className="!w-[520px] !max-w-[520px] max-h-[90vh] overflow-y-auto p-6">
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
                <SelectTrigger className="h-10"><SelectValue placeholder="选择批号" /></SelectTrigger>
                <SelectContent>{batchesData?.items?.map((b: any) => <SelectItem key={b.id} value={String(b.id)}>{b.batch_code}</SelectItem>)}</SelectContent>
              </Select>
            </div>
          </div>

          {/* 第二行：客户 + 业务员 */}
          <div className="grid grid-cols-2 gap-5">
            <div className="space-y-2">
              <Label>客户 <span className="text-red-500">*</span></Label>
              <Select value={customerId} onValueChange={(v) => setCustomerId(v ?? "")}>
                <SelectTrigger className="h-10"><SelectValue placeholder="选择客户" /></SelectTrigger>
                <SelectContent>{customersData?.items?.map((c: any) => <SelectItem key={c.id} value={String(c.id)}>{c.name}</SelectItem>)}</SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label>业务员</Label>
              <Select value={salespersonId} onValueChange={(v) => setSalespersonId(v ?? "")}>
                <SelectTrigger className="h-10"><SelectValue placeholder="选择业务员" /></SelectTrigger>
                <SelectContent>{salespersonsData?.items?.map((s: any) => <SelectItem key={s.id} value={String(s.id)}>{s.full_name ?? s.name}</SelectItem>)}</SelectContent>
              </Select>
            </div>
          </div>

          {/* 规格明细 */}
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <Label>规格明细</Label>
              <Button type="button" variant="outline" size="sm" onClick={addSpecItem}><Plus className="h-4 w-4 mr-1" />添加规格</Button>
            </div>
            <div className="space-y-2">
              {specItems.map((item, idx) => {
                const amount = (Number(item.weight_kg) || 0) * (Number(item.unit_price) || 0);
                return (
                  <div key={idx} className="grid grid-cols-[1fr_80px_100px_100px_80px_40px] gap-2 items-center">
                    <Select value={item.spec} onValueChange={(v) => updateSpecItem(idx, "spec", v ?? "")}>
                      <SelectTrigger className="h-9"><SelectValue placeholder="选择规格" /></SelectTrigger>
                      <SelectContent>
                        {importSpecs.map((p: any) => (
                          <SelectItem key={p.id} value={p.spec || p.name}>{p.spec || p.name} ({p.code})</SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                    <Input inputMode="decimal" value={item.box_count} onChange={(e) => updateSpecItem(idx, "box_count", e.target.value)} className="h-9 text-center" placeholder="箱数" />
                    <Input inputMode="decimal" value={item.weight_kg} onChange={(e) => updateSpecItem(idx, "weight_kg", e.target.value)} className="h-9 text-center" placeholder="重量" />
                    <Input inputMode="decimal" value={item.unit_price} onChange={(e) => updateSpecItem(idx, "unit_price", e.target.value)} className="h-9 text-center" placeholder="单价" />
                    <div className="text-right font-medium text-sm">¥{amount.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</div>
                    <Button type="button" variant="ghost" size="icon" className="h-8 w-8 text-red-500" onClick={() => removeSpecItem(idx)} disabled={specItems.length <= 1}>
                      <X className="h-4 w-4" />
                    </Button>
                  </div>
                );
              })}
            </div>
            <div className="flex justify-end items-center gap-4 text-sm pt-1 border-t">
              <span className="text-muted-foreground">总箱数: <span className="font-medium text-foreground">{specItems.reduce((s, it) => s + (Number(it.box_count) || 0), 0)}</span></span>
              <span className="text-muted-foreground">总重量: <span className="font-medium text-foreground">{specItems.reduce((s, it) => s + (Number(it.weight_kg) || 0), 0).toFixed(3)} kg</span></span>
              <span className="text-muted-foreground">销售金额: <span className="font-bold text-green-600">¥{totalAmount.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</span></span>
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

// ==================== 详情弹窗组件 ====================

function SaleDetailDialog({ sale, onClose }: { sale: Sale; onClose: () => void }) {
  const [activeTab, setActiveTab] = useState("info");
  const queryClient = useQueryClient();

  const [receiptFormOpen, setReceiptFormOpen] = useState(false);
  const [receiptDate, setReceiptDate] = useState("");
  const [receiptAmount, setReceiptAmount] = useState("");
  const [receiptMethod, setReceiptMethod] = useState("bank_transfer");
  const [receiptRef, setReceiptRef] = useState("");
  const [receiptNotes, setReceiptNotes] = useState("");

  const [aftersalesFormOpen, setAftersalesFormOpen] = useState(false);
  const [aftersalesDate, setAftersalesDate] = useState("");
  const [aftersalesType, setAftersalesType] = useState("refund");
  const [aftersalesAmount, setAftersalesAmount] = useState("");
  const [aftersalesReason, setAftersalesReason] = useState("");
  const [aftersalesStatus, setAftersalesStatus] = useState("pending");
  const [aftersalesNotes, setAftersalesNotes] = useState("");

  const createReceiptMutation = useMutation({
    mutationFn: async (payload: any) => { const res = await api.post(`/v1/sales/whole-fish/${sale.id}/receipts`, payload); return res.data; },
    onSuccess: () => { toast.success("收款记录添加成功"); queryClient.invalidateQueries({ queryKey: ["sales"] }); setReceiptFormOpen(false); resetReceiptForm(); },
    onError: (err: any) => toast.error(err.response?.data?.detail || "添加失败"),
  });

  const resetReceiptForm = () => { setReceiptDate(""); setReceiptAmount(""); setReceiptMethod("bank_transfer"); setReceiptRef(""); setReceiptNotes(""); };

  const unpaid = Number(sale.net_amount) - Number(sale.paid_amount);

  return (
    <div className="py-4">
      <div className="flex gap-2 mb-4">
        <Button variant={activeTab === "info" ? "default" : "outline"} size="sm" onClick={() => setActiveTab("info")}>基本信息</Button>
        <Button variant={activeTab === "receipts" ? "default" : "outline"} size="sm" onClick={() => setActiveTab("receipts")}>收款记录 ({sale.receipts.length})</Button>
        <Button variant={activeTab === "aftersales" ? "default" : "outline"} size="sm" onClick={() => setActiveTab("aftersales")}>售后记录 ({sale.aftersales.length})</Button>
      </div>

      {activeTab === "info" && (
        <div className="space-y-4">
          <div className="grid grid-cols-2 gap-3 text-sm">
            <div><span className="text-muted-foreground">销售单号:</span> <span className="ml-1 font-mono">{sale.sale_no ?? "-"}</span></div>
            <div><span className="text-muted-foreground">批次:</span> <span className="ml-1">{sale.batch_code ?? sale.batch_name ?? "-"}</span></div>
            <div><span className="text-muted-foreground">日期:</span> <span className="ml-1">{sale.sale_date}</span></div>
            <div><span className="text-muted-foreground">客户:</span> <span className="ml-1">{sale.customer_name ?? "-"}</span></div>
            <div><span className="text-muted-foreground">规格:</span> <span className="ml-1">{sale.spec ?? "-"}</span></div>
            <div><span className="text-muted-foreground">箱数:</span> <span className="ml-1">{sale.box_count ?? "-"}</span></div>
            <div><span className="text-muted-foreground">重量:</span> <span className="ml-1">{Number(sale.weight_kg).toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })} kg</span></div>
            <div><span className="text-muted-foreground">单价:</span> <span className="ml-1">{Number(sale.unit_price).toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</span></div>
          </div>
          <div className="bg-muted p-3 rounded-md space-y-2 text-sm">
            <div className="flex justify-between"><span>毛金额</span><span>${Number(sale.gross_amount).toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</span></div>
            {Number(sale.rounding_adjustment) > 0 && <div className="flex justify-between text-red-500"><span>抹零调整</span><span>-${Number(sale.rounding_adjustment).toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</span></div>}
            {Number(sale.after_sales_adjustment) > 0 && <div className="flex justify-between text-red-500"><span>售后调整</span><span>-${Number(sale.after_sales_adjustment).toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</span></div>}
            {Number(sale.discount) > 0 && <div className="flex justify-between text-red-500"><span>折扣</span><span>-${Number(sale.discount).toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</span></div>}
            {Number(sale.commission) > 0 && <div className="flex justify-between text-red-500"><span>提成</span><span>-${Number(sale.commission).toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</span></div>}
            <div className="flex justify-between font-semibold border-t pt-1"><span>净金额</span><span>${Number(sale.net_amount).toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</span></div>
            <div className="flex justify-between text-green-600"><span>已付</span><span>${Number(sale.paid_amount).toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</span></div>
            <div className="flex justify-between text-orange-600 font-medium"><span>未付</span><span>${unpaid.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</span></div>
          </div>
        </div>
      )}

      {activeTab === "receipts" && (
        <div className="space-y-4">
          <div className="bg-muted/50 rounded-lg p-4 space-y-3">
            <div className="flex items-center justify-between">
              <h4 className="text-sm font-medium">{receiptFormOpen ? "添加收款" : "收款操作"}</h4>
              {!receiptFormOpen && <Button size="sm" onClick={() => setReceiptFormOpen(true)}><Plus className="h-3 w-3 mr-1" />添加收款</Button>}
            </div>
            {receiptFormOpen && (
              <form onSubmit={(e) => { e.preventDefault(); if (!receiptDate || !receiptAmount) { toast.error("请填写日期和金额"); return; } createReceiptMutation.mutate({ receipt_date: receiptDate, amount: Number(receiptAmount), payment_method: receiptMethod, reference_no: receiptRef.trim() || null, notes: receiptNotes.trim() || null }); }} className="space-y-3">
                <div className="grid grid-cols-2 gap-3">
                  <div className="space-y-1"><Label className="text-xs">收款日期 *</Label><Input type="date" value={receiptDate} onChange={(e) => setReceiptDate(e.target.value)} /></div>
                  <div className="space-y-1"><Label className="text-xs">金额 *</Label><Input type="number" step="0.01" value={receiptAmount} onChange={(e) => setReceiptAmount(e.target.value)} /></div>
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
              <TableHeader><TableRow><TableHead className="text-xs">日期</TableHead><TableHead className="text-xs">方式</TableHead><TableHead className="text-xs text-right">金额</TableHead><TableHead className="text-xs">备注</TableHead></TableRow></TableHeader>
              <TableBody>
                {sale.receipts.map((r) => (
                  <TableRow key={r.id}><TableCell className="text-sm">{r.receipt_date}</TableCell><TableCell className="text-sm">{r.payment_method}</TableCell><TableCell className="text-sm text-right">${Number(r.amount).toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</TableCell><TableCell className="text-sm">{r.notes ?? "-"}</TableCell></TableRow>
                ))}
              </TableBody>
            </Table>
          ) : <div className="text-sm text-muted-foreground text-center py-8">暂无收款记录</div>}
        </div>
      )}

      {activeTab === "aftersales" && (
        <div>
          {sale.aftersales && sale.aftersales.length > 0 ? (
            <Table>
              <TableHeader><TableRow><TableHead className="text-xs">日期</TableHead><TableHead className="text-xs">类型</TableHead><TableHead className="text-xs text-right">金额</TableHead><TableHead className="text-xs">状态</TableHead></TableRow></TableHeader>
              <TableBody>
                {sale.aftersales.map((a) => (
                  <TableRow key={a.id}><TableCell className="text-sm">{a.record_date}</TableCell><TableCell className="text-sm">{a.type}</TableCell><TableCell className="text-sm text-right">${Number(a.amount).toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</TableCell><TableCell className="text-sm">{a.status}</TableCell></TableRow>
                ))}
              </TableBody>
            </Table>
          ) : <div className="text-sm text-muted-foreground text-center py-8">暂无售后记录</div>}
        </div>
      )}
    </div>
  );
}
