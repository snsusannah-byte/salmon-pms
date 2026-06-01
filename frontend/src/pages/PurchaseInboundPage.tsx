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
import { Search, Eye, Printer, PackageCheck, Trash2 } from "lucide-react";

interface InboundItem {
  id: number;
  purchase_no: string;
  purchase_date: string;
  supplier_id: number;
  supplier_name: string;
  total_amount: number;
  status: string;
  payment_status: string;
  invoice_count: number;
  total_weight: number;
  total_boxes: number;
}

export function PurchaseInboundPage() {
  const [search, setSearch] = useState("");
  const [selectedIds, setSelectedIds] = useState<number[]>([]);
  const [detailOpen, setDetailOpen] = useState(false);
  const [detailItem, setDetailItem] = useState<InboundItem | null>(null);
  const [inboundDialogOpen, setInboundDialogOpen] = useState(false);
  const [inboundItem, setInboundItem] = useState<InboundItem | null>(null);
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [deleteItem, setDeleteItem] = useState<InboundItem | null>(null);
  const [deleteLoading, setDeleteLoading] = useState(false);
  const qc = useQueryClient();

  const { data, isLoading } = useQuery<{
    items: InboundItem[];
    total: number;
  }>({
    queryKey: ["purchase-inbound", search],
    queryFn: async () => {
      const params = new URLSearchParams();
      if (search) params.append("search", search);
      params.append("limit", "100");
      const res = await api.get(`/api/v1/import-inbound?${params}`);
      return res.data;
    },
  });

  const items = data?.items || [];
  const hasSelection = selectedIds.length > 0;
  const selectionStatus = items.filter((i) => selectedIds.includes(i.id));

  const handleToggleSelect = (id: number) => {
    setSelectedIds((prev) =>
      prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id]
    );
  };

  const handleDetailOpen = (item: InboundItem) => {
    setDetailItem(item);
    setDetailOpen(true);
  };

  const handleInboundOpen = (item: InboundItem) => {
    setInboundItem(item);
    setInboundDialogOpen(true);
  };

  const handleDeleteOpen = (item: InboundItem) => {
    setDeleteItem(item);
    setDeleteDialogOpen(true);
  };

  const handleDeleteConfirm = async () => {
    if (!deleteItem) return;
    setDeleteLoading(true);
    try {
      await api.delete(`/api/v1/import-inbound/${deleteItem.id}`);
      toast.success("删除成功");
      setDeleteDialogOpen(false);
      setDeleteItem(null);
      setSelectedIds([]);
      qc.invalidateQueries({ queryKey: ["purchase-inbound"] });
    } catch (error: any) {
      toast.error(error.response?.data?.detail || "删除失败");
    } finally {
      setDeleteLoading(false);
    }
  };

  return (
    <div className="p-6 space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">辅料采购入库</h1>
          <p className="text-sm text-muted-foreground">
            管理进口采购入库、入库确认、入库单查询
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
          disabled={!hasSelection || selectionStatus.length !== 1}
          onClick={() => handleDetailOpen(selectionStatus[0])}
        >
          <Eye className="h-3.5 w-3.5 mr-1" />
          查看
        </Button>
        <Button
          variant="outline"
          size="sm"
          disabled={!hasSelection || selectionStatus.length !== 1}
          onClick={() => handleInboundOpen(selectionStatus[0])}
        >
          <PackageCheck className="h-3.5 w-3.5 mr-1" />
          入库
        </Button>
        <Button
          variant="outline"
          size="sm"
          className="text-red-600"
          disabled={!hasSelection || selectionStatus.length !== 1 || deleteLoading}
          onClick={() => handleDeleteOpen(selectionStatus[0])}
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
              <TableHead>发票数</TableHead>
              <TableHead className="text-right">总重量</TableHead>
              <TableHead className="text-right">总箱数</TableHead>
              <TableHead className="text-right">总金额</TableHead>
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
                    {item.purchase_no}
                  </TableCell>
                  <TableCell>{item.purchase_date}</TableCell>
                  <TableCell>{item.supplier_name}</TableCell>
                  <TableCell>{item.invoice_count}</TableCell>
                  <TableCell className="text-right">
                    {item.total_weight?.toFixed(2)} kg
                  </TableCell>
                  <TableCell className="text-right">
                    {item.total_boxes}
                  </TableCell>
                  <TableCell className="text-right">
                    ¥{item.total_amount?.toFixed(2)}
                  </TableCell>
                  <TableCell>
                    <Badge
                      variant={
                        item.status === "completed"
                          ? "default"
                          : item.status === "pending"
                          ? "secondary"
                          : "outline"
                      }
                    >
                      {item.status === "completed"
                        ? "已完成"
                        : item.status === "pending"
                        ? "待入库"
                        : item.status}
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
        <DialogContent className="max-w-2xl">
          <DialogHeader>
            <DialogTitle>采购入库详情 - {detailItem?.purchase_no}</DialogTitle>
          </DialogHeader>
          <div className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div>
                <p className="text-sm text-muted-foreground">供应商</p>
                <p className="font-medium">{detailItem?.supplier_name}</p>
              </div>
              <div>
                <p className="text-sm text-muted-foreground">采购日期</p>
                <p className="font-medium">{detailItem?.purchase_date}</p>
              </div>
            </div>
          </div>
        </DialogContent>
      </Dialog>

      {/* 入库对话框 */}
      <Dialog open={inboundDialogOpen} onOpenChange={setInboundDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>入库确认 - {inboundItem?.purchase_no}</DialogTitle>
          </DialogHeader>
          <div className="space-y-4">
            <p>确定要对采购单 {inboundItem?.purchase_no} 进行入库操作吗？</p>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setInboundDialogOpen(false)}>
              取消
            </Button>
            <Button onClick={() => {
              toast.success("入库成功");
              setInboundDialogOpen(false);
              qc.invalidateQueries({ queryKey: ["purchase-inbound"] });
            }}>
              确认入库
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* 删除确认对话框 */}
      <Dialog open={deleteDialogOpen} onOpenChange={setDeleteDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>确认删除</DialogTitle>
          </DialogHeader>
          <p>确定要删除采购入库单 {deleteItem?.purchase_no} 吗？此操作不可恢复。</p>
          <DialogFooter>
            <Button variant="outline" onClick={() => setDeleteDialogOpen(false)} disabled={deleteLoading}>
              取消
            </Button>
            <Button variant="destructive" onClick={handleDeleteConfirm} disabled={deleteLoading}>
              {deleteLoading ? "删除中..." : "删除"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
