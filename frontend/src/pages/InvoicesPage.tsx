import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { InvoiceFormDialog } from "@/components/InvoiceFormDialog";
import { InvoiceDetailDrawer } from "@/components/InvoiceDetailDrawer";
import { Plus, Search, Eye, Pencil, Trash2, Lock, Unlock } from "lucide-react";
import { toast } from "sonner";
import { BatchImportButton } from "@/components/BatchImportButton";

const customsStatusMap: Record<string, { label: string; color: string }> = {
  pending_customs: { label: "待报关", color: "bg-yellow-100 text-yellow-800" },
  customs_processing: { label: "已报关", color: "bg-blue-100 text-blue-800" },
  cleared: { label: "已结关", color: "bg-green-100 text-green-800" },
  // 兼容旧数据（已不使用的状态映射到新状态）
  pending_shipment: { label: "待报关", color: "bg-yellow-100 text-yellow-800" },
  in_transit: { label: "已报关", color: "bg-blue-100 text-blue-800" },
  picked_up: { label: "已结关", color: "bg-green-100 text-green-800" },
  PENDING_CUSTOMS: { label: "待报关", color: "bg-yellow-100 text-yellow-800" },
  CUSTOMS_PROCESSING: { label: "已报关", color: "bg-blue-100 text-blue-800" },
  CLEARED: { label: "已结关", color: "bg-green-100 text-green-800" },
  PENDING_SHIPMENT: { label: "待报关", color: "bg-yellow-100 text-yellow-800" },
  IN_TRANSIT: { label: "已报关", color: "bg-blue-100 text-blue-800" },
  PICKED_UP: { label: "已结关", color: "bg-green-100 text-green-800" },
};

const exchangeStatusMap: Record<string, { label: string; color: string }> = {
  NOT_EXCHANGED: { label: "未购汇", color: "bg-gray-100 text-gray-800" },
  PARTIAL: { label: "部分购汇", color: "bg-yellow-100 text-yellow-800" },
  COMPLETED: { label: "全部购汇", color: "bg-green-100 text-green-800" },
  // 兼容旧数据
  not_exchanged: { label: "未购汇", color: "bg-gray-100 text-gray-800" },
  partial: { label: "部分购汇", color: "bg-yellow-100 text-yellow-800" },
  completed: { label: "全部购汇", color: "bg-green-100 text-green-800" },
};

interface InvoiceProduct {
  id: number;
  invoice_id: number;
  product_name: string;
  product_spec: string;
  box_count: number;
  net_weight_kg: string;
  unit_price: string;
  total_amount: string;
  notes: string | null;
}

interface Invoice {
  id: number;
  invoice_no: string;
  invoice_date: string;
  kill_date: string | null;
  arrival_date: string | null;
  processing_plant_id: number;
  fish_farm_id: number;
  exporter_id: number;
  total_amount_usd: string;
  total_boxes: number;
  total_weight_kg: string;
  eta: string | null;
  awb_no: string | null;
  gross_weight_kg: string | null;
  net_weight_kg_sum?: string | null; // 产品明细净重汇总（后端计算）
  departure_date: string | null;
  flight_info: string | null;
  origin_certificate: string | null;
  inspection_certificate: string | null;
  customs_status: string;
  exchange_status: string;
  is_locked: boolean;
  processing_plant_name: string | null;
  processing_plant_code: string | null;
  fish_farm_name: string | null;
  fish_farm_code: string | null;
  exporter_name: string | null;
  exporter_code: string | null;
  notes: string | null;
  products: InvoiceProduct[];
  created_at: string;
}

interface InvoiceListResponse {
  total: number;
  items: Invoice[];
  skip: number;
  limit: number;
}

const PAGE_SIZE = 10;

export function InvoicesPage() {
  const [search, setSearch] = useState("");
  const [customsStatus, setCustomsStatus] = useState<string>("all");
  const [exchangeStatus, setExchangeStatus] = useState<string>("all");
  const [page, setPage] = useState(1);
  const [formOpen, setFormOpen] = useState(false);
  const [editingInvoice, setEditingInvoice] = useState<Invoice | null>(null);
  const [detailOpen, setDetailOpen] = useState(false);
  const [detailInvoiceId, setDetailInvoiceId] = useState<number | null>(null);
  const queryClient = useQueryClient();

  const { data, isLoading } = useQuery<InvoiceListResponse>({
    queryKey: ["invoices", search, customsStatus, exchangeStatus, page],
    queryFn: async () => {
      const params = new URLSearchParams();
      if (search) params.append("search", search);
      if (customsStatus && customsStatus !== "all") params.append("customs_status", customsStatus);
      if (exchangeStatus && exchangeStatus !== "all") params.append("exchange_status", exchangeStatus);
      params.append("skip", String((page - 1) * PAGE_SIZE));
      params.append("limit", String(PAGE_SIZE));
      const res = await api.get(`/v1/invoices/?${params.toString()}`);
      return res.data;
    },
  });

  // 查询全部数据用于汇总统计（不分页）
  const { data: allData } = useQuery<InvoiceListResponse>({
    queryKey: ["invoices", search, customsStatus, exchangeStatus, "all"],
    queryFn: async () => {
      const params = new URLSearchParams();
      if (search) params.append("search", search);
      if (customsStatus && customsStatus !== "all") params.append("customs_status", customsStatus);
      if (exchangeStatus && exchangeStatus !== "all") params.append("exchange_status", exchangeStatus);
      params.append("skip", "0");
      params.append("limit", "500");
      const res = await api.get(`/v1/invoices/?${params.toString()}`);
      return res.data;
    },
    enabled: true, // Always load
  });

  const totalPages = data ? Math.ceil(data.total / PAGE_SIZE) : 0;

  const handleView = (invoice: Invoice) => {
    setDetailInvoiceId(invoice.id);
    setDetailOpen(true);
  };

  const [deleteConfirm, setDeleteConfirm] = useState<Invoice | null>(null);

  const handleDelete = async (invoice: Invoice) => {
    if (invoice.is_locked) {
      toast.error("发票已锁定，不能删除");
      return;
    }
    setDeleteConfirm(invoice);
  };

  const confirmDelete = async () => {
    if (!deleteConfirm) return;
    try {
      await api.delete(`/v1/invoices/${deleteConfirm.id}`);
      toast.success("发票已删除");
      queryClient.invalidateQueries({ queryKey: ["invoices"] });
    } catch (error: any) {
      const detail = error.response?.data?.detail;
      let msg: string;
      if (Array.isArray(detail)) {
        msg = detail.map((d: any) => d.msg).join("; ");
      } else if (typeof detail === "string") {
        msg = detail;
      } else {
        msg = "删除失败";
      }
      toast.error(msg);
    } finally {
      setDeleteConfirm(null);
    }
  };

  const handleLockToggle = async (invoice: Invoice) => {
    try {
      if (invoice.is_locked) {
        await api.post(`/v1/invoices/${invoice.id}/unlock`);
        toast.success("发票已解锁");
      } else {
        await api.post(`/v1/invoices/${invoice.id}/lock`);
        toast.success("发票已锁定");
      }
      queryClient.invalidateQueries({ queryKey: ["invoices"] });
    } catch (error: any) {
      toast.error(error.response?.data?.detail ?? "操作失败");
    }
  };

  const handleAdd = () => {
    setEditingInvoice(null);
    setFormOpen(true);
  };

  const handleEdit = (invoice: Invoice) => {
    if (invoice.is_locked) {
      toast.error("发票已锁定，不能编辑");
      return;
    }
    setEditingInvoice(invoice);
    setFormOpen(true);
  };

  return (
    <div className="space-y-6">
      <InvoiceFormDialog
        open={formOpen}
        onOpenChange={setFormOpen}
        initialData={editingInvoice}
      />
      <InvoiceDetailDrawer
        invoiceId={detailInvoiceId}
        open={detailOpen}
        onOpenChange={setDetailOpen}
        onEdit={(id) => {
          const invoice = data?.items?.find((i) => i.id === id);
          if (invoice) {
            setDetailOpen(false);
            handleEdit(invoice);
          }
        }}
      />

      {/* 标题栏 */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">进口单证</h1>
          <p className="text-sm text-muted-foreground">
            共 {data?.total ?? 0} 张发票
          </p>
        </div>
        <div className="flex gap-2">
          <BatchImportButton type="invoices" />
          <Button onClick={handleAdd}>
            <Plus className="h-4 w-4 mr-2" />
            新增发票
          </Button>
        </div>
      </div>

      {/* 筛选栏 */}
      <div className="flex gap-4">
        <div className="relative w-[160px]">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <Input
            placeholder="搜索发票号..."
            value={search}
            onChange={(e) => { setSearch(e.target.value); setPage(1); }}
            className="pl-9 w-[160px]"
          />
        </div>
        <Select value={customsStatus} onValueChange={(v) => { setCustomsStatus(v ?? "all"); setPage(1); }}>
          <SelectTrigger className="w-[90px]">
            <SelectValue>
              {customsStatus === "all" ? "全部报关" : customsStatusMap[customsStatus]?.label || "全部报关"}
            </SelectValue>
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">全部报关</SelectItem>
            <SelectItem value="pending_customs">待报关</SelectItem>
            <SelectItem value="customs_processing">已报关</SelectItem>
            <SelectItem value="cleared">已结关</SelectItem>
          </SelectContent>
        </Select>
        <Select value={exchangeStatus} onValueChange={(v) => { setExchangeStatus(v ?? "all"); setPage(1); }}>
          <SelectTrigger className="w-[90px]">
            <SelectValue>
              {exchangeStatus === "all" ? "全部购汇" : exchangeStatusMap[exchangeStatus]?.label || "全部购汇"}
            </SelectValue>
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">全部购汇</SelectItem>
            {Object.entries(exchangeStatusMap).map(([key, { label }]) => (
              <SelectItem key={key} value={key}>{label}</SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      {/* 全局统计卡片 */}
      <div className="grid grid-cols-4 gap-4">
        <div className="bg-muted/50 rounded-lg p-3 text-center">
          <div className="text-xs text-muted-foreground">发票总数</div>
          <div className="text-lg font-bold">{allData?.total ?? data?.total ?? 0}</div>
        </div>
        <div className="bg-muted/50 rounded-lg p-3 text-center">
          <div className="text-xs text-muted-foreground">总箱数</div>
          <div className="text-lg font-bold text-primary">
            {(allData?.items ?? []).reduce((sum, inv) => sum + (parseInt(String(inv.total_boxes)) || 0), 0)}
          </div>
        </div>
        <div className="bg-muted/50 rounded-lg p-3 text-center">
          <div className="text-xs text-muted-foreground">总重量(kg)</div>
          <div className="text-lg font-bold text-primary">
            {(allData?.items ?? []).reduce((sum, inv) => sum + (parseFloat(String((inv as any).net_weight_kg_sum || inv.total_weight_kg)) || 0), 0).toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2})}
          </div>
        </div>
        <div className="bg-muted/50 rounded-lg p-3 text-center">
          <div className="text-xs text-muted-foreground">总金额(USD)</div>
          <div className="text-lg font-bold text-primary">
            ${(allData?.items ?? []).reduce((sum, inv) => sum + (parseFloat(String(inv.total_amount_usd)) || 0), 0).toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2})}
          </div>
        </div>
      </div>

      {/* 数据表格 */}
      <div className="border rounded-lg">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>发票号</TableHead>
              <TableHead>发票日期</TableHead>
              <TableHead>宰杀日期</TableHead>
              <TableHead>ETA</TableHead>
              <TableHead>加工厂</TableHead>
              <TableHead>出口商</TableHead>
              <TableHead>规格(箱数)</TableHead>
              <TableHead>总箱数</TableHead>
              <TableHead>总净重(kg)</TableHead>
              <TableHead>总金额(USD)</TableHead>
              <TableHead>AWB</TableHead>
              <TableHead>报关状态</TableHead>
              <TableHead>购汇状态</TableHead>
              <TableHead className="w-[120px]">操作</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {isLoading ? (
              <TableRow>
                <TableCell colSpan={14} className="text-center py-8 text-muted-foreground">
                  加载中...
                </TableCell>
              </TableRow>
            ) : (data?.items?.length ?? 0) === 0 ? (
              <TableRow>
                <TableCell colSpan={14} className="text-center py-8 text-muted-foreground">
                  暂无数据
                </TableCell>
              </TableRow>
            ) : (
              data?.items.map((invoice) => {
                const customsInfo = customsStatusMap[invoice.customs_status] ?? { label: invoice.customs_status, color: "" };
                const exchangeInfo = exchangeStatusMap[invoice.exchange_status] ?? { label: invoice.exchange_status, color: "" };
                // 规格汇总：规格 + 箱数
                const specSummary = invoice.products.map(p => `${p.product_spec}(${p.box_count})`).join(", ");
                return (
                  <TableRow key={invoice.id}>
                    <TableCell className="font-medium">
                      {invoice.is_locked && <Lock className="h-3 w-3 inline mr-1 text-red-500" />}
                      {invoice.invoice_no}
                    </TableCell>
                    <TableCell>{invoice.invoice_date}</TableCell>
                    <TableCell>{invoice.kill_date ?? "-"}</TableCell>
                    <TableCell>{invoice.eta ? new Date(invoice.eta).toLocaleString('zh-CN', {year: 'numeric', month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit'}).replace(/\//g, '-') : "-"}</TableCell>
                    <TableCell>{invoice.processing_plant_code ?? invoice.processing_plant_name ?? "-"}</TableCell>
                    <TableCell>{invoice.exporter_name ?? "-"}</TableCell>
                    <TableCell className="text-sm text-muted-foreground max-w-[150px] truncate" title={specSummary}>
                      {specSummary || "-"}
                    </TableCell>
                    <TableCell>{invoice.total_boxes}</TableCell>
                    <TableCell>{Number((invoice as any).net_weight_kg_sum || invoice.total_weight_kg).toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2})}</TableCell>
                    <TableCell>${Number(invoice.total_amount_usd).toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2})}</TableCell>
                    <TableCell>{invoice.awb_no ?? "-"}</TableCell>
                    <TableCell>
                      <Badge variant="secondary" className={customsInfo.color}>
                        {customsInfo.label}
                      </Badge>
                    </TableCell>
                    <TableCell>
                      <Badge variant="secondary" className={exchangeInfo.color}>
                        {exchangeInfo.label}
                      </Badge>
                    </TableCell>
                    <TableCell>
                      <div className="flex gap-1">
                        <Button variant="ghost" size="icon" className="h-8 w-8" onClick={() => handleView(invoice)} title="查看">
                          <Eye className="h-4 w-4" />
                        </Button>
                        <Button variant="ghost" size="icon" className="h-8 w-8" onClick={() => handleEdit(invoice)} title={invoice.is_locked ? "已锁定" : "编辑"} disabled={invoice.is_locked}>
                          <Pencil className={cn("h-4 w-4", invoice.is_locked && "text-muted-foreground")} />
                        </Button>
                        <Button variant="ghost" size="icon" className="h-8 w-8" onClick={() => handleLockToggle(invoice)} title={invoice.is_locked ? "解锁" : "锁定"}>
                          {invoice.is_locked ? <Unlock className="h-4 w-4 text-orange-500" /> : <Lock className="h-4 w-4 text-muted-foreground" />}
                        </Button>
                        <Button variant="ghost" size="icon" className="h-8 w-8 text-red-500" onClick={() => handleDelete(invoice)} title="删除" disabled={invoice.is_locked}>
                          <Trash2 className={cn("h-4 w-4", invoice.is_locked && "text-muted-foreground")} />
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
                <TableCell colSpan={7} className="text-right">本页合计：</TableCell>
                <TableCell>
                  {data.items.reduce((sum, inv) => sum + (inv.total_boxes || 0), 0)}
                </TableCell>
                <TableCell>
                  {data.items.reduce((sum, inv) => sum + Number((inv as any).net_weight_kg_sum || inv.total_weight_kg || 0), 0).toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2})}
                </TableCell>
                <TableCell className="text-primary font-semibold">
                  ${data.items.reduce((sum, inv) => sum + Number(inv.total_amount_usd || 0), 0).toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2})}
                </TableCell>
                <TableCell colSpan={4}></TableCell>
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
            <Button
              variant="outline"
              size="sm"
              onClick={() => setPage(page - 1)}
              disabled={page <= 1}
            >
              上一页
            </Button>
            <span className="text-sm">
              {page} / {totalPages}
            </span>
            <Button
              variant="outline"
              size="sm"
              onClick={() => setPage(page + 1)}
              disabled={page >= totalPages}
            >
              下一页
            </Button>
          </div>
        </div>
      )}

      {/* 删除确认弹窗 */}
      {deleteConfirm && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-background rounded-lg p-6 max-w-sm w-full mx-4 shadow-lg">
            <h3 className="text-lg font-semibold mb-2">确认删除</h3>
            <p className="text-muted-foreground mb-6">
              确定要删除发票 "{deleteConfirm.invoice_no}" 吗？此操作不可撤销。
            </p>
            <div className="flex justify-end gap-2">
              <Button variant="outline" onClick={() => setDeleteConfirm(null)}>
                取消
              </Button>
              <Button variant="destructive" onClick={confirmDelete}>
                删除
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
