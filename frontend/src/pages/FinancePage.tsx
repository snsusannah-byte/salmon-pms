import React, { useState, useEffect, useCallback } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { cn } from "@/lib/utils";
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
  AlertDialog,
  AlertDialogContent,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogDescription,
  AlertDialogFooter,
} from "@/components/ui/alert-dialog";
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
  FileDown,
  Search,
  Lock,
  Unlock,
} from "lucide-react";
import { toast } from "sonner";
import { exportExcel } from "@/lib/export";

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

// 进口费用列表专用：费用为 0 时显示 "-"，表示没有这笔费用
const fmtFee = (v?: number | string | null) => {
  if (v === undefined || v === null || v === "" || Number.isNaN(Number(v)) || Number(v) === 0) return "-";
  return fmt(v);
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
  // 收入
  main_business_revenue: "主营业务收入",
  other_business_revenue: "其他业务收入",
  non_business_revenue: "营业外收入",
  fund_pooling: "资金归集",
  customer_deposit: "客户预付款",

  // 内部划转
  balance_deduction: "余额抵扣",
  marketing_fee: "市场推广费",
  packaging_consumables: "包装物及低值易耗品",
  gift_fee: "赠品费用",
  scan_fee: "扫码手续费",
  transport_fee: "运输装卸费",
  sales_commission: "销售佣金",

  // 支出-管理费用
  staff_salary: "职工薪酬",
  rent_fee: "租赁费",
  office_fee: "办公费",
  travel_fee: "差旅费",
  agency_fee: "中介服务费",
  depreciation: "固定资产折旧",
  maintenance_fee: "维修维护费",
  insurance_fee: "保险费",
  entertainment_fee: "业务招待费",
  training_fee: "培训费",

  // 支出-财务费用
  interest_expense: "利息支出",
  exchange_loss: "汇兑损益",
  bank_fee: "银行手续费",

  // 支出-成本支出
  goods_payment: "货款支付",
  tax_payment: "税费支付",
  clearance_payment: "清关费支付",
  international_freight: "国际运费支付",
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
  invoice_nos?: string;
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
  from_account_id: number | null;
  to_account_id: number | null;
  counterparty_name: string | null;
  reference_no: string | null;
  description: string | null;
  is_locked: boolean;
  related_sale_ids: number[];
}

interface ImportFeeItem {
  invoice_id: number;
  invoice_no: string;
  gross_weight_kg?: number | string;
  expense_date: string;
  customs_broker_id: number | null;
  customs_broker_name: string | null;
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
              {fmt(Number(summary?.total_tax || 0) + Number(summary?.total_clearance_cost || 0))}
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
              {fmtUSD(Number(summary?.total_exchange_usd || 0))}
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
              {fmt(Number(summary?.total_exchange_cny || 0))}
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
              {fmt(Number(summary?.net_flow || 0))}
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
  const [customsBrokerId, setCustomsBrokerId] = useState<number | null>(15);
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

  // Reset on open (only for new record, not edit)
  useEffect(() => {
    if (formOpen && !editingItem) {
      setInvoiceId("");
      setExpenseDate("");
      setCustomsBrokerId(null);
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

  // Fetch invoices (exclude those with import fees)
  const { data: invoicesData } = useQuery<InvoiceOpt[]>({
    queryKey: ["invoices-dropdown", "no-fees"],
    queryFn: async () => {
      const res = await api.get("/v1/invoices?exclude_with_fees=true&limit=500");
      return res.data?.items || res.data || [];
    },
  });

  const invoices: InvoiceOpt[] = invoicesData || [];

  // Fetch customs brokers only (supplier_category=customs_broker)
  const { data: companiesData } = useQuery<{ items: { id: number; name: string; company_full_name: string | null }[] }>({
    queryKey: ["companies", "customs_broker"],
    queryFn: async () => {
      const res = await api.get("/v1/companies?supplier_category=customs_broker&limit=500");
      return res.data;
    },
  });

  const brokers = companiesData?.items || [];

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
        customs_broker_id: customsBrokerId,
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

  const [deleteOpen, setDeleteOpen] = useState(false);
  const [deleteInvoiceId, setDeleteInvoiceId] = useState<number | null>(null);

  const handleDelete = async () => {
    if (!deleteInvoiceId) return;
    try {
      await api.delete(`/v1/finance/import-fees/${deleteInvoiceId}`);
      toast.success("已删除");
      queryClient.invalidateQueries({ queryKey: ["import-fees"] });
      queryClient.invalidateQueries({ queryKey: ["finance-summary"] });
      setDeleteOpen(false);
      setDeleteInvoiceId(null);
    } catch (error: any) {
      toast.error(error.response?.data?.detail ?? "删除失败");
    }
  };

  const handleOpenDetail = (item: ImportFeeItem) => {
    setDetailItem(item);
    setDetailOpen(true);
  };

  const [editingItem, setEditingItem] = useState<ImportFeeItem | null>(null);
  
  // 当 brokers 加载后，自动设置默认值（取第一个报关行）
  useEffect(() => {
    if (brokers.length > 0 && !customsBrokerId && !editingItem) {
      setCustomsBrokerId(brokers[0].id);
    }
  }, [brokers, editingItem]);

  const handleOpenEdit = (item: ImportFeeItem) => {
    setEditingItem(item);
    setInvoiceId(String(item.invoice_id || ""));
    setGrossWeight(String(item.gross_weight_kg ?? ""));
    setExpenseDate(item.expense_date || "");
    setCustomsBrokerId(item.customs_broker_id || 15);
    setImportDuty(String(item.import_duty ?? ""));
    setImportVat(String(item.import_vat ?? ""));
    setPickupFee(String(item.pickup_fee ?? ""));
    setFreight(String(item.freight ?? ""));
    setYardFee(String(item.yard_fee ?? ""));
    setColdStorageFee(String(item.cold_storage_fee ?? ""));
    setClearanceServiceFee(String(item.clearance_service_fee ?? ""));
    setHasYard(!!item.yard_fee);
    setHasCold(!!item.cold_storage_fee);
    setFormOpen(true);
  };

  const handleEditSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!editingItem) return;
    try {
      await api.put(`/v1/finance/import-fees/${editingItem.invoice_id}`, {
        expense_date: expenseDate,
        customs_broker_id: customsBrokerId,
        import_duty: Number(importDuty) || 0,
        import_vat: Number(importVat) || 0,
        pickup_fee: Number(pickupFee) || 0,
        freight: Number(freight) || 0,
        yard_fee: Number(yardFee) || 0,
        cold_storage_fee: Number(coldStorageFee) || 0,
        clearance_service_fee: Number(clearanceServiceFee) || 0,
        gross_weight_kg: Number(grossWeight) || undefined,
      });
      toast.success("进口费用更新成功");
      queryClient.invalidateQueries({ queryKey: ["import-fees"] });
      queryClient.invalidateQueries({ queryKey: ["finance-summary"] });
      setFormOpen(false);
      setEditingItem(null);
    } catch (error: any) {
      const detail = error.response?.data?.detail;
      let msg = "更新失败";
      if (Array.isArray(detail)) {
        msg = detail.map((d: any) => d.msg || String(d)).join("; ");
      } else if (typeof detail === "string") {
        msg = detail;
      } else if (detail && typeof detail === "object") {
        msg = JSON.stringify(detail);
      }
      toast.error(msg);
    }
  };

  return (
    <div className="space-y-4">
      <div className="flex justify-end">
        <Button size="sm" onClick={() => { setEditingItem(null); setFormOpen(true); }}>
          <Plus className="h-4 w-4 mr-1" />
          新增进口费用
        </Button>
      </div>

      {/* 新增/编辑弹窗 */}
      <Dialog open={formOpen} onOpenChange={(v) => { if (!v) { setFormOpen(false); setEditingItem(null); } }}>
        <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <Ship className="w-5 h-5" />
              {editingItem ? "编辑进口费用" : "新增进口费用"}
            </DialogTitle>
          </DialogHeader>

          <form onSubmit={editingItem ? handleEditSubmit : handleSubmit} className="space-y-4 py-2">
            {/* 发票号 */}
            <div className="grid gap-2">
              <Label className="text-sm font-medium">
                关联发票 <span className="text-red-500">*</span>
              </Label>
              {editingItem ? (
                <div className="bg-muted px-3 py-2 rounded-md text-sm">
                  {editingItem.invoice_no || "-"}
                </div>
              ) : (
                <Select value={invoiceId} onValueChange={(v) => onSelectInvoice(v ?? "")}>
                  <SelectTrigger className="w-full">
                    <SelectValue placeholder="请选择发票">
                      {(() => {
                        const selected = invoices.find((i) => String(i.id) === invoiceId);
                        if (!selected) return "请选择发票";
                        return (
                          <span className="flex items-center gap-2">
                            <span className="font-mono">{selected.invoice_no}</span>
                            {selected.processing_plant_name && <span className="text-muted-foreground">{selected.processing_plant_name}</span>}
                            {selected.gross_weight_kg && <span className="text-blue-600">毛重{selected.gross_weight_kg}kg</span>}
                          </span>
                        );
                      })()}
                    </SelectValue>
                  </SelectTrigger>
                  <SelectContent className="min-w-[480px]">
                    {invoices.length === 0 && (
                      <div className="px-3 py-2 text-sm text-muted-foreground">暂无可选发票</div>
                    )}
                    {invoices.map((i) => (
                      <SelectItem key={i.id} value={String(i.id)}>
                        <span className="font-mono">{i.invoice_no}</span>
                        {i.processing_plant_name ? <span className="ml-2 text-muted-foreground">{i.processing_plant_name}</span> : ""}
                        {i.gross_weight_kg ? <span className="ml-2 text-blue-600">毛重{i.gross_weight_kg}kg</span> : ""}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              )}
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

            {/* 费用日期 + 报关行 */}
            <div className="grid grid-cols-2 gap-4">
              <div className="grid gap-2">
                <Label>费用日期 <span className="text-red-500">*</span></Label>
                <Input type="date" value={expenseDate} onChange={(e) => setExpenseDate(e.target.value)} />
              </div>
              <div className="grid gap-2">
                <Label>报关行</Label>
                <Select value={customsBrokerId ? String(customsBrokerId) : ""} onValueChange={(v) => setCustomsBrokerId(Number(v))}>
                  <SelectTrigger className="w-full">
                    <SelectValue placeholder="请选择报关行">
                      {(() => {
                        const selected = brokers.find((b) => b.id === customsBrokerId);
                        if (!selected) return customsBrokerId ? `未找到(ID:${customsBrokerId})` : "请选择报关行";
                        return selected.company_full_name || selected.name;
                      })()}
                    </SelectValue>
                  </SelectTrigger>
                  <SelectContent>
                    {brokers.length === 0 && (
                      <div className="px-3 py-2 text-sm text-muted-foreground">暂无报关行，请先在供应商管理中设置分类为"报关行"</div>
                    )}
                    {brokers.map((c) => (
                      <SelectItem key={c.id} value={String(c.id)}>
                        {c.company_full_name || c.name}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
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
                {/* 目的地查验费 */}
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
                      目的地查验费
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
              <Button type="button" variant="outline" onClick={() => { setFormOpen(false); setEditingItem(null); }}>
                取消
              </Button>
              <Button type="submit">
                <CheckCircle className="w-4 h-4 mr-1" />
                {editingItem ? "更新" : "保存"}
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
              {detailItem.customs_broker_name && (
                <div className="space-y-1">
                  <Label className="text-xs text-muted-foreground">报关行</Label>
                  <div className="font-medium">{detailItem.customs_broker_name}</div>
                </div>
              )}

              <div className="border rounded-lg p-3 space-y-2">
                <div className="space-y-1">
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">进口关税</span>
                    <span className="font-medium">{fmt(detailItem.import_duty)}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">进口增值税</span>
                    <span className="font-medium">{fmt(detailItem.import_vat)}</span>
                  </div>
                  <div className="flex justify-between font-semibold border-t pt-1">
                    <span>税费合计</span>
                    <span>{fmt(detailItem.tax_total)}</span>
                  </div>
                  <div className="flex justify-between pt-1">
                    <span className="text-muted-foreground">提货费</span>
                    <span>{fmt(detailItem.pickup_fee)}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">运费</span>
                    <span>{fmt(detailItem.freight)}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">报关服务费</span>
                    <span>{fmt(detailItem.clearance_service_fee)}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">目的地查验费</span>
                    <span>{fmt(detailItem.yard_fee)}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">冷藏费</span>
                    <span>{fmt(detailItem.cold_storage_fee)}</span>
                  </div>
                  <div className="flex justify-between font-semibold border-t pt-1">
                    <span>清关费合计</span>
                    <span>{fmt(detailItem.clearance_total)}</span>
                  </div>
                </div>
                <div className="flex justify-between font-bold border-t-2 pt-2 text-base">
                  <span>合计</span>
                  <span className="text-blue-700">{fmt(detailItem.grand_total)}</span>
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
              <TableHead>发票号</TableHead>
              <TableHead>费用日期</TableHead>
              <TableHead>报关行</TableHead>
              <TableHead>进口关税</TableHead>
              <TableHead>进口增值税</TableHead>
              <TableHead className="text-amber-700 bg-amber-50/50">税费合计</TableHead>
              <TableHead>提货费</TableHead>
              <TableHead>运费</TableHead>
              <TableHead>报关服务费</TableHead>
              <TableHead>目的地查验费</TableHead>
              <TableHead>冷藏费</TableHead>
              <TableHead className="text-blue-700 bg-blue-50/50">清关费合计</TableHead>
              <TableHead>合计</TableHead>
              <TableHead className="w-[100px]"></TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {isLoading ? (
              <TableRow>
                <TableCell colSpan={14} className="text-center py-8">
                  加载中...
                </TableCell>
              </TableRow>
            ) : !importFees.length ? (
              <TableRow>
                <TableCell colSpan={14} className="text-center py-8 text-muted-foreground">
                  暂无数据
                </TableCell>
              </TableRow>
            ) : (
              <>
                {importFees.map((f) => (
                  <TableRow key={f.invoice_id} className="hover:bg-slate-100 cursor-default transition-colors">
                  <TableCell className="font-medium">{f.invoice_no}</TableCell>
                  <TableCell>{f.expense_date || "-"}</TableCell>
                  <TableCell className="text-xs text-muted-foreground">{f.customs_broker_name || "-"}</TableCell>
                  <TableCell>{fmtFee(f.import_duty)}</TableCell>
                  <TableCell>{fmtFee(f.import_vat)}</TableCell>
                  <TableCell className="font-semibold text-amber-700 bg-amber-50/30">{fmtFee(f.tax_total)}</TableCell>
                  <TableCell>{fmtFee(f.pickup_fee)}</TableCell>
                  <TableCell>{fmtFee(f.freight)}</TableCell>
                  <TableCell>{fmtFee(f.clearance_service_fee)}</TableCell>
                  <TableCell>{fmtFee(f.yard_fee)}</TableCell>
                  <TableCell>{fmtFee(f.cold_storage_fee)}</TableCell>
                  <TableCell className="font-semibold text-blue-700 bg-blue-50/30">{fmtFee(f.clearance_total)}</TableCell>
                  <TableCell className="font-bold">{fmtFee(f.grand_total)}</TableCell>
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
                        className="h-7 w-7 text-blue-500"
                        onClick={() => handleOpenEdit(f)}
                        title="编辑"
                      >
                        <Pencil className="h-3 w-3" />
                      </Button>
                      <Button
                        variant="ghost"
                        size="icon"
                        className="h-7 w-7 text-red-500"
                        onClick={() => { setDeleteInvoiceId(f.invoice_id); setDeleteOpen(true); }}
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
                  <TableCell colSpan={3} className="text-right">本页合计:</TableCell>
                  <TableCell>{fmtFee(importFees.reduce((s, f) => s + Number(f.import_duty || 0), 0))}</TableCell>
                  <TableCell>{fmtFee(importFees.reduce((s, f) => s + Number(f.import_vat || 0), 0))}</TableCell>
                  <TableCell className="font-semibold text-amber-700">{fmtFee(importFees.reduce((s, f) => s + Number(f.tax_total || 0), 0))}</TableCell>
                  <TableCell>{fmtFee(importFees.reduce((s, f) => s + Number(f.pickup_fee || 0), 0))}</TableCell>
                  <TableCell>{fmtFee(importFees.reduce((s, f) => s + Number(f.freight || 0), 0))}</TableCell>
                  <TableCell>{fmtFee(importFees.reduce((s, f) => s + Number(f.clearance_service_fee || 0), 0))}</TableCell>
                  <TableCell>{fmtFee(importFees.reduce((s, f) => s + Number(f.yard_fee || 0), 0))}</TableCell>
                  <TableCell>{fmtFee(importFees.reduce((s, f) => s + Number(f.cold_storage_fee || 0), 0))}</TableCell>
                  <TableCell className="font-semibold text-blue-700">{fmtFee(importFees.reduce((s, f) => s + Number(f.clearance_total || 0), 0))}</TableCell>
                  <TableCell className="font-bold">{fmtFee(importFees.reduce((s, f) => s + Number(f.grand_total || 0), 0))}</TableCell>
                  <TableCell />
                </TableRow>
              )}
            </>
            )}
          </TableBody>
        </Table>
      </div>
      {/* 删除确认弹窗 */}
      <AlertDialog open={deleteOpen} onOpenChange={setDeleteOpen}
      >
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>确认删除</AlertDialogTitle>
            <AlertDialogDescription>
              确定要删除此发票的进口费用吗？此操作不可撤销。
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <Button variant="outline" onClick={() => { setDeleteOpen(false); setDeleteInvoiceId(null); }}
            >
              取消
            </Button>
            <Button variant="destructive" onClick={handleDelete}
            >
              删除
            </Button>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
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
  const [batchTotalUSD, setBatchTotalUSD] = useState(0);
  const [batchExchangedUSD, setBatchExchangedUSD] = useState(0);
  const [batchRemainingUSD, setBatchRemainingUSD] = useState(0);
  const [batchInvoices, setBatchInvoices] = useState<any[]>([]);
  const [selectedInvoiceId, setSelectedInvoiceId] = useState("");
  const [exchangeDate, setExchangeDate] = useState("");
  const [amountUsd, setAmountUsd] = useState("");
  const [exchangeRate, setExchangeRate] = useState("");
  const [amountCny, setAmountCny] = useState("");
  const [feeCny, setFeeCny] = useState("");

  // Reset on open (only for new record, not edit)
  useEffect(() => {
    if (formOpen && !editingRecord) {
      setBatchId("");
      setExchangeDate("");
      setAmountUsd("");
      setExchangeRate("");
      setAmountCny("");
      setFeeCny("");
      setBatchTotalUSD(0);
      setBatchExchangedUSD(0);
      setBatchRemainingUSD(0);
      setBatchInvoices([]);
      setSelectedInvoiceId("");
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

  // Fetch batch purchase total + invoices when batch selected
  const onSelectBatch = async (bid: string) => {
    setBatchId(bid);
    setAmountUsd("");
    setBatchTotalUSD(0);
    setBatchExchangedUSD(0);
    setBatchRemainingUSD(0);
    setBatchInvoices([]);
    setSelectedInvoiceId("");
    if (!bid) return;
    try {
      const res = await api.get(`/v1/finance/batch-purchase-total?batch_id=${bid}`);
      if (res.data?.success && res.data?.data) {
        const total = Number(res.data.data.total_usd) || 0;
        const exchanged = Number(res.data.data.exchanged_usd) || 0;
        const remaining = Number(res.data.data.remaining_usd) || 0;
        setBatchTotalUSD(total);
        setBatchExchangedUSD(exchanged);
        setBatchRemainingUSD(remaining);
        setBatchInvoices(res.data.data.invoices || []);
        setSelectedInvoiceId("__batch__");
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
        invoice_id: selectedInvoiceId && selectedInvoiceId !== "__batch__" ? Number(selectedInvoiceId) : null,
        exchange_date: exchangeDate,
        amount_usd: Number(amountUsd),
        exchange_rate: Number(exchangeRate),
        amount_cny: Number(amountCny),
        fee_cny: Number(feeCny) || 0,
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

  const [deleteOpen, setDeleteOpen] = useState(false);
  const [deleteRecordId, setDeleteRecordId] = useState<number | null>(null);

  const handleDeleteConfirm = async () => {
    if (!deleteRecordId) return;
    try {
      await api.delete(`/v1/finance/exchange/${deleteRecordId}`);
      toast.success("已删除");
      queryClient.invalidateQueries({ queryKey: ["exchange-records"] });
      queryClient.invalidateQueries({ queryKey: ["finance-summary"] });
      setDeleteOpen(false);
      setDeleteRecordId(null);
    } catch (error: any) {
      toast.error(error.response?.data?.detail ?? "删除失败");
    }
  };

  const [editingRecord, setEditingRecord] = useState<ExchangeRecord | null>(null);

  const handleOpenDetail = (record: ExchangeRecord) => {
    setDetailRecord(record);
    setDetailOpen(true);
  };

  const handleOpenEdit = (record: ExchangeRecord) => {
    setEditingRecord(record);
    setBatchId(String(record.batch_id || ""));
    setExchangeDate(record.exchange_date);
    setAmountUsd(String(record.amount_usd ?? ""));
    setExchangeRate(String(record.exchange_rate ?? ""));
    setAmountCny(String(record.amount_cny ?? ""));
    setFeeCny(String(record.fee_cny ?? ""));
    setBatchTotalUSD(0);
    setBatchExchangedUSD(0);
    setBatchRemainingUSD(0);
    setBatchInvoices([]);
    setSelectedInvoiceId("");
    setFormOpen(true);
  };

  const handleEditSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!editingRecord) return;
    try {
      await api.put(`/v1/finance/exchange/${editingRecord.id}`, {
        exchange_date: exchangeDate,
        amount_usd: Number(amountUsd),
        exchange_rate: Number(exchangeRate),
        amount_cny: Number(amountCny),
        fee_cny: Number(feeCny) || 0,
      });
      toast.success("购汇记录更新成功");
      queryClient.invalidateQueries({ queryKey: ["exchange-records"] });
      queryClient.invalidateQueries({ queryKey: ["finance-summary"] });
      setFormOpen(false);
      setEditingRecord(null);
    } catch (error: any) {
      toast.error(error.response?.data?.detail ?? "更新失败");
    }
  };

  return (
    <div className="space-y-4">
      <div className="flex justify-end">
        <Button size="sm" onClick={() => setFormOpen(true)}>
          <Plus className="h-4 w-4 mr-1" />
          新增购汇
        </Button>
      </div>

      <Dialog open={formOpen} onOpenChange={(v) => { if (!v) { setFormOpen(false); setEditingRecord(null); }}}>
        <DialogContent className="max-w-[640px]">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <DollarSign className="w-5 h-5" />
              {editingRecord ? "编辑购汇登记" : "新增购汇登记"}
            </DialogTitle>
          </DialogHeader>

          <form onSubmit={editingRecord ? handleEditSubmit : handleSubmit} className="space-y-5 py-2">
            {/* 关联批次 */}
            <div className="grid gap-2">
              <Label className="text-sm font-medium">
                关联批次 <span className="text-red-500">*</span>
              </Label>
              {editingRecord ? (
                <div className="bg-muted px-3 py-2 rounded-md text-sm">
                  {batches.find((b) => b.id === Number(editingRecord.batch_id))?.batch_code || editingRecord.batch_id || "-"}
                </div>
              ) : (
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
              )}
            </div>

            {batchTotalUSD > 0 && (
              <div className="bg-blue-50 border border-blue-100 p-4 rounded-lg space-y-2">
                <div className="flex justify-between text-sm">
                  <span className="text-blue-700">采购总额</span>
                  <span className="font-semibold">{fmtUSD(batchTotalUSD)}</span>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-blue-700">已购汇</span>
                  <span className="font-semibold">{fmtUSD(batchExchangedUSD)}</span>
                </div>
                <div className="flex justify-between text-sm border-t border-blue-200 pt-1">
                  <span className="text-blue-700 font-medium">未购汇</span>
                  <span className="font-bold text-blue-600">{fmtUSD(batchRemainingUSD)}</span>
                </div>
              </div>
            )}

            {/* 发票选择 */}
            {batchInvoices.length > 0 && (
              <div className="grid gap-2">
                <Label className="text-sm font-medium">选择发票</Label>
                <Select value={selectedInvoiceId} onValueChange={(v) => {
                  setSelectedInvoiceId(v ?? "");
                  if (v && v !== "__batch__") {
                    const inv = batchInvoices.find((i) => String(i.id) === v);
                    if (inv?.remaining_usd) {
                      setAmountUsd(String(Number(inv.remaining_usd).toFixed(2)));
                    } else {
                      setAmountUsd("");
                    }
                  } else if (v === "__batch__") {
                    setAmountUsd(String(Number(batchRemainingUSD).toFixed(2)));
                  }
                }}>
                  <SelectTrigger className="w-full">
                    <SelectValue placeholder="请选择发票" />
                  </SelectTrigger>
                  <SelectContent className="min-w-[400px]">
                    <SelectItem value="__batch__">
                      <span className="font-medium">📦 全批次购汇</span>
                      <span className="ml-2 text-muted-foreground">剩余 {fmtUSD(batchRemainingUSD)}</span>
                    </SelectItem>
                    {batchInvoices.map((inv) => (
                      <SelectItem key={inv.id} value={String(inv.id)}>
                        <span className="font-mono">{inv.invoice_no}</span>
                        <span className="ml-2 text-blue-600">剩余 {fmtUSD(inv.remaining_usd)}</span>
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
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
              <Button type="button" variant="outline" onClick={() => { setFormOpen(false); setEditingRecord(null); }}>
                取消
              </Button>
              <Button type="submit">
                <CheckCircle className="w-4 h-4 mr-1" />
                {editingRecord ? "更新" : "保存"}
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
                      return b.invoice_nos?.replace(/&/g, ", ") || "-";
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
                        className="h-7 w-7 text-blue-500"
                        onClick={() => handleOpenEdit(r)}
                        title="编辑"
                      >
                        <Pencil className="h-3 w-3" />
                      </Button>
                      <Button
                        variant="ghost"
                        size="icon"
                        className="h-7 w-7 text-red-500"
                        onClick={() => { setDeleteRecordId(r.id); setDeleteOpen(true); }}
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
      {/* 删除确认弹窗 */}
      <AlertDialog open={deleteOpen} onOpenChange={setDeleteOpen}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>确认删除</AlertDialogTitle>
            <AlertDialogDescription>
              确定要删除此购汇记录吗？此操作不可撤销。
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <Button variant="outline" onClick={() => { setDeleteOpen(false); setDeleteRecordId(null); }}>
              取消
            </Button>
            <Button variant="destructive" onClick={handleDeleteConfirm}>
              删除
            </Button>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
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
  const [currency, setCurrency] = useState("CNY");
  const [bankAccountId, setBankAccountId] = useState("");
  const [selectedSaleIds, setSelectedSaleIds] = useState<number[]>([]);
  const [selectedCustomerId, setSelectedCustomerId] = useState<string>("");
  const [customerSearch, setCustomerSearch] = useState("");
  const [customerDropdownOpen, setCustomerDropdownOpen] = useState(false);
  const [editingTransaction, setEditingTransaction] = useState<Transaction | null>(null);
  const [deleteTarget, setDeleteTarget] = useState<Transaction | null>(null);
  const [deleteOpen, setDeleteOpen] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");
  const [debouncedSearch, setDebouncedSearch] = useState("");

  // 搜索防抖
  useEffect(() => {
    const timer = setTimeout(() => {
      setDebouncedSearch(searchQuery);
    }, 500);
    return () => clearTimeout(timer);
  }, [searchQuery]);

  // 筛选状态
  const [filterType, setFilterType] = useState("");
  const [filterCategory, setFilterCategory] = useState("");
  const [filterSaleId, setFilterSaleId] = useState("");
  const [filterLocked, setFilterLocked] = useState("");
  const [filterBankAccountId, setFilterBankAccountId] = useState("");

  // 批量删除
  const [selectedIds, setSelectedIds] = useState<number[]>([]);
  const [batchDeleteOpen, setBatchDeleteOpen] = useState(false);

  const { data, isLoading } = useQuery<Transaction[]>({
    queryKey: ["transactions", debouncedSearch, filterType, filterCategory, filterSaleId, filterLocked, filterBankAccountId],
    queryFn: async () => {
      const params = new URLSearchParams();
      if (debouncedSearch.trim()) params.append("search", debouncedSearch.trim());
      if (filterType) params.append("type", filterType);
      if (filterCategory) params.append("category", filterCategory);
      if (filterSaleId.trim() && /^[1-9]\d*$/.test(filterSaleId.trim())) params.append("related_sale_id", filterSaleId.trim());
      else if (filterSaleId.trim()) params.append("sale_no", filterSaleId.trim());
      if (filterLocked === "locked") params.append("is_locked", "true");
      else if (filterLocked === "unlocked") params.append("is_locked", "false");
      if (filterBankAccountId) params.append("bank_account_id", filterBankAccountId);
      const res = await api.get(`/v1/finance/transactions?${params.toString()}`);
      return res.data;
    },
  });

  // Fetch bank accounts
  const { data: bankAccountsData } = useQuery({
    queryKey: ["bank-accounts-transactions"],
    queryFn: async () => {
      const res = await api.get("/v1/finance/bank-accounts");
      return res.data;
    },
  });
  const bankAccounts = bankAccountsData || [];

  // Fetch all sales for displaying related sale numbers in list
  const { data: allSalesData } = useQuery({
    queryKey: ["all-sales-for-transaction-list", data?.flatMap((t) => t.related_sale_ids || [])],
    queryFn: async () => {
      const ids = data?.flatMap((t) => t.related_sale_ids || []).filter((id, i, arr) => arr.indexOf(id) === i) || [];
      if (ids.length === 0) return [];
      const res = await api.get(`/v1/sales/whole-fish?ids=${ids.join(",")}&limit=500`);
      return res.data?.items || [];
    },
    enabled: !!(data && data.length > 0),
  });
  const allSalesMap = React.useMemo(() => {
    const map: Record<number, string> = {};
    (allSalesData || []).forEach((s: any) => {
      map[s.id] = s.sale_no || `#${s.id}`;
    });
    return map;
  }, [allSalesData]);

  // Fetch customers
  const { data: customersData } = useQuery({
    queryKey: ["customers-for-transaction"],
    queryFn: async () => {
      const res = await api.get("/v1/companies?type=customer");
      return res.data?.items || [];
    },
    enabled: category === "main_business_revenue" && formOpen,
  });
  const customersList = customersData || [];

  // Fetch sales for counterparty auto-fill (按客户筛选)
  const { data: salesData } = useQuery({
    queryKey: ["sales-for-transaction", selectedCustomerId],
    queryFn: async () => {
      const params = new URLSearchParams();
      if (selectedCustomerId) params.set("customer_id", selectedCustomerId);
      params.set("limit", "500");
      const res = await api.get(`/v1/sales/whole-fish?${params.toString()}`);
      return res.data?.items || [];
    },
    enabled: type === "income" && category === "main_business_revenue" && formOpen,
  });
  const salesList = (salesData || []).filter((s: any) => {
    const remaining = Number(s.net_amount ?? 0) - Number(s.paid_amount ?? 0);
    return remaining > 0;
  });

  // 计算已选销售单合计待收金额
  const selectedTotal = salesList
    .filter((s: any) => selectedSaleIds.includes(s.id))
    .reduce((sum: number, s: any) => sum + (Number(s.net_amount ?? 0) - Number(s.paid_amount ?? 0)), 0);

  const getBankAccountName = (accountId: number | null) => {
    if (!accountId) return "-";
    const account = bankAccounts.find((b: any) => b.id === accountId);
    if (!account) return "-";
    return `${account.bank_name} ${account.account_number?.slice(-4) || ""}`;
  };

  const lockMutation = useMutation({
    mutationFn: async ({ id, locked }: { id: number; locked: boolean }) => {
      const res = await api.post(`/v1/finance/transactions/${id}/${locked ? "lock" : "unlock"}`);
      return res.data;
    },
    onSuccess: (_, variables) => {
      toast.success(variables.locked ? "交易记录已锁定" : "交易记录已解锁");
      queryClient.invalidateQueries({ queryKey: ["transactions"] });
    },
    onError: (err: any) => {
      toast.error(err.response?.data?.detail || "操作失败");
    },
  });

  const batchLockMutation = useMutation({
    mutationFn: async (ids: number[]) => {
      const res = await api.post("/v1/finance/transactions/batch-lock", { ids });
      return res.data;
    },
    onSuccess: (data) => {
      toast.success(`批量核对成功：${data.locked} 条已锁定${data.already_locked > 0 ? `，${data.already_locked} 条已锁定跳过` : ""}`);
      queryClient.invalidateQueries({ queryKey: ["transactions"] });
      setSelectedIds([]);
    },
    onError: (err: any) => {
      toast.error(err.response?.data?.detail || "批量核对失败");
    },
  });

  const batchUnlockMutation = useMutation({
    mutationFn: async (ids: number[]) => {
      const res = await api.post("/v1/finance/transactions/batch-unlock", { ids });
      return res.data;
    },
    onSuccess: (data) => {
      toast.success(`批量解锁成功：${data.unlocked} 条已解锁${data.not_locked > 0 ? `，${data.not_locked} 条未锁定跳过` : ""}`);
      queryClient.invalidateQueries({ queryKey: ["transactions"] });
      setSelectedIds([]);
    },
    onError: (err: any) => {
      toast.error(err.response?.data?.detail || "批量解锁失败");
    },
  });

  const handleDeleteClick = (transaction: Transaction) => {
    setDeleteTarget(transaction);
    setDeleteOpen(true);
  };

  const handleBatchDelete = async () => {
    if (selectedIds.length === 0) return;
    try {
      const res = await api.post("/v1/finance/transactions/batch-delete", { ids: selectedIds });
      const deleted = res.data?.deleted ?? selectedIds.length;
      const notFound = res.data?.not_found ?? 0;
      toast.success(`已删除 ${deleted} 条记录${notFound > 0 ? `，${notFound} 条未找到` : ""}`);
      queryClient.invalidateQueries({ queryKey: ["transactions"] });
      queryClient.invalidateQueries({ queryKey: ["finance-summary"] });
      setBatchDeleteOpen(false);
      setSelectedIds([]);
    } catch (error: any) {
      toast.error(error.response?.data?.detail ?? "批量删除失败");
    }
  };

  const toggleSelect = (id: number) => {
    setSelectedIds((prev) =>
      prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id]
    );
  };

  const toggleSelectAll = () => {
    if (!data || data.length === 0) return;
    if (selectedIds.length === data.length) {
      setSelectedIds([]);
    } else {
      setSelectedIds(data.map((r) => r.id));
    }
  };

  const handleConfirmDelete = async () => {
    if (!deleteTarget) return;
    try {
      await api.delete(`/v1/finance/transactions/${deleteTarget.id}`);
      toast.success("已删除");
      queryClient.invalidateQueries({ queryKey: ["transactions"] });
      queryClient.invalidateQueries({ queryKey: ["finance-summary"] });
      setDeleteOpen(false);
      setDeleteTarget(null);
    } catch (error: any) {
      toast.error(error.response?.data?.detail ?? "删除失败");
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!date || !type || !category || !amount || Number(amount) <= 0) {
      toast.error("请填写完整信息，金额必须大于0");
      return;
    }
    try {
      const payload: any = {
        transaction_date: date,
        type,
        category,
        amount: Number(amount),
        currency,
        counterparty_name: counterparty || undefined,
        reference_no: referenceNo || undefined,
        description: description || undefined,
      };
      if (type === "income" && bankAccountId) {
        payload.to_account_id = Number(bankAccountId);
      } else if (type === "expense" && bankAccountId) {
        payload.from_account_id = Number(bankAccountId);
      }
      if (selectedSaleIds.length > 0) {
        payload.related_sale_ids = selectedSaleIds;
      }

      if (editingTransaction) {
        await api.put(`/v1/finance/transactions/${editingTransaction.id}`, payload);
        toast.success("交易记录已更新");
      } else {
        await api.post("/v1/finance/transactions", payload);
        
        // 后端 create_transaction 已自动创建关联销售单的收款记录
        // 前端不再重复创建
        
        if (selectedSaleIds.length > 0 && type === "income" && category === "main_business_revenue") {
          const totalAmount = Number(amount);
          // 刷新销售单数据
          queryClient.invalidateQueries({ queryKey: ["sales"] });
          toast.success(`交易记录创建成功，已收款 ¥${totalAmount.toLocaleString()} 并已关联到销售单`);
        } else {
          toast.success("交易记录创建成功");
        }
      }
      queryClient.invalidateQueries({ queryKey: ["transactions"] });
      queryClient.invalidateQueries({ queryKey: ["finance-summary"] });
      setFormOpen(false);
      setEditingTransaction(null);
      setSelectedSaleIds([]);
      setSelectedCustomerId("");
      setCustomerSearch("");
    } catch (error: any) {
      console.error("创建交易记录失败:", error);
      console.error("Response data:", error.response?.data);
      console.error("Response status:", error.response?.status);
      const detail = error.response?.data?.detail;
      const rawData = error.response?.data;
      let msg: string;
      if (Array.isArray(detail)) {
        msg = detail.map((d: any) => d.msg).join("; ");
      } else if (typeof detail === "string") {
        msg = detail;
      } else if (rawData && typeof rawData === "string") {
        msg = rawData;
      } else if (rawData) {
        msg = JSON.stringify(rawData);
      } else {
        msg = editingTransaction ? "更新失败" : "创建失败";
      }
      toast.error(msg);
    }
  };

  const handleOpenEdit = (transaction: Transaction) => {
    setEditingTransaction(transaction);
    setDate(transaction.transaction_date);
    setType(transaction.type as any);
    setCategory(transaction.category);
    setAmount(String(transaction.amount));
    setCurrency(transaction.currency || "CNY");
    setCounterparty(transaction.counterparty_name || "");
    setReferenceNo(transaction.reference_no || "");
    setDescription(transaction.description || "");
    setBankAccountId(transaction.from_account_id ? String(transaction.from_account_id) : transaction.to_account_id ? String(transaction.to_account_id) : "");
    setSelectedSaleIds(transaction.related_sale_ids ?? []);
    setFormOpen(true);
  };

  // 收入分类 key 列表（必须与 transactionCategoryMap 一致）
  const incomeCategoryKeys = [
    "main_business_revenue",
    "other_business_revenue",
    "non_business_revenue",
    "fund_pooling",
    "customer_deposit",
  ];

  const incomeCategories = Object.entries(transactionCategoryMap).filter(([k]) =>
    incomeCategoryKeys.includes(k)
  );
  const expenseCategories = Object.entries(transactionCategoryMap).filter(
    ([k]) => !incomeCategoryKeys.includes(k)
  );

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap justify-between gap-2">
        {/* 搜索框 */}
        <div className="flex flex-wrap gap-2 items-center">
          <div className="relative flex-1 min-w-[200px] max-w-sm">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
            <Input
              placeholder="搜索日期、对方名称、金额、描述、销售单号..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="pl-9"
            />
          </div>
          <Select value={filterType} onValueChange={(v) => { setFilterType(v ?? ""); setFilterCategory(""); }}>
            <SelectTrigger className="w-[120px]">
              <SelectValue placeholder="类型" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="">全部类型</SelectItem>
              {Object.entries(transactionTypeMap).map(([k, v]) => (
                <SelectItem key={k} value={k}>{v}</SelectItem>
              ))}
            </SelectContent>
          </Select>
          <Select value={filterCategory} onValueChange={(v) => setFilterCategory(v ?? "")}>
            <SelectTrigger className="w-[140px]">
              <SelectValue placeholder="分类" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="">全部分类</SelectItem>
              {Object.entries(transactionCategoryMap)
                .filter(([k]) => {
                  if (!filterType) return true;
                  const incomeKeys = ["main_business_revenue", "other_business_revenue", "non_business_revenue", "fund_pooling"];
                  const isIncome = incomeKeys.includes(k);
                  return filterType === "income" ? isIncome : !isIncome;
                })
                .map(([k, v]) => (
                  <SelectItem key={k} value={k}>{v}</SelectItem>
                ))}
            </SelectContent>
          </Select>
          <div className="relative w-[160px]">
            <Input
              placeholder="关联销售单号"
              value={filterSaleId}
              onChange={(e) => setFilterSaleId(e.target.value)}
              className="text-sm"
            />
          </div>
          <Select value={filterLocked} onValueChange={(v) => setFilterLocked(v ?? "")}>
            <SelectTrigger className="w-[120px]">
              <SelectValue placeholder="锁定状态" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="">全部状态</SelectItem>
              <SelectItem value="locked">已锁定</SelectItem>
              <SelectItem value="unlocked">未锁定</SelectItem>
            </SelectContent>
          </Select>
          <Select value={filterBankAccountId} onValueChange={(v) => setFilterBankAccountId(v ?? "")}>
            <SelectTrigger className="w-[160px]">
              <SelectValue placeholder="银行账户" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="">全部账户</SelectItem>
              {bankAccounts.map((b: any) => (
                <SelectItem key={b.id} value={String(b.id)}>
                  {b.bank_name} {b.account_number?.slice(-4)}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          {(searchQuery || filterType || filterCategory || filterSaleId || filterLocked || filterBankAccountId) && (
            <Button variant="ghost" size="sm" onClick={() => {
              setSearchQuery("");
              setDebouncedSearch("");
              setFilterType("");
              setFilterCategory("");
              setFilterSaleId("");
              setFilterLocked("");
              setFilterBankAccountId("");
            }}>
              重置
            </Button>
          )}
        </div>
        <div className="flex gap-2">
          <Button
            size="sm"
            variant="outline"
            onClick={() => {
              if (!data || data.length === 0) {
                toast.info("暂无数据可导出");
                return;
              }
              const ok = exportExcel(
                data,
                [
                  { header: "日期", key: "transaction_date" },
                  { header: "类型", key: "type", format: (v) => transactionTypeMap[v] || v },
                  { header: "分类", key: "category", format: (v) => transactionCategoryMap[v] || v },
                  { header: "金额", key: "amount" },
                  { header: "币种", key: "currency" },
                  { header: "银行账户", key: "from_account_id", format: (v) => getBankAccountName(v || data.find((r: any) => r.from_account_id === v)?.to_account_id) },
                  { header: "对方", key: "counterparty_name" },
                  { header: "描述", key: "description" },
                  { header: "关联销售单", key: "related_sale_ids", format: (v) => v?.length > 0 ? Array.from(new Set(v as number[])).map((id) => allSalesMap[id]).filter(Boolean).join(", ") : "-" },
                ],
                "交易流水"
              );
              if (ok) toast.success("导出成功");
            }}
          >
            <FileDown className="h-4 w-4 mr-1" />
            导出 Excel
          </Button>
          {selectedIds.length > 0 && (
            <Button
              size="sm"
              variant="outline"
              className="border-green-600 text-green-600 hover:bg-green-50"
              onClick={() => {
                const unlockIds = selectedIds.filter((id) => !data?.find((r) => r.id === id)?.is_locked);
                if (unlockIds.length === 0) {
                  toast.info("选中的记录已全部锁定");
                  return;
                }
                batchLockMutation.mutate(unlockIds);
              }}
              disabled={batchLockMutation.isPending}
            >
              <CheckCircle className="h-4 w-4 mr-1" />
              批量核对 ({selectedIds.filter((id) => !data?.find((r) => r.id === id)?.is_locked).length})
            </Button>
          )}
          {selectedIds.length > 0 && (
            <Button
              size="sm"
              variant="outline"
              className="border-amber-600 text-amber-600 hover:bg-amber-50"
              onClick={() => {
                const lockedIds = selectedIds.filter((id) => data?.find((r) => r.id === id)?.is_locked);
                if (lockedIds.length === 0) {
                  toast.info("选中的记录已全部未锁定");
                  return;
                }
                batchUnlockMutation.mutate(lockedIds);
              }}
              disabled={batchUnlockMutation.isPending}
            >
              <Unlock className="h-4 w-4 mr-1" />
              批量解锁 ({selectedIds.filter((id) => data?.find((r) => r.id === id)?.is_locked).length})
            </Button>
          )}
          {selectedIds.length > 0 && (
            <Button
              size="sm"
              variant="destructive"
              onClick={() => setBatchDeleteOpen(true)}
            >
              <Trash2 className="h-4 w-4 mr-1" />
              批量删除 ({selectedIds.length})
            </Button>
          )}
          <Button size="sm" onClick={() => {
            setEditingTransaction(null);
            setDate(new Date().toISOString().split("T")[0]);  // 默认今天，避免空字符串
            setType("expense");
            setCategory("");
            setAmount("");
            setCounterparty("");
            setDescription("");
            setReferenceNo("");
            setCurrency("CNY");
            setBankAccountId("");
            setSelectedSaleIds([]);
            setSelectedIds([]);
            setFormOpen(true);
          }}>
            <Plus className="h-4 w-4 mr-1" />
            新增流水
          </Button>
          <BatchImportButton type="transactions" />
        </div>
      </div>

      <Dialog open={formOpen} onOpenChange={setFormOpen}>
        <DialogContent className="max-w-[400px]">
          <DialogHeader>
            <DialogTitle>{editingTransaction ? "编辑交易流水" : "新增交易流水"}</DialogTitle>
          </DialogHeader>
          <form onSubmit={handleSubmit} className="space-y-3">
            <div>
              <Label>日期</Label>
              <Input type="date" value={date} onChange={(e) => setDate(e.target.value)} />
            </div>
            <div className="grid grid-cols-2 gap-2">
              <div>
                <Label>类型</Label>
                <Select value={type} onValueChange={(v) => { setType(v ?? ""); setCategory(""); }}>
                  <SelectTrigger>
                    <SelectValue>{type ? transactionTypeMap[type] : "选择类型"}</SelectValue>
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
                    <SelectValue>{category ? transactionCategoryMap[category] : "选择分类"}</SelectValue>
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
                <Select value={currency} onValueChange={(v) => setCurrency(v ?? "CNY")}>
                  <SelectTrigger>
                    <SelectValue>
                      {(() => {
                        const map: Record<string, string> = { CNY: "人民币 (CNY)", USD: "美元 (USD)", EUR: "欧元 (EUR)" };
                        return map[currency] || currency;
                      })()}
                    </SelectValue>
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="CNY">人民币 (CNY)</SelectItem>
                    <SelectItem value="USD">美元 (USD)</SelectItem>
                    <SelectItem value="EUR">欧元 (EUR)</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>
            {type === "income" && category === "main_business_revenue" && (
              <div className="space-y-3">
                <div>
                  <Label>选择客户</Label>
                  {/* 可搜索客户选择器 */}
                  <div className="relative">
                    <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                    <Input
                      placeholder="搜索客户名称..."
                      value={customerSearch}
                      onChange={(e) => {
                        setCustomerSearch(e.target.value);
                        setCustomerDropdownOpen(true);
                      }}
                      onFocus={() => setCustomerDropdownOpen(true)}
                      className="pl-9"
                    />
                    {customerDropdownOpen && (
                      <div className="absolute z-50 w-full mt-1 bg-white border rounded-md shadow-lg max-h-[200px] overflow-y-auto">
                        {(() => {
                          const filtered = customerSearch.trim()
                            ? customersList.filter((c: any) => c.name.toLowerCase().includes(customerSearch.toLowerCase()))
                            : customersList;
                          if (filtered.length === 0) return (
                            <div className="px-3 py-2 text-sm text-muted-foreground">未找到客户</div>
                          );
                          return filtered.map((c: any) => (
                            <div
                              key={c.id}
                              className={cn(
                                "px-3 py-2 text-sm cursor-pointer hover:bg-accent",
                                selectedCustomerId === String(c.id) && "bg-accent font-medium"
                              )}
                              onClick={() => {
                                setSelectedCustomerId(String(c.id));
                                setCounterparty(c.name);
                                setCustomerSearch(c.name);
                                setCustomerDropdownOpen(false);
                                setSelectedSaleIds([]);
                              }}
                            >
                              {c.name}
                            </div>
                          ));
                        })()}
                      </div>
                    )}
                  </div>
                  {/* 点击外部关闭下拉 */}
                  {customerDropdownOpen && (
                    <div className="fixed inset-0 z-40" onClick={() => setCustomerDropdownOpen(false)} />
                  )}
                </div>
                
                {selectedCustomerId && (
                  <div>
                    <Label>关联销售单（可多选）</Label>
                    <div className="border rounded-md p-2 space-y-1 max-h-[200px] overflow-y-auto">
                      {salesList.length === 0 && (
                        <p className="text-xs text-muted-foreground py-2">该客户暂无未付款销售单</p>
                      )}
                      {salesList.map((s: any) => {
                        const remaining = Number(s.net_amount ?? 0) - Number(s.paid_amount ?? 0);
                        const isSelected = selectedSaleIds.includes(s.id);
                        return (
                          <div key={s.id} className="flex items-center gap-2 py-1">
                            <Checkbox
                              checked={isSelected}
                              onCheckedChange={(checked) => {
                                if (checked) {
                                  setSelectedSaleIds((prev) => [...prev, s.id]);
                                } else {
                                  setSelectedSaleIds((prev) => prev.filter((id) => id !== s.id));
                                }
                              }}
                            />
                            <div className="flex-1 text-xs">
                              <span className="font-medium">{s.sale_no ?? `#${s.id}`}</span>
                              <span className="text-muted-foreground"> · 待付 ¥{remaining.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</span>
                            </div>
                          </div>
                        );
                      })}
                    </div>
                    {selectedSaleIds.length > 0 && (
                      <div className="text-xs mt-2 space-y-1">
                        <p className="text-muted-foreground">
                          已选 {selectedSaleIds.length} 单
                        </p>
                        <p className="font-medium text-orange-600">
                          合计待收: ¥{selectedTotal.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                        </p>
                        {Number(amount) > 0 && Number(amount) < selectedTotal && (
                          <p className="text-xs text-blue-600">
                            本次实收 ¥{Number(amount).toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}，剩余 ¥{(selectedTotal - Number(amount)).toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })} 将留待下次收取
                          </p>
                        )}
                      </div>
                    )}
                  </div>
                )}
              </div>
            )}

            <div>
              <Label>银行账户</Label>
              <Select value={bankAccountId} onValueChange={(v) => setBankAccountId(v ?? "")}>
                <SelectTrigger>
                  <SelectValue>
                    {(() => {
                      const b = bankAccounts.find((b: any) => String(b.id) === bankAccountId);
                      return b ? `${b.bank_name} ${b.account_number?.slice(-4)}` : "选择银行账户（可选）";
                    })()}
                  </SelectValue>
                </SelectTrigger>
                <SelectContent>
                  {bankAccounts.map((b: any) => (
                    <SelectItem key={b.id} value={String(b.id)} className="text-xs">
                      {b.bank_name} {b.account_number?.slice(-4)}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div>
              <Label>对方名称</Label>
              <Input value={counterparty} onChange={(e) => setCounterparty(e.target.value)} placeholder={type === "income" ? "选择销售单后自动填充" : "可选"} />
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
              <Button type="submit">{editingTransaction ? "更新" : "保存"}</Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>

      {/* 删除确认 */}
      <Dialog open={deleteOpen} onOpenChange={setDeleteOpen}>
        <DialogContent className="max-w-sm">
          <DialogHeader>
            <DialogTitle>确认删除</DialogTitle>
          </DialogHeader>
          <p className="py-4">
            确定删除交易流水「{deleteTarget?.transaction_date} · {transactionTypeMap[deleteTarget?.type ?? ""]} · {transactionCategoryMap[deleteTarget?.category ?? ""]} · ¥{deleteTarget?.amount}」吗？
          </p>
          <DialogFooter>
            <Button variant="outline" onClick={() => { setDeleteOpen(false); setDeleteTarget(null); }}>
              取消
            </Button>
            <Button variant="destructive" onClick={handleConfirmDelete}>
              删除
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* 批量删除确认 */}
      <Dialog open={batchDeleteOpen} onOpenChange={setBatchDeleteOpen}>
        <DialogContent className="max-w-sm">
          <DialogHeader>
            <DialogTitle>确认批量删除</DialogTitle>
          </DialogHeader>
          <p className="py-4">
            确定删除选中的 {selectedIds.length} 条交易流水吗？此操作不可撤销。
          </p>
          <DialogFooter>
            <Button variant="outline" onClick={() => { setBatchDeleteOpen(false); }}>
              取消
            </Button>
            <Button variant="destructive" onClick={handleBatchDelete}>
              删除
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <div className="border rounded-lg">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead className="w-[40px]">
                <Checkbox
                  checked={data && data.length > 0 && selectedIds.length === data.length}
                  onCheckedChange={toggleSelectAll}
                />
              </TableHead>
              <TableHead>日期</TableHead>
              <TableHead>类型</TableHead>
              <TableHead>分类</TableHead>
              <TableHead className="text-right">金额</TableHead>
              <TableHead>币种</TableHead>
              <TableHead>银行账户</TableHead>
              <TableHead>对方</TableHead>
              <TableHead>描述</TableHead>
              <TableHead>关联销售单</TableHead>
              <TableHead className="w-[60px]"></TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {isLoading ? (
              <TableRow>
                <TableCell colSpan={11} className="text-center py-8">
                  加载中...
                </TableCell>
              </TableRow>
            ) : !data?.length ? (
              <TableRow>
                <TableCell colSpan={11} className="text-center py-8 text-muted-foreground">
                  暂无数据
                </TableCell>
              </TableRow>
            ) : (
              <>
                {data.map((r) => (
                <TableRow key={r.id} className={r.is_locked ? "bg-muted/30" : ""}>
                  <TableCell>
                    <Checkbox
                      checked={selectedIds.includes(r.id)}
                      onCheckedChange={() => toggleSelect(r.id)}
                      disabled={r.is_locked}
                    />
                  </TableCell>
                  <TableCell>
                    <div className="flex items-center gap-1.5">
                      {r.is_locked && <Lock className="h-3 w-3 text-muted-foreground" />}
                      {r.transaction_date}
                    </div>
                  </TableCell>
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
                    {Number(r.amount).toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                  </TableCell>
                  <TableCell>{r.currency}</TableCell>
                  <TableCell className="text-xs text-muted-foreground">
                    {getBankAccountName(r.from_account_id || r.to_account_id)}
                  </TableCell>
                  <TableCell>{r.counterparty_name ?? "-"}</TableCell>
                  <TableCell className="text-xs text-muted-foreground max-w-[150px] truncate">
                    {r.description ?? "-"}
                  </TableCell>
                  <TableCell className="text-xs">
                    {r.related_sale_ids?.length > 0
                      ? [...new Set(r.related_sale_ids)].map(id => allSalesMap[id]).filter(Boolean).join(", ")
                      : "-"}
                  </TableCell>
                  <TableCell>
                    <div className="flex gap-1">
                      {r.is_locked ? (
                        <Button
                          variant="ghost"
                          size="sm"
                          className="h-7 px-2 text-xs text-muted-foreground"
                          onClick={() => lockMutation.mutate({ id: r.id, locked: false })}
                          disabled={lockMutation.isPending}
                        >
                          <Unlock className="h-3 w-3 mr-1" />
                          解锁
                        </Button>
                      ) : (
                        <>
                          <Button
                            variant="ghost"
                            size="icon"
                            className="h-7 w-7"
                            onClick={() => handleOpenEdit(r)}
                            title="编辑"
                          >
                            <Pencil className="h-3 w-3" />
                          </Button>
                          <Button
                            variant="ghost"
                            size="icon"
                            className="h-7 w-7 text-red-500"
                            onClick={() => handleDeleteClick(r)}
                            title="删除"
                          >
                            <Trash2 className="h-3 w-3" />
                          </Button>
                          <Button
                            variant="ghost"
                            size="sm"
                            className="h-7 px-2 text-xs"
                            onClick={() => lockMutation.mutate({ id: r.id, locked: true })}
                            disabled={lockMutation.isPending}
                            title="核对锁定"
                          >
                            <Lock className="h-3 w-3 mr-1" />
                            核对
                          </Button>
                        </>
                      )}
                    </div>
                  </TableCell>
                </TableRow>
              ))}
              {/* 页汇总行 */}
              {data.length > 0 && (
                <TableRow className="bg-muted/50 font-medium border-t-2">
                  <TableCell />
                  <TableCell colSpan={3} className="text-right">本页合计:</TableCell>
                  <TableCell className="text-right font-bold">
                    {data.reduce((s, r) => s + (r.type === "income" ? Number(r.amount || 0) : -Number(r.amount || 0)), 0).toLocaleString("zh-CN", {minimumFractionDigits: 2, maximumFractionDigits: 2})}
                  </TableCell>
                  <TableCell colSpan={5} />
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

