import React, { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter,
} from "@/components/ui/dialog";
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from "@/components/ui/select";
import { Badge } from "@/components/ui/badge";
import { Checkbox } from "@/components/ui/checkbox";
import { toast } from "sonner";
import {
  Search, Plus, Package, Eye, Trash2, Pencil, Banknote,
  ChevronDown, ChevronUp, Download, ArrowDown
} from "lucide-react";
import { cn } from "@/lib/utils";
import MaterialPurchaseDialog from "@/components/material/MaterialPurchaseDialog";

// ==================== 类型 ====================
interface MaterialPurchaseOrder {
  id: number;
  order_no: string;
  order_date: string;
  supplier_id: number;
  supplier_name: string;
  actual_total: number;
  status: string;
  payment_status: string;
  warehouse_name?: string;
  item_count: number;
  batch_no?: string;
  total_boxes: number;
  total_qty: number;
  unit?: string;
  product_names?: string[];
}

interface MaterialPurchaseItem {
  id: number;
  product_id: number;
  product_name: string;
  product_code: string;
  box_count: number;
  items_per_box: number;
  total_qty: number;
  unit: string;
  quoted_unit_price: number | null;
  quoted_amount: number | null;
  actual_amount: number;
  actual_unit_price: number;
  received_qty: number;
  is_fully_received: boolean;
  batch_no?: string;
}

interface PurchaseOrderDetail extends MaterialPurchaseOrder {
  items: MaterialPurchaseItem[];
  quoted_total: number | null;
  paid_amount: number;
  warehouse_id: number | null;
  notes: string | null;
}

interface InboundItem {
  item_id: number;
  product_id: number;
  product_name: string;
  product_code: string;
  total_qty: number;
  received_qty: number;
  unit: string;
  inbound_qty: number;
  actual_unit_price: number;
  inbound_date?: string;
}

interface BankAccount {
  id: number;
  account_name: string;
  bank_name: string;
}

// ==================== 辅助函数 ====================
const getStatusBadge = (status: string) => {
  const map: Record<string, string> = {
    pending: "bg-yellow-100 text-yellow-800",
    partial_inbound: "bg-orange-100 text-orange-800",
    completed: "bg-green-100 text-green-800",
    cancelled: "bg-gray-100 text-gray-600",
  };
  const labelMap: Record<string, string> = {
    pending: "待入库",
    partial_inbound: "部分入库",
    completed: "已完成",
    cancelled: "已取消",
  };
  return { className: map[status] || "bg-gray-100", label: labelMap[status] || status };
};

const getPaymentStatusBadge = (status: string) => {
  const map: Record<string, { className: string; label: string }> = {
    unpaid: { className: "bg-red-100 text-red-700", label: "未付款" },
    partial: { className: "bg-yellow-100 text-yellow-700", label: "部分付款" },
    paid: { className: "bg-green-100 text-green-700", label: "已付款" },
  };
  return map[status] || { className: "bg-gray-100 text-gray-600", label: status };
};

const fmtMoney = (v: number | string | null) => {
  if (v == null) return "-";
  const n = typeof v === "string" ? parseFloat(v) : v;
  if (isNaN(n)) return "-";
  return n.toLocaleString("zh-CN", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
};

const PAGE_SIZE = 10;

// ==================== 主组件 ====================
export default function MaterialPurchasePage() {
  const qc = useQueryClient();
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState<string>("all");
  const [page, setPage] = useState(1);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [detailDialogOpen, setDetailDialogOpen] = useState(false);
  const [selectedOrder, setSelectedOrder] = useState<PurchaseOrderDetail | null>(null);
  const [deleteId, setDeleteId] = useState<number | null>(null);
  const [selectedIds, setSelectedIds] = useState<Set<number>>(new Set());
  const [editDialogOpen, setEditDialogOpen] = useState(false);
  const [editOrderId, setEditOrderId] = useState<number | null>(null);
  const [paymentDialogOpen, setPaymentDialogOpen] = useState(false);
  const [paymentOrder, setPaymentOrder] = useState<PurchaseOrderDetail | null>(null);
  const [paymentAmount, setPaymentAmount] = useState("");
  const [paymentBankAccountId, setPaymentBankAccountId] = useState<number | "">("");
  const [paymentLoading, setPaymentLoading] = useState(false);
  const [batchDeleteDialogOpen, setBatchDeleteDialogOpen] = useState(false);
  const [selectedRow, setSelectedRow] = useState<MaterialPurchaseOrder | null>(null);
  const [selectedRowDetail, setSelectedRowDetail] = useState<PurchaseOrderDetail | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);

  const [inboundDialogOpen, setInboundDialogOpen] = useState(false);
  const [inboundOrder, setInboundOrder] = useState<PurchaseOrderDetail | null>(null);
  const [inboundItems, setInboundItems] = useState<InboundItem[]>([]);
  const [inboundLoading, setInboundLoading] = useState(false);

  // 查询采购单列表
  const { data: orders = [], isLoading } = useQuery<MaterialPurchaseOrder[]>({
    queryKey: ["material-purchase-orders", statusFilter],
    queryFn: async () => {
      const params = new URLSearchParams();
      if (statusFilter !== "all") params.append("status", statusFilter);
      const res = await api.get(`/v1/material-purchases?${params.toString()}`);
      // 后端返回 { total, items, skip, limit }，提取 items 数组
      return res.data?.items || [];
    },
  });

  // 查询银行账户列表
  const { data: bankAccounts = [] } = useQuery<BankAccount[]>({
    queryKey: ["bank-accounts"],
    queryFn: async () => {
      const res = await api.get("/v1/finance/bank-accounts?limit=100");
      return Array.isArray(res.data) ? res.data : (res.data?.items || []);
    },
  });

  // 查询采购单详情
  const fetchOrderDetail = async (id: number): Promise<PurchaseOrderDetail> => {
    const res = await api.get(`/v1/material-purchases/${id}`);
    return res.data;
  };

  // 删除采购单
  const deleteMutation = useMutation({
    mutationFn: async (id: number) => {
      await api.delete(`/v1/material-purchases/${id}`);
    },
    onSuccess: () => {
      toast.success("删除成功");
      setSelectedIds((prev) => {
        const next = new Set(prev);
        next.delete(deleteId!);
        return next;
      });
      qc.invalidateQueries({ queryKey: ["material-purchase-orders"] });
      setDeleteId(null);
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.detail || "删除失败");
    },
  });

  // 批量删除
  const batchDeleteMutation = useMutation({
    mutationFn: async (ids: number[]) => {
      const res = await api.post("/v1/material-purchases/batch-delete", { ids });
      return res.data;
    },
    onSuccess: (data) => {
      if (data?.failed && data.failed.length > 0) {
        toast.error(`成功删除 ${data.deleted} 条，失败 ${data.failed.length} 条`);
      } else {
        toast.success("批量删除成功");
      }
      setSelectedIds(new Set());
      qc.invalidateQueries({ queryKey: ["material-purchase-orders"] });
      setBatchDeleteDialogOpen(false);
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.detail || "批量删除失败");
    },
  });

  // 收款
  const paymentMutation = useMutation({
    mutationFn: async ({ id, amount, bank_account_id }: { id: number; amount: number; bank_account_id: number }) => {
      const res = await api.post(`/v1/material-purchases/${id}/payment`, { amount, bank_account_id });
      return res.data;
    },
    onSuccess: () => {
      toast.success("收款成功");
      setPaymentDialogOpen(false);
      setPaymentOrder(null);
      setPaymentAmount("");
      setPaymentBankAccountId("");
      qc.invalidateQueries({ queryKey: ["material-purchase-orders"] });
      qc.invalidateQueries({ queryKey: ["companies"] });
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.detail || "收款失败");
    },
  });

  const filtered = orders.filter((o) => {
    if (!search) return true;
    const s = search.toLowerCase();
    return (
      o.order_no.toLowerCase().includes(s) ||
      o.supplier_name.toLowerCase().includes(s)
    );
  });

  const totalPages = Math.ceil(filtered.length / PAGE_SIZE) || 1;
  const pageData = filtered.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE);

  const totalBoxes = filtered.reduce((sum, o) => sum + (o.total_boxes || 0), 0);
  const totalQty = filtered.reduce((sum, o) => sum + (o.total_qty || 0), 0);
  const totalAmount = filtered.reduce((sum, o) => sum + (o.actual_total || 0), 0);
  const pendingCount = filtered.filter((o) => o.status === "pending").length;

  // 勾选相关
  const toggleSelectAll = () => {
    if (selectedIds.size === pageData.length) setSelectedIds(new Set());
    else setSelectedIds(new Set(pageData.map((s) => s.id)));
  };
  const toggleSelect = (id: number, checked: boolean | "indeterminate") => {
    if (checked === "indeterminate") return;
    const newSet = new Set(selectedIds);
    if (checked) newSet.add(id);
    else newSet.delete(id);
    setSelectedIds(newSet);
  };

  const hasSelection = selectedIds.size > 0;
  const single = selectedIds.size === 1;
  const multi = selectedIds.size > 1;
  const selectedSales = hasSelection
    ? orders.filter((s) => selectedIds.has(s.id))
    : [];
  const singleSale = single ? selectedSales[0] : null;

  const handleViewDetail = async (order: MaterialPurchaseOrder) => {
    const detail = await fetchOrderDetail(order.id);
    setSelectedOrder(detail);
    setDetailDialogOpen(true);
  };

  const handleEdit = async (order: MaterialPurchaseOrder) => {
    setEditOrderId(order.id);
    setEditDialogOpen(true);
  };

  const handlePaymentOpen = async (order: MaterialPurchaseOrder) => {
    const detail = await fetchOrderDetail(order.id);
    setPaymentOrder(detail);
    const remaining = Math.max(0, (detail.actual_total || 0) - (detail.paid_amount || 0));
    setPaymentAmount(remaining > 0 ? remaining.toFixed(2) : "");
    setPaymentBankAccountId("");
    setPaymentDialogOpen(true);
  };

  const handleInboundOpen = async (order: MaterialPurchaseOrder) => {
    const detail = await fetchOrderDetail(order.id);
    setInboundOrder(detail);
    setInboundItems(
      detail.items.map((item) => ({
        item_id: item.id,
        product_id: item.product_id,
        product_name: item.product_name,
        product_code: item.product_code,
        total_qty: item.total_qty,
        received_qty: item.received_qty,
        unit: item.unit,
        inbound_qty: item.total_qty - item.received_qty,
        actual_unit_price: item.actual_unit_price,
      }))
    );
    setInboundDialogOpen(true);
  };

  const handleInboundSave = async () => {
    if (!inboundOrder) return;
    const items = inboundItems.filter((i) => i.inbound_qty > 0);
    if (items.length === 0) {
      toast.error("请至少输入一个入库数量");
      return;
    }
    setInboundLoading(true);
    try {
      const res = await api.post(`/v1/material-purchases/${inboundOrder.id}/inbound`, items);
      toast.success(res.data?.message || "入库成功");
      setInboundDialogOpen(false);
      setInboundOrder(null);
      setInboundItems([]);
      qc.invalidateQueries({ queryKey: ["material-purchase-orders"] });
      qc.invalidateQueries({ queryKey: ["warehouse-v2-stocks"] });
    } catch (error: any) {
      toast.error(error.response?.data?.detail || "入库失败");
    } finally {
      setInboundLoading(false);
    }
  };

  const handlePaymentSave = async () => {
    if (!paymentOrder) return;
    const amount = Number(paymentAmount);
    if (amount <= 0) {
      toast.error("收款金额必须大于0");
      return;
    }
    if (!paymentBankAccountId) {
      toast.error("请选择银行账户");
      return;
    }
    setPaymentLoading(true);
    try {
      paymentMutation.mutate({ id: paymentOrder.id, amount, bank_account_id: Number(paymentBankAccountId) });
    } finally {
      setPaymentLoading(false);
    }
  };

  const handleBatchDelete = () => {
    if (selectedIds.size === 0) {
      toast.error("请先选择要删除的记录");
      return;
    }
    setBatchDeleteDialogOpen(true);
  };

  const confirmBatchDelete = () => {
    batchDeleteMutation.mutate(Array.from(selectedIds));
  };

  const handleSingleDelete = (id: number) => {
    setDeleteId(id);
  };

  return (
    <div className="h-full flex flex-col gap-4 p-4">
      {/* 标题栏 */}
      <div className="flex items-center justify-between">
        <h1 className="text-lg font-bold flex items-center gap-2">
          <Package className="w-5 h-5" />
          辅料采购入库
        </h1>
      </div>

      {/* 搜索 + 筛选 */}
      <div className="flex items-center gap-3">
        <div className="relative flex-1 max-w-sm">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
          <Input
            className="pl-9"
            placeholder="搜索采购单号/供应商..."
            value={search}
            onChange={(e) => {
              setSearch(e.target.value);
              setPage(1);
            }}
          />
        </div>
        <select
          value={statusFilter}
          onChange={(e) => {
            setStatusFilter(e.target.value);
            setPage(1);
          }}
          className="h-10 rounded-md border border-input bg-background px-3 py-2 text-sm"
        >
          <option value="all">全部状态</option>
          <option value="pending">待入库</option>
          <option value="partial_inbound">部分入库</option>
          <option value="completed">已完成</option>
          <option value="cancelled">已取消</option>
        </select>
      </div>

      {/* 操作栏 */}
      <div className={cn("flex items-center gap-2 flex-wrap p-2 rounded-md border transition-colors", hasSelection ? "bg-primary/5 border-primary/20" : "border-transparent")}>
        <Button size="sm" variant="outline" onClick={() => setDialogOpen(true)}>
          <Plus className="h-4 w-4 mr-1" />
          辅料采购
        </Button>
        <Button size="sm" variant="outline">
          <Download className="h-4 w-4 mr-1" />
          导出
        </Button>
        {hasSelection && <div className="h-6 w-px bg-border" />}
        <Button
          size="sm"
          variant="ghost"
          disabled={!single}
          onClick={() => singleSale && handleViewDetail(singleSale)}
        >
          <Eye className="h-4 w-4 mr-1" />
          查看
        </Button>
        <Button
          size="sm"
          variant="ghost"
          disabled={!single || singleSale?.status !== "pending"}
          onClick={() => singleSale && handleEdit(singleSale)}
        >
          <Pencil className="h-4 w-4 mr-1" />
          编辑
        </Button>
        <Button
          size="sm"
          variant="ghost"
          className="text-blue-600"
          disabled={!single || (singleSale?.status !== "pending" && singleSale?.status !== "partial_inbound")}
          onClick={() => singleSale && handleInboundOpen(singleSale)}
        >
          <ArrowDown className="h-4 w-4 mr-1" />
          入库
        </Button>
        <Button
          size="sm"
          variant="ghost"
          className="text-green-600"
          disabled={
            !single ||
            singleSale?.payment_status === "paid" ||
            singleSale?.status === "cancelled"
          }
          onClick={() => singleSale && handlePaymentOpen(singleSale)}
        >
          <Banknote className="h-4 w-4 mr-1" />
          收款
        </Button>
        <Button
          size="sm"
          variant="ghost"
          className="text-red-500"
          disabled={!hasSelection}
          onClick={multi ? handleBatchDelete : () => singleSale && handleSingleDelete(singleSale.id)}
        >
          <Trash2 className="h-4 w-4 mr-1" />
          {multi ? "批量删除" : "删除"}
        </Button>
      </div>

      {/* 列表区 */}
      <div className="flex-1 flex flex-col min-h-0 border rounded-lg overflow-hidden">
        {isLoading ? (
          <div className="flex-1 flex items-center justify-center text-gray-400">
            加载中...
          </div>
        ) : (
          <div className="flex-1 overflow-auto">
            <table className="w-full text-sm">
              <thead className="bg-gray-50 sticky top-0 z-10">
                <tr>
                  <th className="px-3 py-2 w-[40px]">
                    <Checkbox
                      checked={
                        pageData.length > 0 && selectedIds.size === pageData.length
                      }
                      onCheckedChange={toggleSelectAll}
                    />
                  </th>
                  <th className="px-3 py-2 text-left whitespace-nowrap">采购单号</th>
                  <th className="px-3 py-2 text-left whitespace-nowrap">日期</th>
                  <th className="px-3 py-2 text-left whitespace-nowrap">供应商</th>
                  <th className="px-3 py-2 text-left whitespace-nowrap">产品</th>
                  <th className="px-3 py-2 text-left whitespace-nowrap">批次</th>
                  <th className="px-3 py-2 text-right whitespace-nowrap">箱数</th>
                  <th className="px-3 py-2 text-right whitespace-nowrap">数量</th>
                  <th className="px-3 py-2 text-center whitespace-nowrap">单位</th>
                  <th className="px-3 py-2 text-right whitespace-nowrap">金额(元)</th>
                  <th className="px-3 py-2 text-center whitespace-nowrap">状态</th>
                  <th className="px-3 py-2 text-center whitespace-nowrap">付款</th>
                </tr>
              </thead>
              <tbody>
                {pageData.length === 0 && (
                  <tr>
                    <td
                      colSpan={12}
                      className="px-4 py-8 text-center text-gray-400"
                    >
                      暂无采购记录
                    </td>
                  </tr>
                )}
                {pageData.map((order) => (
                  <tr
                    key={order.id}
                    className={cn(
                      "border-t hover:bg-gray-50 cursor-pointer",
                      selectedIds.has(order.id) && "bg-primary/5",
                      selectedRow?.id === order.id && "bg-primary/10"
                    )}
                    onClick={() => {
                      setSelectedRow(order);
                      setSelectedIds(new Set([order.id]));
                      // 获取详情
                      setDetailLoading(true);
                      fetchOrderDetail(order.id)
                        .then((detail) => setSelectedRowDetail(detail))
                        .finally(() => setDetailLoading(false));
                    }}
                  >
                    <td className="px-3 py-2" onClick={(e) => e.stopPropagation()}>
                      <Checkbox
                        checked={selectedIds.has(order.id)}
                        onCheckedChange={(checked) =>
                          toggleSelect(order.id, checked)
                        }
                      />
                    </td>
                    <td
                      className="px-3 py-2 font-mono text-blue-600 cursor-pointer hover:underline whitespace-nowrap"
                      onClick={() => handleViewDetail(order)}
                    >
                      {order.order_no}
                    </td>
                    <td className="px-3 py-2 whitespace-nowrap">
                      {order.order_date}
                    </td>
                    <td className="px-3 py-2 whitespace-nowrap">
                      {order.supplier_name}
                    </td>
                    <td className="px-3 py-2 text-xs text-gray-600 whitespace-nowrap">
                      {order.product_names?.length
                        ? order.product_names.join("、")
                        : `${order.item_count} 种物料`}
                    </td>
                    <td className="px-3 py-2 text-xs text-gray-500 whitespace-nowrap">
                      {order.batch_no
                        ? (() => {
                            const m = order.batch_no?.match(
                              /(\d{4})(\d{2})(\d{2})/
                            );
                            return m ? `${m[2]}${m[3]}` : order.batch_no;
                          })()
                        : "-"}
                    </td>
                    <td className="px-3 py-2 text-right whitespace-nowrap">
                      {order.total_boxes || "-"}
                    </td>
                    <td className="px-3 py-2 text-right whitespace-nowrap">
                      {order.total_qty || "-"}
                    </td>
                    <td className="px-3 py-2 text-center whitespace-nowrap">
                      {order.unit || "-"}
                    </td>
                    <td className="px-3 py-2 text-right font-medium whitespace-nowrap">
                      ¥{fmtMoney(order.actual_total)}
                    </td>
                    <td className="px-3 py-2 text-center whitespace-nowrap">
                      <span
                        className={cn(
                          "px-2 py-0.5 rounded text-xs",
                          getStatusBadge(order.status).className
                        )}
                      >
                        {getStatusBadge(order.status).label}
                      </span>
                    </td>
                    <td className="px-3 py-2 text-center whitespace-nowrap">
                      <span
                        className={cn(
                          "px-2 py-0.5 rounded text-xs",
                          getPaymentStatusBadge(order.payment_status).className
                        )}
                      >
                        {getPaymentStatusBadge(order.payment_status).label}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
        {/* 选中行详情 */}
        {selectedRow && (
          <div className="flex-none border-t bg-gray-50 p-4">
            <div className="flex items-center justify-between mb-3">
              <div className="flex items-center gap-3">
                <h3 className="font-semibold text-base">采购单详情</h3>
                <Badge variant="outline" className="text-blue-600 border-blue-200">
                  {selectedRow.order_no}
                </Badge>
              </div>
              <Button
                variant="ghost"
                size="icon"
                className="h-8 w-8"
                onClick={() => {
                  setSelectedRow(null);
                  setSelectedRowDetail(null);
                }}
              >
                ×
              </Button>
            </div>
            
            {/* 汇总信息 - 只显示仓库和备注（一行） */}
            <div className="flex justify-between text-sm text-muted-foreground mb-3">
              <span>仓库：{selectedRow.warehouse_name || "-"}</span>
              <span>备注：{selectedRowDetail?.notes || "无"}</span>
            </div>
            
            {detailLoading ? (
              <div className="text-sm text-muted-foreground py-4 text-center">加载明细中...</div>
            ) : selectedRowDetail ? (
              <div className="space-y-3">
                {/* 明细表格 */}
                <table className="w-full text-sm border rounded-lg overflow-hidden">
                  <thead className="bg-gray-100">
                    <tr>
                      <th className="px-3 py-2 text-left">物料</th>
                      <th className="px-3 py-2 text-right">箱数</th>
                      <th className="px-3 py-2 text-right">每箱</th>
                      <th className="px-3 py-2 text-right">总数量</th>
                      <th className="px-3 py-2 text-center">单位</th>
                      <th className="px-3 py-2 text-right">核算单价</th>
                      <th className="px-3 py-2 text-right">实付金额</th>
                      <th className="px-3 py-2 text-center">入库状态</th>
                    </tr>
                  </thead>
                  <tbody>
                    {selectedRowDetail.items.map((item) => (
                      <tr key={item.id} className="border-t">
                        <td className="px-3 py-2">
                          <div className="font-medium">{item.product_name}</div>
                          <div className="text-xs text-muted-foreground">{item.product_code}</div>
                        </td>
                        <td className="px-3 py-2 text-right">{item.box_count}</td>
                        <td className="px-3 py-2 text-right">{item.items_per_box}</td>
                        <td className="px-3 py-2 text-right">{item.total_qty}</td>
                        <td className="px-3 py-2 text-center">{item.unit}</td>
                        <td className="px-3 py-2 text-right">
                          ¥{fmtMoney(item.actual_unit_price)}/{item.unit}
                        </td>
                        <td className="px-3 py-2 text-right">¥{fmtMoney(item.actual_amount)}</td>
                        <td className="px-3 py-2 text-center">
                          {item.is_fully_received ? (
                            <span className="px-2 py-0.5 rounded text-xs bg-green-100 text-green-800">已入库</span>
                          ) : (
                            <span className="px-2 py-0.5 rounded text-xs bg-yellow-100 text-yellow-800">
                              {item.received_qty}/{item.total_qty}
                            </span>
                          )}
                        </td>
                      </tr>
                    ))}
                    {/* 明细汇总行 */}
                    <tr className="border-t-2 bg-gray-50 font-medium">
                      <td className="px-3 py-2 text-right text-xs" colSpan={1}>合计：</td>
                      <td className="px-3 py-2 text-right text-xs">
                        {selectedRowDetail.items.reduce((s, it) => s + (it.box_count || 0), 0)}
                      </td>
                      <td className="px-3 py-2 text-center text-xs">-</td>
                      <td className="px-3 py-2 text-right text-xs">
                        {selectedRowDetail.items.reduce((s, it) => s + (it.total_qty || 0), 0)}
                      </td>
                      <td className="px-3 py-2 text-center text-xs">{selectedRowDetail.unit || "-"}</td>
                      <td className="px-3 py-2 text-center text-xs">-</td>
                      <td className="px-3 py-2 text-right text-xs">
                        ¥{fmtMoney(selectedRowDetail.items.reduce((s, it) => s + (it.actual_amount || 0), 0))}
                      </td>
                      <td className="px-3 py-2 text-center text-xs">
                        {selectedRowDetail.items.every(it => it.is_fully_received) ? (
                          <span className="px-2 py-0.5 rounded text-xs bg-green-100 text-green-800">全部入库</span>
                        ) : (
                          <span className="px-2 py-0.5 rounded text-xs bg-yellow-100 text-yellow-800">部分入库</span>
                        )}
                      </td>
                    </tr>
                  </tbody>
                </table>
                

              </div>
            ) : (
              <div className="text-sm text-muted-foreground py-2">
                物料：{selectedRow.product_names?.join("、") || `${selectedRow.item_count} 种物料`}
                <span className="mx-2">·</span>
                箱数：{selectedRow.total_boxes}
                <span className="mx-2">·</span>
                数量：{selectedRow.total_qty} {selectedRow.unit}
                <span className="mx-2">·</span>
                金额：¥{fmtMoney(selectedRow.actual_total)}
              </div>
            )}
          </div>
        )}

        {/* 汇总行 */}
        <div className="flex-none border-t bg-gray-100 px-4 py-2 grid grid-cols-5 gap-4 text-sm">
          <div>
            <span className="text-muted-foreground">采购单数：</span>
            <span className="font-medium">{filtered.length} 单</span>
          </div>
          <div>
            <span className="text-muted-foreground">待入库：</span>
            <span className="font-medium text-yellow-700">{pendingCount} 单</span>
          </div>
          <div>
            <span className="text-muted-foreground">总箱数：</span>
            <span className="font-medium">{totalBoxes.toLocaleString()}</span>
          </div>
          <div>
            <span className="text-muted-foreground">总数量：</span>
            <span className="font-medium">{totalQty.toLocaleString()}</span>
          </div>
          <div>
            <span className="text-muted-foreground">总金额：</span>
            <span className="font-medium text-blue-600">¥{fmtMoney(totalAmount)}</span>
          </div>
        </div>

        {/* 分页 */}
        {totalPages > 1 && (
          <div className="flex-none border-t bg-gray-50 px-4 py-2 flex items-center justify-between text-sm">
            <span className="text-muted-foreground">
              显示 {pageData.length} 条 / 共 {filtered.length} 条
            </span>
            <div className="flex items-center gap-2">
              <Button
                size="sm"
                variant="outline"
                disabled={page <= 1}
                onClick={() => setPage(page - 1)}
              >
                上一页
              </Button>
              <span className="text-muted-foreground">
                {page} / {totalPages}
              </span>
              <Button
                size="sm"
                variant="outline"
                disabled={page >= totalPages}
                onClick={() => setPage(page + 1)}
              >
                下一页
              </Button>
            </div>
          </div>
        )}
      </div>

      {/* 新建采购弹窗 */}
      <MaterialPurchaseDialog
        open={dialogOpen}
        onClose={() => setDialogOpen(false)}
        onSuccess={() => {
          qc.invalidateQueries({ queryKey: ["material-purchase-orders"] });
        }}
      />

      {/* 详情弹窗 */}
      <Dialog
        open={detailDialogOpen}
        onOpenChange={(v) => !v && setDetailDialogOpen(false)}
      >
        <DialogContent className="max-w-3xl max-h-[80vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>
              采购单详情 - {selectedOrder?.order_no}
            </DialogTitle>
          </DialogHeader>
          {selectedOrder && (
            <div className="space-y-4">
              <div className="grid grid-cols-3 gap-3 text-sm">
                <div>
                  <span className="text-muted-foreground">供应商：</span>
                  {selectedOrder.supplier_name}
                </div>
                <div>
                  <span className="text-muted-foreground">日期：</span>
                  {selectedOrder.order_date}
                </div>
                <div>
                  <span className="text-muted-foreground">仓库：</span>
                  {selectedOrder.warehouse_name || "-"}
                </div>
              </div>

              <table className="w-full text-sm">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="px-3 py-2 text-left">物料</th>
                    <th className="px-3 py-2 text-right">箱数</th>
                    <th className="px-3 py-2 text-right">每箱</th>
                    <th className="px-3 py-2 text-right">总数量</th>
                    <th className="px-3 py-2 text-center">单位</th>
                    <th className="px-3 py-2 text-right">核算单价</th>
                    <th className="px-3 py-2 text-right">实付金额</th>
                    <th className="px-3 py-2 text-center">状态</th>
                  </tr>
                </thead>
                <tbody>
                  {selectedOrder.items.map((item) => (
                    <tr key={item.id} className="border-t">
                      <td className="px-3 py-2">
                        <div className="font-medium">{item.product_name}</div>
                        <div className="text-xs text-muted-foreground">
                          {item.product_code}
                        </div>
                      </td>
                      <td className="px-3 py-2 text-right">
                        {item.box_count}
                      </td>
                      <td className="px-3 py-2 text-right">
                        {item.items_per_box}
                      </td>
                      <td className="px-3 py-2 text-right">
                        {item.total_qty}
                      </td>
                      <td className="px-3 py-2 text-center">
                        {item.unit}
                      </td>
                      <td className="px-3 py-2 text-right">
                        ¥{fmtMoney(item.actual_unit_price)}/{item.unit}
                      </td>
                      <td className="px-3 py-2 text-right">
                        ¥{fmtMoney(item.actual_amount)}
                      </td>
                      <td className="px-3 py-2 text-center">
                        {item.is_fully_received ? (
                          <Badge className="bg-green-100 text-green-800">
                            已入库
                          </Badge>
                        ) : (
                          <Badge className="bg-yellow-100 text-yellow-800">
                            待入库
                          </Badge>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>

              <div className="flex justify-between text-sm border-t pt-3">
                <span className="text-muted-foreground">
                  备注：{selectedOrder.notes || "无"}
                </span>
                <span className="font-medium">
                  实付总计：¥{fmtMoney(selectedOrder.actual_total)}
                </span>
              </div>
            </div>
          )}
        </DialogContent>
      </Dialog>

      {/* 删除确认 */}
      <Dialog open={!!deleteId} onOpenChange={(v) => !v && setDeleteId(null)}>
        <DialogContent className="max-w-sm">
          <DialogHeader>
            <DialogTitle>确认删除</DialogTitle>
          </DialogHeader>
          <p className="text-sm text-muted-foreground py-2">
            删除后不可恢复，是否继续？
          </p>
          <DialogFooter>
            <Button variant="outline" onClick={() => setDeleteId(null)}>
              取消
            </Button>
            <Button
              variant="destructive"
              onClick={() => deleteId && deleteMutation.mutate(deleteId)}
              disabled={deleteMutation.isPending}
            >
              确认删除
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* 批量删除确认 */}
      <Dialog
        open={batchDeleteDialogOpen}
        onOpenChange={(v) => !v && setBatchDeleteDialogOpen(false)}
      >
        <DialogContent className="max-w-sm">
          <DialogHeader>
            <DialogTitle>确认批量删除</DialogTitle>
          </DialogHeader>
          <p className="text-sm text-muted-foreground py-2">
            选中 {selectedIds.size} 条记录，删除后不可恢复，是否继续？
          </p>
          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => setBatchDeleteDialogOpen(false)}
            >
              取消
            </Button>
            <Button
              variant="destructive"
              onClick={confirmBatchDelete}
              disabled={batchDeleteMutation.isPending}
            >
              确认删除
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* 收款弹窗 */}
      <Dialog
        open={paymentDialogOpen}
        onOpenChange={(v) => !v && setPaymentDialogOpen(false)}
      >
        <DialogContent className="max-w-sm">
          <DialogHeader>
            <DialogTitle>
              收款 - {paymentOrder?.order_no}
            </DialogTitle>
          </DialogHeader>
          <div className="space-y-3 py-2">
            <div className="text-sm">
              <span className="text-muted-foreground">供应商：</span>
              {paymentOrder?.supplier_name}
            </div>
            <div className="text-sm">
              <span className="text-muted-foreground">应付金额：</span>
              ¥{fmtMoney(paymentOrder?.actual_total)}
            </div>
            <div className="text-sm">
              <span className="text-muted-foreground">已付金额：</span>
              ¥{fmtMoney(paymentOrder?.paid_amount)}
            </div>
            <div className="text-sm">
              <span className="text-muted-foreground">待付金额：</span>
              <span className="text-red-600 font-medium">
                ¥
                {fmtMoney(
                  Math.max(
                    0,
                    (paymentOrder?.actual_total || 0) -
                      (paymentOrder?.paid_amount || 0)
                  )
                )}
              </span>
            </div>
            <div>
              <label className="text-sm text-muted-foreground">
                收款金额
              </label>
              <Input
                type="number"
                step="0.01"
                value={paymentAmount}
                onChange={(e) => setPaymentAmount(e.target.value)}
                placeholder="输入收款金额"
              />
            </div>
            <div className="space-y-2">
              <label className="text-sm text-muted-foreground">
                银行账户
              </label>
              <Select
                value={paymentBankAccountId ? String(paymentBankAccountId) : ""}
                onValueChange={(val) => setPaymentBankAccountId(val ? Number(val) : "")}
              >
                <SelectTrigger>
                  <SelectValue placeholder="选择银行账户" />
                </SelectTrigger>
                <SelectContent>
                  {bankAccounts.map((acc) => (
                    <SelectItem key={acc.id} value={String(acc.id)}>
                      {acc.bank_name} - {acc.account_name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>
          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => setPaymentDialogOpen(false)}
            >
              取消
            </Button>
            <Button
              onClick={handlePaymentSave}
              disabled={paymentLoading || paymentMutation.isPending}
            >
              确认收款
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* 入库弹窗 */}
      <Dialog open={inboundDialogOpen} onOpenChange={(v) => !v && setInboundDialogOpen(false)}>
        <DialogContent className="max-w-2xl">
          <DialogHeader>
            <DialogTitle>采购入库 — {inboundOrder?.order_no}</DialogTitle>
          </DialogHeader>
          <div className="space-y-4">
            <div className="flex items-center gap-4 text-sm text-gray-500">
              <span>供应商：{inboundOrder?.supplier_name}</span>
              <span>采购日期：{inboundOrder?.order_date}</span>
            </div>
            <div className="flex items-center gap-2">
              <label className="text-sm font-medium">入库日期：</label>
              <input
                type="date"
                value={inboundItems[0]?.inbound_date || new Date().toISOString().split('T')[0]}
                onChange={(e) => {
                  const newDate = e.target.value;
                  setInboundItems(inboundItems.map(item => ({...item, inbound_date: newDate})));
                }}
                className="border rounded px-2 py-1 text-sm"
              />
            </div>
            <div className="border rounded-md overflow-hidden">
              <table className="w-full text-sm">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="px-3 py-2 text-left">物料</th>
                    <th className="px-3 py-2 text-right">采购数量</th>
                    <th className="px-3 py-2 text-right">已入库</th>
                    <th className="px-3 py-2 text-center">单位</th>
                    <th className="px-3 py-2 text-right">本次入库</th>
                  </tr>
                </thead>
                <tbody>
                  {inboundItems.map((item, idx) => (
                    <tr key={item.item_id} className="border-t">
                      <td className="px-3 py-2">
                        <div className="font-medium">{item.product_name}</div>
                        <div className="text-xs text-gray-500">{item.product_code}</div>
                      </td>
                      <td className="px-3 py-2 text-right">{item.total_qty}</td>
                      <td className="px-3 py-2 text-right">{item.received_qty}</td>
                      <td className="px-3 py-2 text-center">{item.unit}</td>
                      <td className="px-3 py-2 text-right">
                        <Input
                          type="number"
                          step="0.001"
                          min={0}
                          max={item.total_qty - item.received_qty}
                          value={item.inbound_qty}
                          onChange={(e) => {
                            const val = Number(e.target.value);
                            const max = item.total_qty - item.received_qty;
                            const newItems = [...inboundItems];
                            newItems[idx].inbound_qty = Math.min(Math.max(0, val), max);
                            setInboundItems(newItems);
                          }}
                          className="w-24 text-right"
                        />
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <div className="text-xs text-gray-500">
              提示：入库数量不能超过剩余未入库数量（采购数量 - 已入库数量）
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setInboundDialogOpen(false)}>
              取消
            </Button>
            <Button onClick={handleInboundSave} disabled={inboundLoading}>
              确认入库
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
