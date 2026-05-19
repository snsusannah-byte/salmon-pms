/**
 * 退货管理页面 - ReturnsPage.tsx (常驻操作栏版)
 */
import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  Search, Plus, Eye, Pencil, Trash2, Package, CheckCircle, XCircle, Ban,
  Send, CreditCard, RefreshCcw, FileText, RotateCcw
} from "lucide-react";
import { toast } from "sonner";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from "@/components/ui/table";
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter,
} from "@/components/ui/dialog";
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from "@/components/ui/select";
import { Checkbox } from "@/components/ui/checkbox";
import { Label } from "@/components/ui/label";
import { cn } from "@/lib/utils";
import { ReturnOrderForm } from "@/components/returns/ReturnOrderForm";

const PAGE_SIZE = 20;

const statusMap: Record<string, { label: string; color: string }> = {
  draft: { label: "草稿", color: "bg-gray-100 text-gray-700" },
  pending_approval: { label: "待审批", color: "bg-yellow-100 text-yellow-700" },
  approved: { label: "已批准", color: "bg-blue-100 text-blue-700" },
  completed: { label: "已完成", color: "bg-green-100 text-green-700" },
  rejected: { label: "已拒绝", color: "bg-red-100 text-red-700" },
  cancelled: { label: "已取消", color: "bg-gray-100 text-gray-500" },
};

const reasonMap: Record<string, string> = {
  quality_issue: "质量问题",
  logistics_damage: "物流损坏",
  spec_mismatch: "规格不符",
  temperature_issue: "温控问题",
  foreign_matter: "异物混入",
  customer_reason: "客户原因",
  expired: "临期/过期",
  other: "其他",
};

const refundMethodMap: Record<string, string> = {
  direct_refund: "直接退款",
  balance_deduction: "抵扣货款",
  prepayment: "转预付款",
  deferred: "挂账",
};

export default function ReturnsPage() {
  const queryClient = useQueryClient();
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState<string>("");
  const [reasonFilter, setReasonFilter] = useState<string>("");
  const [selectedIds, setSelectedIds] = useState<Set<number>>(new Set());
  const [detailOpen, setDetailOpen] = useState(false);
  const [detailReturn, setDetailReturn] = useState<any>(null);
  const [formOpen, setFormOpen] = useState(false);
  const [editData, setEditData] = useState<any>(null);

  // 客户列表缓存
  const { data: customersData } = useQuery({
    queryKey: ["customers-cache-returns"],
    queryFn: async () => {
      const res = await api.get("/v1/companies/?type=customer&limit=500");
      const map: Record<number, string> = {};
      res.data.items?.forEach((c: any) => { map[c.id] = c.name; });
      return map;
    },
    staleTime: 1000 * 60 * 5,
  });

  // 银行账号缓存
  const { data: bankAccountsData } = useQuery({
    queryKey: ["bank-accounts-cache-returns"],
    queryFn: async () => {
      const res = await api.get("/v1/finance/bank-accounts?limit=500");
      const map: Record<number, string> = {};
      res.data?.forEach((acc: any) => { map[acc.id] = `${acc.bank_name}${acc.account_number ? `(${acc.account_number})` : ""}`; });
      return map;
    },
    staleTime: 1000 * 60 * 5,
  });

  const { data, isLoading } = useQuery({
    queryKey: ["returns", page, search, statusFilter, reasonFilter],
    queryFn: async () => {
      const params = new URLSearchParams();
      params.set("skip", String((page - 1) * PAGE_SIZE));
      params.set("limit", String(PAGE_SIZE));
      if (search) params.set("search", search);
      if (statusFilter) params.set("status", statusFilter);
      if (reasonFilter) params.set("return_reason", reasonFilter);
      const res = await api.get(`/v1/returns?${params.toString()}`);
      return res.data;
    },
  });

  const statsQuery = useQuery({
    queryKey: ["return-stats"],
    queryFn: async () => {
      const res = await api.get("/v1/returns/stats/summary");
      return res.data;
    },
  });

  const deleteMutation = useMutation({
    mutationFn: async (id: number) => { await api.delete(`/v1/returns/${id}`); },
    onSuccess: () => {
      toast.success("删除成功");
      queryClient.invalidateQueries({ queryKey: ["returns"] });
      queryClient.invalidateQueries({ queryKey: ["return-stats"] });
      setSelectedIds(new Set());
    },
    onError: (err: any) => toast.error(err.response?.data?.detail || "删除失败"),
  });

  const submitMutation = useMutation({
    mutationFn: async (id: number) => { await api.post(`/v1/returns/${id}/submit`); },
    onSuccess: () => {
      toast.success("已提交审批");
      queryClient.invalidateQueries({ queryKey: ["returns"] });
      queryClient.invalidateQueries({ queryKey: ["return-stats"] });
      setSelectedIds(new Set());
    },
    onError: (err: any) => toast.error(err.response?.data?.detail || "提交失败"),
  });

  const approveMutation = useMutation({
    mutationFn: async ({ id, approved, notes }: { id: number; approved: boolean; notes?: string }) => {
      await api.post(`/v1/returns/${id}/approve`, { approved, notes });
    },
    onSuccess: (_, vars) => {
      toast.success(vars.approved ? "审批通过" : "已拒绝");
      queryClient.invalidateQueries({ queryKey: ["returns"] });
      queryClient.invalidateQueries({ queryKey: ["return-stats"] });
      setSelectedIds(new Set());
    },
    onError: (err: any) => toast.error(err.response?.data?.detail || "审批失败"),
  });

  const cancelMutation = useMutation({
    mutationFn: async (id: number) => { await api.post(`/v1/returns/${id}/cancel`); },
    onSuccess: () => {
      toast.success("已取消");
      queryClient.invalidateQueries({ queryKey: ["returns"] });
      queryClient.invalidateQueries({ queryKey: ["return-stats"] });
      setSelectedIds(new Set());
    },
    onError: (err: any) => toast.error(err.response?.data?.detail || "取消失败"),
  });

  const refundMutation = useMutation({
    mutationFn: async (item: any) => {
      const payload: any = { refund_method: item.refund_method };
      if (item.bank_account_id) payload.bank_account_id = item.bank_account_id;
      await api.post(`/v1/returns/${item.id}/refund`, payload);
    },
    onSuccess: () => {
      toast.success("执行退款成功");
      queryClient.invalidateQueries({ queryKey: ["returns"] });
      queryClient.invalidateQueries({ queryKey: ["return-stats"] });
      setSelectedIds(new Set());
    },
    onError: (err: any) => toast.error(err.response?.data?.detail || "执行退款失败"),
  });

  const revertMutation = useMutation({
    mutationFn: async (id: number) => { await api.post(`/v1/returns/${id}/revert`); },
    onSuccess: () => {
      toast.success("已撤销完成，打回草稿");
      queryClient.invalidateQueries({ queryKey: ["returns"] });
      queryClient.invalidateQueries({ queryKey: ["return-stats"] });
      setSelectedIds(new Set());
    },
    onError: (err: any) => toast.error(err.response?.data?.detail || "撤销失败"),
  });

  const totalPages = Math.ceil((data?.total ?? 0) / PAGE_SIZE);

  const getCustomerName = (id: number) => customersData?.[id] ?? "-";

  // 选中行派生
  const selectedItems = selectedIds.size > 0
    ? data?.items?.filter((it: any) => selectedIds.has(it.id)) || []
    : [];
  const singleItem = selectedItems.length === 1 ? selectedItems[0] : null;
  const hasSelection = selectedIds.size > 0;
  const single = selectedIds.size === 1;

  const toggleSelectAll = () => {
    if (!data?.items) return;
    if (selectedIds.size === data.items.length) {
      setSelectedIds(new Set());
    } else {
      setSelectedIds(new Set(data.items.map((it: any) => it.id)));
    }
  };

  const toggleSelect = (id: number, checked: boolean) => {
    const newSet = new Set(selectedIds);
    if (checked) newSet.add(id);
    else newSet.delete(id);
    setSelectedIds(newSet);
  };

  return (
    <div className="p-4 space-y-4 max-w-[1400px] mx-auto">
      {/* 标题 */}
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold flex items-center gap-2">
          <Package className="h-6 w-6" />
          退货管理
        </h1>
      </div>

      {/* 统计卡片 */}
      {statsQuery.data?.summary && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          <Card>
            <CardContent className="p-3">
              <p className="text-xs text-muted-foreground">本月退货单</p>
              <p className="text-xl font-bold">{statsQuery.data.summary.total_return_orders}</p>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="p-3">
              <p className="text-xs text-muted-foreground">退货总金额</p>
              <p className="text-xl font-bold text-red-500">
                ¥{Number(statsQuery.data.summary.total_return_amount).toLocaleString("en-US", { minimumFractionDigits: 2 })}
              </p>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="p-3">
              <p className="text-xs text-muted-foreground">退货总重量</p>
              <p className="text-xl font-bold">
                {Number(statsQuery.data.summary.total_return_weight_kg).toLocaleString("en-US", { minimumFractionDigits: 2 })} kg
              </p>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="p-3">
              <p className="text-xs text-muted-foreground">已完成/总单</p>
              <p className="text-xl font-bold">
                {statsQuery.data.summary.completed_count} / {statsQuery.data.summary.total_return_orders}
              </p>
            </CardContent>
          </Card>
        </div>
      )}

      {/* 筛选栏 */}
      <div className="flex flex-wrap gap-2 items-center">
        <div className="relative flex-1 min-w-[200px]">
          <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
          <Input
            placeholder="搜索退货单号/客户/问题描述"
            value={search}
            onChange={(e) => { setSearch(e.target.value); setPage(1); }}
            className="pl-9"
          />
        </div>
        <Select value={statusFilter} onValueChange={(v) => { setStatusFilter(v); setPage(1); }}>
          <SelectTrigger className="w-[140px]">
            <SelectValue placeholder="全部状态" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="">全部状态</SelectItem>
            {Object.entries(statusMap).map(([k, v]) => (
              <SelectItem key={k} value={k}>{v.label}</SelectItem>
            ))}
          </SelectContent>
        </Select>
        <Select value={reasonFilter} onValueChange={(v) => { setReasonFilter(v); setPage(1); }}>
          <SelectTrigger className="w-[160px]">
            <SelectValue placeholder="全部原因" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="">全部原因</SelectItem>
            {Object.entries(reasonMap).map(([k, v]) => (
              <SelectItem key={k} value={k}>{v}</SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      {/* 常驻操作栏（固定在搜索行下方，始终显示） */}
      <div className="flex items-center gap-2 flex-wrap min-h-[36px]">
        <Button variant="ghost" size="sm" onClick={() => { setEditData(null); setFormOpen(true); }} title="新建退货单">
          <Plus className="h-4 w-4 mr-1 text-orange-600" /><span className="text-orange-600">新建退货单</span>
        </Button>
        <div className="h-6 w-px bg-border" />
        <Button variant="ghost" size="sm" disabled={!single} onClick={() => singleItem && (setDetailReturn(singleItem), setDetailOpen(true))} title="查看详情">
          <Eye className="h-4 w-4 mr-1" />查看
        </Button>
        <Button variant="ghost" size="sm" disabled={!single} onClick={() => singleItem && (setEditData(singleItem), setFormOpen(true))} title="编辑退货单">
          <Pencil className="h-4 w-4 mr-1" />编辑
        </Button>
        <Button variant="ghost" size="sm" className="text-blue-600" disabled={selectedIds.size === 0 || selectedItems.some((it: any) => it.status !== "draft")} onClick={() => selectedItems.forEach((it: any) => submitMutation.mutate(it.id))} title="批量提交审批">
          <Send className="h-4 w-4 mr-1" />批量提交{selectedIds.size > 1 ? ` (${selectedIds.size})` : ""}
        </Button>
        <Button variant="ghost" size="sm" className="text-green-600" disabled={selectedIds.size === 0 || selectedItems.some((it: any) => it.status !== "pending_approval")} onClick={() => selectedItems.forEach((it: any) => approveMutation.mutate({ id: it.id, approved: true }))} title="批量审批通过">
          <CheckCircle className="h-4 w-4 mr-1" />批量通过{selectedIds.size > 1 ? ` (${selectedIds.size})` : ""}
        </Button>
        <Button variant="ghost" size="sm" className="text-red-600" disabled={!single || singleItem?.status !== "pending_approval"} onClick={() => singleItem && approveMutation.mutate({ id: singleItem.id, approved: false })} title="审批拒绝">
          <XCircle className="h-4 w-4 mr-1" />拒绝
        </Button>
        <Button variant="ghost" size="sm" className="text-green-600" disabled={selectedIds.size === 0 || selectedItems.some((it: any) => it.status !== "approved")} onClick={() => selectedItems.forEach((it: any) => refundMutation.mutate(it))} title="批量执行退款">
          <CreditCard className="h-4 w-4 mr-1" />执行退款{selectedIds.size > 1 ? ` (${selectedIds.size})` : ""}
        </Button>
        <Button variant="ghost" size="sm" className="text-purple-600" disabled={selectedIds.size === 0 || selectedItems.some((it: any) => it.status !== "completed")} onClick={() => selectedItems.forEach((it: any) => revertMutation.mutate(it.id))} title="撤销完成，打回草稿">
          <RotateCcw className="h-4 w-4 mr-1" />撤销{selectedIds.size > 1 ? ` (${selectedIds.size})` : ""}
        </Button>
        <Button variant="ghost" size="sm" className="text-orange-500" disabled={selectedIds.size === 0 || selectedItems.some((it: any) => ["completed", "cancelled"].includes(it.status))} onClick={() => selectedItems.forEach((it: any) => cancelMutation.mutate(it.id))} title="取消退货单">
          <Ban className="h-4 w-4 mr-1" />取消{selectedIds.size > 1 ? ` (${selectedIds.size})` : ""}
        </Button>
        <Button variant="ghost" size="sm" className="text-red-500" disabled={!hasSelection || selectedItems.some((it: any) => !["draft", "cancelled"].includes(it.status))} onClick={() => selectedItems.forEach((it: any) => deleteMutation.mutate(it.id))} title="删除退货单">
          <Trash2 className="h-4 w-4 mr-1" />{selectedIds.size > 1 ? `批量删除 (${selectedIds.size})` : "删除"}
        </Button>

        {/* 批量操作提示（多条选中时） */}
        {selectedIds.size > 1 && (
          <span className="text-xs text-muted-foreground ml-2 border-l pl-2">
            已选 {selectedIds.size} 条
          </span>
        )}
      </div>

      {/* 列表 */}
      <div className="border rounded-md overflow-hidden">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead className="w-[40px]">
                <Checkbox
                  checked={data?.items ? selectedIds.size === data.items.length && data.items.length > 0 : false}
                  onCheckedChange={toggleSelectAll}
                />
              </TableHead>
              <TableHead>退货单号</TableHead>
              <TableHead>日期</TableHead>
              <TableHead>客户</TableHead>
              <TableHead>关联销售单</TableHead>
              <TableHead>加工厂</TableHead>
              <TableHead className="text-right">重量(kg)</TableHead>
              <TableHead className="text-right">金额</TableHead>
              <TableHead>退款方式</TableHead>
              <TableHead>状态</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {isLoading ? (
              <TableRow><TableCell colSpan={10} className="text-center py-8">加载中...</TableCell></TableRow>
            ) : (data?.items?.length ?? 0) === 0 ? (
              <TableRow><TableCell colSpan={10} className="text-center py-8">暂无退货记录</TableCell></TableRow>
            ) : (
              data.items.map((item: any) => {
                const status = statusMap[item.status] ?? { label: item.status, color: "" };
                return (
                  <TableRow key={item.id}>
                    <TableCell>
                      <Checkbox checked={selectedIds.has(item.id)} onCheckedChange={(checked) => toggleSelect(item.id, !!checked)} />
                    </TableCell>
                    <TableCell 
                      className="font-mono text-sm cursor-pointer hover:underline"
                      onClick={() => {
                        if (item.status === "completed") {
                          setDetailReturn(item);
                          setDetailOpen(true);
                        } else {
                          setEditData(item);
                          setFormOpen(true);
                        }
                      }}
                    >
                      {item.return_no}
                    </TableCell>
                    <TableCell className="text-sm">{item.return_date}</TableCell>
                    <TableCell className="text-sm">{getCustomerName(item.customer_id)}</TableCell>
                    <TableCell className="text-sm font-mono">{item.sale_no || "-"}</TableCell>
                    <TableCell className="text-sm">{item.processing_plant_eu_no ?? item.processing_plant_name ?? "-"}</TableCell>
                    <TableCell className="text-right text-sm">
                      {Number(item.total_weight_kg).toLocaleString("en-US", { minimumFractionDigits: 2 })}
                    </TableCell>
                    <TableCell className="text-right text-sm font-medium text-red-500">
                      ¥{Number(item.total_amount).toLocaleString("en-US", { minimumFractionDigits: 2 })}
                    </TableCell>
                    <TableCell className="text-sm">
                      {item.refund_method ? (refundMethodMap[item.refund_method] ?? item.refund_method) : <span className="text-muted-foreground">-</span>}
                    </TableCell>
                    <TableCell>
                      <span className={cn("text-xs font-medium px-2 py-0.5 rounded", status.color)}>{status.label}</span>
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

      {/* 详情弹窗 */}
      <Dialog open={detailOpen} onOpenChange={setDetailOpen}>
        <DialogContent className="max-w-[900px] max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>退货单详情</DialogTitle>
            <DialogDescription>
              {detailReturn?.return_no}
            </DialogDescription>
          </DialogHeader>
          {detailReturn && (
            <div className="space-y-4">
              {/* 基本信息 */}
              <div className="grid grid-cols-2 gap-3 text-sm">
                <div><span className="text-muted-foreground">退货日期:</span> {detailReturn.return_date}</div>
                <div><span className="text-muted-foreground">状态:</span> <span className={cn("font-medium", statusMap[detailReturn.status]?.color?.replace('bg-', '').split(' ')[0] || "")}>{statusMap[detailReturn.status]?.label}</span></div>
                <div><span className="text-muted-foreground">客户:</span> {getCustomerName(detailReturn.customer_id)}</div>
                <div><span className="text-muted-foreground">加工厂:</span> {detailReturn.processing_plant_eu_no ?? detailReturn.processing_plant_name ?? "-"}</div>
                <div><span className="text-muted-foreground">关联销售单:</span> {detailReturn.sale_no || "-"}</div>
                <div><span className="text-muted-foreground">退款方式:</span> {detailReturn.refund_method ? refundMethodMap[detailReturn.refund_method] : "-"}{detailReturn.bank_account_id && bankAccountsData?.[detailReturn.bank_account_id] ? ` · ${bankAccountsData[detailReturn.bank_account_id]}` : ""}</div>
                {detailReturn.refund_date && <div><span className="text-muted-foreground">退款日期:</span> {detailReturn.refund_date}</div>}
              </div>

              {/* 汇总 */}
              <div className="bg-muted/50 rounded-md p-3 text-sm space-y-1">
                <div className="flex justify-between">
                  <span>退货总重量</span>
                  <span className="font-medium">{Number(detailReturn.total_weight_kg).toLocaleString("en-US", { minimumFractionDigits: 2 })} kg</span>
                </div>
                <div className="flex justify-between text-red-500 font-medium border-t pt-1">
                  <span>退货总金额</span>
                  <span>¥{Number(detailReturn.total_amount).toLocaleString("en-US", { minimumFractionDigits: 2 })}</span>
                </div>
                {Number(detailReturn.refund_amount) > 0 && (
                  <div className="flex justify-between text-green-600">
                    <span>已退款金额</span>
                    <span>¥{Number(detailReturn.refund_amount).toLocaleString("en-US", { minimumFractionDigits: 2 })}</span>
                  </div>
                )}
              </div>

              {/* 问题描述 */}
              {detailReturn.problem_description && (
                <div className="text-sm">
                  <p className="font-medium mb-1">问题描述</p>
                  <p className="text-muted-foreground whitespace-pre-wrap">{detailReturn.problem_description}</p>
                </div>
              )}

              {/* 退货明细 */}
              {detailReturn.items && detailReturn.items.length > 0 && (
                <div>
                  <p className="font-medium text-sm mb-2">退货明细</p>
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead className="text-xs">规格/产品</TableHead>
                        <TableHead className="text-xs text-right">重量(kg)</TableHead>
                        <TableHead className="text-xs text-right">单价</TableHead>
                        <TableHead className="text-xs text-right">金额</TableHead>
                        <TableHead className="text-xs">备注</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {detailReturn.items.map((it: any) => (
                        <TableRow key={it.id}>
                          <TableCell className="text-sm">{it.product_name ?? it.spec ?? "-"}</TableCell>
                          <TableCell className="text-sm text-right">{Number(it.weight_kg).toLocaleString("en-US", { minimumFractionDigits: 2 })}</TableCell>
                          <TableCell className="text-sm text-right">¥{Number(it.unit_price).toLocaleString("en-US", { minimumFractionDigits: 2 })}</TableCell>
                          <TableCell className="text-sm text-right font-medium">¥{Number(it.amount).toLocaleString("en-US", { minimumFractionDigits: 2 })}</TableCell>
                          <TableCell className="text-sm">{it.remarks || "-"}</TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </div>
              )}

              {/* 附件 */}
              {detailReturn.attachments && detailReturn.attachments.length > 0 && (
                <div>
                  <p className="font-medium text-sm mb-2">附件 ({detailReturn.attachments.length})</p>
                  <div className="flex flex-wrap gap-2">
                    {detailReturn.attachments.map((att: any) => (
                      <div key={att.id} className="border rounded-md p-2 w-[100px]">
                        {att.file_type === "image" ? (
                          <img src={`/uploads/${att.file_path}`} alt={att.original_name} className="w-full h-[60px] object-cover rounded" />
                        ) : att.file_type === "video" ? (
                          <div className="w-full h-[60px] bg-gray-100 rounded flex items-center justify-center text-xs text-muted-foreground">视频</div>
                        ) : (
                          <div className="w-full h-[60px] bg-gray-100 rounded flex items-center justify-center text-xs text-muted-foreground">文档</div>
                        )}
                        <p className="text-[10px] truncate mt-1">{att.original_name}</p>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* 详情弹窗操作按钮 */}
              <DialogFooter className="gap-2 pt-2">
                {detailReturn.status === "draft" && (
                  <Button variant="outline" size="sm" onClick={() => { setDetailOpen(false); setEditData(detailReturn); setFormOpen(true); }}>
                    <Pencil className="h-4 w-4 mr-1" />编辑
                  </Button>
                )}
                {detailReturn.status === "draft" && (
                  <Button size="sm" onClick={() => { submitMutation.mutate(detailReturn.id); setDetailOpen(false); }}>
                    <Send className="h-4 w-4 mr-1" />提交审批
                  </Button>
                )}
                {detailReturn.status === "pending_approval" && (
                  <>
                    <Button variant="outline" size="sm" className="text-red-600" onClick={() => { approveMutation.mutate({ id: detailReturn.id, approved: false }); setDetailOpen(false); }}>
                      <XCircle className="h-4 w-4 mr-1" />拒绝
                    </Button>
                    <Button size="sm" className="bg-green-600 hover:bg-green-700" onClick={() => { approveMutation.mutate({ id: detailReturn.id, approved: true }); setDetailOpen(false); }}>
                      <CheckCircle className="h-4 w-4 mr-1" />通过
                    </Button>
                  </>
                )}
                {detailReturn.status !== "completed" && detailReturn.status !== "cancelled" && (
                  <Button variant="outline" size="sm" className="text-orange-500" onClick={() => { cancelMutation.mutate(detailReturn.id); setDetailOpen(false); }}>
                    <Ban className="h-4 w-4 mr-1" />取消
                  </Button>
                )}
              </DialogFooter>
            </div>
          )}
        </DialogContent>
      </Dialog>

      {/* 创建/编辑退货单弹窗 */}
      <ReturnOrderForm open={formOpen} onClose={() => { setFormOpen(false); setEditData(null); }} editData={editData} />
    </div>
  );
}
