import { useState, useEffect } from "react";
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
import {
  Plus,
  Search,
  Eye,
  Lock,
  Unlock,
  Trash2,
  X,
  Boxes,
  DollarSign,
  Weight,
} from "lucide-react";
import { toast } from "sonner";

const statusMap: Record<string, { label: string; color: string }> = {
  open: { label: "开放", color: "bg-green-100 text-green-800" },
  locked: { label: "已锁定", color: "bg-orange-100 text-orange-800" },
  settled: { label: "已结算", color: "bg-blue-100 text-blue-800" },
};

interface BatchInvoice {
  invoice_id: number;
  invoice_no: string;
  invoice_date: string;
  processing_plant_name: string | null;
  exporter_name: string | null;
  total_amount_usd: string;
  total_boxes: number;
  total_weight_kg: string;
}

interface Batch {
  // 批次ID列改为显示batch_code
  id: number;
  batch_code: string;
  batch_name: string;
  invoice_nos: string;
  status: string;
  total_amount_usd: string | null;
  total_boxes: number;
  total_weight_kg: string | null;
  notes: string | null;
  invoice_count: number;
  invoices: BatchInvoice[];
  created_at: string;
  updated_at: string;
}

interface BatchListResponse {
  total: number;
  items: Batch[];
  skip: number;
  limit: number;
}

interface Invoice {
  id: number;
  invoice_no: string;
  invoice_date: string;
  processing_plant_name: string | null;
  processing_plant_code: string | null;
  exporter_name: string | null;
  total_amount_usd: string;
  total_boxes: number;
  total_weight_kg: string;
}

const PAGE_SIZE = 10;

export function BatchesPage() {
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState<string>("all");
  const [page, setPage] = useState(1);
  const [formOpen, setFormOpen] = useState(false);
  const [detailOpen, setDetailOpen] = useState(false);
  const [detailBatch, setDetailBatch] = useState<Batch | null>(null);
  const queryClient = useQueryClient();

  const { data, isLoading } = useQuery<BatchListResponse>({
    queryKey: ["batches", search, statusFilter, page],
    queryFn: async () => {
      const params = new URLSearchParams();
      if (search) params.append("search", search);
      if (statusFilter && statusFilter !== "all") params.append("status", statusFilter);
      params.append("skip", String((page - 1) * PAGE_SIZE));
      params.append("limit", String(PAGE_SIZE));
      const res = await api.get(`/v1/batches/?${params.toString()}`);
      return res.data;
    },
  });

  const totalPages = data ? Math.ceil(data.total / PAGE_SIZE) : 0;

  const handleDelete = async (batch: Batch) => {
    if (batch.status === "locked") {
      toast.error("批次已锁定，不能删除");
      return;
    }
    if (!confirm(`确定要删除批次 "${batch.batch_name}" 吗？`)) return;
    try {
      await api.delete(`/v1/batches/${batch.id}`);
      toast.success("批次已删除");
      queryClient.invalidateQueries({ queryKey: ["batches"] });
    } catch (error: any) {
      toast.error(error.response?.data?.detail ?? "删除失败");
    }
  };

  const handleLockToggle = async (batch: Batch) => {
    try {
      if (batch.status === "locked") {
        await api.post(`/v1/batches/${batch.id}/unlock`);
        toast.success("批次已解锁");
      } else {
        await api.post(`/v1/batches/${batch.id}/lock`);
        toast.success("批次已锁定");
      }
      queryClient.invalidateQueries({ queryKey: ["batches"] });
      if (detailBatch?.id === batch.id) {
        setDetailBatch(null);
        setDetailOpen(false);
      }
    } catch (error: any) {
      toast.error(error.response?.data?.detail ?? "操作失败");
    }
  };

  const handleView = (batch: Batch) => {
    setDetailBatch(batch);
    setDetailOpen(true);
  };

  const handleRemoveInvoice = async (batchId: number, invoiceId: number) => {
    try {
      await api.delete(`/v1/batches/${batchId}/invoices/${invoiceId}`);
      toast.success("发票已从批次移除");
      queryClient.invalidateQueries({ queryKey: ["batches"] });
      // Refresh detail
      const res = await api.get(`/v1/batches/${batchId}`);
      setDetailBatch(res.data);
    } catch (error: any) {
      toast.error(error.response?.data?.detail ?? "移除失败");
    }
  };

  return (
    <div className="space-y-6">
      {/* 创建弹窗 */}
      <BatchFormDialog open={formOpen} onOpenChange={setFormOpen} />

      {/* 详情弹窗 */}
      <Dialog open={detailOpen} onOpenChange={setDetailOpen}>
        <DialogContent className="max-w-[700px] max-h-[90vh] overflow-y-auto">
          <DialogHeader className="pb-4 border-b flex flex-row items-center justify-between">
            <div>
              <DialogTitle>批次详情 {detailBatch?.batch_code}</DialogTitle>
              <DialogDescription>
                {detailBatch?.batch_name}
              </DialogDescription>
            </div>
            <div className="flex gap-2">
              {detailBatch && (
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => handleLockToggle(detailBatch)}
                >
                  {detailBatch.status === "locked" ? (
                    <>
                      <Unlock className="h-3 w-3 mr-1" />
                      解锁
                    </>
                  ) : (
                    <>
                      <Lock className="h-3 w-3 mr-1" />
                      锁定
                    </>
                  )}
                </Button>
              )}
              <Button variant="ghost" size="icon" className="h-8 w-8" onClick={() => setDetailOpen(false)}>
                <X className="h-4 w-4" />
              </Button>
            </div>
          </DialogHeader>

          {detailBatch && (
            <div className="space-y-6 py-4">
              {/* 状态 */}
              <div className="flex gap-3">
                {(() => {
                  const s = statusMap[detailBatch.status] ?? { label: detailBatch.status, color: "" };
                  return (
                    <Badge variant="secondary" className={s.color}>
                      {s.label}
                    </Badge>
                  );
                })()}
                <Badge variant="secondary">
                  <Boxes className="h-3 w-3 mr-1" />
                  {detailBatch.invoice_count} 张发票
                </Badge>
              </div>

              {/* 汇总 */}
              <div className="grid grid-cols-3 gap-3 text-sm bg-muted p-3 rounded-md">
                <div className="text-center">
                  <div className="text-muted-foreground text-xs">总箱数</div>
                  <div className="text-lg font-semibold">{detailBatch.total_boxes}</div>
                </div>
                <div className="text-center">
                  <div className="text-muted-foreground text-xs">总净重</div>
                  <div className="text-lg font-semibold">
                    {Number(detailBatch.total_weight_kg || 0).toLocaleString()} kg
                  </div>
                </div>
                <div className="text-center">
                  <div className="text-muted-foreground text-xs">总金额(USD)</div>
                  <div className="text-lg font-semibold text-primary">
                    ${Number(detailBatch.total_amount_usd || 0).toLocaleString()}
                  </div>
                </div>
              </div>

              {/* 发票列表 */}
              <div className="space-y-3">
                <h3 className="text-sm font-semibold text-foreground">批次发票明细</h3>
                {detailBatch.invoices.length > 0 ? (
                  <div className="border rounded-md overflow-hidden">
                    <Table>
                      <TableHeader>
                        <TableRow>
                          <TableHead className="text-xs">发票号</TableHead>
                          <TableHead className="text-xs">日期</TableHead>
                          <TableHead className="text-xs">加工厂</TableHead>
                          <TableHead className="text-xs">出口商</TableHead>
                          <TableHead className="text-xs text-right">箱数</TableHead>
                          <TableHead className="text-xs text-right">金额(USD)</TableHead>
                          {detailBatch.status === "open" && (
                            <TableHead className="text-xs text-center w-[60px]">操作</TableHead>
                          )}
                        </TableRow>
                      </TableHeader>
                      <TableBody>
                        {detailBatch.invoices.map((inv) => (
                          <TableRow key={inv.invoice_id}>
                            <TableCell className="text-sm font-medium">{inv.invoice_no}</TableCell>
                            <TableCell className="text-sm">{inv.invoice_date}</TableCell>
                            <TableCell className="text-sm">{inv.processing_plant_name ?? "-"}</TableCell>
                            <TableCell className="text-sm">{inv.exporter_name ?? "-"}</TableCell>
                            <TableCell className="text-sm text-right">{inv.total_boxes}</TableCell>
                            <TableCell className="text-sm text-right">
                              ${Number(inv.total_amount_usd).toLocaleString()}
                            </TableCell>
                            {detailBatch.status === "open" && (
                              <TableCell className="text-center">
                                <Button
                                  variant="ghost"
                                  size="icon"
                                  className="h-7 w-7 text-red-500"
                                  onClick={() => handleRemoveInvoice(detailBatch.id, inv.invoice_id)}
                                  title="从批次移除"
                                >
                                  <Trash2 className="h-3 w-3" />
                                </Button>
                              </TableCell>
                            )}
                          </TableRow>
                        ))}
                      </TableBody>
                      {/* 合计行 */}
                      <tfoot className="bg-muted/50 border-t">
                        <TableRow className="font-medium text-sm">
                          <TableCell colSpan={4} className="text-right">合计</TableCell>
                          <TableCell className="text-right">
                            {detailBatch.invoices.reduce((sum, i) => sum + (i.total_boxes || 0), 0)}
                          </TableCell>
                          <TableCell className="text-right text-primary font-semibold">
                            ${detailBatch.invoices
                              .reduce((sum, i) => sum + Number(i.total_amount_usd || 0), 0)
                              .toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                          </TableCell>
                          {detailBatch.status === "open" && <TableCell></TableCell>}
                        </TableRow>
                      </tfoot>
                    </Table>
                  </div>
                ) : (
                  <div className="text-sm text-muted-foreground py-4 text-center border rounded-md">
                    暂无发票
                  </div>
                )}
              </div>

              {detailBatch.notes && (
                <div className="space-y-2">
                  <h3 className="text-sm font-semibold text-foreground">备注</h3>
                  <div className="text-sm bg-muted p-3 rounded-md whitespace-pre-wrap">
                    {detailBatch.notes}
                  </div>
                </div>
              )}
            </div>
          )}
        </DialogContent>
      </Dialog>

      {/* 标题栏 */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">批次管理</h1>
          <p className="text-sm text-muted-foreground">
            共 {data?.total ?? 0} 个批次
          </p>
        </div>
        <Button onClick={() => setFormOpen(true)}>
          <Plus className="h-4 w-4 mr-2" />
          新建批次
        </Button>
      </div>

      {/* 筛选栏 */}
      <div className="flex gap-4">
        <div className="relative flex-1 max-w-sm">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <Input
            placeholder="搜索批次名称..."
            value={search}
            onChange={(e) => { setSearch(e.target.value); setPage(1); }}
            className="pl-9"
          />
        </div>
        <Select value={statusFilter} onValueChange={(v) => { setStatusFilter(v ?? "all"); setPage(1); }}>
          <SelectTrigger className="w-[160px]">
            <SelectValue placeholder="状态筛选" />
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
              <TableHead>批次ID</TableHead>
              <TableHead>批次名称</TableHead>
              <TableHead>状态</TableHead>
              <TableHead>关联发票</TableHead>
              <TableHead>总箱数</TableHead>
              <TableHead>总净重(kg)</TableHead>
              <TableHead>总金额(USD)</TableHead>
              <TableHead>操作</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {isLoading ? (
              <TableRow>
                <TableCell colSpan={8} className="text-center py-8 text-muted-foreground">
                  加载中...
                </TableCell>
              </TableRow>
            ) : data?.items.length === 0 ? (
              <TableRow>
                <TableCell colSpan={8} className="text-center py-8 text-muted-foreground">
                  暂无数据
                </TableCell>
              </TableRow>
            ) : (
              data?.items.map((batch) => {
                const statusInfo = statusMap[batch.status] ?? { label: batch.status, color: "" };
                return (
                  <TableRow key={batch.id}>
                    <TableCell className="font-medium text-muted-foreground text-xs">
                      {batch.batch_code}
                    </TableCell>
                    <TableCell className="font-medium">
                      {batch.status === "locked" && <Lock className="h-3 w-3 inline mr-1 text-orange-500" />}
                      {batch.batch_name}
                    </TableCell>
                    <TableCell>
                      <Badge variant="secondary" className={statusInfo.color}>
                        {statusInfo.label}
                      </Badge>
                    </TableCell>
                    <TableCell>{batch.invoice_nos}</TableCell>
                    <TableCell>{batch.total_boxes}</TableCell>
                    <TableCell>
                      {Number(batch.total_weight_kg || 0).toLocaleString(undefined, { minimumFractionDigits: 3, maximumFractionDigits: 3 })}
                    </TableCell>
                    <TableCell className="font-semibold">
                      ${Number(batch.total_amount_usd || 0).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                    </TableCell>
                    <TableCell>
                      <div className="flex gap-1">
                        <Button variant="ghost" size="icon" className="h-8 w-8" onClick={() => handleView(batch)} title="查看">
                          <Eye className="h-4 w-4" />
                        </Button>
                        <Button variant="ghost" size="icon" className="h-8 w-8" onClick={() => handleLockToggle(batch)} title={batch.status === "locked" ? "解锁" : "锁定"}>
                          {batch.status === "locked" ? (
                            <Unlock className="h-4 w-4 text-orange-500" />
                          ) : (
                            <Lock className="h-4 w-4 text-muted-foreground" />
                          )}
                        </Button>
                        <Button variant="ghost" size="icon" className="h-8 w-8 text-red-500" onClick={() => handleDelete(batch)} title="删除" disabled={batch.status === "locked"}>
                          <Trash2 className={cn("h-4 w-4", batch.status === "locked" && "text-muted-foreground")} />
                        </Button>
                      </div>
                    </TableCell>
                  </TableRow>
                );
              })
            )}
          </TableBody>
          {/* 汇总行 */}
          {!isLoading && data && data.items.length > 0 && (
            <tfoot className="bg-muted/50 border-t">
              <TableRow className="font-medium text-sm">
                <TableCell colSpan={4} className="text-right">本页合计：</TableCell>
                <TableCell>
                  {data.items.reduce((sum, b) => sum + (b.total_boxes || 0), 0)}
                </TableCell>
                <TableCell>
                  {data.items.reduce((sum, b) => sum + Number(b.total_weight_kg || 0), 0).toLocaleString(undefined, { minimumFractionDigits: 3, maximumFractionDigits: 3 })}
                </TableCell>
                <TableCell className="text-primary font-semibold">
                  ${data.items.reduce((sum, b) => sum + Number(b.total_amount_usd || 0), 0).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                </TableCell>
                <TableCell></TableCell>
              </TableRow>
            </tfoot>
          )}
        </Table>
      </div>

      {/* 分页 */}
      {totalPages > 1 && (
        <div className="flex items-center justify-between">
          <div className="text-sm text-muted-foreground">
            显示 {(page - 1) * PAGE_SIZE + 1} - {Math.min(page * PAGE_SIZE, data?.total ?? 0)} / 共 {data?.total ?? 0} 条
          </div>
          <div className="flex items-center gap-2">
            <Button variant="outline" size="sm" onClick={() => setPage(page - 1)} disabled={page <= 1}>
              上一页
            </Button>
            <span className="text-sm">{page} / {totalPages}</span>
            <Button variant="outline" size="sm" onClick={() => setPage(page + 1)} disabled={page >= totalPages}>
              下一页
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}

// ==================== 创建批次弹窗 ====================

function BatchFormDialog({ open, onOpenChange }: { open: boolean; onOpenChange: (open: boolean) => void }) {
  const queryClient = useQueryClient();
  const [batchName, setBatchName] = useState("");
  const [notes, setNotes] = useState("");
  const [selectedInvoiceIds, setSelectedInvoiceIds] = useState<number[]>([]);
  const [isSubmitting, setIsSubmitting] = useState(false);

  // 获取未分配批次的发票
  const { data: invoicesData, isLoading: invoicesLoading } = useQuery<{ items: Invoice[]; total: number }>({
    queryKey: ["invoices-for-batch"],
    queryFn: async () => {
      const res = await api.get("/v1/invoices/?limit=500&exclude_assigned=true");
      return res.data;
    },
    enabled: open,
  });

  const resetForm = () => {
    setBatchName("");
    setNotes("");
    setSelectedInvoiceIds([]);
  };

  // 根据选中的发票自动生成批次名称
  const invoices = invoicesData?.items ?? [];
  const selectedInvoices = invoices.filter((inv) => selectedInvoiceIds.includes(inv.id));

  useEffect(() => {
    // 有选择发票时，按发票号生成名称
    if (selectedInvoices.length > 0) {
      const name = selectedInvoices.map((inv) => inv.invoice_no).join("&");
      setBatchName(name);
    } else {
      setBatchName("");
    }
  }, [selectedInvoiceIds, invoicesData]);

  const toggleInvoice = (id: number) => {
    setSelectedInvoiceIds((prev) =>
      prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id]
    );
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSubmitting(true);
    try {
      const payload = {
        batch_name: batchName.trim() || undefined,
        notes: notes.trim() || undefined,
        invoice_ids: selectedInvoiceIds.length > 0 ? selectedInvoiceIds : undefined,
      };
      await api.post("/v1/batches/", payload);
      toast.success("批次创建成功");
      queryClient.invalidateQueries({ queryKey: ["batches"] });
      queryClient.invalidateQueries({ queryKey: ["invoices-for-batch"] });
      onOpenChange(false);
      resetForm();
    } catch (error: any) {
      toast.error(error.response?.data?.detail ?? "创建失败");
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={(v) => { if (!v) { onOpenChange(false); resetForm(); } }}>
      <DialogContent className="max-w-[600px] w-[95vw] max-h-[90vh] overflow-y-auto p-6">
        <DialogHeader>
          <DialogTitle>新建批次</DialogTitle>
        </DialogHeader>

        <form onSubmit={handleSubmit} className="space-y-6">
          {/* 基本信息 */}
          <div className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="batch_name">批次名称</Label>
              <Input
                id="batch_name"
                value={batchName}
                onChange={(e) => setBatchName(e.target.value)}
                placeholder="留空自动按发票号生成"
              />
              <p className="text-xs text-muted-foreground">根据选择的发票自动生成</p>
            </div>
          </div>
          <div className="space-y-2">
            <Label htmlFor="notes">备注</Label>
            <Input
              id="notes"
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              placeholder="可选"
            />
          </div>

          {/* 发票选择 */}
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <Label>选择发票（可选）</Label>
              <span className="text-xs text-muted-foreground">
                已选 {selectedInvoiceIds.length} 张
              </span>
            </div>
            {invoicesLoading ? (
              <div className="text-sm text-muted-foreground py-4 text-center border rounded-md">
                加载发票中...
              </div>
            ) : !invoicesData?.items || invoicesData.items.length === 0 ? (
              <div className="text-sm text-muted-foreground py-4 text-center border rounded-md">
                暂无可分配的发票
              </div>
            ) : (
              <div className="border rounded-md max-h-[280px] overflow-y-auto">
                <div className="grid grid-cols-12 gap-2 px-3 py-2 text-xs text-muted-foreground font-medium bg-muted/50">
                  <div className="col-span-1 text-center">选择</div>
                  <div className="col-span-3">发票号</div>
                  <div className="col-span-2">日期</div>
                  <div className="col-span-2">EU注册号</div>
                  <div className="col-span-2">箱数</div>
                  <div className="col-span-2 text-right">金额</div>
                </div>
                {invoicesData.items.map((inv) => {
                  const selected = selectedInvoiceIds.includes(inv.id);
                  return (
                    <div
                      key={inv.id}
                      className={cn(
                        "grid grid-cols-12 gap-2 px-3 py-2 text-sm cursor-pointer border-t hover:bg-muted/30 transition-colors items-center",
                        selected && "bg-primary/5"
                      )}
                      onClick={() => toggleInvoice(inv.id)}
                    >
                      <div className="col-span-1 text-center">
                        <div
                          className={cn(
                            "w-4 h-4 rounded border mx-auto flex items-center justify-center text-xs",
                            selected
                              ? "bg-primary border-primary text-primary-foreground"
                              : "border-muted-foreground"
                          )}
                        >
                          {selected && "✓"}
                        </div>
                      </div>
                      <div className="col-span-3 font-medium">{inv.invoice_no}</div>
                      <div className="col-span-2">{inv.invoice_date}</div>
                      <div className="col-span-2">{inv.processing_plant_code ?? "-"}</div>
                      <div className="col-span-2">{inv.total_boxes}</div>
                      <div className="col-span-2 text-right">${Number(inv.total_amount_usd).toLocaleString()}</div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>

          <DialogFooter>
            <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>
              取消
            </Button>
            <Button type="submit" disabled={isSubmitting}>
              {isSubmitting ? "创建中..." : "创建批次"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
