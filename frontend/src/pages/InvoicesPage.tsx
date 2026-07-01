import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { useQueryClient } from "@tanstack/react-query";
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
import { Badge } from "@/components/ui/badge";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "@/components/ui/dialog";
import { InvoiceFormDialog } from "@/components/InvoiceFormDialog";
import { InvoiceDetailDrawer } from "@/components/InvoiceDetailDrawer";
import { Plus, Search, Eye, Pencil, Trash2, Lock, Unlock, DollarSign, X } from "lucide-react";
import { toast } from "sonner";
import { BatchImportButton } from "@/components/BatchImportButton";

const customsStatusMap: Record<string, { label: string; color: string }> = {
  pending_customs: { label: "待报关", color: "bg-yellow-100 text-yellow-800" },
  customs_processing: { label: "已报关", color: "bg-blue-100 text-blue-800" },
  cleared: { label: "已结关", color: "bg-green-100 text-green-800" },
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
  not_exchanged: { label: "未购汇", color: "bg-gray-100 text-gray-800" },
  completed: { label: "已购汇", color: "bg-green-100 text-green-800" },
  partial: { label: "已购汇", color: "bg-green-100 text-green-800" },
  NOT_EXCHANGED: { label: "未购汇", color: "bg-gray-100 text-gray-800" },
  COMPLETED: { label: "已购汇", color: "bg-green-100 text-green-800" },
  PARTIAL: { label: "已购汇", color: "bg-green-100 text-green-800" },
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
  supplier_id: number;
  total_amount_usd: string;
  total_boxes: number;
  total_weight_kg: string;
  eta: string | null;
  awb_no: string | null;
  gross_weight_kg: string | null;
  net_weight_kg_sum?: string | null;
  departure_date: string | null;
  flight_info: string | null;
  origin_certificate: string | null;
  inspection_certificate: string | null;
  customs_status: string;
  exchange_status: string;
  is_locked: boolean;
  is_master: boolean;
  parent_invoice_id: number | null;
  parent_invoice_no: string | null;
  processing_plant_name: string | null;
  processing_plant_code: string | null;
  fish_farm_name: string | null;
  fish_farm_code: string | null;
  exporter_name: string | null;
  exporter_code: string | null;
  importer_name: string | null;
  notes: string | null;
  products: InvoiceProduct[];
  sub_invoices?: { id: number; invoice_no: string }[] | null;
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
  const [selectedInvoice, setSelectedInvoice] = useState<Invoice | null>(null);
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
    enabled: true,
  });

  const totalPages = data ? Math.ceil(data.total / PAGE_SIZE) : 0;

  const handleView = (invoice: Invoice) => {
    setDetailInvoiceId(invoice.id);
    setDetailOpen(true);
  };

  const [deleteConfirm, setDeleteConfirm] = useState<Invoice | null>(null);
  const [allocateInvoice, setAllocateInvoice] = useState<Invoice | null>(null);
  const [allocateClearanceCost, setAllocateClearanceCost] = useState("");
  const [allocateImportDuty, setAllocateImportDuty] = useState("");
  const [allocateImportVat, setAllocateImportVat] = useState("");
  const [allocateMethod, setAllocateMethod] = useState("by_boxes");

  const handleDelete = async (invoice: Invoice) => {
    if (invoice.is_locked) {
      toast.error("发票已锁定，不能删除");
      return;
    }
    setDeleteConfirm(invoice);
  };

  const handleAllocate = async (invoice: Invoice) => {
    setAllocateInvoice(invoice);
  };

  const confirmDelete = async () => {
    if (!deleteConfirm) return;
    try {
      await api.delete(`/v1/invoices/${deleteConfirm.id}`);
      toast.success("发票已删除");
      queryClient.invalidateQueries({ queryKey: ["invoices"] });
      if (selectedInvoice?.id === deleteConfirm.id) {
        setSelectedInvoice(null);
      }
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
    <div className="h-full flex flex-col gap-4">
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

      {/* ==================== 功能区 ==================== */}
      <div className="flex-none space-y-3">
        {/* 搜索行：标题 + 搜索 + 筛选 + 操作按钮 */}
        <div className="flex items-center justify-between gap-4">
          <div className="flex items-center gap-4">
            <div>
              <h1 className="text-2xl font-bold">进口单证</h1>
              <p className="text-sm text-muted-foreground">
                共 {data?.total ?? 0} 张发票
              </p>
            </div>
            <div className="flex gap-2">
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
                  <SelectItem value="not_exchanged">未购汇</SelectItem>
                  <SelectItem value="completed">已购汇</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>
          <div className="flex gap-2">
            <BatchImportButton type="invoices" />
            <Button onClick={handleAdd}>
              <Plus className="h-4 w-4 mr-2" />
              新增发票
            </Button>
          </div>
        </div>

        {/* 汇总行 */}
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
      </div>

      {/* ==================== 列表区 + 详情区 ==================== */}
      <div className="flex-1 flex flex-col min-h-0 gap-4">

        {/* 列表区 — 自适应高度，超出时内部滚动 */}
        <div className="flex-none flex flex-col min-h-0 border rounded-lg overflow-hidden">
          <div className="overflow-auto" style={{ maxHeight: 'calc(100vh - 320px)' }}>
            <Table>
              <TableHeader>
                <TableRow className="bg-muted/50">
                  <TableHead className="sticky top-0 bg-background z-10 w-[140px]">发票号</TableHead>
                  <TableHead className="sticky top-0 bg-background z-10">发票日期</TableHead>
                  <TableHead className="sticky top-0 bg-background z-10">宰杀日期</TableHead>
                  <TableHead className="sticky top-0 bg-background z-10">ETA</TableHead>
                  <TableHead className="sticky top-0 bg-background z-10">加工厂</TableHead>
                  <TableHead className="sticky top-0 bg-background z-10">出口商</TableHead>
                  <TableHead className="sticky top-0 bg-background z-10">进口商</TableHead>
                  <TableHead className="sticky top-0 bg-background z-10">规格(箱数)</TableHead>
                  <TableHead className="sticky top-0 bg-background z-10">总箱数</TableHead>
                  <TableHead className="sticky top-0 bg-background z-10">总净重(kg)</TableHead>
                  <TableHead className="sticky top-0 bg-background z-10">总金额(USD)</TableHead>
                  <TableHead className="sticky top-0 bg-background z-10">AWB</TableHead>
                  <TableHead className="sticky top-0 bg-background z-10">报关状态</TableHead>
                  <TableHead className="sticky top-0 bg-background z-10">购汇状态</TableHead>
                  <TableHead className="sticky top-0 bg-background z-10 w-[140px]">操作</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {isLoading ? (
                  <TableRow>
                    <TableCell colSpan={15} className="text-center py-8 text-muted-foreground">
                      加载中...
                    </TableCell>
                  </TableRow>
                ) : (data?.items?.length ?? 0) === 0 ? (
                  <TableRow>
                    <TableCell colSpan={15} className="text-center py-8 text-muted-foreground">
                      暂无数据
                    </TableCell>
                  </TableRow>
                ) : (
                  data?.items.map((invoice) => {
                    const customsInfo = customsStatusMap[invoice.customs_status] ?? { label: invoice.customs_status, color: "" };
                    const exchangeInfo = exchangeStatusMap[invoice.exchange_status] ?? { label: invoice.exchange_status, color: "" };
                    const specSummary = invoice.products.map(p => `${p.product_spec}(${p.box_count})`).join(", ");
                    const isSelected = selectedInvoice?.id === invoice.id;
                    return (
                      <TableRow
                        key={invoice.id}
                        className={cn(
                          "cursor-pointer transition-colors",
                          isSelected && "bg-primary/10 hover:bg-primary/15"
                        )}
                        onClick={() => setSelectedInvoice(invoice)}
                      >
                        <TableCell className="font-medium">
                          {invoice.is_locked && <Lock className="h-3 w-3 inline mr-1 text-red-500" />}
                          {invoice.parent_invoice_id && (
                            <span className="text-xs text-muted-foreground mr-1">└</span>
                          )}
                          {invoice.invoice_no}
                          {invoice.is_master === true && !invoice.parent_invoice_id && (
                            <Badge variant="outline" className="ml-1 text-[10px] h-4 px-1 bg-blue-50 text-blue-600">主</Badge>
                          )}
                          {invoice.parent_invoice_id && invoice.parent_invoice_no && (
                            <span className="text-xs text-muted-foreground ml-1">({invoice.parent_invoice_no})</span>
                          )}
                        </TableCell>
                        <TableCell>{invoice.invoice_date}</TableCell>
                        <TableCell>{invoice.kill_date ?? "-"}</TableCell>
                        <TableCell>{invoice.eta ? new Date(invoice.eta).toLocaleString('zh-CN', {year: 'numeric', month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit'}).replace(/\//g, '-') : "-"}</TableCell>
                        <TableCell>{invoice.processing_plant_code ?? invoice.processing_plant_name ?? "-"}</TableCell>
                        <TableCell>{invoice.exporter_name ?? "-"}</TableCell>
                        <TableCell>{invoice.importer_name ?? "-"}</TableCell>
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
                            <Button variant="ghost" size="icon" className="h-8 w-8" onClick={(e) => { e.stopPropagation(); handleView(invoice); }} title="查看">
                              <Eye className="h-4 w-4" />
                            </Button>
                            <Button variant="ghost" size="icon" className="h-8 w-8" onClick={(e) => { e.stopPropagation(); handleLockToggle(invoice); }} title={invoice.is_locked ? "解锁" : "锁定"}>
                              {invoice.is_locked ? <Unlock className="h-4 w-4 text-orange-500" /> : <Lock className="h-4 w-4 text-muted-foreground" />}
                            </Button>
                            {!invoice.is_locked && (
                              <>
                                <Button variant="ghost" size="icon" className="h-8 w-8" onClick={(e) => { e.stopPropagation(); handleEdit(invoice); }} title="编辑">
                                  <Pencil className="h-4 w-4" />
                                </Button>
                                {invoice.sub_invoices && invoice.sub_invoices.length > 0 ? (
                                  <Button variant="ghost" size="icon" className="h-8 w-8 text-red-300 cursor-not-allowed" disabled title={`存在 ${invoice.sub_invoices.length} 条从票，请先删除从票`}>
                                    <Trash2 className="h-4 w-4" />
                                  </Button>
                                ) : (
                                  <Button variant="ghost" size="icon" className="h-8 w-8 text-red-500" onClick={(e) => { e.stopPropagation(); handleDelete(invoice); }} title="删除">
                                    <Trash2 className="h-4 w-4" />
                                  </Button>
                                )}
                                {((invoice.is_master === true || invoice.is_master === null) || invoice.parent_invoice_id) && (
                                  <Button variant="ghost" size="icon" className="h-8 w-8 text-blue-500" onClick={(e) => { e.stopPropagation(); handleAllocate(invoice); }} title="费用分摊">
                                    <DollarSign className="h-4 w-4" />
                                  </Button>
                                )}
                              </>
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

          {/* 分页 + 汇总行 */}
          <div className="flex-none border-t bg-muted/30">
            {!isLoading && data && data.items.length > 0 && (
              <div className="flex items-center justify-between px-4 py-2 text-sm">
                <div className="flex items-center gap-4">
                  <span className="text-muted-foreground">
                    显示 {(page - 1) * PAGE_SIZE + 1} - {Math.min(page * PAGE_SIZE, data?.total ?? 0)} / 共 {data?.total ?? 0} 条
                  </span>
                  <span className="text-muted-foreground">|</span>
                  <span>本页合计：箱数 {data.items.reduce((sum, inv) => sum + (inv.total_boxes || 0), 0)} · 净重 {data.items.reduce((sum, inv) => sum + Number((inv as any).net_weight_kg_sum || inv.total_weight_kg || 0), 0).toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2})} kg · 金额 ${data.items.reduce((sum, inv) => sum + Number(inv.total_amount_usd || 0), 0).toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2})}</span>
                </div>
                {totalPages > 1 && (
                  <div className="flex items-center gap-2">
                    <Button variant="outline" size="sm" onClick={() => setPage(page - 1)} disabled={page <= 1}>上一页</Button>
                    <span className="text-sm">{page} / {totalPages}</span>
                    <Button variant="outline" size="sm" onClick={() => setPage(page + 1)} disabled={page >= totalPages}>下一页</Button>
                  </div>
                )}
              </div>
            )}
          </div>
        </div>

        {/* ==================== 详情区 ==================== */}
        {selectedInvoice && (
          <div className="flex-none border rounded-lg overflow-auto bg-background">
            <div className="p-3 space-y-3">
              {/* 详情头部 */}
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <h3 className="font-semibold text-base">发票详情</h3>
                  <Badge variant="secondary" className={customsStatusMap[selectedInvoice.customs_status]?.color || ""}>
                    {customsStatusMap[selectedInvoice.customs_status]?.label || selectedInvoice.customs_status}
                  </Badge>
                  <Badge variant="secondary" className={exchangeStatusMap[selectedInvoice.exchange_status]?.color || ""}>
                    {exchangeStatusMap[selectedInvoice.exchange_status]?.label || selectedInvoice.exchange_status}
                  </Badge>
                  {selectedInvoice.is_locked && (
                    <Badge variant="outline" className="text-red-500 border-red-200">
                      <Lock className="h-3 w-3 mr-1" />已锁定
                    </Badge>
                  )}
                </div>
                <div className="flex gap-2">
                  <Button variant="ghost" size="sm" onClick={() => handleView(selectedInvoice)}>
                    <Eye className="h-4 w-4 mr-1" />完整详情
                  </Button>
                  <Button variant="ghost" size="icon" className="h-8 w-8" onClick={() => setSelectedInvoice(null)}>
                    <X className="h-4 w-4" />
                  </Button>
                </div>
              </div>

              {/* 产品明细（在上） */}
              {selectedInvoice.products.length > 0 && (
                <div>
                  <div className="text-muted-foreground text-xs mb-1">产品明细 ({selectedInvoice.products.length} 项)</div>
                  <div className="border rounded-md overflow-hidden">
                    <Table>
                      <TableHeader>
                        <TableRow className="bg-muted/30">
                          <TableHead className="text-xs h-7">规格</TableHead>
                          <TableHead className="text-xs h-7">箱数</TableHead>
                          <TableHead className="text-xs h-7">净重(kg)</TableHead>
                          <TableHead className="text-xs h-7">单价(USD)</TableHead>
                          <TableHead className="text-xs h-7">金额(USD)</TableHead>
                          <TableHead className="text-xs h-7">备注</TableHead>
                        </TableRow>
                      </TableHeader>
                      <TableBody>
                        {selectedInvoice.products.map((p) => (
                          <TableRow key={p.id} className="h-7">
                            <TableCell className="text-sm py-0.5">{p.product_spec}</TableCell>
                            <TableCell className="text-sm py-0.5">{p.box_count}</TableCell>
                            <TableCell className="text-sm py-0.5">{p.net_weight_kg}</TableCell>
                            <TableCell className="text-sm py-0.5">${p.unit_price}</TableCell>
                            <TableCell className="text-sm py-0.5">${p.total_amount}</TableCell>
                            <TableCell className="text-sm py-0.5 text-muted-foreground">{p.notes ?? "-"}</TableCell>
                          </TableRow>
                        ))}
                        {/* 汇总行 */}
                        <TableRow className="bg-muted/20 font-medium h-7">
                          <TableCell className="text-sm py-0.5">合计</TableCell>
                          <TableCell className="text-sm py-0.5">{selectedInvoice.products.reduce((s, p) => s + p.box_count, 0)}</TableCell>
                          <TableCell className="text-sm py-0.5">{selectedInvoice.products.reduce((s, p) => s + parseFloat(p.net_weight_kg), 0).toFixed(3)}</TableCell>
                          <TableCell className="text-sm py-0.5">-</TableCell>
                          <TableCell className="text-sm py-0.5">${selectedInvoice.products.reduce((s, p) => s + parseFloat(p.total_amount), 0).toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2})}</TableCell>
                          <TableCell className="text-sm py-0.5">-</TableCell>
                        </TableRow>
                      </TableBody>
                    </Table>
                  </div>
                </div>
              )}
            </div>
          </div>
        )}
      </div>

      {/* ==================== 弹窗 ==================== */}

      {/* 费用分摊弹窗 */}
      {allocateInvoice && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-background rounded-lg p-6 max-w-md w-full mx-4 shadow-lg">
            <h3 className="text-lg font-semibold mb-2">AWB 费用分摊</h3>
            <p className="text-sm text-muted-foreground mb-4">
              发票: {allocateInvoice.invoice_no} {allocateInvoice.awb_no && `(AWB: ${allocateInvoice.awb_no})`}
            </p>
            <div className="space-y-3 mb-6">
              <div className="space-y-1">
                <Label className="text-xs">清关运费(总额)</Label>
                <Input type="number" placeholder="0" value={allocateClearanceCost} onChange={(e) => setAllocateClearanceCost(e.target.value)} />
              </div>
              <div className="space-y-1">
                <Label className="text-xs">进口关税(总额)</Label>
                <Input type="number" placeholder="0" value={allocateImportDuty} onChange={(e) => setAllocateImportDuty(e.target.value)} />
              </div>
              <div className="space-y-1">
                <Label className="text-xs">进口增值税(总额)</Label>
                <Input type="number" placeholder="0" value={allocateImportVat} onChange={(e) => setAllocateImportVat(e.target.value)} />
              </div>
              <div className="space-y-1">
                <Label className="text-xs">分摊方式</Label>
                <Select value={allocateMethod} onValueChange={(v) => setAllocateMethod(v ?? "by_boxes")}>
                  <SelectTrigger className="w-full">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="by_boxes">按箱数</SelectItem>
                    <SelectItem value="by_weight">按重量</SelectItem>
                    <SelectItem value="by_amount">按金额</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>
            <div className="flex justify-end gap-2">
              <Button variant="outline" onClick={() => { setAllocateInvoice(null); setAllocateClearanceCost(""); setAllocateImportDuty(""); setAllocateImportVat(""); setAllocateMethod("by_boxes"); }}>
                取消
              </Button>
              <Button onClick={async () => {
                try {
                  const params = new URLSearchParams();
                  if (allocateClearanceCost) params.append('clearance_cost', allocateClearanceCost);
                  if (allocateImportDuty) params.append('import_duty', allocateImportDuty);
                  if (allocateImportVat) params.append('import_vat', allocateImportVat);
                  params.append('allocation_method', allocateMethod);
                  
                  await api.post(`/v1/invoices/${allocateInvoice.id}/allocate-costs?${params.toString()}`);
                  toast.success('费用分摊成功');
                  queryClient.invalidateQueries({ queryKey: ['invoices'] });
                  setAllocateInvoice(null);
                  setAllocateClearanceCost("");
                  setAllocateImportDuty("");
                  setAllocateImportVat("");
                  setAllocateMethod("by_boxes");
                } catch (error: any) {
                  toast.error(error.response?.data?.detail || '分摊失败');
                }
              }}>
                确认分摊
              </Button>
            </div>
          </div>
        </div>
      )}

      {/* 删除确认弹窗 */}
      <Dialog open={!!deleteConfirm} onOpenChange={() => setDeleteConfirm(null)}>
        <DialogContent className="max-w-sm">
          <DialogHeader>
            <DialogTitle>确认删除</DialogTitle>
          </DialogHeader>
          <p className="text-muted-foreground mb-6">
            确定要删除发票 "{deleteConfirm?.invoice_no}" 吗？此操作不可撤销。
          </p>
          <DialogFooter>
            <Button variant="outline" onClick={() => setDeleteConfirm(null)}>
              取消
            </Button>
            <Button variant="destructive" onClick={confirmDelete}>
              删除
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
