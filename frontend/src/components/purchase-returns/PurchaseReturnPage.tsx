// 采购售后单列表页面 — 三文鱼PMS
import { useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from "@/components/ui/table";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { api } from "@/lib/api";
import { Search, Plus, Eye, Trash2, Pencil } from "lucide-react";
import { PurchaseReturnForm } from "./PurchaseReturnForm";

// ==================== 状态标签 ====================

const statusMap: Record<string, { label: string; variant: any }> = {
  completed: { label: "已生效", variant: "default" },
  cancelled: { label: "已取消", variant: "outline" },
};

const refundMethodMap: Record<string, string> = {
  deduct_payable: "抵扣应付款",
  direct_refund: "直接退款",
  deferred: "挂账/延期",
};

// ==================== 组件 ====================

export function PurchaseReturnPage() {
  const queryClient = useQueryClient();
  const [search, setSearch] = useState("");
  const [formOpen, setFormOpen] = useState(false);
  const [editData, setEditData] = useState<any>(null);
  const [detailOpen, setDetailOpen] = useState(false);
  const [detailData, setDetailData] = useState<any>(null);
  const [deleteId, setDeleteId] = useState<number | null>(null);

  const { data, isLoading, refetch } = useQuery({
    queryKey: ["purchase-returns", search],
    queryFn: async () => {
      const params = new URLSearchParams();
      if (search) params.append("search", search);
      params.append("limit", "100");
      const res = await api.get(`/v1/purchase-returns?${params}`);
      return res.data;
    },
  });

  const items = data?.items || [];

  const handleView = async (item: any) => {
    try {
      const res = await api.get(`/v1/purchase-returns/${item.id}`);
      setDetailData(res.data);
      setDetailOpen(true);
    } catch (err: any) {
      toast.error("获取详情失败");
    }
  };

  const handleEdit = (item: any) => {
    setEditData(item);
    setFormOpen(true);
  };

  const handleDelete = async () => {
    if (!deleteId) return;
    try {
      await api.delete(`/v1/purchase-returns/${deleteId}`);
      toast.success("删除成功，已回滚扣款");
      setDeleteId(null);
      queryClient.invalidateQueries({ queryKey: ["purchase-returns"] });
      queryClient.invalidateQueries({ queryKey: ["purchase-inbound"] });
      queryClient.invalidateQueries({ queryKey: ["material-purchases"] });
    } catch (err: any) {
      toast.error(err.response?.data?.detail || "删除失败");
    }
  };

  return (
    <div className="p-6 space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">采购售后管理</h1>
          <p className="text-sm text-muted-foreground">管理采购售后、退货、扣款等</p>
        </div>
        <Button onClick={() => { setEditData(null); setFormOpen(true); }}>
          <Plus className="h-4 w-4 mr-1" /> 创建售后单
        </Button>
      </div>

      <div className="flex items-center gap-2">
        <div className="relative w-64">
          <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
          <Input
            placeholder="搜索售后单号..."
            className="pl-8"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>
      </div>

      <div className="border rounded-md">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>售后单号</TableHead>
              <TableHead>日期</TableHead>
              <TableHead>供应商</TableHead>
              <TableHead>关联采购单</TableHead>
              <TableHead className="text-right">重量(kg)</TableHead>
              <TableHead className="text-right">金额(元)</TableHead>
              <TableHead>退款方式</TableHead>
              <TableHead>状态</TableHead>
              <TableHead className="w-[200px]">操作</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {isLoading ? (
              <TableRow>
                <TableCell colSpan={9} className="text-center py-8">加载中...</TableCell>
              </TableRow>
            ) : items.length === 0 ? (
              <TableRow>
                <TableCell colSpan={9} className="text-center py-8 text-muted-foreground">
                  暂无采购售后记录
                </TableCell>
              </TableRow>
            ) : (
              items.map((item: any) => {
                const status = statusMap[item.status] || { label: item.status, variant: "outline" };
                return (
                  <TableRow key={item.id}>
                    <TableCell className="font-medium font-mono">{item.return_no}</TableCell>
                    <TableCell>{item.return_date}</TableCell>
                    <TableCell>{item.supplier_name}</TableCell>
                    <TableCell className="font-mono text-sm">{item.purchase_no || "-"}</TableCell>
                    <TableCell className="text-right">{item.total_weight_kg?.toFixed?.(3) || item.total_weight_kg}</TableCell>
                    <TableCell className="text-right font-medium">¥{item.total_amount?.toFixed?.(2) || item.total_amount}</TableCell>
                    <TableCell>{refundMethodMap[item.refund_method] || item.refund_method}</TableCell>
                    <TableCell>
                      <Badge variant={status.variant}>{status.label}</Badge>
                    </TableCell>
                    <TableCell>
                      <div className="flex gap-1">
                        <Button variant="ghost" size="icon" className="h-7 w-7" onClick={() => handleView(item)} title="查看">
                          <Eye className="h-3.5 w-3.5" />
                        </Button>
                        {item.status !== "cancelled" && (
                          <Button variant="ghost" size="icon" className="h-7 w-7" onClick={() => handleEdit(item)} title="编辑">
                            <Pencil className="h-3.5 w-3.5" />
                          </Button>
                        )}
                        {item.status !== "cancelled" && (
                          <Button variant="ghost" size="icon" className="h-7 w-7 text-red-500" onClick={() => setDeleteId(item.id)} title="删除">
                            <Trash2 className="h-3.5 w-3.5" />
                          </Button>
                        )}
                      </div>
                    </TableCell>
                  </TableRow>
                );
              })
            )}
          </TableBody>
        </Table>
      </div>

      {/* 创建/编辑弹窗 */}
      <PurchaseReturnForm
        open={formOpen}
        onClose={() => { setFormOpen(false); setEditData(null); }}
        editData={editData}
      />

      {/* 详情弹窗 */}
      <Dialog open={detailOpen} onOpenChange={setDetailOpen}>
        <DialogContent className="max-w-3xl max-h-[80vh] overflow-auto">
          <DialogHeader>
            <DialogTitle>采购售后单详情 - {detailData?.return_no}</DialogTitle>
          </DialogHeader>
          {detailData && (
            <div className="space-y-4">
              <div className="grid grid-cols-3 gap-4 text-sm">
                <div><span className="text-muted-foreground">供应商</span><p className="font-medium">{detailData.supplier_name}</p></div>
                <div><span className="text-muted-foreground">售后日期</span><p className="font-medium">{detailData.return_date}</p></div>
                <div><span className="text-muted-foreground">退款方式</span><p className="font-medium">{refundMethodMap[detailData.refund_method]}</p></div>
                <div><span className="text-muted-foreground">总重量</span><p className="font-medium">{detailData.total_weight_kg} kg</p></div>
                <div><span className="text-muted-foreground">售后金额</span><p className="font-medium text-red-600">¥{detailData.total_amount?.toFixed?.(2)}</p></div>
                <div><span className="text-muted-foreground">状态</span><p className="font-medium">{statusMap[detailData.status]?.label || detailData.status}</p></div>
              </div>

              {detailData.problem_description && (
                <div>
                  <span className="text-muted-foreground text-sm">问题描述</span>
                  <p className="text-sm mt-1 bg-muted p-2 rounded">{detailData.problem_description}</p>
                </div>
              )}

              {detailData.items && detailData.items.length > 0 && (
                <div>
                  <span className="text-muted-foreground text-sm">售后明细</span>
                  <table className="w-full text-sm mt-1 border rounded-md">
                    <thead className="bg-muted/50">
                      <tr>
                        <th className="text-left p-2">序号</th>
                        <th className="text-right p-2">重量(kg)</th>
                        <th className="text-right p-2">单价</th>
                        <th className="text-right p-2">金额</th>
                        <th className="text-left p-2">备注</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y">
                      {detailData.items.map((it: any, idx: number) => (
                        <tr key={idx}>
                          <td className="p-2">{idx + 1}</td>
                          <td className="p-2 text-right">{it.weight_kg}</td>
                          <td className="p-2 text-right">¥{it.unit_price}</td>
                          <td className="p-2 text-right font-medium">¥{it.amount?.toFixed?.(2)}</td>
                          <td className="p-2">{it.remarks || "-"}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}

              {detailData.attachments && detailData.attachments.length > 0 && (
                <div>
                  <span className="text-muted-foreground text-sm">附件</span>
                  <div className="flex flex-wrap gap-2 mt-1">
                    {detailData.attachments.map((att: any) => (
                      <a
                        key={att.id}
                        href={att.download_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-sm text-blue-600 hover:underline bg-blue-50 px-2 py-1 rounded"
                      >
                        {att.original_name}
                      </a>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}
        </DialogContent>
      </Dialog>

      {/* 删除确认 */}
      <Dialog open={!!deleteId} onOpenChange={() => setDeleteId(null)}>
        <DialogContent className="max-w-sm">
          <DialogHeader><DialogTitle>确认删除</DialogTitle></DialogHeader>
          <p className="text-sm">删除后将回滚该售后单的扣款金额，确定要删除吗？</p>
          <div className="flex justify-end gap-2 mt-4">
            <Button variant="outline" size="sm" onClick={() => setDeleteId(null)}>取消</Button>
            <Button variant="destructive" size="sm" onClick={handleDelete}>删除</Button>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}

export default PurchaseReturnPage;
