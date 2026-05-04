import React, { useState, useEffect, useCallback } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Checkbox } from "@/components/ui/checkbox";
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
} from "@/components/ui/dialog";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { BatchImportButton } from "@/components/BatchImportButton";
import {
  Plus,
  Trash2,
  DollarSign,
  Receipt,
  Truck,
  FileText,
  Ship,
  CheckCircle,
  Info,
  List,
  Pencil,
  Eye,
  ArrowUpDown,
  Coins,
} from "lucide-react";
import { toast } from "sonner";

/* ─────────────── 清关费用系数 ─────────────── */
const RATES = {
  pickup: 0.84,
  coldStorage: 0.5,
  freight: 800,
  yard: 250,
  customs: 600,
};

/* ─────────────── 金额格式化 ─────────────── */
const fmt = (v?: number | string | null) => {
  if (v === undefined || v === null || v === "" || Number.isNaN(Number(v))) return "-";
  return `¥${Number(v).toLocaleString("zh-CN", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  })}`;
};

const fmtUSD = (v?: number | string | null) => {
  if (v === undefined || v === null || v === "" || Number.isNaN(Number(v))) return "-";
  return `$${Number(v).toLocaleString("zh-CN", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  })}`;
};

const transactionTypeMap: Record<string, string> = {
  income: "收入",
  expense: "支出",
  transfer: "转账",
  exchange: "购汇",
};

const transactionCategoryMap: Record<string, string> = {
  sales_income: "销售收入",
  investment: "投资款",
  loan: "借款",
  interest: "利息收入",
  online_operation: "线上运营",
  rent: "场地租赁",
  fixed_asset: "固定资产",
  salary: "工资",
  travel: "差旅",
  scan_fee: "扫码手续费",
  tax: "税费",
  logistics_cost: "物流费",
  clearance_cost: "清关费",
  other: "其他",
};

interface InvoiceOpt {
  id: number;
  invoice_no: string;
  processing_plant_name?: string;
  gross_weight_kg?: number | string;
  total_amount_usd?: number | string;
}

interface BatchOpt {
  id: number;
  batch_code: string;
  batch_name?: string;
}

interface ExchangeRecord {
  id: number;
  invoice_id?: number;
  batch_id?: number;
  exchange_date: string;
  amount_usd: string;
  exchange_rate: string;
  amount_cny: string;
  fee_cny: string;
  status: string;
}

interface Transaction {
  id: number;
  transaction_date: string;
  type: string;
  category: string;
  amount: string;
  currency: string;
  counterparty_name: string | null;
  reference_no: string | null;
  description: string | null;
}

interface ImportFeeItem {
  invoice_id: number;
  invoice_no: string;
  expense_date: string;
  import_duty: number;
  import_vat: number;
  tax_total: number;
  pickup_fee: number;
  freight: number;
  yard_fee: number;
  cold_storage_fee: number;
  clearance_service_fee: number;
  clearance_total: number;
  grand_total: number;
}

/* ═══════════════════════════════════════════
   主组件
   ═══════════════════════════════════════════ */
export function FinancePage() {
  const [page, setPage] = useState(1);
  const [activeTab, setActiveTab] = useState("import");
  const PAGE_SIZE = 20;

  const queryClient = useQueryClient();

  const { data: summary } = useQuery({
    queryKey: ["finance-summary"],
    queryFn: async () => {
      const res = await api.get("/v1/finance/summary");
      return res.data;
    },
  });

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">财务管理</h1>
          <p className="text-sm text-muted-foreground">进口费用 / 购汇登记 / 交易流水</p>
        </div>
        <BatchImportButton type="finance" />
      </div>

      {/* 汇总卡片 */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium">进口费用合计</CardTitle>
            <Ship className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              ¥{(Number(summary?.total_tax || 0) + Number(summary?.total_clearance_cost || 0)).toLocaleString()}
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium">购汇总额(USD)</CardTitle>
            <DollarSign className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              ${Number(summary?.total_exchange_usd || 0).toLocaleString()}
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium">购汇总(CNY)</CardTitle>
            <Receipt className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              ¥{Number(summary?.total_exchange_cny || 0).toLocaleString()}
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium">资金净流入</CardTitle>
            <FileText className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              ¥{Number(summary?.net_flow || 0).toLocaleString()}
            </div>
          </CardContent>
        </Card>
      </div>

      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList className="grid w-full grid-cols-3">
          <TabsTrigger value="import" className="flex items-center gap-1">
            <Ship className="h-4 w-4" /> 进口费用
          </TabsTrigger>
          <TabsTrigger value="exchange" className="flex items-center gap-1">
            <DollarSign className="h-4 w-4" /> 购汇登记
          </TabsTrigger>
          <TabsTrigger value="transactions" className="flex items-center gap-1">
            <List className="h-4 w-4" /> 交易流水
          </TabsTrigger>
        </TabsList>

        <TabsContent value="import" className="pt-4">
          <ImportFeesTab />
        </TabsContent>
        <TabsContent value="exchange" className="pt-4">
          <ExchangeTab />
        </TabsContent>
        <TabsContent value="transactions" className="pt-4">
          <TransactionsTab />
        </TabsContent>
      </Tabs>
    </div>
  );
}

// ==================== Tab 1: 进口费用 ====================

function ImportFeesTab() {
  const queryClient = useQueryClient();
  const [formOpen, setFormOpen] = useState(false);
  const [detailOpen, setDetailOpen] = useState(false);
  const [detailItem, setDetailItem] = useState<ImportFeeItem | null>(null);

  // Form state
  const [invoiceId, setInvoiceId] = useState("");
  const [expenseDate, setExpenseDate] = useState("");
  const [grossWeight, setGrossWeight] = useState("");
  const [importDuty, setImportDuty] = useState("");
  const [importVat, setImportVat] = useState("");
  const [pickupFee, setPickupFee] = useState("");
  const [freight, setFreight] = useState(String(RATES.freight));
  const [yardFee, setYardFee] = useState("");
  const [coldStorageFee, setColdStorageFee] = useState("");
  const [clearanceServiceFee, setClearanceServiceFee] = useState(String(RATES.customs));
  const [hasYard, setHasYard] = useState(false);
  const [hasCold, setHasCold] = useState(false);

  // Reset on open
  useEffect(() => {
    if (formOpen) {
      setInvoiceId("");
      setExpenseDate("");
      setGrossWeight("");
      setImportDuty("");
      setImportVat("");
      setPickupFee("");
      setFreight(String(RATES.freight));
      setYardFee("");
      setColdStorageFee("");
      setClearanceServiceFee(String(RATES.customs));
      setHasYard(false);
      setHasCold(false);
    }
  }, [formOpen]);

  // Fetch invoices
  const { data: invoicesData } = useQuery<InvoiceOpt[]>({
    queryKey: ["invoices-dropdown"],
    queryFn: async () => {
      const res = await api.get("/v1/invoices?limit=500");
      return res.data?.items || res.data || [];
    },
  });

  const invoices: InvoiceOpt[] = invoicesData || [];

  // Fetch import fees list
  const { data: importFeesData, isLoading } = useQuery<{ items: ImportFeeItem[]; total: number }>({
    queryKey: ["import-fees"],
    queryFn: async () => {
      const res = await api.get("/v1/finance/import-fees");
      return res.data;
    },
  });

  const importFees = importFeesData?.items || [];

  const onSelectInvoice = (id: string) => {
    setInvoiceId(id);
    const inv = invoices.find((i) => String(i.id) === id);
    if (inv?.gross_weight_kg) {
      setGrossWeight(String(inv.gross_weight_kg));
    } else {
      setGrossWeight("");
    }
  };

  const autoCalc = () => {
    const gw = parseFloat(grossWeight) || 0;
    if (!gw) {
      toast.error("请先填写出关毛重");
      return;
    }
    setPickupFee(String(Number((gw * RATES.pickup).toFixed(2))));
    if (hasCold) {
      setColdStorageFee(String(Number((gw * RATES.coldStorage).toFixed(2))));
    }
    if (hasYard) {
      setYardFee(String(RATES.yard));
    }
    if (!clearanceServiceFee) setClearanceServiceFee(String(RATES.customs));
    if (!freight) setFreight(String(RATES.freight));
  };

  const clearanceTotal =
    (parseFloat(pickupFee) || 0) +
    (parseFloat(coldStorageFee) || 0) +
    (parseFloat(freight) || 0) +
    (parseFloat(yardFee) || 0) +
    (parseFloat(clearanceServiceFee) || 0);

  const taxTotal = (parseFloat(importDuty) || 0) + (parseFloat(importVat) || 0);
  const grandTotal = taxTotal + clearanceTotal;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!invoiceId) {
      toast.error("请选择发票");
      return;
    }
    if (!expenseDate) {
      toast.error("请选择费用日期");
      return;
    }
    try {
      await api.post("/v1/finance/import-fees", {
        invoice_id: Number(invoiceId),
        expense_date: expenseDate,
        import_duty: Number(importDuty) || 0,
        import_vat: Number(importVat) || 0,
        pickup_fee: Number(pickupFee) || 0,
        freight: Number(freight) || 0,
        yard_fee: Number(yardFee) || 0,
        cold_storage_fee: Number(coldStorageFee) || 0,
        clearance_service_fee: Number(clearanceServiceFee) || 0,
      });
      toast.success("进口费用保存成功");
      queryClient.invalidateQueries({ queryKey: ["import-fees"] });
      queryClient.invalidateQueries({ queryKey: ["finance-summary"] });
      setFormOpen(false);
    } catch (error: any) {
      toast.error(error.response?.data?.detail ?? "保存失败");
    }
  };

  const handleDelete = async (invoiceId: number) => {
    if (!confirm("确定删除此发票的进口费用？")) return;
    try {
      await api.delete(`/v1/finance/import-fees/${invoiceId}`);
      toast.success("已删除");
      queryClient.invalidateQueries({ queryKey: ["import-fees"] });
      queryClient.invalidateQueries({ queryKey: ["finance-summary"] });
    } catch (error: any) {
      toast.error(error.response?.data?.detail ?? "删除失败");
    }
  };

  const handleOpenDetail = (item: ImportFeeItem) => {
    setDetailItem(item);
    setDetailOpen(true);
  };

  return (
    <div className="space-y-4">
      <div className="flex justify-end">
        <Button size="sm" onClick={() => setFormOpen(true)}>
          <Plus className="h-4 w-4 mr-1" />
          新增进口费用
        </Button>
      </div>

      {/* 新增弹窗 */}
      <Dialog open={formOpen} onOpenChange={setFormOpen}>
        <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <Ship className="w-5 h-5" />
              新增进口费用
            </DialogTitle>
          </DialogHeader>

          <form onSubmit={handleSubmit} className="space-y-4 py-2">
            {/* 发票号 */}
            <div className="grid gap-2">
              <Label className="text-sm font-medium">
                关联发票 <span className="text-red-500">*</span>
              </Label>
              <Select value={invoiceId} onValueChange={(v) => onSelectInvoice(v ?? "")}>
                <SelectTrigger className="w-full">
                  <SelectValue placeholder="请选择发票" />
                </SelectTrigger>
                <SelectContent className="min-w-[480px]">
                  {invoices.map((i) => (
                    <SelectItem key={i.id} value={String(i.id)}>
                      <span className="font-mono">{i.invoice_no}</span>
                      {i.processing_plant_name ? <span className="ml-2 text-muted-foreground">{i.processing_plant_name}</span> : ""}
                      {i.gross_weight_kg ? <span className="ml-2 text-blue-600">毛重{i.gross_weight_kg}kg</span> : ""}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            {/* 海关税费 */}
            <div className="border rounded-lg p-4 space-y-3">
              <div className="text-sm font-medium text-gray-700">海关税费</div>
              <div className="grid grid-cols-2 gap-4">
                <div className="grid gap-2">
                  <Label>进口关税 (¥)</Label>
                  <Input
                    type="number"
                    value={importDuty}
                    onChange={(e) => setImportDuty(e.target.value)}
                    step="0.01"
                    placeholder="0.00"
                  />
                </div>
                <div className="grid gap-2">
                  <Label>进口增值税 (¥)</Label>
                  <Input
                    type="number"
                    value={importVat}
                    onChange={(e) => setImportVat(e.target.value)}
                    step="0.01"
                    placeholder="0.00"
                  />
                </div>
              </div>
              <div className="bg-muted p-2 rounded text-sm flex justify-between font-semibold">
                <span>税费合计</span>
                <span>{fmt(taxTotal)}</span>
              </div>
            </div>

            {/* 费用日期 */}
            <div className="grid gap-2">
              <Label>费用日期 <span className="text-red-500">*</span></Label>
              <Input type="date" value={expenseDate} onChange={(e) => setExpenseDate(e.target.value)} />
            </div>

            {/* 清关费用 */}
            <div className="border rounded-lg p-4 space-y-3">
              <div className="text-sm font-medium text-gray-700">付给报关公司费用</div>

              {/* 出关毛重 */}
              <div className="grid grid-cols-2 gap-4">
                <div className="grid gap-2">
                  <Label>出关毛重 (kg)</Label>
                  <Input
                    type="number"
                    value={grossWeight}
                    onChange={(e) => setGrossWeight(e.target.value)}
                    step="0.01"
                    placeholder="如从单证导入则自动带出"
                  />
                </div>
                <div className="flex items-end">
                  <Button type="button" variant="outline" onClick={autoCalc}>
                    根据毛重计算
                  </Button>
                </div>
              </div>

              <div className="grid grid-cols-3 gap-4">
                <div className="grid gap-2">
                  <Label>提货费 (¥)</Label>
                  <Input
                    type="number"
                    value={pickupFee}
                    onChange={(e) => setPickupFee(e.target.value)}
                    step="0.01"
                    placeholder={`${RATES.pickup} 元/kg`}
                  />
                  <span className="text-xs text-gray-400">
                    自动：毛重 × {RATES.pickup} 元/kg
                  </span>
                </div>
                <div className="grid gap-2">
                  <Label>运费 (¥)</Label>
                  <Input
                    type="number"
                    value={freight}
                    onChange={(e) => setFreight(e.target.value)}
                    step="0.01"
                    placeholder={String(RATES.freight)}
                  />
                  <span className="text-xs text-gray-400">
                    默认 {RATES.freight} 元/单
                  </span>
                </div>
                <div className="grid gap-2">
                  <Label>报关服务费 (¥)</Label>
                  <Input
                    type="number"
                    value={clearanceServiceFee}
                    onChange={(e) => setClearanceServiceFee(e.target.value)}
                    step="0.01"
                    placeholder={String(RATES.customs)}
                  />
                  <span className="text-xs text-gray-400">
                    默认 {RATES.customs} 元/单
                  </span>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-4">
                {/* 浦虹场地费 */}
                <div className="grid gap-2">
                  <div className="flex items-center gap-2">
                    <Checkbox
                      id="yard"
                      checked={hasYard}
                      onCheckedChange={(v) => {
                        setHasYard(!!v);
                        if (v) setYardFee(String(RATES.yard));
                        else setYardFee("");
                      }}
                    />
                    <Label htmlFor="yard" className="cursor-pointer">
                      浦虹场地费（目的地查验）
                    </Label>
                  </div>
                  <Input
                    type="number"
                    value={yardFee}
                    onChange={(e) => setYardFee(e.target.value)}
                    step="0.01"
                    disabled={!hasYard}
                    placeholder={hasYard ? `${RATES.yard} 元/单` : "请先勾选"}
                  />
                  {hasYard && (
                    <span className="text-xs text-blue-500">
                      提示费用：{RATES.yard} 元/单
                    </span>
                  )}
                </div>

                {/* 冷藏费 */}
                <div className="grid gap-2">
                  <div className="flex items-center gap-2">
                    <Checkbox
                      id="cold"
                      checked={hasCold}
                      onCheckedChange={(v) => {
                        setHasCold(!!v);
                        if (v) {
                          const gw = parseFloat(grossWeight) || 0;
                          setColdStorageFee(gw ? String(Number((gw * RATES.coldStorage).toFixed(2))) : "");
                        } else {
                          setColdStorageFee("");
                        }
                      }}
                    />
                    <Label htmlFor="cold" className="cursor-pointer">
                      冷藏费
                    </Label>
                  </div>
                  <Input
                    type="number"
                    value={coldStorageFee}
                    onChange={(e) => setColdStorageFee(e.target.value)}
                    step="0.01"
                    disabled={!hasCold}
                    placeholder={
                      hasCold
                        ? `${grossWeight ? Number((parseFloat(grossWeight) * RATES.coldStorage).toFixed(2)) : RATES.coldStorage} 元`
                        : "请先勾选"
                    }
                  />
                  {hasCold && (
                    <span className="text-xs text-blue-500">
                      提示费用：毛重 × {RATES.coldStorage} ={" "}
                      {grossWeight
                        ? Number((parseFloat(grossWeight) * RATES.coldStorage).toFixed(2))
                        : RATES.coldStorage}{" "}
                      元
                    </span>
                  )}
                </div>
              </div>

              {/* AWB 提醒 */}
              <div className="bg-yellow-50 border border-yellow-200 rounded p-2 text-xs text-yellow-800 flex items-start gap-2">
                <Info className="w-4 h-4 shrink-0 mt-0.5" />
                <span>
                  提示：如航司收取冷藏费，请提醒出口商在空运提单AWB备注 &quot;KEEP COOL
                  DURING DEPARTURE AND TRANSPORT. BUT DO NOT MOVE INTO COLD
                  STORAGE WAREHOUSE AT FINAL DESTINATION.&quot;
                </span>
              </div>

              <div className="bg-gray-50 p-2 rounded text-sm flex justify-between font-semibold">
                <span>清关费用合计</span>
                <span className="text-blue-600">{fmt(clearanceTotal)}</span>
              </div>
            </div>

            {/* 总合计 */}
            <div className="bg-blue-50 p-3 rounded-lg text-sm flex justify-between font-bold">
              <span>费用总计（税费+清关）</span>
              <span className="text-blue-700">{fmt(grandTotal)}</span>
            </div>

            <DialogFooter>
              <Button type="button" variant="outline" onClick={() => setFormOpen(false)}>
                取消
              </Button>
              <Button type="submit">
                <CheckCircle className="w-4 h-4 mr-1" />
                保存
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>

      {/* 详情弹窗 */}
      <Dialog open={detailOpen} onOpenChange={setDetailOpen}>
        <DialogContent className="max-w-[520px]">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <Eye className="w-5 h-5" />
              进口费用详情
            </DialogTitle>
          </DialogHeader>
          {detailItem && (
            <div className="space-y-4 py-2 text-sm">
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-1">
                  <Label className="text-xs text-muted-foreground">发票号</Label>
                  <div className="font-medium">{detailItem.invoice_no}</div>
                </div>
                <div className="space-y-1">
                  <Label className="text-xs text-muted-foreground">费用日期</Label>
                  <div className="font-medium">{detailItem.expense_date || "-"}</div>
                </div>
              </div>

              <div className="border rounded-lg p-3 space-y-2">
                <div className="text-sm font-medium text-gray-700">海关税费</div>
                <div className="grid grid-cols-2 gap-2">
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">进口关税</span>
                    <span className="font-medium">{fmt(detailItem.import_duty)}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">进口增值税</span>
                    <span className="font-medium">{fmt(detailItem.import_vat)}</span>
                  </div>
                </div>
                <div className="flex justify-between font-semibold border-t pt-1">
                  <span>税费合计</span>
                  <span>{fmt(detailItem.tax_total)}</span>
                </div>
              </div>

              <div className="border rounded-lg p-3 space-y-2">
                <div className="text-sm font-medium text-gray-700">清关费用</div>
                <div className="space-y-1">
                  <div className="flex justify-between"><span className="text-muted-foreground">提货费</span><span>{fmt(detailItem.pickup_fee)}</span></div>
                  <div className="flex justify-between"><span className="text-muted-foreground">运费</span><span>{fmt(detailItem.freight)}</span></div>
                  <div className="flex justify-between"><span className="text-muted-foreground">场地费</span><span>{fmt(detailItem.yard_fee)}</span></div>
                  <div className="flex justify-between"><span className="text-muted-foreground">冷藏费</span><span>{fmt(detailItem.cold_storage_fee)}</span></div>
                  <div className="flex justify-between"><span className="text-muted-foreground">报关服务费</span><span>{fmt(detailItem.clearance_service_fee)}</span></div>
                </div>
                <div className="flex justify-between font-semibold border-t pt-1">
                  <span>清关费用合计</span>
                  <span className="text-blue-600">{fmt(detailItem.clearance_total)}</span>
                </div>
              </div>

              <div className="bg-blue-50 p-3 rounded-lg flex justify-between font-bold text-base">
                <span>费用总计</span>
                <span className="text-blue-700">{fmt(detailItem.grand_total)}</span>
              </div>
            </div>
          )}
        </DialogContent>
      </Dialog>

      <div className="border rounded-lg">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>发票号</TableHead>
              <TableHead>费用日期</TableHead>
              <TableHead>关税</TableHead>
              <TableHead>增值税</TableHead>
              <TableHead>清关费用</TableHead>
              <TableHead>合计</TableHead>
              <TableHead className="w-[100px]"></TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {isLoading ? (
              <TableRow>
                <TableCell colSpan={7} className="text-center py-8">
                  加载中...
                </TableCell>
              </TableRow>
            ) : !importFees.length ? (
              <TableRow>
                <TableCell colSpan={7} className="text-center py-8 text-muted-foreground">
                  暂无数据
                </TableCell>
              </TableRow>
            ) : (
              <>
                {importFees.map((f) => (
                  <TableRow key={f.invoice_id}>
                  <TableCell className="font-medium">{f.invoice_no}</TableCell>
                  <TableCell>{f.expense_date || "-"}</TableCell>
                  <TableCell>{fmt(f.import_duty)}</TableCell>
                  <TableCell>{fmt(f.import_vat)}</TableCell>
                  <TableCell>{fmt(f.clearance_total)}</TableCell>
                  <TableCell className="font-semibold">{fmt(f.grand_total)}</TableCell>
                  <TableCell>
                    <div className="flex gap-1">
                      <Button
                        variant="ghost"
                        size="icon"
                        className="h-7 w-7"
                        onClick={() => handleOpenDetail(f)}
                        title="查看详情"
                      >
                        <Eye className="h-3 w-3" />
                      </Button>
                      <Button
                        variant="ghost"
                        size="icon"
                        className="h-7 w-7 text-red-500"
                        onClick={() => handleDelete(f.invoice_id)}
                        title="删除"
                      >
                        <Trash2 className="h-3 w-3" />
                      </Button>
                    </div>
                  </TableCell>
                </TableRow>
              ))}
              {/* 页汇总行 */}
              {importFees.length > 0 && (
                <TableRow className="bg-muted/50 font-medium border-t-2">
                  <TableCell colSpan={2} className="text-right">本页合计:</TableCell>
                  <TableCell>{fmt(importFees.reduce((s, f) => s + Number(f.import_duty || 0), 0))}</TableCell>
                  <TableCell>{fmt(importFees.reduce((s, f) => s + Number(f.import_vat || 0), 0))}</TableCell>
                  <TableCell>{fmt(importFees.reduce((s, f) => s + Number(f.clearance_total || 0), 0))}</TableCell>
                  <TableCell className="font-bold">{fmt(importFees.reduce((s, f) => s + Number(f.grand_total || 0), 0))}</TableCell>
                  <TableCell />
                </TableRow>
              )}
            </>
            )}
          </TableBody>
        </Table>
      </div>
    </div>
  );
}

// ==================== Tab 2: 购汇登记 ====================

function ExchangeTab() {
  const queryClient = useQueryClient();
  const [formOpen, setFormOpen] = useState(false);
  const [detailOpen, setDetailOpen] = useState(false);
  const [detailRecord, setDetailRecord] = useState<ExchangeRecord | null>(null);

  // Form state
  const [batchId, setBatchId] = useState("");
  const [exchangeDate, setExchangeDate] = useState("");
  const [amountUsd, setAmountUsd] = useState("");
  const [exchangeRate, setExchangeRate] = useState("");
  const [amountCny, setAmountCny] = useState("");
  const [feeCny, setFeeCny] = useState("");
  const [batchTotalUSD, setBatchTotalUSD] = useState(0);

  // Reset on open
  useEffect(() => {
    if (formOpen) {
      setBatchId("");
      setExchangeDate("");
      setAmountUsd("");
      setExchangeRate("");
      setAmountCny("");
      setFeeCny("");
      setBatchTotalUSD(0);
    }
  }, [formOpen]);

  // Fetch batches
  const { data: batchesData } = useQuery<BatchOpt[]>({
    queryKey: ["batches-dropdown"],
    queryFn: async () => {
      const res = await api.get("/v1/batches?limit=500");
      return res.data?.items || res.data || [];
    },
  });

  const batches: BatchOpt[] = batchesData || [];

  // Fetch exchange records
  const { data: exchangeData, isLoading } = useQuery<ExchangeRecord[]>({
    queryKey: ["exchange-records"],
    queryFn: async () => {
      const res = await api.get("/v1/finance/exchange");
      return res.data;
    },
  });

  const exchanges = exchangeData || [];

  // Auto-calculate CNY
  useEffect(() => {
    const usd = parseFloat(amountUsd) || 0;
    const rate = parseFloat(exchangeRate) || 0;
    if (usd && rate) {
      setAmountCny(String(Number((usd * rate).toFixed(2))));
    }
  }, [amountUsd, exchangeRate]);

  // Fetch batch purchase total when batch selected
  const onSelectBatch = async (bid: string) => {
    setBatchId(bid);
    setAmountUsd("");
    setBatchTotalUSD(0);
    if (!bid) return;
    try {
      const res = await api.get(`/v1/finance/batch-purchase-total?batch_id=${bid}`);
      if (res.data?.success && res.data?.data) {
        const total = Number(res.data.data.total_usd) || 0;
        setBatchTotalUSD(total);
        setAmountUsd(String(total));
      }
    } catch (err: any) {
      toast.error(err.response?.data?.detail ?? "获取采购总额失败");
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!batchId) {
      toast.error("请选择批次");
      return;
    }
    if (!exchangeDate) {
      toast.error("请选择购汇日期");
      return;
    }
    try {
      await api.post("/v1/finance/exchange", {
        batch_id: Number(batchId),
        exchange_date: exchangeDate,
        amount_usd: Number(amountUsd),
        exchange_rate: Number(exchangeRate),
        amount_cny: Number(amountCny),
        fee_cny: Number(feeCny) || 0,
        invoice_id: null,
        bank_account_id: null,
      });
      toast.success("购汇记录创建成功");
      queryClient.invalidateQueries({ queryKey: ["exchange-records"] });
      queryClient.invalidateQueries({ queryKey: ["finance-summary"] });
      setFormOpen(false);
    } catch (error: any) {
      toast.error(error.response?.data?.detail ?? "创建失败");
    }
  };

  const handleDelete = async (id: number) => {
    if (!confirm("确定删除此购汇记录？")) return;
    try {
      await api.delete(`/v1/finance/exchange/${id}`);
      toast.success("已删除");
      queryClient.invalidateQueries({ queryKey: ["exchange-records"] });
      queryClient.invalidateQueries({ queryKey: ["finance-summary"] });
    } catch (error: any) {
      toast.error(error.response?.data?.detail ?? "删除失败");
    }
  };

  const handleOpenDetail = (record: ExchangeRecord) => {
    setDetailRecord(record);
    setDetailOpen(true);
  };

  return (
    <div className="space-y-4">
      <div className="flex justify-end">
        <Button size="sm" onClick={() => setFormOpen(true)}>
          <Plus className="h-4 w-4 mr-1" />
          新增购汇
        </Button>
      </div>

      <Dialog open={formOpen} onOpenChange={setFormOpen}>
        <DialogContent className="max-w-[640px]">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <DollarSign className="w-5 h-5" />
              新增购汇登记
            </DialogTitle>
          </DialogHeader>

          <form onSubmit={handleSubmit} className="space-y-5 py-2">
            {/* 关联批次 */}
            <div className="grid gap-2">
              <Label className="text-sm font-medium">
                关联批次 <span className="text-red-500">*</span>
              </Label>
              <Select value={String(batchId)} onValueChange={(v) => onSelectBatch(v ?? "")}>
                <SelectTrigger className="w-full">
                  <SelectValue placeholder="请选择批次" />
                </SelectTrigger>
                <SelectContent className="min-w-[400px]">
                  {batches.map((b) => (
                    <SelectItem key={b.id} value={String(b.id)}>
                      <span className="font-mono">{b.batch_code}</span>
                      {b.batch_name ? <span className="ml-2 text-muted-foreground">{b.batch_name}</span> : ""}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            {batchTotalUSD > 0 && (
              <div className="bg-blue-50 border border-blue-100 p-4 rounded-lg">
                <div className="text-sm text-blue-700 font-medium">该批次采购总额</div>
                <div className="text-2xl font-bold text-blue-600 mt-1">
                  {fmtUSD(batchTotalUSD)}
                </div>
              </div>
            )}

            {/* 金额与汇率 */}
            <div className="grid grid-cols-[1fr_1fr_140px] gap-4">
              <div className="grid gap-2">
                <Label className="text-sm">USD金额</Label>
                <Input
                  type="number"
                  value={amountUsd}
                  onChange={(e) => setAmountUsd(e.target.value)}
                  step="0.01"
                  className="text-base"
                />
              </div>
              <div className="grid gap-2">
                <Label className="text-sm">汇率</Label>
                <Input
                  type="number"
                  value={exchangeRate}
                  onChange={(e) => setExchangeRate(e.target.value)}
                  step="0.0001"
                  placeholder="如 7.2345"
                  className="text-base"
                />
              </div>
              <div className="grid gap-2">
                <Label className="text-sm">
                  购汇日期 <span className="text-red-500">*</span>
                </Label>
                <Input
                  type="date"
                  value={exchangeDate}
                  onChange={(e) => setExchangeDate(e.target.value)}
                  className="text-base"
                />
              </div>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div className="grid gap-2">
                <Label className="text-sm text-muted-foreground">CNY金额（自动计算）</Label>
                <Input
                  type="number"
                  value={amountCny}
                  onChange={(e) => setAmountCny(e.target.value)}
                  step="0.01"
                  className="bg-muted"
                />
              </div>
              <div className="grid gap-2">
                <Label className="text-sm">手续费 (¥)</Label>
                <Input
                  type="number"
                  value={feeCny}
                  onChange={(e) => setFeeCny(e.target.value)}
                  step="0.01"
                  placeholder="0"
                />
              </div>
            </div>

            <div className="bg-muted p-3 rounded text-sm flex justify-between font-semibold">
              <span>购汇合计 (CNY)</span>
              <span>
                {fmt((parseFloat(amountCny) || 0) + (parseFloat(feeCny) || 0))}
              </span>
            </div>

            <DialogFooter>
              <Button type="button" variant="outline" onClick={() => setFormOpen(false)}>
                取消
              </Button>
              <Button type="submit">
                <CheckCircle className="w-4 h-4 mr-1" />
                保存
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>

      {/* 详情弹窗 */}
      <Dialog open={detailOpen} onOpenChange={setDetailOpen}>
        <DialogContent className="max-w-[480px]">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <Eye className="w-5 h-5" />
              购汇详情
            </DialogTitle>
          </DialogHeader>
          {detailRecord && (
            <div className="space-y-4 py-2 text-sm">
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-1">
                  <Label className="text-xs text-muted-foreground">批次</Label>
                  <div className="font-medium">
                    {batches.find((b) => b.id === detailRecord.batch_id)?.batch_code || detailRecord.batch_id || "-"}
                  </div>
                </div>
                <div className="space-y-1">
                  <Label className="text-xs text-muted-foreground">购汇日期</Label>
                  <div className="font-medium">{detailRecord.exchange_date}</div>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-1">
                  <Label className="text-xs text-muted-foreground">USD金额</Label>
                  <div className="font-medium">{fmtUSD(detailRecord.amount_usd)}</div>
                </div>
                <div className="space-y-1">
                  <Label className="text-xs text-muted-foreground">汇率</Label>
                  <div className="font-medium">{detailRecord.exchange_rate}</div>
                </div>
              </div>

              <div className="border rounded-lg p-3 space-y-2">
                <div className="text-sm font-medium text-gray-700">购汇明细</div>
                <div className="space-y-1">
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">购汇金额 (CNY)</span>
                    <span className="font-medium">{fmt(detailRecord.amount_cny)}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">购汇手续费</span>
                    <span className="font-medium">{fmt(detailRecord.fee_cny)}</span>
                  </div>
                </div>
                <div className="flex justify-between font-semibold border-t pt-1">
                  <span>合计 (CNY)</span>
                  <span className="text-blue-600">
                    {fmt(Number(detailRecord.amount_cny || 0) + Number(detailRecord.fee_cny || 0))}
                  </span>
                </div>
              </div>
            </div>
          )}
        </DialogContent>
      </Dialog>

      <div className="border rounded-lg">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>批次</TableHead>
              <TableHead>关联发票</TableHead>
              <TableHead>日期</TableHead>
              <TableHead>USD</TableHead>
              <TableHead>汇率</TableHead>
              <TableHead>购汇金额CNY</TableHead>
              <TableHead>购汇手续费</TableHead>
              <TableHead>合计CNY</TableHead>
              <TableHead className="w-[100px]"></TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {isLoading ? (
              <TableRow>
                <TableCell colSpan={9} className="text-center py-8">
                  加载中...
                </TableCell>
              </TableRow>
            ) : !exchanges.length ? (
              <TableRow>
                <TableCell colSpan={9} className="text-center py-8 text-muted-foreground">
                  暂无数据
                </TableCell>
              </TableRow>
            ) : (
              <>
              {exchanges.map((r) => (
                <TableRow key={r.id}>
                  <TableCell>
                    {batches.find((b) => b.id === r.batch_id)?.batch_code ||
                      r.batch_id ||
                      "-"}
                  </TableCell>
                  <TableCell className="text-muted-foreground text-xs">
                    {(() => {
                      const b = batches.find((b) => b.id === r.batch_id);
                      if (!b) return "-";
                      return b.batch_name?.replace(/&/g, ", ") || "-";
                    })()}
                  </TableCell>
                  <TableCell>{r.exchange_date}</TableCell>
                  <TableCell>{fmtUSD(r.amount_usd)}</TableCell>
                  <TableCell>{r.exchange_rate}</TableCell>
                  <TableCell>{fmt(r.amount_cny)}</TableCell>
                  <TableCell>{fmt(r.fee_cny)}</TableCell>
                  <TableCell className="font-semibold">{fmt(Number(r.amount_cny || 0) + Number(r.fee_cny || 0))}</TableCell>
                  <TableCell>
                    <div className="flex gap-1">
                      <Button
                        variant="ghost"
                        size="icon"
                        className="h-7 w-7"
                        onClick={() => handleOpenDetail(r)}
                        title="查看详情"
                      >
                        <Eye className="h-3 w-3" />
                      </Button>
                      <Button
                        variant="ghost"
                        size="icon"
                        className="h-7 w-7 text-red-500"
                        onClick={() => handleDelete(r.id)}
                        title="删除"
                      >
                        <Trash2 className="h-3 w-3" />
                      </Button>
                    </div>
                  </TableCell>
                </TableRow>
              ))}
              {/* 页汇总行 */}
              {exchanges.length > 0 && (
                <TableRow className="bg-muted/50 font-medium border-t-2">
                  <TableCell colSpan={3} className="text-right">本页合计:</TableCell>
                  <TableCell className="font-bold">{fmtUSD(exchanges.reduce((s, r) => s + Number(r.amount_usd || 0), 0))}</TableCell>
                  <TableCell />
                  <TableCell className="font-bold">{fmt(exchanges.reduce((s, r) => s + Number(r.amount_cny || 0), 0))}</TableCell>
                  <TableCell>{fmt(exchanges.reduce((s, r) => s + Number(r.fee_cny || 0), 0))}</TableCell>
                  <TableCell className="font-bold">{fmt(exchanges.reduce((s, r) => s + Number(r.amount_cny || 0) + Number(r.fee_cny || 0), 0))}</TableCell>
                  <TableCell />
                </TableRow>
              )}
            </>
            )}
          </TableBody>
        </Table>
      </div>
    </div>
  );
}

// ==================== Tab 3: 交易流水 ====================

function TransactionsTab() {
  const queryClient = useQueryClient();
  const [formOpen, setFormOpen] = useState(false);
  const [date, setDate] = useState("");
  const [type, setType] = useState("expense");
  const [category, setCategory] = useState("other");
  const [amount, setAmount] = useState("");
  const [counterparty, setCounterparty] = useState("");
  const [description, setDescription] = useState("");
  const [referenceNo, setReferenceNo] = useState("");

  // Reset on open
  useEffect(() => {
    if (formOpen) {
      setDate("");
      setAmount("");
      setCounterparty("");
      setDescription("");
      setReferenceNo("");
    }
  }, [formOpen]);

  const { data, isLoading } = useQuery<Transaction[]>({
    queryKey: ["transactions"],
    queryFn: async () => {
      const res = await api.get("/v1/finance/transactions");
      return res.data;
    },
  });

  const handleDelete = async (id: number) => {
    if (!confirm("确定删除？")) return;
    try {
      await api.delete(`/v1/finance/transactions/${id}`);
      toast.success("已删除");
      queryClient.invalidateQueries({ queryKey: ["transactions"] });
      queryClient.invalidateQueries({ queryKey: ["finance-summary"] });
    } catch (error: any) {
      toast.error(error.response?.data?.detail ?? "删除失败");
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await api.post("/v1/finance/transactions", {
        transaction_date: date,
        type,
        category,
        amount: Number(amount),
        currency: "CNY",
        counterparty_name: counterparty || undefined,
        reference_no: referenceNo || undefined,
        description: description || undefined,
      });
      toast.success("交易记录创建成功");
      queryClient.invalidateQueries({ queryKey: ["transactions"] });
      queryClient.invalidateQueries({ queryKey: ["finance-summary"] });
      setFormOpen(false);
      setDate("");
      setAmount("");
      setCounterparty("");
      setDescription("");
      setReferenceNo("");
    } catch (error: any) {
      toast.error(error.response?.data?.detail ?? "创建失败");
    }
  };

  // Income categories
  const incomeCategories = Object.entries(transactionCategoryMap).filter(([k]) =>
    ["sales_income", "investment", "loan", "interest"].includes(k)
  );
  // Expense categories
  const expenseCategories = Object.entries(transactionCategoryMap).filter(
    ([k]) =>
      !["sales_income", "investment", "loan", "interest"].includes(k)
  );

  return (
    <div className="space-y-4">
      <div className="flex justify-end gap-2">
        <Button size="sm" onClick={() => setFormOpen(true)}>
          <Plus className="h-4 w-4 mr-1" />
          新增流水
        </Button>
        <BatchImportButton type="transactions" />
      </div>

      <Dialog open={formOpen} onOpenChange={setFormOpen}>
        <DialogContent className="max-w-[400px]">
          <DialogHeader>
            <DialogTitle>新增交易流水</DialogTitle>
          </DialogHeader>
          <form onSubmit={handleSubmit} className="space-y-3">
            <div>
              <Label>日期</Label>
              <Input type="date" value={date} onChange={(e) => setDate(e.target.value)} />
            </div>
            <div className="grid grid-cols-2 gap-2">
              <div>
                <Label>类型</Label>
                <Select value={type} onValueChange={(v) => setType(v ?? "")}>
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {Object.entries(transactionTypeMap).map(([k, v]) => (
                      <SelectItem key={k} value={k}>{v}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div>
                <Label>分类</Label>
                <Select value={category} onValueChange={(v) => setCategory(v ?? "")}>
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {type === "income"
                      ? incomeCategories.map(([k, v]) => (
                          <SelectItem key={k} value={k}>{v}</SelectItem>
                        ))
                      : expenseCategories.map(([k, v]) => (
                          <SelectItem key={k} value={k}>{v}</SelectItem>
                        ))}
                  </SelectContent>
                </Select>
              </div>
            </div>
            <div className="grid grid-cols-2 gap-2">
              <div>
                <Label>金额</Label>
                <Input type="number" value={amount} onChange={(e) => setAmount(e.target.value)} />
              </div>
              <div>
                <Label>币种</Label>
                <Input value="CNY" disabled className="bg-muted" />
              </div>
            </div>
            <div>
              <Label>对方名称</Label>
              <Input value={counterparty} onChange={(e) => setCounterparty(e.target.value)} placeholder="可选" />
            </div>
            <div>
              <Label>参考号</Label>
              <Input value={referenceNo} onChange={(e) => setReferenceNo(e.target.value)} placeholder="可选" />
            </div>
            <div>
              <Label>描述</Label>
              <Input value={description} onChange={(e) => setDescription(e.target.value)} placeholder="可选" />
            </div>
            <DialogFooter>
              <Button type="button" variant="outline" onClick={() => setFormOpen(false)}>
                取消
              </Button>
              <Button type="submit">保存</Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>

      <div className="border rounded-lg">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>日期</TableHead>
              <TableHead>类型</TableHead>
              <TableHead>分类</TableHead>
              <TableHead className="text-right">金额</TableHead>
              <TableHead>币种</TableHead>
              <TableHead>对方</TableHead>
              <TableHead>参考号</TableHead>
              <TableHead className="w-[60px]"></TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {isLoading ? (
              <TableRow>
                <TableCell colSpan={8} className="text-center py-8">
                  加载中...
                </TableCell>
              </TableRow>
            ) : !data?.length ? (
              <TableRow>
                <TableCell colSpan={8} className="text-center py-8 text-muted-foreground">
                  暂无数据
                </TableCell>
              </TableRow>
            ) : (
              <>
                {data.map((r) => (
                <TableRow key={r.id}>
                  <TableCell>{r.transaction_date}</TableCell>
                  <TableCell>
                    <span
                      className={`px-2 py-0.5 rounded text-xs font-medium ${
                        r.type === "income"
                          ? "bg-green-100 text-green-700"
                          : r.type === "expense"
                          ? "bg-red-100 text-red-700"
                          : "bg-gray-100 text-gray-700"
                      }`}
                    >
                      {transactionTypeMap[r.type] ?? r.type}
                    </span>
                  </TableCell>
                  <TableCell>{transactionCategoryMap[r.category] ?? r.category}</TableCell>
                  <TableCell className="text-right font-medium">
                    {Number(r.amount).toLocaleString()}
                  </TableCell>
                  <TableCell>{r.currency}</TableCell>
                  <TableCell>{r.counterparty_name ?? "-"}</TableCell>
                  <TableCell className="text-xs text-muted-foreground">
                    {r.reference_no ?? "-"}
                  </TableCell>
                  <TableCell>
                    <Button
                      variant="ghost"
                      size="icon"
                      className="h-7 w-7 text-red-500"
                      onClick={() => handleDelete(r.id)}
                    >
                      <Trash2 className="h-3 w-3" />
                    </Button>
                  </TableCell>
                </TableRow>
              ))}
              {/* 页汇总行 */}
              {data.length > 0 && (
                <TableRow className="bg-muted/50 font-medium border-t-2">
                  <TableCell colSpan={3} className="text-right">本页合计:</TableCell>
                  <TableCell className="text-right font-bold">
                    {data.reduce((s, r) => s + (r.type === "income" ? Number(r.amount || 0) : -Number(r.amount || 0)), 0).toLocaleString("zh-CN", {minimumFractionDigits: 2, maximumFractionDigits: 2})}
                  </TableCell>
                  <TableCell colSpan={4} />
                </TableRow>
              )}
            </>
            )}
          </TableBody>
        </Table>
      </div>
    </div>
  );
}
