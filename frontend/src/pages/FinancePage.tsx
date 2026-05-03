import React, { useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
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
import { Plus, Trash2, DollarSign, Receipt, Truck, FileText } from "lucide-react";
import { toast } from "sonner";

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

interface ExchangeRecord {
  id: number;
  invoice_id: number;
  exchange_date: string;
  amount_usd: string;
  exchange_rate: string;
  amount_cny: string;
  fee_cny: string;
  status: string;
}

interface ImportTax {
  id: number;
  invoice_id: number;
  tax_date: string;
  import_duty: string;
  import_vat: string;
  consumption_tax: string;
  other_taxes: string;
  total_tax: string;
}

interface ClearanceCost {
  id: number;
  invoice_id: number;
  cost_date: string;
  clearance_fee: string;
  freight_fee: string;
  inspection_fee: string;
  quarantine_fee: string;
  other_costs: string;
  total_cost: string;
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

export function FinancePage() {
  const [activeTab, setActiveTab] = useState("exchange");
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
          <p className="text-sm text-muted-foreground">购汇 / 税费 / 清关 / 流水</p>
        </div>
        <BatchImportButton type="finance" />
      </div>

      {/* 汇总卡片 */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
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
            <CardTitle className="text-sm font-medium">税费合计</CardTitle>
            <FileText className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              ¥{Number(summary?.total_tax || 0).toLocaleString()}
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium">清关运费</CardTitle>
            <Truck className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              ¥{Number(summary?.total_clearance_cost || 0).toLocaleString()}
            </div>
          </CardContent>
        </Card>
      </div>

      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList className="grid w-full grid-cols-4">
          <TabsTrigger value="exchange">购汇记录</TabsTrigger>
          <TabsTrigger value="taxes">进口税费</TabsTrigger>
          <TabsTrigger value="clearance">清关运费</TabsTrigger>
          <TabsTrigger value="transactions">交易流水</TabsTrigger>
        </TabsList>

        <TabsContent value="exchange" className="pt-4">
          <ExchangeTab />
        </TabsContent>
        <TabsContent value="taxes" className="pt-4">
          <TaxesTab />
        </TabsContent>
        <TabsContent value="clearance" className="pt-4">
          <ClearanceTab />
        </TabsContent>
        <TabsContent value="transactions" className="pt-4">
          <TransactionsTab />
        </TabsContent>
      </Tabs>
    </div>
  );
}

// ==================== 购汇记录 ====================

function ExchangeTab() {
  const queryClient = useQueryClient();
  const [formOpen, setFormOpen] = useState(false);
  const [invoiceId, setInvoiceId] = useState("");
  const [exchangeDate, setExchangeDate] = useState("");
  const [amountUsd, setAmountUsd] = useState("");
  const [exchangeRate, setExchangeRate] = useState("");
  const [amountCny, setAmountCny] = useState("");
  const [feeCny, setFeeCny] = useState("0");

  // 弹窗打开时重置
  React.useEffect(() => {
    if (formOpen) {
      setInvoiceId(""); setExchangeDate(""); setAmountUsd(""); setExchangeRate(""); setAmountCny(""); setFeeCny("0");
    }
  }, [formOpen]);

  const { data, isLoading } = useQuery<ExchangeRecord[]>({
    queryKey: ["exchange-records"],
    queryFn: async () => {
      const res = await api.get("/v1/finance/exchange");
      return res.data;
    },
  });

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

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await api.post("/v1/finance/exchange", {
        invoice_id: Number(invoiceId),
        exchange_date: exchangeDate,
        amount_usd: Number(amountUsd),
        exchange_rate: Number(exchangeRate),
        amount_cny: Number(amountCny),
        fee_cny: Number(feeCny) || 0,
      });
      toast.success("购汇记录创建成功");
      queryClient.invalidateQueries({ queryKey: ["exchange-records"] });
      queryClient.invalidateQueries({ queryKey: ["finance-summary"] });
      setFormOpen(false);
      setInvoiceId(""); setExchangeDate(""); setAmountUsd(""); setExchangeRate(""); setAmountCny(""); setFeeCny("0");
    } catch (error: any) {
      toast.error(error.response?.data?.detail ?? "创建失败");
    }
  };

  return (
    <div className="space-y-4">
      <div className="flex justify-end">
        <Button size="sm" onClick={() => setFormOpen(true)}><Plus className="h-4 w-4 mr-1" />新增购汇</Button>
      </div>

      <Dialog open={formOpen} onOpenChange={setFormOpen}>
        <DialogContent className="max-w-[400px]">
          <DialogHeader><DialogTitle>新增购汇记录</DialogTitle></DialogHeader>
          <form onSubmit={handleSubmit} className="space-y-3">
            <div><Label>发票ID</Label><Input type="number" value={invoiceId} onChange={e => setInvoiceId(e.target.value)} /></div>
            <div><Label>购汇日期</Label><Input type="date" value={exchangeDate} onChange={e => setExchangeDate(e.target.value)} /></div>
            <div className="grid grid-cols-2 gap-2">
              <div><Label>USD金额</Label><Input type="number" value={amountUsd} onChange={e => setAmountUsd(e.target.value)} /></div>
              <div><Label>汇率</Label><Input type="number" step="0.0001" value={exchangeRate} onChange={e => setExchangeRate(e.target.value)} /></div>
            </div>
            <div className="grid grid-cols-2 gap-2">
              <div><Label>CNY金额</Label><Input type="number" value={amountCny} onChange={e => setAmountCny(e.target.value)} /></div>
              <div><Label>手续费</Label><Input type="number" value={feeCny} onChange={e => setFeeCny(e.target.value)} /></div>
            </div>
            <DialogFooter>
              <Button type="button" variant="outline" onClick={() => setFormOpen(false)}>取消</Button>
              <Button type="submit">保存</Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>

      <div className="border rounded-lg">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>发票ID</TableHead><TableHead>日期</TableHead><TableHead>USD</TableHead>
              <TableHead>汇率</TableHead><TableHead>CNY</TableHead><TableHead>手续费</TableHead><TableHead className="w-[60px]"></TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {isLoading ? <TableRow><TableCell colSpan={7} className="text-center py-8">加载中...</TableCell></TableRow>
            : !data?.length ? <TableRow><TableCell colSpan={7} className="text-center py-8 text-muted-foreground">暂无数据</TableCell></TableRow>
            : data.map(r => (
              <TableRow key={r.id}>
                <TableCell>{r.invoice_id}</TableCell>
                <TableCell>{r.exchange_date}</TableCell>
                <TableCell>${Number(r.amount_usd).toLocaleString()}</TableCell>
                <TableCell>{r.exchange_rate}</TableCell>
                <TableCell>¥{Number(r.amount_cny).toLocaleString()}</TableCell>
                <TableCell>¥{Number(r.fee_cny).toLocaleString()}</TableCell>
                <TableCell><Button variant="ghost" size="icon" className="h-7 w-7 text-red-500" onClick={() => handleDelete(r.id)}><Trash2 className="h-3 w-3" /></Button></TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>
    </div>
  );
}

// ==================== 进口税费 ====================

function TaxesTab() {
  const queryClient = useQueryClient();
  const [formOpen, setFormOpen] = useState(false);
  const [invoiceId, setInvoiceId] = useState("");
  const [taxDate, setTaxDate] = useState("");
  const [importDuty, setImportDuty] = useState("0");
  const [importVat, setImportVat] = useState("0");
  const [consumptionTax, setConsumptionTax] = useState("0");
  const [otherTaxes, setOtherTaxes] = useState("0");

  // 弹窗打开时重置
  React.useEffect(() => {
    if (formOpen) {
      setInvoiceId(""); setTaxDate(""); setImportDuty("0"); setImportVat("0"); setConsumptionTax("0"); setOtherTaxes("0");
    }
  }, [formOpen]);

  const totalTax = Number(importDuty) + Number(importVat) + Number(consumptionTax) + Number(otherTaxes);

  const { data, isLoading } = useQuery<ImportTax[]>({
    queryKey: ["import-taxes"],
    queryFn: async () => { const res = await api.get("/v1/finance/taxes"); return res.data; },
  });

  const handleDelete = async (id: number) => {
    if (!confirm("确定删除？")) return;
    try { await api.delete(`/v1/finance/taxes/${id}`); toast.success("已删除"); queryClient.invalidateQueries({ queryKey: ["import-taxes", "finance-summary"] }); }
    catch (error: any) { toast.error(error.response?.data?.detail ?? "删除失败"); }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await api.post("/v1/finance/taxes", { invoice_id: Number(invoiceId), tax_date: taxDate, import_duty: Number(importDuty), import_vat: Number(importVat), consumption_tax: Number(consumptionTax), other_taxes: Number(otherTaxes), total_tax: totalTax });
      toast.success("税费记录创建成功");
      queryClient.invalidateQueries({ queryKey: ["import-taxes", "finance-summary"] });
      setFormOpen(false);
    } catch (error: any) { toast.error(error.response?.data?.detail ?? "创建失败"); }
  };

  return (
    <div className="space-y-4">
      <div className="flex justify-end">
        <Button size="sm" onClick={() => setFormOpen(true)}><Plus className="h-4 w-4 mr-1" />新增税费</Button>
      </div>
      <Dialog open={formOpen} onOpenChange={setFormOpen}>
        <DialogContent className="max-w-[400px]">
          <DialogHeader><DialogTitle>新增税费记录</DialogTitle></DialogHeader>
          <form onSubmit={handleSubmit} className="space-y-3">
            <div><Label>发票ID</Label><Input type="number" value={invoiceId} onChange={e => setInvoiceId(e.target.value)} /></div>
            <div><Label>税费日期</Label><Input type="date" value={taxDate} onChange={e => setTaxDate(e.target.value)} /></div>
            <div className="grid grid-cols-2 gap-2">
              <div><Label>进口关税</Label><Input type="number" value={importDuty} onChange={e => setImportDuty(e.target.value)} /></div>
              <div><Label>进口增值税</Label><Input type="number" value={importVat} onChange={e => setImportVat(e.target.value)} /></div>
            </div>
            <div className="grid grid-cols-2 gap-2">
              <div><Label>消费税</Label><Input type="number" value={consumptionTax} onChange={e => setConsumptionTax(e.target.value)} /></div>
              <div><Label>其他税费</Label><Input type="number" value={otherTaxes} onChange={e => setOtherTaxes(e.target.value)} /></div>
            </div>
            <div className="bg-muted p-2 rounded text-sm flex justify-between font-semibold"><span>税费合计</span><span>¥{totalTax.toLocaleString(undefined, {minimumFractionDigits: 2})}</span></div>
            <DialogFooter><Button type="button" variant="outline" onClick={() => setFormOpen(false)}>取消</Button><Button type="submit">保存</Button></DialogFooter>
          </form>
        </DialogContent>
      </Dialog>
      <div className="border rounded-lg">
        <Table>
          <TableHeader><TableRow><TableHead>发票</TableHead><TableHead>日期</TableHead><TableHead>关税</TableHead><TableHead>增值税</TableHead><TableHead>合计</TableHead><TableHead className="w-[60px]"></TableHead></TableRow></TableHeader>
          <TableBody>
            {isLoading ? <TableRow><TableCell colSpan={6} className="text-center py-8">加载中...</TableCell></TableRow>
            : !data?.length ? <TableRow><TableCell colSpan={6} className="text-center py-8 text-muted-foreground">暂无数据</TableCell></TableRow>
            : data.map(r => (
              <TableRow key={r.id}><TableCell>{r.invoice_id}</TableCell><TableCell>{r.tax_date}</TableCell><TableCell>¥{Number(r.import_duty).toLocaleString()}</TableCell><TableCell>¥{Number(r.import_vat).toLocaleString()}</TableCell><TableCell className="font-semibold">¥{Number(r.total_tax).toLocaleString()}</TableCell><TableCell><Button variant="ghost" size="icon" className="h-7 w-7 text-red-500" onClick={() => handleDelete(r.id)}><Trash2 className="h-3 w-3" /></Button></TableCell></TableRow>
            ))}
          </TableBody>
        </Table>
      </div>
    </div>
  );
}

// ==================== 清关运费 ====================

function ClearanceTab() {
  const queryClient = useQueryClient();
  const [formOpen, setFormOpen] = useState(false);
  const [invoiceId, setInvoiceId] = useState("");
  const [costDate, setCostDate] = useState("");
  const [clearanceFee, setClearanceFee] = useState("0");
  const [freightFee, setFreightFee] = useState("0");
  const [inspectionFee, setInspectionFee] = useState("0");
  const [otherCosts, setOtherCosts] = useState("0");

  // 弹窗打开时重置
  React.useEffect(() => {
    if (formOpen) {
      setInvoiceId(""); setCostDate(""); setClearanceFee("0"); setFreightFee("0"); setInspectionFee("0"); setOtherCosts("0");
    }
  }, [formOpen]);

  const totalCost = Number(clearanceFee) + Number(freightFee) + Number(inspectionFee) + Number(otherCosts);

  const { data, isLoading } = useQuery<ClearanceCost[]>({
    queryKey: ["clearance-costs"],
    queryFn: async () => { const res = await api.get("/v1/finance/clearance"); return res.data; },
  });

  const handleDelete = async (id: number) => {
    if (!confirm("确定删除？")) return;
    try { await api.delete(`/v1/finance/clearance/${id}`); toast.success("已删除"); queryClient.invalidateQueries({ queryKey: ["clearance-costs", "finance-summary"] }); }
    catch (error: any) { toast.error(error.response?.data?.detail ?? "删除失败"); }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await api.post("/v1/finance/clearance", { invoice_id: Number(invoiceId), cost_date: costDate, clearance_fee: Number(clearanceFee), freight_fee: Number(freightFee), inspection_fee: Number(inspectionFee), quarantine_fee: 0, other_costs: Number(otherCosts), total_cost: totalCost });
      toast.success("清关运费创建成功");
      queryClient.invalidateQueries({ queryKey: ["clearance-costs", "finance-summary"] });
      setFormOpen(false);
    } catch (error: any) { toast.error(error.response?.data?.detail ?? "创建失败"); }
  };

  return (
    <div className="space-y-4">
      <div className="flex justify-end">
        <Button size="sm" onClick={() => setFormOpen(true)}><Plus className="h-4 w-4 mr-1" />新增费用</Button>
      </div>
      <Dialog open={formOpen} onOpenChange={setFormOpen}>
        <DialogContent className="max-w-[400px]">
          <DialogHeader><DialogTitle>新增清关运费</DialogTitle></DialogHeader>
          <form onSubmit={handleSubmit} className="space-y-3">
            <div><Label>发票ID</Label><Input type="number" value={invoiceId} onChange={e => setInvoiceId(e.target.value)} /></div>
            <div><Label>费用日期</Label><Input type="date" value={costDate} onChange={e => setCostDate(e.target.value)} /></div>
            <div className="grid grid-cols-2 gap-2">
              <div><Label>清关费</Label><Input type="number" value={clearanceFee} onChange={e => setClearanceFee(e.target.value)} /></div>
              <div><Label>运费</Label><Input type="number" value={freightFee} onChange={e => setFreightFee(e.target.value)} /></div>
            </div>
            <div className="grid grid-cols-2 gap-2">
              <div><Label>检验费</Label><Input type="number" value={inspectionFee} onChange={e => setInspectionFee(e.target.value)} /></div>
              <div><Label>其他</Label><Input type="number" value={otherCosts} onChange={e => setOtherCosts(e.target.value)} /></div>
            </div>
            <div className="bg-muted p-2 rounded text-sm flex justify-between font-semibold"><span>费用合计</span><span>¥{totalCost.toLocaleString(undefined, {minimumFractionDigits: 2})}</span></div>
            <DialogFooter><Button type="button" variant="outline" onClick={() => setFormOpen(false)}>取消</Button><Button type="submit">保存</Button></DialogFooter>
          </form>
        </DialogContent>
      </Dialog>
      <div className="border rounded-lg">
        <Table>
          <TableHeader><TableRow><TableHead>发票</TableHead><TableHead>日期</TableHead><TableHead>清关费</TableHead><TableHead>运费</TableHead><TableHead>合计</TableHead><TableHead className="w-[60px]"></TableHead></TableRow></TableHeader>
          <TableBody>
            {isLoading ? <TableRow><TableCell colSpan={6} className="text-center py-8">加载中...</TableCell></TableRow>
            : !data?.length ? <TableRow><TableCell colSpan={6} className="text-center py-8 text-muted-foreground">暂无数据</TableCell></TableRow>
            : data.map(r => (
              <TableRow key={r.id}><TableCell>{r.invoice_id}</TableCell><TableCell>{r.cost_date}</TableCell><TableCell>¥{Number(r.clearance_fee).toLocaleString()}</TableCell><TableCell>¥{Number(r.freight_fee).toLocaleString()}</TableCell><TableCell className="font-semibold">¥{Number(r.total_cost).toLocaleString()}</TableCell><TableCell><Button variant="ghost" size="icon" className="h-7 w-7 text-red-500" onClick={() => handleDelete(r.id)}><Trash2 className="h-3 w-3" /></Button></TableCell></TableRow>
            ))}
          </TableBody>
        </Table>
      </div>
    </div>
  );
}

// ==================== 交易流水 ====================

function TransactionsTab() {
  const queryClient = useQueryClient();
  const [formOpen, setFormOpen] = useState(false);
  const [date, setDate] = useState("");
  const [type, setType] = useState("expense");
  const [category, setCategory] = useState("other");
  const [amount, setAmount] = useState("");
  const [currency, setCurrency] = useState("CNY");
  const [counterparty, setCounterparty] = useState("");
  const [description, setDescription] = useState("");

  // 弹窗打开时重置
  React.useEffect(() => {
    if (formOpen) {
      setDate(""); setAmount(""); setCounterparty(""); setDescription("");
    }
  }, [formOpen]);

  const { data, isLoading } = useQuery<Transaction[]>({
    queryKey: ["transactions"],
    queryFn: async () => { const res = await api.get("/v1/finance/transactions"); return res.data; },
  });

  const handleDelete = async (id: number) => {
    if (!confirm("确定删除？")) return;
    try { await api.delete(`/v1/finance/transactions/${id}`); toast.success("已删除"); queryClient.invalidateQueries({ queryKey: ["transactions", "finance-summary"] }); }
    catch (error: any) { toast.error(error.response?.data?.detail ?? "删除失败"); }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await api.post("/v1/finance/transactions", { transaction_date: date, type, category, amount: Number(amount), currency, counterparty_name: counterparty || undefined, description: description || undefined });
      toast.success("交易记录创建成功");
      queryClient.invalidateQueries({ queryKey: ["transactions", "finance-summary"] });
      setFormOpen(false); setDate(""); setAmount(""); setCounterparty(""); setDescription("");
    } catch (error: any) { toast.error(error.response?.data?.detail ?? "创建失败"); }
  };

  return (
    <div className="space-y-4">
      <div className="flex justify-end">
        <Button size="sm" onClick={() => setFormOpen(true)}><Plus className="h-4 w-4 mr-1" />新增流水</Button>
      </div>
      <Dialog open={formOpen} onOpenChange={setFormOpen}>
        <DialogContent className="max-w-[400px]">
          <DialogHeader><DialogTitle>新增交易流水</DialogTitle></DialogHeader>
          <form onSubmit={handleSubmit} className="space-y-3">
            <div><Label>日期</Label><Input type="date" value={date} onChange={e => setDate(e.target.value)} /></div>
            <div className="grid grid-cols-2 gap-2">
              <div><Label>类型</Label>
                <Select value={type} onValueChange={(v) => setType(v ?? "")}>
                  <SelectTrigger><SelectValue /></SelectTrigger>
                  <SelectContent>{Object.entries(transactionTypeMap).map(([k,v]) => <SelectItem key={k} value={k}>{v}</SelectItem>)}</SelectContent>
                </Select>
              </div>
              <div><Label>分类</Label>
                <Select value={category} onValueChange={(v) => setCategory(v ?? "")}>
                  <SelectTrigger><SelectValue /></SelectTrigger>
                  <SelectContent>{Object.entries(transactionCategoryMap).map(([k,v]) => <SelectItem key={k} value={k}>{v}</SelectItem>)}</SelectContent>
                </Select>
              </div>
            </div>
            <div className="grid grid-cols-2 gap-2">
              <div><Label>金额</Label><Input type="number" value={amount} onChange={e => setAmount(e.target.value)} /></div>
              <div><Label>币种</Label><Input value={currency} onChange={e => setCurrency(e.target.value)} /></div>
            </div>
            <div><Label>对方名称</Label><Input value={counterparty} onChange={e => setCounterparty(e.target.value)} placeholder="可选" /></div>
            <div><Label>描述</Label><Input value={description} onChange={e => setDescription(e.target.value)} placeholder="可选" /></div>
            <DialogFooter><Button type="button" variant="outline" onClick={() => setFormOpen(false)}>取消</Button><Button type="submit">保存</Button></DialogFooter>
          </form>
        </DialogContent>
      </Dialog>
      <div className="border rounded-lg">
        <Table>
          <TableHeader><TableRow><TableHead>日期</TableHead><TableHead>类型</TableHead><TableHead>分类</TableHead><TableHead className="text-right">金额</TableHead><TableHead>币种</TableHead><TableHead>对方</TableHead><TableHead className="w-[60px]"></TableHead></TableRow></TableHeader>
          <TableBody>
            {isLoading ? <TableRow><TableCell colSpan={7} className="text-center py-8">加载中...</TableCell></TableRow>
            : !data?.length ? <TableRow><TableCell colSpan={7} className="text-center py-8 text-muted-foreground">暂无数据</TableCell></TableRow>
            : data.map(r => (
              <TableRow key={r.id}>
                <TableCell>{r.transaction_date}</TableCell>
                <TableCell>{transactionTypeMap[r.type] ?? r.type}</TableCell>
                <TableCell>{transactionCategoryMap[r.category] ?? r.category}</TableCell>
                <TableCell className="text-right font-medium">{Number(r.amount).toLocaleString()}</TableCell>
                <TableCell>{r.currency}</TableCell>
                <TableCell>{r.counterparty_name ?? "-"}</TableCell>
                <TableCell><Button variant="ghost" size="icon" className="h-7 w-7 text-red-500" onClick={() => handleDelete(r.id)}><Trash2 className="h-3 w-3" /></Button></TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>
    </div>
  );
}
