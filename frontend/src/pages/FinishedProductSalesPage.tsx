import React, { useState, useRef } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
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
  DialogDescription,
} from "@/components/ui/dialog";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  Plus,
  Search,
  Eye,
  Pencil,
  Trash2,
  X,
  DollarSign,
  Receipt,
  AlertTriangle,
  Upload,
  FileSpreadsheet,
  Download,
} from "lucide-react";
import { toast } from "sonner";

// ==================== 状态映射 ====================

const statusMap: Record<string, { label: string; color: string }> = {
  pending: { label: "待收款", color: "bg-red-100 text-red-800" },
  partial_paid: { label: "部分收款", color: "bg-yellow-100 text-yellow-800" },
  fully_paid: { label: "全部收款", color: "bg-green-100 text-green-800" },
  after_sales: { label: "售后中", color: "bg-purple-100 text-purple-800" },
};

const aftersalesTypeMap: Record<string, string> = {
  return: "退货",
  refund: "退款",
  discount: "折扣",
  compensation: "赔偿",
};

const paymentMethodOptions = [
  { value: "cash", label: "现金" },
  { value: "bank_transfer", label: "银行转账" },
  { value: "check", label: "支票" },
  { value: "wechat", label: "微信支付" },
  { value: "alipay", label: "支付宝" },
  { value: "other", label: "其他" },
];

// ==================== 接口定义 ====================

interface Receipt {
  id: number;
  sale_id: number;
  receipt_date: string;
  amount: string;
  payment_method: string;
  bank_account_id: number | null;
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

interface Sale {
  id: number;
  sale_date: string;
  slaughter_date: string | null;  // V3新增
  total_weight_kg: number | null; // V3新增
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
  receipts: Receipt[];
  aftersales: Aftersales[];
  items?: SaleItem[]; // V3新增
}

interface SaleItem {
  id: number;
  item_type: "main" | "accessory" | "gift";
  product_id: number;
  product_name: string;
  weight_kg: number | null;
  quantity: number | null;
  unit_price: number | null;
}

interface SaleListResponse {
  total: number;
  items: Sale[];
  skip: number;
  limit: number;
}

const PAGE_SIZE = 10;

// ==================== 批量导入模板配置 ====================

const FINISHED_PRODUCT_IMPORT_HEADERS = [
  { en: "customer_name", cn: "客户名称" },
  { en: "sale_date", cn: "销售日期" },
  { en: "product_code", cn: "产品编码" },
  { en: "product_name", cn: "产品名称" },
  { en: "quantity", cn: "份数" },
  { en: "unit_price", cn: "单价(USD)" },
  { en: "scan_fee", cn: "扫码费" },
  { en: "discount", cn: "折扣" },
  { en: "notes", cn: "备注" },
];

// ==================== 页面主组件 ====================

export function FinishedProductSalesPage() {
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState<string>("all");
  const [page, setPage] = useState(1);
  const [formOpen, setFormOpen] = useState(false);
  const [detailOpen, setDetailOpen] = useState(false);
  const [detailSale, setDetailSale] = useState<Sale | null>(null);
  const [editingSale, setEditingSale] = useState<Sale | null>(null);
  const queryClient = useQueryClient();

  const { data, isLoading } = useQuery<SaleListResponse>({
    queryKey: ["finished-product-sales", statusFilter, page, search],
    queryFn: async () => {
      const params = new URLSearchParams();
      if (statusFilter && statusFilter !== "all") params.append("status", statusFilter);
      if (search.trim()) params.append("search", search.trim());
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

  const handleView = (sale: Sale) => {
    setDetailSale(sale);
    setDetailOpen(true);
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

      {/* 详情弹窗 */}
      <Dialog open={detailOpen} onOpenChange={setDetailOpen}>
        <DialogContent className="max-w-[800px] max-h-[90vh] overflow-y-auto">
          <DialogHeader className="pb-4 border-b flex flex-row items-center justify-between">
            <div>
              <DialogTitle>成品销售详情</DialogTitle>
              <DialogDescription>
                销售 #{detailSale?.id} · {detailSale?.customer_name}
              </DialogDescription>
            </div>
            <Button variant="ghost" size="icon" className="h-8 w-8" onClick={() => setDetailOpen(false)}>
              <X className="h-4 w-4" />
            </Button>
          </DialogHeader>

          {detailSale && (
            <SaleDetailDialog sale={detailSale} onClose={() => setDetailOpen(false)} />
          )}
        </DialogContent>
      </Dialog>

      {/* 标题栏 */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">成品销售</h1>
          <p className="text-sm text-muted-foreground">共 {data?.total ?? 0} 条销售记录</p>
        </div>
        <div className="flex gap-2">
          <FinishedProductBatchImportButton />
          <Button onClick={() => { setEditingSale(null); setFormOpen(true); }}>
            <Plus className="h-4 w-4 mr-2" />
            新增销售
          </Button>
        </div>
      </div>

      {/* 筛选栏 */}
      <div className="flex gap-4">
        <div className="relative flex-1 max-w-sm">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <Input
            placeholder="搜索客户或产品..."
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

      {/* 数据表格 */}
      <div className="border rounded-lg">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>ID</TableHead>
              <TableHead>日期</TableHead>
              <TableHead>宰杀日期</TableHead>
              <TableHead>客户</TableHead>
              <TableHead>产品</TableHead>
              <TableHead>份数</TableHead>
              <TableHead>净金额</TableHead>
              <TableHead>已付</TableHead>
              <TableHead>未付</TableHead>
              <TableHead>状态</TableHead>
              <TableHead>操作</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {isLoading ? (
              <TableRow>
                <TableCell colSpan={11} className="text-center py-8 text-muted-foreground">加载中...</TableCell>
              </TableRow>
            ) : (data?.items?.length ?? 0) === 0 ? (
              <TableRow>
                <TableCell colSpan={11} className="text-center py-8 text-muted-foreground">暂无数据</TableCell>
              </TableRow>
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
                    <TableCell className="text-sm text-muted-foreground">{sale.slaughter_date || "-"}</TableCell>
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
                      <Badge variant="secondary" className={statusInfo.color}>
                        {statusInfo.label}
                      </Badge>
                    </TableCell>
                    <TableCell>
                      <div className="flex gap-1">
                        <Button variant="ghost" size="icon" className="h-8 w-8" onClick={() => handleView(sale)} title="查看">
                          <Eye className="h-4 w-4" />
                        </Button>
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

      {/* 分页 */}
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

// ==================== 详情弹窗组件 ====================

function SaleDetailDialog({ sale, onClose }: { sale: Sale; onClose: () => void }) {
  const queryClient = useQueryClient();
  const [activeTab, setActiveTab] = useState("info");

  // Receipt form state
  const [receiptFormOpen, setReceiptFormOpen] = useState(false);
  const [receiptDate, setReceiptDate] = useState("");
  const [receiptAmount, setReceiptAmount] = useState("");
  const [receiptMethod, setReceiptMethod] = useState("bank_transfer");
  const [receiptRef, setReceiptRef] = useState("");
  const [receiptNotes, setReceiptNotes] = useState("");

  // Aftersales form state
  const [aftersalesFormOpen, setAftersalesFormOpen] = useState(false);
  const [editingAftersalesId, setEditingAftersalesId] = useState<number | null>(null);
  const [aftersalesDate, setAftersalesDate] = useState("");
  const [aftersalesType, setAftersalesType] = useState("refund");
  const [aftersalesAmount, setAftersalesAmount] = useState("");
  const [aftersalesReason, setAftersalesReason] = useState("");
  const [aftersalesStatus, setAftersalesStatus] = useState("pending");
  const [aftersalesNotes, setAftersalesNotes] = useState("");

  // Refresh detail data
  const refreshDetail = async () => {
    try {
      const res = await api.get(`/v1/finished-product-sales/${sale.id}`);
      // Update the detail sale data in parent would require lifting state,
      // but we can invalidate the list query to refresh
      queryClient.invalidateQueries({ queryKey: ["finished-product-sales"] });
    } catch {
      // silent
    }
  };

  // Create receipt mutation
  const createReceiptMutation = useMutation({
    mutationFn: async (payload: any) => {
      const res = await api.post(`/v1/finished-product-sales/${sale.id}/receipts`, payload);
      return res.data;
    },
    onSuccess: () => {
      toast.success("收款记录添加成功");
      queryClient.invalidateQueries({ queryKey: ["finished-product-sales"] });
      resetReceiptForm();
      setReceiptFormOpen(false);
      refreshDetail();
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.detail ?? "添加失败");
    },
  });

  // Delete receipt mutation
  const deleteReceiptMutation = useMutation({
    mutationFn: async (receiptId: number) => {
      await api.delete(`/v1/finished-product-sales/${sale.id}/receipts/${receiptId}`);
    },
    onSuccess: () => {
      toast.success("收款记录已删除");
      queryClient.invalidateQueries({ queryKey: ["finished-product-sales"] });
      refreshDetail();
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.detail ?? "删除失败");
    },
  });

  // Create aftersales mutation
  const createAftersalesMutation = useMutation({
    mutationFn: async (payload: any) => {
      const res = await api.post(`/v1/finished-product-sales/${sale.id}/aftersales`, payload);
      return res.data;
    },
    onSuccess: () => {
      toast.success(editingAftersalesId ? "售后记录更新成功" : "售后记录添加成功");
      queryClient.invalidateQueries({ queryKey: ["finished-product-sales"] });
      resetAftersalesForm();
      setAftersalesFormOpen(false);
      setEditingAftersalesId(null);
      refreshDetail();
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.detail ?? "操作失败");
    },
  });

  // Update aftersales mutation
  const updateAftersalesMutation = useMutation({
    mutationFn: async ({ id, payload }: { id: number; payload: any }) => {
      const res = await api.put(`/v1/finished-product-sales/${sale.id}/aftersales/${id}`, payload);
      return res.data;
    },
    onSuccess: () => {
      toast.success("售后记录更新成功");
      queryClient.invalidateQueries({ queryKey: ["finished-product-sales"] });
      resetAftersalesForm();
      setAftersalesFormOpen(false);
      setEditingAftersalesId(null);
      refreshDetail();
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.detail ?? "更新失败");
    },
  });

  // Delete aftersales mutation
  const deleteAftersalesMutation = useMutation({
    mutationFn: async (recordId: number) => {
      await api.delete(`/v1/finished-product-sales/${sale.id}/aftersales/${recordId}`);
    },
    onSuccess: () => {
      toast.success("售后记录已删除");
      queryClient.invalidateQueries({ queryKey: ["finished-product-sales"] });
      refreshDetail();
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.detail ?? "删除失败");
    },
  });

  const resetReceiptForm = () => {
    setReceiptDate("");
    setReceiptAmount("");
    setReceiptMethod("bank_transfer");
    setReceiptRef("");
    setReceiptNotes("");
  };

  const resetAftersalesForm = () => {
    setAftersalesDate("");
    setAftersalesType("refund");
    setAftersalesAmount("");
    setAftersalesReason("");
    setAftersalesStatus("pending");
    setAftersalesNotes("");
  };

  const handleReceiptSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!receiptDate || !receiptAmount) {
      toast.error("请填写日期和金额");
      return;
    }
    createReceiptMutation.mutate({
      receipt_date: receiptDate,
      amount: Number(receiptAmount),
      payment_method: receiptMethod,
      reference_no: receiptRef.trim() || null,
      notes: receiptNotes.trim() || null,
    });
  };

  const handleAftersalesSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!aftersalesDate || !aftersalesAmount) {
      toast.error("请填写日期和金额");
      return;
    }
    const payload = {
      record_date: aftersalesDate,
      type: aftersalesType,
      amount: Number(aftersalesAmount),
      reason: aftersalesReason.trim() || null,
      status: aftersalesStatus,
      notes: aftersalesNotes.trim() || null,
    };
    if (editingAftersalesId) {
      updateAftersalesMutation.mutate({ id: editingAftersalesId, payload });
    } else {
      createAftersalesMutation.mutate(payload);
    }
  };

  const startEditAftersales = (a: Aftersales) => {
    setEditingAftersalesId(a.id);
    setAftersalesDate(a.record_date);
    setAftersalesType(a.type);
    setAftersalesAmount(String(a.amount));
    setAftersalesReason(a.reason ?? "");
    setAftersalesStatus(a.status);
    setAftersalesNotes(a.notes ?? "");
    setAftersalesFormOpen(true);
  };

  const unpaid = Number(sale.net_amount) - Number(sale.paid_amount);

  return (
    <div className="py-4">
      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList className="grid w-full grid-cols-3">
          <TabsTrigger value="info">基本信息</TabsTrigger>
          <TabsTrigger value="receipts">
            <Receipt className="h-3 w-3 mr-1" />
            收款记录 ({sale.receipts?.length ?? 0})
          </TabsTrigger>
          <TabsTrigger value="aftersales">
            <AlertTriangle className="h-3 w-3 mr-1" />
            售后记录 ({sale.aftersales?.length ?? 0})
          </TabsTrigger>
        </TabsList>

        {/* 基本信息 Tab */}
        <TabsContent value="info" className="space-y-4 pt-4">
          <div className="grid grid-cols-2 gap-3 text-sm">
            <div><span className="text-muted-foreground">销售ID:</span> <span className="ml-1">#{sale.id}</span></div>
            <div><span className="text-muted-foreground">日期:</span> <span className="ml-1">{sale.sale_date}</span></div>
            <div><span className="text-muted-foreground">客户:</span> <span className="ml-1">{sale.customer_name ?? "-"}</span></div>
            <div><span className="text-muted-foreground">产品:</span> <span className="ml-1">{sale.product_name ?? "-"} {sale.product_spec ?? ""}</span></div>
            <div><span className="text-muted-foreground">份数:</span> <span className="ml-1">{sale.quantity}</span></div>
            <div><span className="text-muted-foreground">单价:</span> <span className="ml-1">${Number(sale.unit_price).toLocaleString()}</span></div>
            <div><span className="text-muted-foreground">销售员:</span> <span className="ml-1">{sale.salesperson_name ?? "-"}</span></div>
            <div><span className="text-muted-foreground">状态:</span> <span className="ml-1">
              <Badge variant="secondary" className={statusMap[sale.status]?.color}>
                {statusMap[sale.status]?.label ?? sale.status}
              </Badge>
            </span></div>
          </div>
          {sale.notes && (
            <div className="text-sm">
              <span className="text-muted-foreground">备注:</span> <span className="ml-1">{sale.notes}</span>
            </div>
          )}
          <div className="bg-muted p-3 rounded-md space-y-2 text-sm">
            <div className="flex justify-between"><span>毛金额</span><span>${Number(sale.gross_amount).toLocaleString()}</span></div>
            {Number(sale.scan_fee) > 0 && <div className="flex justify-between text-red-500"><span>扫码费</span><span>-${Number(sale.scan_fee).toLocaleString()}</span></div>}
            {Number(sale.discount) > 0 && <div className="flex justify-between text-red-500"><span>折扣</span><span>-${Number(sale.discount).toLocaleString()}</span></div>}
            {Number(sale.commission) > 0 && <div className="flex justify-between text-red-500"><span>佣金</span><span>-${Number(sale.commission).toLocaleString()}</span></div>}
            <div className="flex justify-between font-semibold border-t pt-1">
              <span>净金额</span>
              <span>${Number(sale.net_amount).toLocaleString()}</span>
            </div>
            <div className="flex justify-between text-green-600">
              <span>已付</span>
              <span>${Number(sale.paid_amount).toLocaleString()}</span>
            </div>
            <div className="flex justify-between text-orange-600 font-medium">
              <span>未付</span>
              <span>${unpaid.toLocaleString()}</span>
            </div>
          </div>
        </TabsContent>

        {/* 收款记录 Tab */}
        <TabsContent value="receipts" className="space-y-4 pt-4">
          {/* 添加收款表单 */}
          <div className="bg-muted/50 rounded-lg p-4 space-y-3">
            <div className="flex items-center justify-between">
              <h4 className="text-sm font-medium flex items-center gap-1">
                <DollarSign className="h-4 w-4" />
                {receiptFormOpen ? "添加收款" : "收款操作"}
              </h4>
              {!receiptFormOpen && (
                <Button size="sm" onClick={() => setReceiptFormOpen(true)}>
                  <Plus className="h-3 w-3 mr-1" />添加收款
                </Button>
              )}
            </div>
            {receiptFormOpen && (
              <form onSubmit={handleReceiptSubmit} className="space-y-3">
                <div className="grid grid-cols-2 gap-3">
                  <div className="space-y-1">
                    <Label className="text-xs">收款日期 *</Label>
                    <Input type="date" value={receiptDate} onChange={(e) => setReceiptDate(e.target.value)} />
                  </div>
                  <div className="space-y-1">
                    <Label className="text-xs">金额 *</Label>
                    <Input type="number" step="0.01" value={receiptAmount} onChange={(e) => setReceiptAmount(e.target.value)} placeholder="输入金额" />
                  </div>
                  <div className="space-y-1">
                    <Label className="text-xs">支付方式</Label>
                    <Select value={receiptMethod} onValueChange={(v) => setReceiptMethod(v ?? "")}>
                      <SelectTrigger><SelectValue /></SelectTrigger>
                      <SelectContent>
                        {paymentMethodOptions.map((opt) => (
                          <SelectItem key={opt.value} value={opt.value}>{opt.label}</SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                  <div className="space-y-1">
                    <Label className="text-xs">参考号</Label>
                    <Input value={receiptRef} onChange={(e) => setReceiptRef(e.target.value)} placeholder="可选" />
                  </div>
                </div>
                <div className="space-y-1">
                  <Label className="text-xs">备注</Label>
                  <Input value={receiptNotes} onChange={(e) => setReceiptNotes(e.target.value)} placeholder="可选" />
                </div>
                <div className="flex gap-2 justify-end">
                  <Button type="button" variant="ghost" size="sm" onClick={() => { setReceiptFormOpen(false); resetReceiptForm(); }}>取消</Button>
                  <Button type="submit" size="sm" disabled={createReceiptMutation.isPending}>
                    {createReceiptMutation.isPending ? "保存中..." : "保存"}
                  </Button>
                </div>
              </form>
            )}
          </div>

          {/* 收款列表 */}
          {sale.receipts && sale.receipts.length > 0 ? (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead className="text-xs">日期</TableHead>
                  <TableHead className="text-xs">方式</TableHead>
                  <TableHead className="text-xs text-right">金额</TableHead>
                  <TableHead className="text-xs">参考号</TableHead>
                  <TableHead className="text-xs">备注</TableHead>
                  <TableHead className="text-xs text-right">操作</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {sale.receipts.map((r) => (
                  <TableRow key={r.id}>
                    <TableCell className="text-sm">{r.receipt_date}</TableCell>
                    <TableCell className="text-sm">
                      {paymentMethodOptions.find((o) => o.value === r.payment_method)?.label ?? r.payment_method}
                    </TableCell>
                    <TableCell className="text-sm text-right">${Number(r.amount).toLocaleString()}</TableCell>
                    <TableCell className="text-sm">{r.reference_no ?? "-"}</TableCell>
                    <TableCell className="text-sm">{r.notes ?? "-"}</TableCell>
                    <TableCell className="text-sm text-right">
                      <Button
                        variant="ghost"
                        size="icon"
                        className="h-7 w-7 text-red-500"
                        onClick={() => {
                          if (confirm("确定删除此收款记录？")) {
                            deleteReceiptMutation.mutate(r.id);
                          }
                        }}
                        disabled={deleteReceiptMutation.isPending}
                      >
                        <Trash2 className="h-3 w-3" />
                      </Button>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          ) : (
            <div className="text-sm text-muted-foreground text-center py-8">暂无收款记录</div>
          )}
        </TabsContent>

        {/* 售后记录 Tab */}
        <TabsContent value="aftersales" className="space-y-4 pt-4">
          {/* 添加/编辑售后表单 */}
          <div className="bg-muted/50 rounded-lg p-4 space-y-3">
            <div className="flex items-center justify-between">
              <h4 className="text-sm font-medium flex items-center gap-1">
                <AlertTriangle className="h-4 w-4" />
                {aftersalesFormOpen ? (editingAftersalesId ? "编辑售后记录" : "添加售后记录") : "售后操作"}
              </h4>
              {!aftersalesFormOpen && (
                <Button size="sm" onClick={() => { setAftersalesFormOpen(true); setEditingAftersalesId(null); resetAftersalesForm(); }}>
                  <Plus className="h-3 w-3 mr-1" />添加售后
                </Button>
              )}
            </div>
            {aftersalesFormOpen && (
              <form onSubmit={handleAftersalesSubmit} className="space-y-3">
                <div className="grid grid-cols-2 gap-3">
                  <div className="space-y-1">
                    <Label className="text-xs">日期 *</Label>
                    <Input type="date" value={aftersalesDate} onChange={(e) => setAftersalesDate(e.target.value)} />
                  </div>
                  <div className="space-y-1">
                    <Label className="text-xs">类型 *</Label>
                    <Select value={aftersalesType} onValueChange={(v) => setAftersalesType(v ?? "")}>
                      <SelectTrigger><SelectValue /></SelectTrigger>
                      <SelectContent>
                        {Object.entries(aftersalesTypeMap).map(([key, label]) => (
                          <SelectItem key={key} value={key}>{label}</SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                  <div className="space-y-1">
                    <Label className="text-xs">金额 *</Label>
                    <Input type="number" step="0.01" value={aftersalesAmount} onChange={(e) => setAftersalesAmount(e.target.value)} placeholder="输入金额" />
                  </div>
                  <div className="space-y-1">
                    <Label className="text-xs">状态</Label>
                    <Select value={aftersalesStatus} onValueChange={(v) => setAftersalesStatus(v ?? "")}>
                      <SelectTrigger><SelectValue /></SelectTrigger>
                      <SelectContent>
                        <SelectItem value="pending">待处理</SelectItem>
                        <SelectItem value="processing">处理中</SelectItem>
                        <SelectItem value="resolved">已解决</SelectItem>
                        <SelectItem value="closed">已关闭</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                </div>
                <div className="space-y-1">
                  <Label className="text-xs">原因</Label>
                  <Input value={aftersalesReason} onChange={(e) => setAftersalesReason(e.target.value)} placeholder="可选" />
                </div>
                <div className="space-y-1">
                  <Label className="text-xs">备注</Label>
                  <Input value={aftersalesNotes} onChange={(e) => setAftersalesNotes(e.target.value)} placeholder="可选" />
                </div>
                <div className="flex gap-2 justify-end">
                  <Button type="button" variant="ghost" size="sm" onClick={() => { setAftersalesFormOpen(false); setEditingAftersalesId(null); resetAftersalesForm(); }}>取消</Button>
                  <Button type="submit" size="sm" disabled={createAftersalesMutation.isPending || updateAftersalesMutation.isPending}>
                    {createAftersalesMutation.isPending || updateAftersalesMutation.isPending ? "保存中..." : "保存"}
                  </Button>
                </div>
              </form>
            )}
          </div>

          {/* 售后列表 */}
          {sale.aftersales && sale.aftersales.length > 0 ? (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead className="text-xs">日期</TableHead>
                  <TableHead className="text-xs">类型</TableHead>
                  <TableHead className="text-xs text-right">金额</TableHead>
                  <TableHead className="text-xs">原因</TableHead>
                  <TableHead className="text-xs">状态</TableHead>
                  <TableHead className="text-xs text-right">操作</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {sale.aftersales.map((a) => (
                  <TableRow key={a.id}>
                    <TableCell className="text-sm">{a.record_date}</TableCell>
                    <TableCell className="text-sm">{aftersalesTypeMap[a.type] ?? a.type}</TableCell>
                    <TableCell className="text-sm text-right">${Number(a.amount).toLocaleString()}</TableCell>
                    <TableCell className="text-sm">{a.reason ?? "-"}</TableCell>
                    <TableCell className="text-sm">{a.status}</TableCell>
                    <TableCell className="text-sm text-right">
                      <div className="flex gap-1 justify-end">
                        <Button
                          variant="ghost"
                          size="icon"
                          className="h-7 w-7"
                          onClick={() => startEditAftersales(a)}
                          title="编辑"
                        >
                          <Pencil className="h-3 w-3" />
                        </Button>
                        <Button
                          variant="ghost"
                          size="icon"
                          className="h-7 w-7 text-red-500"
                          onClick={() => {
                            if (confirm("确定删除此售后记录？")) {
                              deleteAftersalesMutation.mutate(a.id);
                            }
                          }}
                          disabled={deleteAftersalesMutation.isPending}
                        >
                          <Trash2 className="h-3 w-3" />
                        </Button>
                      </div>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          ) : (
            <div className="text-sm text-muted-foreground text-center py-8">暂无售后记录</div>
          )}
        </TabsContent>
      </Tabs>
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

  // 基础字段
  const [saleDate, setSaleDate] = useState("");
  const [customerId, setCustomerId] = useState("");
  const [productId, setProductId] = useState("");
  const [quantity, setQuantity] = useState("");
  const [unitPrice, setUnitPrice] = useState("");
  const [scanFee, setScanFee] = useState("0");
  const [discount, setDiscount] = useState("0");
  const [commission, setCommission] = useState("0");
  const [notes, setNotes] = useState("");

  // V3新增字段
  const [slaughterDate, setSlaughterDate] = useState("");
  const [totalWeightKg, setTotalWeightKg] = useState("");
  const [items, setItems] = useState<{ item_type: "main" | "accessory" | "gift"; product_id: string; weight_kg: string; quantity: string; unit_price: string }[]>([]);

  const grossAmount = (Number(quantity) || 0) * (Number(unitPrice) || 0);
  const netAmount = grossAmount - (Number(scanFee) || 0) - (Number(discount) || 0) - (Number(commission) || 0);

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
      setSlaughterDate(initialData.slaughter_date ?? "");
      setTotalWeightKg(initialData.total_weight_kg ? String(initialData.total_weight_kg) : "");
      setItems(initialData.items?.map((it) => ({
        item_type: it.item_type,
        product_id: String(it.product_id),
        weight_kg: it.weight_kg ? String(it.weight_kg) : "",
        quantity: it.quantity ? String(it.quantity) : "",
        unit_price: it.unit_price ? String(it.unit_price) : "",
      })) || []);
    } else {
      setSaleDate(""); setCustomerId(""); setProductId(""); setQuantity(""); setUnitPrice("");
      setScanFee("0"); setDiscount("0"); setCommission("0"); setNotes("");
      setSlaughterDate(""); setTotalWeightKg(""); setItems([]);
    }
  };

  const { data: customersData } = useQuery({
    queryKey: ["customers-for-finished-sale"],
    queryFn: async () => { const res = await api.get("/v1/companies/?type=customer&limit=500"); return res.data; },
    enabled: open,
  });

  const { data: productsData } = useQuery({
    queryKey: ["products-for-finished-sale"],
    queryFn: async () => { const res = await api.get("/v1/products/?limit=500"); return res.data; },
    enabled: open,
  });

  // 获取可选宰杀日期
  const { data: slaughterDatesData } = useQuery({
    queryKey: ["slaughter-dates-for-sale"],
    queryFn: async () => {
      const res = await api.get("/v1/finished-product-sales/options/slaughter-dates");
      return res.data;
    },
    enabled: open,
  });

  const slaughterDates = slaughterDatesData || [];
  const allProducts = productsData?.items || [];

  // V3: 自动计算总重量（份数 × 每份重量(g) / 1000）
  React.useEffect(() => {
    if (productId && quantity) {
      const product = allProducts.find((p: any) => String(p.id) === productId);
      if (product?.portion_weight_g) {
        const weightKg = (Number(quantity) * product.portion_weight_g) / 1000;
        setTotalWeightKg(String(weightKg.toFixed(3)));
      }
    }
  }, [productId, quantity, allProducts]);

  function addItem(type: "main" | "accessory" | "gift") {
    setItems([...items, { item_type: type, product_id: "", weight_kg: "", quantity: "", unit_price: "" }]);
  }

  function updateItem(index: number, field: string, value: string) {
    const newItems = [...items];
    (newItems[index] as any)[field] = value;
    setItems(newItems);
  }

  function removeItem(index: number) {
    setItems(items.filter((_, i) => i !== index));
  }

  const selectedSlaughter = slaughterDates.find((d: any) => d.date === slaughterDate);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!saleDate || !customerId || !productId || !quantity || !unitPrice) {
      toast.error("请填写必填字段");
      return;
    }
    setIsSubmitting(true);
    try {
      const payload: any = {
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

      // V3字段
      if (slaughterDate) {
        payload.slaughter_date = slaughterDate;
        payload.total_weight_kg = Number(totalWeightKg) || 0;
      }
      if (items.length > 0) {
        payload.items = items
          .filter((it) => it.product_id)
          .map((it) => ({
            item_type: it.item_type,
            product_id: Number(it.product_id),
            weight_kg: it.item_type === "main" ? Number(it.weight_kg) || 0 : null,
            quantity: it.item_type !== "main" ? Number(it.quantity) || 0 : null,
            unit_price: it.item_type === "main" ? Number(it.unit_price) || 0 : null,
          }));
      }

      if (initialData) {
        await api.put(`/v1/finished-product-sales/${initialData.id}`, payload);
        toast.success("销售记录更新成功");
      } else {
        if (slaughterDate || items.length > 0) {
          await api.post("/v1/finished-product-sales/with-items", payload);
        } else {
          await api.post("/v1/finished-product-sales/", payload);
        }
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
      <DialogContent className="max-w-[700px] w-[95vw] max-h-[90vh] overflow-y-auto p-6">
        <DialogHeader>
          <DialogTitle>{initialData ? "编辑销售记录" : "新增销售记录"}</DialogTitle>
        </DialogHeader>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2"><Label>销售日期 *</Label><Input type="date" value={saleDate} onChange={(e) => setSaleDate(e.target.value)} /></div>
            <div className="space-y-2">
              <Label>客户 *</Label>
              <Select value={customerId} onValueChange={(v) => setCustomerId(v ?? "")}>
                <SelectTrigger><SelectValue placeholder="选择客户" /></SelectTrigger>
                <SelectContent>{customersData?.items?.map((c: any) => <SelectItem key={c.id} value={String(c.id)}>{c.name}</SelectItem>)}</SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label>成品 *</Label>
              <Select value={productId} onValueChange={(v) => setProductId(v ?? "")}>
                <SelectTrigger><SelectValue placeholder="选择成品" /></SelectTrigger>
                <SelectContent>{allProducts.map((p: any) => <SelectItem key={p.id} value={String(p.id)}>{p.name} {p.spec ?? ""}</SelectItem>)}</SelectContent>
              </Select>
            </div>
            <div className="space-y-2"><Label>份数 *</Label><Input type="number" value={quantity} onChange={(e) => setQuantity(e.target.value)} /></div>
            <div className="space-y-2"><Label>单价 *</Label><Input type="number" step="0.0001" value={unitPrice} onChange={(e) => setUnitPrice(e.target.value)} /></div>
            <div className="space-y-2"><Label>扫码费</Label><Input type="number" value={scanFee} onChange={(e) => setScanFee(e.target.value)} /></div>
            <div className="space-y-2"><Label>折扣</Label><Input type="number" value={discount} onChange={(e) => setDiscount(e.target.value)} /></div>
            <div className="space-y-2"><Label>佣金</Label><Input type="number" value={commission} onChange={(e) => setCommission(e.target.value)} /></div>
          </div>

          {/* V3: 宰杀日期选择 */}
          <div className="space-y-2">
            <Label>关联宰杀日期（可选）</Label>
            <Select value={slaughterDate} onValueChange={(v) => setSlaughterDate(v ?? "")}>
              <SelectTrigger><SelectValue placeholder="选择已锁定的宰杀日期" /></SelectTrigger>
              <SelectContent>
                <SelectItem value="">不关联</SelectItem>
                {slaughterDates.map((d: any) => (
                  <SelectItem key={d.date} value={d.date}>
                    {d.date} (可用{d.available_meat_kg?.toFixed?.(1) ?? d.available_meat_kg}kg, 成本{d.cost_price_per_kg?.toFixed?.(2) ?? d.cost_price_per_kg}元/kg)
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            {selectedSlaughter && (
              <p className="text-xs text-muted-foreground">
                已选择：{selectedSlaughter.date} · 可用肉 {selectedSlaughter.available_meat_kg?.toFixed?.(1) ?? selectedSlaughter.available_meat_kg}kg · 成本 ¥{selectedSlaughter.cost_price_per_kg?.toFixed?.(2) ?? selectedSlaughter.cost_price_per_kg}/kg
              </p>
            )}
          </div>

          {slaughterDate && (
            <div className="space-y-2">
              <Label>销售总重量(kg)</Label>
              <Input type="number" step="0.001" value={totalWeightKg} onChange={(e) => setTotalWeightKg(e.target.value)} placeholder="输入销售总重量" />
            </div>
          )}

          {/* V3: 销售子项 */}
          <div className="space-y-3 border rounded-md p-3">
            <p className="text-sm font-medium">销售子项（可选）</p>
            {items.length === 0 && <p className="text-xs text-muted-foreground">暂无子项，点击下方按钮添加</p>}
            {items.map((it, idx) => (
              <div key={idx} className="grid grid-cols-[1fr_1fr_1fr_1fr_auto] gap-2 items-end">
                <div className="space-y-1">
                  <Label className="text-xs">类型</Label>
                  <Select value={it.item_type} onValueChange={(v: any) => updateItem(idx, "item_type", v)}>
                    <SelectTrigger className="h-8"><SelectValue /></SelectTrigger>
                    <SelectContent>
                      <SelectItem value="main">正品</SelectItem>
                      <SelectItem value="accessory">配套</SelectItem>
                      <SelectItem value="gift">赠品</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <div className="space-y-1">
                  <Label className="text-xs">产品</Label>
                  <Select value={it.product_id} onValueChange={(v) => updateItem(idx, "product_id", v ?? "")}>
                    <SelectTrigger className="h-8"><SelectValue placeholder="选择" /></SelectTrigger>
                    <SelectContent>{allProducts.map((p: any) => <SelectItem key={p.id} value={String(p.id)}>{p.name}</SelectItem>)}</SelectContent>
                  </Select>
                </div>
                {it.item_type === "main" ? (
                  <>
                    <div className="space-y-1"><Label className="text-xs">重量(kg)</Label><Input className="h-8" type="number" step="0.001" value={it.weight_kg} onChange={(e) => updateItem(idx, "weight_kg", e.target.value)} /></div>
                    <div className="space-y-1"><Label className="text-xs">单价</Label><Input className="h-8" type="number" step="0.01" value={it.unit_price} onChange={(e) => updateItem(idx, "unit_price", e.target.value)} /></div>
                  </>
                ) : (
                  <>
                    <div className="space-y-1"><Label className="text-xs">份数</Label><Input className="h-8" type="number" value={it.quantity} onChange={(e) => updateItem(idx, "quantity", e.target.value)} /></div>
                    <div />
                  </>
                )}
                <Button type="button" variant="ghost" size="icon" className="h-8 w-8" onClick={() => removeItem(idx)}><Trash2 className="h-4 w-4" /></Button>
              </div>
            ))}
            <div className="flex gap-2">
              <Button type="button" variant="outline" size="sm" onClick={() => addItem("main")}>+ 正品</Button>
              <Button type="button" variant="outline" size="sm" onClick={() => addItem("accessory")}>+ 配套</Button>
              <Button type="button" variant="outline" size="sm" onClick={() => addItem("gift")}>+ 赠品</Button>
            </div>
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

// ==================== 批量导入按钮组件 ====================

function FinishedProductBatchImportButton() {
  const queryClient = useQueryClient();
  const [isUploading, setIsUploading] = useState(false);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [previewData, setPreviewData] = useState<any[]>([]);
  const [previewHeaders, setPreviewHeaders] = useState<string[]>([]);
  const [previewErrors, setPreviewErrors] = useState<string[]>([]);
  const [parsedRows, setParsedRows] = useState<any[]>([]);
  const [importFile, setImportFile] = useState<File | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const downloadTemplate = () => {
    const headers = FINISHED_PRODUCT_IMPORT_HEADERS.map((h) => h.cn).join(",");
    const sample = FINISHED_PRODUCT_IMPORT_HEADERS.map(() => "").join(",");
    const csvContent = `data:text/csv;charset=utf-8,\uFEFF${headers}\n${sample}`;
    const encodedUri = encodeURI(csvContent);
    const link = document.createElement("a");
    link.setAttribute("href", encodedUri);
    link.setAttribute("download", "成品销售导入模板.csv");
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    toast.success("模板已下载");
  };

  const parseCSV = (text: string) => {
    const lines = text.trim().split("\n");
    if (lines.length < 2) {
      throw new Error("文件内容为空，至少需要表头+一行数据");
    }

    const rawHeaders = lines[0].split(",").map((h) => h.trim().replace(/^\uFEFF/, ""));
    const headerMap: Record<string, string> = {};
    const displayHeaders: string[] = [];

    rawHeaders.forEach((h) => {
      const found = FINISHED_PRODUCT_IMPORT_HEADERS.find((th) => th.cn === h || th.en === h);
      if (found) {
        headerMap[h] = found.en;
        displayHeaders.push(found.cn);
      } else {
        headerMap[h] = h;
        displayHeaders.push(h);
      }
    });

    const rows = lines
      .slice(1)
      .map((line, idx) => {
        const cells = line.split(",").map((c) => c.trim());
        const row: Record<string, any> = {};
        rawHeaders.forEach((h, i) => {
          const key = headerMap[h] || h;
          row[key] = cells[i] || "";
        });
        row.__line = idx + 2;
        return row;
      })
      .filter((r) => Object.values(r).some((v) => String(v).trim() !== "" && v !== r.__line));

    return {
      headers: displayHeaders,
      rawHeaders: rawHeaders.map((h) => headerMap[h] || h),
      rows,
    };
  };

  const validateRows = (rows: any[]) => {
    const errors: string[] = [];
    rows.forEach((row) => {
      if (!row.customer_name) {
        errors.push(`第${row.__line}行：客户名称不能为空`);
      }
      if (!row.sale_date) {
        errors.push(`第${row.__line}行：销售日期不能为空`);
      }
      if (!row.product_code && !row.product_name) {
        errors.push(`第${row.__line}行：产品编码和产品名称至少填一个`);
      }
      if (!row.quantity || isNaN(Number(row.quantity)) || Number(row.quantity) <= 0) {
        errors.push(`第${row.__line}行：份数必须是大于0的数字`);
      }
      if (!row.unit_price || isNaN(Number(row.unit_price))) {
        errors.push(`第${row.__line}行：单价必须是有效数字`);
      }
    });
    return errors;
  };

  const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setImportFile(file);
    setIsUploading(true);
    try {
      const text = await file.text();
      const { headers, rows } = parseCSV(text);

      if (rows.length === 0) {
        toast.error("未解析到有效数据行");
        setImportFile(null);
        return;
      }

      const errors = validateRows(rows);
      setPreviewHeaders(headers);
      setPreviewData(rows.slice(0, 5));
      setPreviewErrors(errors);
      setParsedRows(rows);
    } catch (error: any) {
      toast.error(error.message || "解析失败");
      setImportFile(null);
    } finally {
      setIsUploading(false);
      if (fileInputRef.current) {
        fileInputRef.current.value = "";
      }
    }
  };

  const handleClearImport = () => {
    setImportFile(null);
    setPreviewData([]);
    setParsedRows([]);
    setPreviewErrors([]);
    setPreviewHeaders([]);
    if (fileInputRef.current) {
      fileInputRef.current.value = "";
    }
  };

  const handleConfirmImport = async () => {
    if (previewErrors.length > 0) {
      toast.error("请先修正数据错误");
      return;
    }

    setIsUploading(true);
    try {
      const res = await api.post("/v1/finished-product-sales/batch-import", {
        rows: parsedRows,
      });
      const result = res.data;
      toast.success(`导入完成：新增 ${result.created || 0} 条，更新 ${result.updated || 0} 条`);
      queryClient.invalidateQueries({ queryKey: ["finished-product-sales"] });
      setDialogOpen(false);
      handleClearImport();
    } catch (error: any) {
      toast.error(error.response?.data?.detail || error.message || "导入失败");
    } finally {
      setIsUploading(false);
    }
  };

  return (
    <>
      <Button variant="outline" size="sm" onClick={() => setDialogOpen(true)}>
        <Upload className="h-4 w-4 mr-2" />
        批量导入
      </Button>

      <Dialog open={dialogOpen} onOpenChange={(v) => { if (!v) { setDialogOpen(false); handleClearImport(); } }}>
        <DialogContent className="max-w-[900px] max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <FileSpreadsheet className="h-5 w-5" />
              批量导入成品销售记录
            </DialogTitle>
          </DialogHeader>

          <div className="space-y-4 py-4">
            <div
              className="border-2 border-dashed border-gray-300 rounded-lg p-8 text-center cursor-pointer hover:border-blue-400 hover:bg-blue-50/50 transition-colors"
              onClick={() => fileInputRef.current?.click()}
            >
              <input
                ref={fileInputRef}
                type="file"
                accept=".csv"
                className="hidden"
                onChange={handleFileChange}
              />
              <Upload className="w-12 h-12 text-gray-400 mx-auto mb-4" />
              <p className="text-gray-600 mb-2">
                {importFile ? importFile.name : "点击或拖拽 CSV 文件到此处"}
              </p>
              <p className="text-sm text-gray-400">支持 .csv 格式（UTF-8 编码）</p>
            </div>

            <div className="text-sm text-gray-600 space-y-2">
              <div className="flex items-center justify-between">
                <p className="font-medium">CSV 格式要求（第一行标题，数据从第二行开始）：</p>
                <Button variant="ghost" size="sm" onClick={downloadTemplate}>
                  <Download className="h-4 w-4 mr-2" />
                  下载模板
                </Button>
              </div>
              <div className="bg-slate-50 p-3 rounded text-xs font-mono overflow-x-auto">
                {FINISHED_PRODUCT_IMPORT_HEADERS.map((h) => h.cn).join(" | ")}
              </div>
              <p className="text-xs text-gray-500">
                请使用中文表头或英文表头，系统会自动匹配字段
              </p>
            </div>

            {previewErrors.length > 0 && (
              <div className="space-y-2">
                <div className="flex items-center gap-2 text-red-500 font-medium text-sm">
                  <AlertTriangle className="h-4 w-4" />
                  发现 {previewErrors.length} 个问题，请修正后重新上传
                </div>
                <div className="bg-red-50 rounded-lg p-3 space-y-1 max-h-32 overflow-y-auto">
                  {previewErrors.map((err, i) => (
                    <p key={i} className="text-xs text-red-600">{err}</p>
                  ))}
                </div>
              </div>
            )}

            {previewData.length > 0 && (
              <div className="border rounded-lg overflow-hidden">
                <div className="bg-slate-50 px-3 py-2 text-sm font-medium flex items-center justify-between">
                  <span>导入预览</span>
                  <Badge variant="secondary">{parsedRows.length} 条</Badge>
                </div>
                <div className="max-h-60 overflow-y-auto">
                  <Table>
                    <TableHeader className="bg-muted sticky top-0">
                      <TableRow>
                        {previewHeaders.map((key) => (
                          <TableHead key={key} className="text-xs whitespace-nowrap">{key}</TableHead>
                        ))}
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {previewData.map((row, i) => (
                        <TableRow key={i}>
                          {previewHeaders.map((key, j) => {
                            const rawKey = FINISHED_PRODUCT_IMPORT_HEADERS.find((th) => th.cn === key)?.en || key;
                            const val = row[rawKey] || "";
                            const hasError = previewErrors.some(
                              (e) => e.includes(`第${row.__line}行`) && !val
                            );
                            return (
                              <TableCell key={j} className="text-xs max-w-[120px] truncate" title={String(val)}>
                                {hasError ? (
                                  <Badge variant="destructive" className="text-[10px]">必填</Badge>
                                ) : (
                                  String(val) || "-"
                                )}
                              </TableCell>
                            );
                          })}
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                  {parsedRows.length > 5 && (
                    <div className="px-2 py-2 text-xs text-gray-500 text-center bg-muted/30">
                      ... 还有 {parsedRows.length - 5} 条数据
                    </div>
                  )}
                </div>
              </div>
            )}
          </div>

          <DialogFooter className="gap-2">
            <Button variant="outline" onClick={() => { setDialogOpen(false); handleClearImport(); }}>
              <X className="h-4 w-4 mr-2" />
              取消
            </Button>
            {importFile && (
              <Button variant="ghost" onClick={handleClearImport} disabled={isUploading}>
                重新选择
              </Button>
            )}
            <Button
              onClick={handleConfirmImport}
              disabled={isUploading || parsedRows.length === 0 || previewErrors.length > 0}
            >
              {isUploading ? "导入中..." : `确认导入 (${parsedRows.length} 条)`}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
}
