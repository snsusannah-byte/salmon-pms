import { api } from "@/lib/api";
import { useQuery } from "@tanstack/react-query";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from "@/components/ui/dialog";
import { Badge } from "@/components/ui/badge";

const customsStatusMap: Record<string, { label: string; color: string }> = {
  PENDING_SHIPMENT: { label: "未报关", color: "bg-gray-100 text-gray-800" },
  IN_TRANSIT: { label: "运输中", color: "bg-blue-100 text-blue-800" },
  PENDING_CUSTOMS: { label: "待报关", color: "bg-yellow-100 text-yellow-800" },
  CUSTOMS_PROCESSING: { label: "报关中", color: "bg-orange-100 text-orange-800" },
  CLEARED: { label: "已清关", color: "bg-green-100 text-green-800" },
  PICKED_UP: { label: "已提货", color: "bg-purple-100 text-purple-800" },
  // 兼容旧数据
  pending_shipment: { label: "未报关", color: "bg-gray-100 text-gray-800" },
  in_transit: { label: "运输中", color: "bg-blue-100 text-blue-800" },
  pending_customs: { label: "待报关", color: "bg-yellow-100 text-yellow-800" },
  customs_processing: { label: "报关中", color: "bg-orange-100 text-orange-800" },
  cleared: { label: "已清关", color: "bg-green-100 text-green-800" },
  picked_up: { label: "已提货", color: "bg-purple-100 text-purple-800" },
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
import { Button } from "@/components/ui/button";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Pencil, X, Lock } from "lucide-react";



interface InvoiceDetailProps {
  invoiceId: number | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onEdit?: (invoiceId: number) => void;
}

interface InvoiceDetail {
  id: number;
  invoice_no: string;
  invoice_date: string;
  kill_date: string | null;
  arrival_date: string | null;
  processing_plant_id: number;
  processing_plant_name: string | null;
  fish_farm_id: number;
  fish_farm_name: string | null;
  exporter_id: number;
  exporter_name: string | null;
  supplier_id: number;
  supplier_name: string | null;
  total_amount_usd: string;
  total_boxes: number;
  total_weight_kg: string;
  awb_no: string | null;
  gross_weight_kg: string | null;
  eta: string | null;
  departure_date: string | null;
  flight_info: string | null;
  origin_certificate: string | null;
  inspection_certificate: string | null;
  customs_status: string;
  exchange_status: string;
  is_locked: boolean;
  notes: string | null;
  products: Array<{
    id: number;
    product_name: string;
    product_spec: string;
    box_count: number;
    net_weight_kg: string;
    unit_price: string;
    total_amount: string;
  }>;
  created_at: string;
  updated_at: string;
}

export function InvoiceDetailDrawer({ invoiceId, open, onOpenChange, onEdit }: InvoiceDetailProps) {
  const { data: invoice, isLoading } = useQuery<InvoiceDetail>({
    queryKey: ["invoice", invoiceId],
    queryFn: async () => {
      if (!invoiceId) return null as any;
      const res = await api.get(`/v1/invoices/${invoiceId}`);
      return res.data;
    },
    enabled: !!invoiceId && open,
  });

  if (isLoading) {
    return (
      <Dialog open={open} onOpenChange={onOpenChange}>
        <DialogContent className="max-w-[600px] max-h-[90vh] overflow-y-auto">
          <div className="flex items-center justify-center h-40">
            <div className="text-muted-foreground">加载中...</div>
          </div>
        </DialogContent>
      </Dialog>
    );
  }

  if (!invoice) return null;

  const customsInfo = customsStatusMap[invoice.customs_status] ?? { label: invoice.customs_status, color: "" };
  const exchangeInfo = exchangeStatusMap[invoice.exchange_status] ?? { label: invoice.exchange_status, color: "" };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-[600px] max-h-[90vh] overflow-y-auto">
        <DialogHeader className="pb-4 border-b flex flex-row items-center justify-between">
          <div>
            <DialogTitle>发票详情</DialogTitle>
            <DialogDescription>
              发票编号: {invoice.invoice_no}
            </DialogDescription>
          </div>
          <div className="flex gap-2">
            {onEdit && (
              <Button variant="outline" size="sm" onClick={() => onEdit(invoice.id)}>
                <Pencil className="h-3 w-3 mr-1" />
                编辑
              </Button>
            )}
            <Button variant="ghost" size="icon" className="h-8 w-8" onClick={() => onOpenChange(false)}>
              <X className="h-4 w-4" />
            </Button>
          </div>
        </DialogHeader>

        <div className="space-y-6 py-6">
          {/* 基本信息 */}
          <div className="space-y-3">
            <h3 className="text-sm font-semibold text-foreground">基本信息</h3>
            <div className="grid grid-cols-2 gap-3 text-sm">
              <div>
                <span className="text-muted-foreground">发票日期:</span>
                <span className="ml-2">{invoice.invoice_date}</span>
              </div>
              <div>
                <span className="text-muted-foreground">宰杀日期:</span>
                <span className="ml-2">{invoice.kill_date ?? "-"}</span>
              </div>
              <div>
                <span className="text-muted-foreground">加工厂:</span>
                <span className="ml-2">{invoice.processing_plant_name ?? "-"}</span>
              </div>
              <div>
                <span className="text-muted-foreground">渔场:</span>
                <span className="ml-2">{invoice.fish_farm_name ?? "-"}</span>
              </div>
              <div>
                <span className="text-muted-foreground">出口商:</span>
                <span className="ml-2">{invoice.exporter_name ?? "-"}</span>
              </div>
              <div>
                <span className="text-muted-foreground">供应商:</span>
                <span className="ml-2">{invoice.supplier_name ?? "-"}</span>
              </div>
            </div>
          </div>

          {/* 状态 */}
          <div className="space-y-3">
            <h3 className="text-sm font-semibold text-foreground">状态</h3>
            <div className="flex gap-3 flex-wrap">
              <Badge variant="secondary" className={customsInfo.color}>
                报关: {customsInfo.label}
              </Badge>
              <Badge variant="secondary" className={exchangeInfo.color}>
                购汇: {exchangeInfo.label}
              </Badge>
              {invoice.is_locked && (
                <Badge variant="secondary" className="bg-red-100 text-red-800">
                  <Lock className="h-3 w-3 mr-1 inline" />
                  已锁定
                </Badge>
              )}
            </div>
          </div>

          {/* 物流信息 */}
          <div className="space-y-3">
            <h3 className="text-sm font-semibold text-foreground">物流与证书</h3>
            <div className="grid grid-cols-2 gap-3 text-sm">
              <div>
                <span className="text-muted-foreground">AWB:</span>
                <span className="ml-2">{invoice.awb_no ?? "-"}</span>
              </div>
              <div>
                <span className="text-muted-foreground">ETA:</span>
                <span className="ml-2">{invoice.eta ?? "-"}</span>
              </div>
              <div>
                <span className="text-muted-foreground">航班:</span>
                <span className="ml-2">{invoice.flight_info ?? "-"}</span>
              </div>
              <div>
                <span className="text-muted-foreground">毛重:</span>
                <span className="ml-2">{invoice.gross_weight_kg ?? "-"} kg</span>
              </div>
              <div>
                <span className="text-muted-foreground">原产地证:</span>
                <span className="ml-2">{invoice.origin_certificate ?? "-"}</span>
              </div>
              <div>
                <span className="text-muted-foreground">检验检疫证:</span>
                <span className="ml-2">{invoice.inspection_certificate ?? "-"}</span>
              </div>
            </div>
          </div>

          {/* 产品明细 */}
          <div className="space-y-3">
            <h3 className="text-sm font-semibold text-foreground">产品明细</h3>
            {invoice.products.length > 0 ? (
              <div className="border rounded-md overflow-hidden">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead className="text-xs">产品</TableHead>
                      <TableHead className="text-xs">规格</TableHead>
                      <TableHead className="text-xs text-right">箱数</TableHead>
                      <TableHead className="text-xs text-right">重量(kg)</TableHead>
                      <TableHead className="text-xs text-right">单价(USD)</TableHead>
                      <TableHead className="text-xs text-right">金额(USD)</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {invoice.products.map((product) => (
                      <TableRow key={product.id}>
                        <TableCell className="text-sm">{product.product_name}</TableCell>
                        <TableCell className="text-sm">{product.product_spec}</TableCell>
                        <TableCell className="text-sm text-right">{product.box_count}</TableCell>
                        <TableCell className="text-sm text-right">{Number(product.net_weight_kg).toLocaleString()}</TableCell>
                        <TableCell className="text-sm text-right">{Number(product.unit_price).toLocaleString()}</TableCell>
                        <TableCell className="text-sm text-right">{Number(product.total_amount).toLocaleString()}</TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                  {/* 合计行 */}
                  <tfoot className="bg-muted/50 border-t">
                    <TableRow className="font-medium text-sm">
                      <TableCell colSpan={2} className="text-right">合计</TableCell>
                      <TableCell className="text-right">
                        {invoice.products.reduce((sum, p) => sum + (p.box_count || 0), 0)}
                      </TableCell>
                      <TableCell className="text-right">
                        {invoice.products.reduce((sum, p) => sum + Number(p.net_weight_kg || 0), 0).toLocaleString(undefined, {minimumFractionDigits: 3, maximumFractionDigits: 3})}
                      </TableCell>
                      <TableCell></TableCell>
                      <TableCell className="text-right text-primary font-semibold">
                        ${invoice.products.reduce((sum, p) => sum + Number(p.total_amount || 0), 0).toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2})}
                      </TableCell>
                    </TableRow>
                  </tfoot>
                </Table>
              </div>
            ) : (
              <div className="text-sm text-muted-foreground py-4 text-center border rounded-md">
                暂无产品明细
              </div>
            )}
          </div>

          {/* 备注 */}
          {invoice.notes && (
            <div className="space-y-2">
              <h3 className="text-sm font-semibold text-foreground">备注</h3>
              <div className="text-sm bg-muted p-3 rounded-md whitespace-pre-wrap">
                {invoice.notes}
              </div>
            </div>
          )}
        </div>
      </DialogContent>
    </Dialog>
  );
}
