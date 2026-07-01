import { useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from "@/components/ui/table";
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter,
} from "@/components/ui/dialog";
import { Badge } from "@/components/ui/badge";
import { Checkbox } from "@/components/ui/checkbox";
import { toast } from "sonner";
import { Search, Eye, PackageCheck, Trash2, MinusCircle } from "lucide-react";
import { PurchaseReturnForm } from "@/components/purchase-returns/PurchaseReturnForm";

interface InboundItem {
  id: number;
  order_no: string;
  order_date: string;
  supplier_id: number;
  supplier_name: string;
  actual_total: number;
  after_sales_adjustment?: number;
  net_amount?: number;
  paid_amount?: number;
  status: string;
  payment_status: string;
  total_boxes: number;
  total_qty: number;
  unit: string;
  item_count: number;
  warehouse_name: string | null;
  product_names: string[];
}

interface InboundDetail {
  id: number;
  product_id: number;
  product_name: string;
  product_code: string;
  box_count: number;
  items_per_box: number;
  total_qty: number;
  unit: string;
  actual_amount: number;
  actual_unit_price: number;
  received_qty: number;
  is_fully_received: boolean;
}

export function PurchaseInboundPage() {
  const [search, setSearch] = useState("");
  const [selectedIds, setSelectedIds] = useState<number[]>([]);
  const [detailOpen, setDetailOpen] = useState(false);
  const [detailItem, setDetailItem] = useState<InboundItem | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [detailData, setDetailData] = useState<InboundDetail[]>([]);

  const [inboundDialogOpen, setInboundDialogOpen] = useState(false);
  const [inboundItem, setInboundItem] = useState<InboundItem | null>(null);
  const [inboundDetails, setInboundDetails] = useState<InboundDetail[]>([]);
  const [inboundQtys, setInboundQtys] = useState<Record<number, string>>({});
  const [inboundLoading, setInboundLoading] = useState(false);

  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [deleteItem, setDeleteItem] = useState<InboundItem | null>(null);
  const [deleteLoading, setDeleteLoading] = useState(false);

  // 采购售后（完整明细）
  const [returnFormOpen, setReturnFormOpen] = useState(false);
  const [returnFormOrder, setReturnFormOrder] = useState<InboundItem | null>(null);

  const qc = useQueryClient();

  const { data, isLoading } = useQuery<{
    items: InboundItem[];
    total: number;
  }>({
    queryKey: ["material-purchases", search],
    queryFn: async () => {
      const params = new URLSearchParams();
      if (search) params.append("keyword", search);
      params.append("limit", "100");
      const res = await api.get(`/v1/material-purchases?${params}`);
      // 如果后端返回的是数组而不是 {items, total}，兼容处理
      const payload = res.data;
      if (Array.isArray(payload)) {
        return { items: payload, total: payload.length };
      }
      return payload;
    },
  });

  const items = data?.items || [];
  const hasSelection = selectedIds.length > 0;
  const selectionItems = items.filter((i) => selectedIds.includes(i.id));
  const selectedSingle = selectionItems.length === 1 ? selectionItems[0] : null;

  const handleToggleSelect = (id: number) => {
    setSelectedIds((prev) =>
      prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id]
    );
  };

  const fetchOrderDetail = async (orderId: number): Promise<InboundDetail[]> => {
    const res = await api.get(`/v1/material-purchases/${orderId}`);
    return res.data?.items || [];
  };

  const handleDetailOpen = async (item: InboundItem) => {
    setDetailItem(item);
    setDetailOpen(true);
    setDetailLoading(true);
    try {
      const details = await fetchOrderDetail(item.id);
      setDetailData(details);
    } catch (err: any) {
      toast.error(err.response?.data?.detail || "获取详情失败");
    } finally {
      setDetailLoading(false);
    }
  };

  const handleInboundOpen = async (item: InboundItem) => {
    setInboundItem(item);
    setInboundDialogOpen(true);
    setInboundLoading(true);
    try {
      const details = await fetchOrderDetail(item.id);
      setInboundDetails(details);
      // 默认填入剩余数量
      const defaults: Record<number, string> = {};
      details.forEach((d) => {
        const remaining = d.total_qty - d.received_qty;
        defaults[d.id] = remaining > 0 ? String(remaining) : "0";
      });
      setInboundQtys(defaults);
    } catch (err: any) {
      toast.error(err.response?.data?.detail || "获取详情失败");
    } finally {
      setInboundLoading(false);
    }
  };

  const handleInboundConfirm = async () => {
    if (!inboundItem) return;
    setInboundLoading(true);
    try {
      const payload = inboundDetails
        .map((d) => {
          const qty = parseFloat(inboundQtys[d.id] || "0");
          if (qty <= 0) return null;
          const remaining = d.total_qty - d.received_qty;
          if (qty > remaining) {
            throw new Error(
              `${d.product_name} 入库数量超过剩余数量（剩余 ${remaining}）`
            );
          }
          return { item_id: d.id, inbound_qty: qty };
        })
        .filter(Boolean);

      if (payload.length === 0) {
        toast.error("请至少输入一项入库数量");
        setInboundLoading(false);
        return;
      }

      await api.post(`/v1/material-purchases/${inboundItem.id}/inbound`, payload);
      toast.success("入库成功");
      setInboundDialogOpen(false);
      setInboundItem(null);
      setInboundDetails([]);
      setInboundQtys({});
      setSelectedIds([]);
      qc.invalidateQueries({ queryKey: ["material-purchases"] });
    } catch (error: any) {
      toast.error(error.response?.data?.detail || error.message || "入库失败");
    } finally {
      setInboundLoading(false);
    }
  };

  const handleDeleteOpen = (item: InboundItem) => {
    setDeleteItem(item);
    setDeleteDialogOpen(true);
  };

  const handleDeleteConfirm = async () => {
    if (!deleteItem) return;
    setDeleteLoading(true);
    try {
      await api.delete(`/v1/material-purchases/${deleteItem.id}`);
      toast.success("删除成功");
      setDeleteDialogOpen(false);
      setDeleteItem(null);
      setSelectedIds([]);
      qc.invalidateQueries({ queryKey: ["material-purchases"] });
    } catch (error: any) {
      toast.error(error.response?.data?.detail || "删除失败");
    } finally {
      setDeleteLoading(false);
    }
  };

  const handleReturnOpen = (item: InboundItem) => {
    setReturnFormOrder(item);
    setReturnFormOpen(true);
  };

  const statusLabel = (status: string) => {
    switch (status) {
      case "completed": return "已完成";
      case "pending": return "待入库";
      case "partial_inbound": return "部分入库";
      case "cancelled": return "已取消";
      default: return status;
    }
  };

  const statusVariant = (status: string) => {
    switch (status) {
      case "completed": return "default";
      case "pending": return "secondary";
      case "partial_inbound": return "outline";
      case "cancelled": return "destructive";
      default: return "outline";
    }
  };

  const paymentLabel = (ps: string) => {
    switch (ps) {
      case "paid": return "已付清";
      case "partial": return "部分付款";
      default: return "未付款";
    }
  };

  return (
    <div className="p-6 space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">辅料采购入库</h1>
          <p className="text-sm text-muted-foreground">
            管理辅料采购入库、入库确认、采购单查询
          </p>
        </div>
        <div className="flex items-center gap-2">
          <div className="relative">
            <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
            <Input
              placeholder="搜索采购单号/供应商..."
              className="pl-8 w-64"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
            />
          </div>
        </div>
      </div>

      <div className="flex items-center gap-2">
        <Button
          variant="outline"
          size="sm"
          disabled={!selectedSingle}
          onClick={() => selectedSingle && handleDetailOpen(selectedSingle)}
        >
          <Eye className="h-3.5 w-3.5 mr-1" />
          查看
        </Button>
        <Button
          variant="outline"
          size="sm"
          disabled={!selectedSingle || selectedSingle.status === "completed"}
          onClick={() => selectedSingle && handleInboundOpen(selectedSingle)}
        >
          <PackageCheck className="h-3.5 w-3.5 mr-1" />
          入库
        </Button>
        <Button
          variant="outline"
          size="sm"
          className="text-orange-600"
          disabled={!selectedSingle}
          onClick={() => selectedSingle && handleReturnOpen(selectedSingle)}
        >
          <MinusCircle className="h-3.5 w-3.5 mr-1" />
          采购售后
        </Button>
        <Button
          variant="outline"
          size="sm"
          className="text-red-600"
          disabled={!selectedSingle || deleteLoading}
          onClick={() => selectedSingle && handleDeleteOpen(selectedSingle)}
        >
          <Trash2 className="h-3.5 w-3.5 mr-1" />
          {deleteLoading ? "删除中..." : "删除"}
        </Button>
      </div>

      <div className="border rounded-md">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead className="w-12">
                <Checkbox
                  checked={items.length > 0 && selectedIds.length === items.length}
                  onCheckedChange={(checked) => {
                    if (checked) {
                      setSelectedIds(items.map((i) => i.id));
                    } else {
                      setSelectedIds([]);
                    }
                  }}
                />
              </TableHead>
              <TableHead>采购单号</TableHead>
              <TableHead>日期</TableHead>
              <TableHead>供应商</TableHead>
              <TableHead>物料</TableHead>
              <TableHead className="text-right">总箱数</TableHead>
              <TableHead className="text-right">总金额</TableHead>
              <TableHead className="text-right">售后扣款</TableHead>
              <TableHead className="text-right">净金额</TableHead>
              <TableHead>付款状态</TableHead>
              <TableHead>状态</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {isLoading ? (
              <TableRow>
                <TableCell colSpan={9} className="text-center py-8">
                  加载中...
                </TableCell>
              </TableRow>
            ) : items.length === 0 ? (
              <TableRow>
                <TableCell colSpan={9} className="text-center py-8 text-muted-foreground">
                  暂无采购入库记录
                </TableCell>
              </TableRow>
            ) : (
              items.map((item) => (
                <TableRow
                  key={item.id}
                  className={selectedIds.includes(item.id) ? "bg-muted" : ""}
                >
                  <TableCell>
                    <Checkbox
                      checked={selectedIds.includes(item.id)}
                      onCheckedChange={() => handleToggleSelect(item.id)}
                    />
                  </TableCell>
                  <TableCell className="font-medium">
                    {item.order_no}
                  </TableCell>
                  <TableCell>{item.order_date}</TableCell>
                  <TableCell>{item.supplier_name}</TableCell>
                  <TableCell>
                    {item.product_names?.slice(0, 2).join(", ")}
                    {item.product_names && item.product_names.length > 2 ? " ..." : ""}
                  </TableCell>
                  <TableCell className="text-right">
                    {item.total_boxes}
                  </TableCell>
                  <TableCell className="text-right">
                    ¥{item.actual_total?.toFixed(2)}
                  </TableCell>
                  <TableCell className="text-right">
                    {item.after_sales_adjustment ? (
                      <span className="text-red-500">-¥{item.after_sales_adjustment?.toFixed(2)}</span>
                    ) : (
                      "-"
                    )}
                  </TableCell>
                  <TableCell className="text-right">
                    {item.net_amount !== undefined ? (
                      <span className="font-medium">¥{item.net_amount?.toFixed(2)}</span>
                    ) : (
                      "¥" + item.actual_total?.toFixed(2)
                    )}
                  </TableCell>
                  <TableCell>
                    <Badge variant="outline">{paymentLabel(item.payment_status)}</Badge>
                  </TableCell>
                  <TableCell>
                    <Badge variant={statusVariant(item.status)}>
                      {statusLabel(item.status)}
                    </Badge>
                  </TableCell>
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </div>

      {/* 详情对话框 */}
      <Dialog open={detailOpen} onOpenChange={setDetailOpen}>
        <DialogContent className="max-w-3xl max-h-[80vh] overflow-auto">
          <DialogHeader>
            <DialogTitle>采购入库详情 - {detailItem?.order_no}</DialogTitle>
          </DialogHeader>
          <div className="space-y-4">
            <div className="grid grid-cols-3 gap-4 text-sm">
              <div>
                <p className="text-muted-foreground">供应商</p>
                <p className="font-medium">{detailItem?.supplier_name}</p>
              </div>
              <div>
                <p className="text-muted-foreground">采购日期</p>
                <p className="font-medium">{detailItem?.order_date}</p>
              </div>
              <div>
                <p className="text-muted-foreground">仓库</p>
                <p className="font-medium">{detailItem?.warehouse_name || "-"}</p>
              </div>
              <div>
                <p className="text-muted-foreground">总金额</p>
                <p className="font-medium">¥{detailItem?.actual_total?.toFixed(2)}</p>
              </div>
              <div>
                <p className="text-muted-foreground">售后扣款</p>
                <p className="font-medium text-red-500">
                  {detailItem?.after_sales_adjustment ? `-¥${detailItem.after_sales_adjustment.toFixed(2)}` : "-"}
                </p>
              </div>
              <div>
                <p className="text-muted-foreground">净金额</p>
                <p className="font-medium">
                  {detailItem?.net_amount !== undefined ? `¥${detailItem.net_amount.toFixed(2)}` : `¥${detailItem?.actual_total?.toFixed(2)}`}
                </p>
              </div>
              <div>
                <p className="text-muted-foreground">状态</p>
                <p className="font-medium">{detailItem && statusLabel(detailItem.status)}</p>
              </div>
              <div>
                <p className="text-muted-foreground">付款状态</p>
                <p className="font-medium">{detailItem && paymentLabel(detailItem.payment_status)}</p>
              </div>
              <div>
                <p className="text-muted-foreground">已付款</p>
                <p className="font-medium">¥{detailItem?.paid_amount?.toFixed(2) || "0.00"}</p>
              </div>
            </div>

            <div className="border rounded-md">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>物料</TableHead>
                    <TableHead>规格</TableHead>
                    <TableHead className="text-right">箱数</TableHead>
                    <TableHead className="text-right">每箱</TableHead>
                    <TableHead className="text-right">数量</TableHead>
                    <TableHead className="text-right">单价</TableHead>
                    <TableHead className="text-right">金额</TableHead>
                    <TableHead className="text-right">已入库</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {detailLoading ? (
                    <TableRow>
                      <TableCell colSpan={8} className="text-center py-4">加载中...</TableCell>
                    </TableRow>
                  ) : detailData.length === 0 ? (
                    <TableRow>
                      <TableCell colSpan={8} className="text-center py-4 text-muted-foreground">
                        暂无明细
                      </TableCell>
                    </TableRow>
                  ) : (
                    detailData.map((d) => (
                      <TableRow key={d.id}>
                        <TableCell>{d.product_name}</TableCell>
                        <TableCell>{d.product_spec || "-"}</TableCell>
                        <TableCell className="text-right">{d.box_count}</TableCell>
                        <TableCell className="text-right">{d.items_per_box}</TableCell>
                        <TableCell className="text-right">{d.total_qty} {d.unit}</TableCell>
                        <TableCell className="text-right">¥{d.actual_unit_price?.toFixed(2)}</TableCell>
                        <TableCell className="text-right">¥{d.actual_amount?.toFixed(2)}</TableCell>
                        <TableCell className="text-right">
                          {d.received_qty?.toFixed(0)} / {d.total_qty?.toFixed(0)}
                        </TableCell>
                      </TableRow>
                    ))
                  )}
                </TableBody>
              </Table>
            </div>
          </div>
        </DialogContent>
      </Dialog>

      {/* 入库对话框 */}
      <Dialog open={inboundDialogOpen} onOpenChange={setInboundDialogOpen}>
        <DialogContent className="max-w-2xl max-h-[80vh] overflow-auto">
          <DialogHeader>
            <DialogTitle>入库确认 - {inboundItem?.order_no}</DialogTitle>
          </DialogHeader>
          <div className="space-y-4">
            {inboundLoading ? (
              <p className="text-center py-4 text-muted-foreground">加载中...</p>
            ) : inboundDetails.length === 0 ? (
              <p className="text-center py-4 text-muted-foreground">暂无明细</p>
            ) : (
              <div className="border rounded-md">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>物料</TableHead>
                      <TableHead className="text-right">采购数量</TableHead>
                      <TableHead className="text-right">已入库</TableHead>
                      <TableHead className="text-right">本次入库</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {inboundDetails.map((d) => {
                      const remaining = d.total_qty - d.received_qty;
                      return (
                        <TableRow key={d.id}>
                          <TableCell>
                            {d.product_name}
                            <span className="text-xs text-muted-foreground ml-1">
                              ({d.unit})
                            </span>
                          </TableCell>
                          <TableCell className="text-right">{d.total_qty}</TableCell>
                          <TableCell className="text-right">{d.received_qty}</TableCell>
                          <TableCell className="text-right">
                            <Input
                              type="number"
                              min={0}
                              max={remaining}
                              step="1"
                              className="w-24 text-right inline-block"
                              value={inboundQtys[d.id] || "0"}
                              onChange={(e) =>
                                setInboundQtys((prev) => ({
                                  ...prev,
                                  [d.id]: e.target.value,
                                }))
                              }
                            />
                          </TableCell>
                        </TableRow>
                      );
                    })}
                  </TableBody>
                </Table>
              </div>
            )}
          </div>
          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => setInboundDialogOpen(false)}
              disabled={inboundLoading}
            >
              取消
            </Button>
            <Button
              onClick={handleInboundConfirm}
              disabled={inboundLoading || inboundDetails.length === 0}
            >
              {inboundLoading ? "入库中..." : "确认入库"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* 采购售后（完整明细） */}
      <PurchaseReturnForm
        open={returnFormOpen}
        onClose={() => {
          setReturnFormOpen(false);
          setReturnFormOrder(null);
          qc.invalidateQueries({ queryKey: ["material-purchases"] });
        }}
        initialOrder={
          returnFormOrder
            ? {
                id: returnFormOrder.id,
                order_type: "material_purchase",
                purchase_no: returnFormOrder.order_no,
                supplier_id: returnFormOrder.supplier_id,
                supplier_name: returnFormOrder.supplier_name,
                total_amount: returnFormOrder.actual_total,
              }
            : null
        }
      />

      {/* 删除确认对话框 */}
      <Dialog open={deleteDialogOpen} onOpenChange={setDeleteDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>确认删除</DialogTitle>
          </DialogHeader>
          <p>
            确定要删除采购单 <strong>{deleteItem?.order_no}</strong> 吗？
            <br />
            <span className="text-sm text-muted-foreground">
              此操作将同时删除关联的库存记录、批次和交易流水，不可恢复。
            </span>
          </p>
          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => setDeleteDialogOpen(false)}
              disabled={deleteLoading}
            >
              取消
            </Button>
            <Button
              variant="destructive"
              onClick={handleDeleteConfirm}
              disabled={deleteLoading}
            >
              {deleteLoading ? "删除中..." : "删除"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
