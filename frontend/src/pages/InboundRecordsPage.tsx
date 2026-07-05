import React, { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from "@/components/ui/table";
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from "@/components/ui/select";
import { Badge } from "@/components/ui/badge";
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter,
} from "@/components/ui/dialog";
import { toast } from "sonner";
import { Search, ArrowDown, Trash2, AlertTriangle, Loader2 } from "lucide-react";

interface InboundRecord {
  id: number;
  inbound_no: string;
  source_type: string;
  source_no: string | null;
  warehouse_name: string;
  product_name: string;
  batch_no: string | null;
  qty: number;
  unit: string;
  unit_cost: number;
  total_cost: number;
  status: string;
  inbound_date: string;
  confirmed_at: string | null;
  notes: string | null;
}

const fetchInbounds = async (params: Record<string, any>) => {
  const { data } = await api.get("/v1/warehouse-v2/inbounds", { params });
  return data;
};

const getStatusBadge = (status: string) => {
  const map: Record<string, string> = {
    pending: "bg-yellow-100 text-yellow-800",
    completed: "bg-green-100 text-green-800",
    cancelled: "bg-gray-100 text-gray-500",
  };
  return map[status] || "bg-gray-100 text-gray-800";
};

const getStatusLabel = (status: string) => {
  const map: Record<string, string> = {
    pending: "待确认",
    completed: "已完成",
    cancelled: "已取消",
  };
  return map[status] || status;
};

const getSourceTypeLabel = (type: string) => {
  const map: Record<string, string> = {
    purchase_order: "采购单",
    import_invoice: "进口单证",
    import_clearance: "报关入库",
    transfer_in: "调拨入",
    return: "退货",
  };
  return map[type] || type;
};

const fmt = (n?: number | string | null, digits = 2) => {
  if (n === undefined || n === null || n === "") return "-";
  const num = Number(n);
  if (isNaN(num)) return "-";
  return num.toLocaleString("zh-CN", { minimumFractionDigits: digits, maximumFractionDigits: digits });
};

export function InboundRecordsPage() {
  const queryClient = useQueryClient();
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState<string>("");
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [selectedInbound, setSelectedInbound] = useState<InboundRecord | null>(null);

  const { data, isLoading } = useQuery({
    queryKey: ["warehouse-v2-inbounds", statusFilter],
    queryFn: () => fetchInbounds({ status: statusFilter || undefined, limit: 500 }),
  });

  const items: InboundRecord[] = data?.items || [];

  const filtered = items.filter((item) => {
    const matchSearch =
      item.inbound_no?.toLowerCase().includes(search.toLowerCase()) ||
      item.product_name?.toLowerCase().includes(search.toLowerCase()) ||
      item.warehouse_name?.toLowerCase().includes(search.toLowerCase()) ||
      item.source_no?.toLowerCase().includes(search.toLowerCase());
    return matchSearch;
  });

  const deleteInbound = useMutation({
    mutationFn: async (id: number) => {
      await api.post(`/v1/warehouse-v2/inbounds/${id}/cancel`);
    },
    onSuccess: () => {
      toast.success("入库单已取消/删除");
      queryClient.invalidateQueries({ queryKey: ["warehouse-v2-inbounds"] });
      queryClient.invalidateQueries({ queryKey: ["warehouse-v2-stocks"] });
      queryClient.invalidateQueries({ queryKey: ["warehouse-v2-summary"] });
      setDeleteDialogOpen(false);
      setSelectedInbound(null);
    },
    onError: (err: any) => {
      toast.error(err.response?.data?.detail || "操作失败");
    },
  });

  return (
    <div className="p-6 space-y-6 h-full flex flex-col">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold flex items-center gap-2">
          <ArrowDown className="h-6 w-6 text-green-600" />
          入库记录
        </h1>
      </div>

      {/* 筛选栏 */}
      <div className="flex items-center gap-4">
        <div className="relative flex-1 max-w-sm">
          <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-gray-400" />
          <Input
            placeholder="搜索单号、产品、仓库..."
            className="pl-8"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>
        <Select value={statusFilter} onValueChange={(v) => setStatusFilter(v ?? "")}>
          <SelectTrigger className="w-32">
            <SelectValue placeholder="状态" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="">全部</SelectItem>
            <SelectItem value="pending">待确认</SelectItem>
            <SelectItem value="completed">已完成</SelectItem>
            <SelectItem value="cancelled">已取消</SelectItem>
          </SelectContent>
        </Select>
        <span className="text-sm text-gray-500">共 {filtered.length} 条</span>
      </div>

      {/* 入库记录表格 */}
      <div className="flex-1 border rounded-lg overflow-hidden">
        <div className="overflow-auto h-full">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead className="sticky top-0 bg-background z-10">入库单号</TableHead>
                <TableHead className="sticky top-0 bg-background z-10">来源类型</TableHead>
                <TableHead className="sticky top-0 bg-background z-10">来源单号</TableHead>
                <TableHead className="sticky top-0 bg-background z-10">仓库</TableHead>
                <TableHead className="sticky top-0 bg-background z-10">产品</TableHead>
                <TableHead className="sticky top-0 bg-background z-10">批次</TableHead>
                <TableHead className="sticky top-0 bg-background z-10 text-right">数量</TableHead>
                <TableHead className="sticky top-0 bg-background z-10 text-right">单位成本</TableHead>
                <TableHead className="sticky top-0 bg-background z-10 text-right">总金额</TableHead>
                <TableHead className="sticky top-0 bg-background z-10">入库日期</TableHead>
                <TableHead className="sticky top-0 bg-background z-10">状态</TableHead>
                <TableHead className="sticky top-0 bg-background z-10 text-center">操作</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {isLoading ? (
                <TableRow>
                  <TableCell colSpan={12} className="text-center py-8">加载中...</TableCell>
                </TableRow>
              ) : filtered.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={12} className="text-center py-8 text-gray-500">暂无入库记录</TableCell>
                </TableRow>
              ) : (
                filtered.map((item) => (
                  <TableRow key={item.id}>
                    <TableCell className="font-mono text-xs">{item.inbound_no}</TableCell>
                    <TableCell>
                      <Badge variant="outline">{getSourceTypeLabel(item.source_type)}</Badge>
                    </TableCell>
                    <TableCell className="text-sm text-gray-500">{item.source_no || "-"}</TableCell>
                    <TableCell>{item.warehouse_name}</TableCell>
                    <TableCell className="font-medium">{item.product_name}</TableCell>
                    <TableCell className="font-mono text-xs">{item.batch_no || "-"}</TableCell>
                    <TableCell className="text-right">
                      {fmt(item.qty)} {item.unit}
                    </TableCell>
                    <TableCell className="text-right">¥{fmt(item.unit_cost, 4)}</TableCell>
                    <TableCell className="text-right font-medium">¥{fmt(item.total_cost)}</TableCell>
                    <TableCell className="text-sm">{item.inbound_date}</TableCell>
                    <TableCell>
                      <Badge className={getStatusBadge(item.status)}>
                        {getStatusLabel(item.status)}
                      </Badge>
                    </TableCell>
                    <TableCell className="text-center">
                      {item.status === "pending" && (
                        <Button
                          variant="ghost"
                          size="sm"
                          className="h-6 px-2 text-red-600"
                          onClick={() => {
                            setSelectedInbound(item);
                            setDeleteDialogOpen(true);
                          }}
                        >
                          <Trash2 className="h-3.5 w-3.5 mr-1" />
                          取消
                        </Button>
                      )}
                    </TableCell>
                  </TableRow>
                ))
              )}
            </TableBody>
          </Table>
        </div>
      </div>

      {/* 删除确认弹窗 */}
      <Dialog open={deleteDialogOpen} onOpenChange={setDeleteDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2 text-red-600">
              <AlertTriangle className="h-5 w-5" />
              确认取消入库单
            </DialogTitle>
          </DialogHeader>
          <div className="space-y-2 text-sm">
            <p>确定要取消以下入库单吗？</p>
            <div className="bg-muted p-3 rounded-md space-y-1">
              <p><strong>单号：</strong>{selectedInbound?.inbound_no}</p>
              <p><strong>产品：</strong>{selectedInbound?.product_name}</p>
              <p><strong>仓库：</strong>{selectedInbound?.warehouse_name}</p>
              <p><strong>数量：</strong>{fmt(selectedInbound?.qty)} {selectedInbound?.unit}</p>
            </div>
            <p className="text-red-600">取消后该入库单将不再生效，但已确认的入库不会自动回滚库存。</p>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setDeleteDialogOpen(false)}>取消</Button>
            <Button
              variant="destructive"
              onClick={() => selectedInbound && deleteInbound.mutate(selectedInbound.id)}
              disabled={deleteInbound.isPending}
            >
              {deleteInbound.isPending && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
              确认取消
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}

export default InboundRecordsPage;
