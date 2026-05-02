import React, { useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "@/components/ui/dialog";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Badge } from "@/components/ui/badge";
import { Plus, Search, Eye, Pencil, Trash2 } from "lucide-react";
import { toast } from "sonner";

const statusMap: Record<string, { label: string; color: string }> = {
  pending: { label: "待收款", color: "bg-red-100 text-red-800" },
  partial_paid: { label: "部分收款", color: "bg-yellow-100 text-yellow-800" },
  fully_paid: { label: "全部收款", color: "bg-green-100 text-green-800" },
  after_sales: { label: "售后中", color: "bg-purple-100 text-purple-800" },
};

interface Sale {
  id: number;
  sale_date: string;
  customer_id: number;
  customer_name: string | null;
  product_id: number;
  product_name: string | null;
  product_spec: string | null;
  quantity: number;
  unit_price: string;
  gross_amount: string;
  scan_fee: string;
  discount: string;
  commission: string;
  net_amount: string;
  paid_amount: string;
  status: string;
  salesperson_id: number | null;
  salesperson_name: string | null;
  notes: string | null;
  is_locked: boolean;
}

interface SaleListResponse {
  total: number;
  items: Sale[];
  skip: number;
  limit: number;
}

const PAGE_SIZE = 10;

export function FinishedProductSalesPage() {
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState<string>("all");
  const [page, setPage] = useState(1);
  const [formOpen, setFormOpen] = useState(false);
  const [editingSale, setEditingSale] = useState<Sale | null>(null);
  const queryClient = useQueryClient();

  const { data, isLoading } = useQuery<SaleListResponse>({
    queryKey: ["finished-product-sales", statusFilter, page],
    queryFn: async () => {
      const params = new URLSearchParams();
      if (statusFilter && statusFilter !== "all") params.append("status", statusFilter);
      params.append("skip", String((page - 1) * PAGE_SIZE));
      params.append("limit", String(PAGE_SIZE));
      const res = await api.get(`/v1/finished-product-sales/?${params.toString()}`);
      return res.data;
    },
  });

  const totalPages = data ? Math.ceil(data.total / PAGE_SIZE) : 0;

  const handleDelete = async (sale: Sale) => {
    if (sale.is_locked) {
      toast.error("销售记录已锁定，不能删除");
      return;
    }
    if (!confirm(`确定要删除销售记录 #${sale.id} 吗？`)) return;
    try {
      await api.delete(`/v1/finished-product-sales/${sale.id}`);
      toast.success("销售记录已删除");
      queryClient.invalidateQueries({ queryKey: ["finished-product-sales"] });
    } catch (error: any) {
      toast.error(error.response?.data?.detail ?? "删除失败");
    }
  };

  const handleEdit = (sale: Sale) => {
    if (sale.is_locked) {
      toast.error("销售记录已锁定，不能编辑");
      return;
    }
    setEditingSale(sale);
    setFormOpen(true);
  };

  return (
    <div className="space-y-6">
      <SaleFormDialog
        open={formOpen}
        onOpenChange={setFormOpen}
        initialData={editingSale}
        onSuccess={() => {
          queryClient.invalidateQueries({ queryKey: ["finished-product-sales"] });
          setEditingSale(null);
        }}
      />

      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">成品销售</h1>
          <p className="text-sm text-muted-foreground">共 {data?.total ?? 0} 条销售记录</p>
        </div>
        <Button onClick={() => { setEditingSale(null); setFormOpen(true); }}>
          <Plus className="h-4 w-4 mr-2" />
          新增销售
        </Button>
      </div>

      <div className="flex gap-4">
        <div className="relative flex-1 max-w-sm">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <Input
            placeholder="搜索客户..."
            value={search}
            onChange={(e) => { setSearch(e.target.value); setPage(1); }}
            className="pl-9"
          />
        </div>
        <Select value={statusFilter} onValueChange={(v) => { setStatusFilter(v ?? "all"); setPage(1); }}>
          <SelectTrigger className="w-[160px]">
            <SelectValue placeholder="收款状态" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">全部状态</SelectItem>
            {Object.entries(statusMap).map(([key, { label }]) => (
              <SelectItem key={key} value={key}>{label}</SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      <div className="border rounded-lg">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>ID</TableHead>
              <TableHead>日期</TableHead>
              <TableHead>客户</TableHead>
              <TableHead>产品</TableHead>
              <TableHead>数量</TableHead>
              <TableHead>净金额</TableHead>
              <TableHead>已付</TableHead>
              <TableHead>未付</TableHead>
              <TableHead>状态</TableHead>
              <TableHead>操作</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {isLoading ? (
              <TableRow><TableCell colSpan={10} className="text-center py-8 text-muted-foreground">加载中...</TableCell></TableRow>
            ) : (data?.items?.length ?? 0) === 0 ? (
              <TableRow><TableCell colSpan={10} className="text-center py-8 text-muted-foreground">暂无数据</TableCell></TableRow>
            ) : (
              data?.items.map((sale) => {
                const statusInfo = statusMap[sale.status] ?? { label: sale.status, color: "" };
                const unpaid = Number(sale.net_amount) - Number(sale.paid_amount);
                return (
                  <TableRow key={sale.id}>
                    <TableCell className="font-medium">
                      {sale.is_locked && <span className="text-orange-500 mr-1">🔒</span>}
                      #{sale.id}
                    </TableCell>
                    <TableCell>{sale.sale_date}</TableCell>
                    <TableCell>{sale.customer_name ?? "-"}</TableCell>
                    <TableCell>
                      <div className="text-sm">{sale.product_name ?? "-"}</div>
                      <div className="text-xs text-muted-foreground">{sale.product_spec ?? ""}</div>
                    </TableCell>
                    <TableCell>{sale.quantity}</TableCell>
                    <TableCell>${Number(sale.net_amount).toLocaleString()}</TableCell>
                    <TableCell className="text-green-600">${Number(sale.paid_amount).toLocaleString()}</TableCell>
                    <TableCell className={cn("font-medium", unpaid > 0 ? "text-orange-600" : "text-muted-foreground")}>
                      ${unpaid.toLocaleString()}
                    </TableCell>
                    <TableCell>
                      <Badge variant="secondary" className={statusInfo.color}>{statusInfo.label}</Badge>
                    </TableCell>
                    <TableCell>
                      <div className="flex gap-1">
                        <Button variant="ghost" size="icon" className="h-8 w-8" onClick={() => handleEdit(sale)} title="编辑" disabled={sale.is_locked}>
                          <Pencil className={cn("h-4 w-4", sale.is_locked && "text-muted-foreground")} />
                        </Button>
                        <Button variant="ghost" size="icon" className="h-8 w-8 text-red-500" onClick={() => handleDelete(sale)} title="删除" disabled={sale.is_locked}>
                          <Trash2 className={cn("h-4 w-4", sale.is_locked && "text-muted-foreground")} />
                        </Button>
                      </div>
                    </TableCell>
                  </TableRow>
                );
              })
            )}
          </TableBody>
        </Table>
      </div>

      {totalPages > 1 && (
        <div className="flex items-center justify-between">
          <div className="text-sm text-muted-foreground">
            显示 {(page - 1) * PAGE_SIZE + 1} - {Math.min(page * PAGE_SIZE, data?.total ?? 0)} / 共 {data?.total ?? 0} 条
          </div>
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

// ==================== 成品销售表单弹窗 ====================

function SaleFormDialog({
  open,
  onOpenChange,
  initialData,
  onSuccess,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  initialData: Sale | null;
  onSuccess: () => void;
}) {
  const queryClient = useQueryClient();
  const [isSubmitting, setIsSubmitting] = useState(false);

  const [saleDate, setSaleDate] = useState("");
  const [customerId, setCustomerId] = useState("");
  const [productId, setProductId] = useState("");
  const [quantity, setQuantity] = useState("");
  const [unitPrice, setUnitPrice] = useState("");
  const [scanFee, setScanFee] = useState("0");
  const [discount, setDiscount] = useState("0");
  const [commission, setCommission] = useState("0");
  const [notes, setNotes] = useState("");

  const grossAmount = (Number(quantity) || 0) * (Number(unitPrice) || 0);
  const netAmount = grossAmount - (Number(scanFee) || 0) - (Number(discount) || 0) - (Number(commission) || 0);

  // 弹窗打开时重置表单
  React.useEffect(() => {
    if (open) {
      resetForm();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open, initialData?.id]);

  const resetForm = () => {
    if (initialData) {
      setSaleDate(initialData.sale_date);
      setCustomerId(String(initialData.customer_id));
      setProductId(String(initialData.product_id));
      setQuantity(String(initialData.quantity));
      setUnitPrice(String(initialData.unit_price));
      setScanFee(String(initialData.scan_fee ?? 0));
      setDiscount(String(initialData.discount ?? 0));
      setCommission(String(initialData.commission ?? 0));
      setNotes(initialData.notes ?? "");
    } else {
      setSaleDate(""); setCustomerId(""); setProductId(""); setQuantity(""); setUnitPrice("");
      setScanFee("0"); setDiscount("0"); setCommission("0"); setNotes("");
    }
  };

  const { data: customersData } = useQuery({
    queryKey: ["customers-for-finished-sale"],
    queryFn: async () => { const res = await api.get("/v1/companies/?type=customer&limit=500"); return res.data; },
    enabled: open,
  });

  const { data: productsData } = useQuery({
    queryKey: ["products-for-finished-sale"],
    queryFn: async () => { const res = await api.get("/v1/products/?category=finished_product&limit=500"); return res.data; },
    enabled: open,
  });

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!saleDate || !customerId || !productId || !quantity || !unitPrice) {
      toast.error("请填写必填字段");
      return;
    }
    setIsSubmitting(true);
    try {
      const payload = {
        sale_date: saleDate,
        customer_id: Number(customerId),
        product_id: Number(productId),
        quantity: Number(quantity),
        unit_price: Number(unitPrice),
        gross_amount: grossAmount,
        net_amount: Math.max(0, netAmount),
        scan_fee: Number(scanFee) || 0,
        discount: Number(discount) || 0,
        commission: Number(commission) || 0,
        notes: notes.trim() || undefined,
      };
      if (initialData) {
        await api.put(`/v1/finished-product-sales/${initialData.id}`, payload);
        toast.success("销售记录更新成功");
      } else {
        await api.post("/v1/finished-product-sales/", payload);
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
      <DialogContent className="max-w-[500px]">
        <DialogHeader>
          <DialogTitle>{initialData ? "编辑销售记录" : "新增销售记录"}</DialogTitle>
        </DialogHeader>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2"><Label>销售日期 *</Label><Input type="date" value={saleDate} onChange={(e) => setSaleDate(e.target.value)} /></div>
            <div className="space-y-2">
              <Label>客户 *</Label>
              <Select value={customerId} onValueChange={setCustomerId}>
                <SelectTrigger><SelectValue placeholder="选择客户" /></SelectTrigger>
                <SelectContent>{customersData?.items?.map((c: any) => <SelectItem key={c.id} value={String(c.id)}>{c.name}</SelectItem>)}</SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label>成品 *</Label>
              <Select value={productId} onValueChange={setProductId}>
                <SelectTrigger><SelectValue placeholder="选择成品" /></SelectTrigger>
                <SelectContent>{productsData?.items?.map((p: any) => <SelectItem key={p.id} value={String(p.id)}>{p.name} {p.spec ?? ""}</SelectItem>)}</SelectContent>
              </Select>
            </div>
            <div className="space-y-2"><Label>数量(件) *</Label><Input type="number" value={quantity} onChange={(e) => setQuantity(e.target.value)} /></div>
            <div className="space-y-2"><Label>单价 *</Label><Input type="number" step="0.0001" value={unitPrice} onChange={(e) => setUnitPrice(e.target.value)} /></div>
            <div className="space-y-2"><Label>扫码费</Label><Input type="number" value={scanFee} onChange={(e) => setScanFee(e.target.value)} /></div>
            <div className="space-y-2"><Label>折扣</Label><Input type="number" value={discount} onChange={(e) => setDiscount(e.target.value)} /></div>
            <div className="space-y-2"><Label>佣金</Label><Input type="number" value={commission} onChange={(e) => setCommission(e.target.value)} /></div>
          </div>
          <div className="bg-muted p-3 rounded-md space-y-1 text-sm">
            <div className="flex justify-between"><span className="text-muted-foreground">毛金额</span><span>${grossAmount.toLocaleString(undefined, { minimumFractionDigits: 2 })}</span></div>
            <div className="flex justify-between font-semibold border-t pt-1"><span>净金额</span><span className="text-primary">${Math.max(0, netAmount).toLocaleString(undefined, { minimumFractionDigits: 2 })}</span></div>
          </div>
          <div className="space-y-2"><Label>备注</Label><Input value={notes} onChange={(e) => setNotes(e.target.value)} placeholder="可选" /></div>
          <DialogFooter>
            <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>取消</Button>
            <Button type="submit" disabled={isSubmitting}>{isSubmitting ? "保存中..." : (initialData ? "保存" : "创建")}</Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
