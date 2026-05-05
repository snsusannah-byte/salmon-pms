import { useState, useMemo } from "react";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
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
  DialogTrigger,
} from "@/components/ui/dialog";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { toast } from "sonner";
import {
  Loader2,
  Eye,
  ChevronLeft,
  ChevronRight,
  FileBarChart,
  FileSpreadsheet,
  FileText,
  TrendingUp,
  Package,
  DollarSign,
  ArrowDownLeft,
  ArrowUpRight,
  Printer,
} from "lucide-react";

// ==================== 工具函数 ====================

function fmt$(v: number | string | null | undefined) {
  const n = Number(v || 0);
  return `¥${n.toLocaleString("zh-CN", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

function fmtDate(d: string | null | undefined) {
  if (!d) return "-";
  return new Date(d).toLocaleDateString("zh-CN");
}

function clsProfit(v: number) {
  return v >= 0 ? "text-green-600" : "text-red-600";
}

// ==================== 分页组件 ====================

function SimplePagination({
  current,
  total,
  pageSize,
  onChange,
}: {
  current: number;
  total: number;
  pageSize: number;
  onChange: (page: number) => void;
}) {
  const totalPages = Math.max(1, Math.ceil(total / pageSize));
  if (totalPages <= 1) return null;
  return (
    <div className="flex items-center justify-between px-2 py-3">
      <span className="text-xs text-muted-foreground">
        第 {current + 1} / {totalPages} 页，共 {total} 条
      </span>
      <div className="flex gap-1">
        <Button
          variant="outline"
          size="sm"
          disabled={current === 0}
          onClick={() => onChange(current - 1)}
        >
          <ChevronLeft className="h-3 w-3" />
        </Button>
        <Button
          variant="outline"
          size="sm"
          disabled={current >= totalPages - 1}
          onClick={() => onChange(current + 1)}
        >
          <ChevronRight className="h-3 w-3" />
        </Button>
      </div>
    </div>
  );
}

// ==================== 日期筛选 ====================

function DateFilter({
  startDate,
  endDate,
  onStartChange,
  onEndChange,
  onSearch,
}: {
  startDate: string;
  endDate: string;
  onStartChange: (v: string) => void;
  onEndChange: (v: string) => void;
  onSearch: () => void;
}) {
  return (
    <div className="flex flex-wrap items-end gap-3 mb-4">
      <div className="grid gap-1">
        <Label className="text-xs">开始日期</Label>
        <Input
          type="date"
          className="h-8 w-40"
          value={startDate}
          onChange={(e) => onStartChange(e.target.value)}
        />
      </div>
      <div className="grid gap-1">
        <Label className="text-xs">结束日期</Label>
        <Input
          type="date"
          className="h-8 w-40"
          value={endDate}
          onChange={(e) => onEndChange(e.target.value)}
        />
      </div>
      <Button size="sm" className="h-8" onClick={onSearch}>
        查询
      </Button>
    </div>
  );
}

// ==================== Tab 1: 批次财报 ====================

function BatchReportsTab() {
  const [page, setPage] = useState(0);
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");
  const [searchKey, setSearchKey] = useState("");
  const [detailId, setDetailId] = useState<number | null>(null);

  const { data, isLoading } = useQuery({
    queryKey: ["reports-batches", page, startDate, endDate, searchKey],
    queryFn: async () => {
      const params = new URLSearchParams({
        skip: String(page * 30),
        limit: "30",
      });
      if (startDate) params.set("start_date", startDate);
      if (endDate) params.set("end_date", endDate);
      const res = await api.get(`/v1/reports/batches?${params}`);
      return res.data as {
        total: number;
        items: any[];
        skip: number;
        limit: number;
      };
    },
  });

  const { data: detailData } = useQuery({
    queryKey: ["batch-report-detail", detailId],
    queryFn: async () => {
      if (!detailId) return null;
      const res = await api.get(`/v1/reports/batches/${detailId}`);
      return res.data;
    },
    enabled: !!detailId,
  });

  const filtered = useMemo(() => {
    if (!data) return [];
    if (!searchKey) return data.items;
    return data.items.filter((item) =>
      (item.batch_name || "").toLowerCase().includes(searchKey.toLowerCase()) ||
      (item.batch_code || "").toLowerCase().includes(searchKey.toLowerCase())
    );
  }, [data, searchKey]);

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap items-end gap-3">
        <DateFilter
          startDate={startDate}
          endDate={endDate}
          onStartChange={setStartDate}
          onEndChange={setEndDate}
          onSearch={() => setPage(0)}
        />
        <div className="ml-auto">
          <Input
            placeholder="搜索批次名称/编号"
            className="h-8 w-48"
            value={searchKey}
            onChange={(e) => { setSearchKey(e.target.value); setPage(0); }}
          />
        </div>
      </div>

      <Card>
        <CardContent className="p-0">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead className="text-xs">批次编号</TableHead>
                <TableHead className="text-xs">批次名称</TableHead>
                <TableHead className="text-xs">日期</TableHead>
                <TableHead className="text-xs">状态</TableHead>
                <TableHead className="text-xs text-right">采购成本(CNY)</TableHead>
                <TableHead className="text-xs text-right">销售净额(CNY)</TableHead>
                <TableHead className="text-xs text-right">净利润(CNY)</TableHead>
                <TableHead className="text-xs text-right">利润率</TableHead>
                <TableHead className="text-xs text-center">操作</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {isLoading ? (
                <TableRow>
                  <TableCell colSpan={9} className="text-center py-8">
                    <Loader2 className="h-5 w-5 animate-spin mx-auto" />
                  </TableCell>
                </TableRow>
              ) : filtered.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={9} className="text-center text-muted-foreground py-8">
                    暂无数据
                  </TableCell>
                </TableRow>
              ) : (
                filtered.map((item) => (
                  <TableRow key={item.batch_id}>
                    <TableCell className="text-xs font-medium">{item.batch_code}</TableCell>
                    <TableCell className="text-xs">{item.batch_name}</TableCell>
                    <TableCell className="text-xs">{fmtDate(item.batch_date)}</TableCell>
                    <TableCell>
                      <Badge variant="outline" className="text-[10px] h-5">
                        {item.status}
                      </Badge>
                    </TableCell>
                    <TableCell className="text-xs text-right">{fmt$(item.total_purchase_cny)}</TableCell>
                    <TableCell className="text-xs text-right">{fmt$(item.total_sales_net)}</TableCell>
                    <TableCell className={cn("text-xs text-right font-medium", clsProfit(Number(item.net_profit)))}>
                      {fmt$(item.net_profit)}
                    </TableCell>
                    <TableCell className={cn("text-xs text-right", clsProfit(Number(item.profit_margin || 0)))}>
                      {item.profit_margin !== null && item.profit_margin !== undefined
                        ? `${Number(item.profit_margin).toFixed(1)}%`
                        : "-"}
                    </TableCell>
                    <TableCell className="text-center">
                      <Dialog>
                        <DialogTrigger>
                          <Button variant="ghost" size="sm" className="h-7 px-2" onClick={() => setDetailId(item.batch_id)}>
                            <Eye className="h-3.5 w-3.5" />
                          </Button>
                        </DialogTrigger>
                        <DialogContent className="max-w-[900px] max-h-[85vh] overflow-y-auto">
                          <DialogHeader>
                            <DialogTitle className="text-base">批次财报详情</DialogTitle>
                          </DialogHeader>
                          {detailData ? (
                            <div className="space-y-4 text-sm">
                              <div className="grid grid-cols-3 gap-3 text-xs">
                                <div><span className="text-muted-foreground">批次:</span> {detailData.batch_code}</div>
                                <div><span className="text-muted-foreground">名称:</span> {detailData.batch_name}</div>
                                <div><span className="text-muted-foreground">日期:</span> {fmtDate(detailData.batch_date)}</div>
                              </div>
                              <div className="border rounded-lg overflow-hidden">
                                <Table>
                                  <TableHeader>
                                    <TableRow className="bg-muted/50">
                                      <TableHead className="text-xs">发票号</TableHead>
                                      <TableHead className="text-xs text-right">采购金额(CNY)</TableHead>
                                      <TableHead className="text-xs text-right">税费(CNY)</TableHead>
                                      <TableHead className="text-xs text-right">清关费(CNY)</TableHead>
                                      <TableHead className="text-xs text-right">购汇(CNY)</TableHead>
                                      <TableHead className="text-xs text-right">销售净额(CNY)</TableHead>
                                      <TableHead className="text-xs text-right">净利润(CNY)</TableHead>
                                    </TableRow>
                                  </TableHeader>
                                  <TableBody>
                                    {(detailData.invoices || []).map((inv: any) => (
                                      <TableRow key={inv.invoice_id}>
                                        <TableCell className="text-xs">{inv.invoice_no}</TableCell>
                                        <TableCell className="text-xs text-right">{fmt$(inv.purchase_cost_cny)}</TableCell>
                                        <TableCell className="text-xs text-right">{fmt$(inv.import_duty + inv.import_vat)}</TableCell>
                                        <TableCell className="text-xs text-right">{fmt$(inv.clearance_cost)}</TableCell>
                                        <TableCell className="text-xs text-right">{fmt$(inv.exchange_payment)}</TableCell>
                                        <TableCell className="text-xs text-right">{fmt$(inv.sales_net)}</TableCell>
                                        <TableCell className={cn("text-xs text-right font-medium", clsProfit(Number(inv.net_profit)))}>
                                          {fmt$(inv.net_profit)}
                                        </TableCell>
                                      </TableRow>
                                    ))}
                                  </TableBody>
                                </Table>
                              </div>
                              <div className="flex justify-end gap-4 text-xs font-medium">
                                <span>总采购: {fmt$(detailData.total_purchase_cny)}</span>
                                <span>总销售: {fmt$(detailData.total_sales_net)}</span>
                                <span className={clsProfit(Number(detailData.net_profit))}>
                                  净利润: {fmt$(detailData.net_profit)}
                                </span>
                              </div>
                            </div>
                          ) : (
                            <div className="py-8 text-center">
                              <Loader2 className="h-5 w-5 animate-spin mx-auto" />
                            </div>
                          )}
                        </DialogContent>
                      </Dialog>
                    </TableCell>
                  </TableRow>
                ))
              )}
            </TableBody>
          </Table>
          <SimplePagination
            current={page}
            total={data?.total || 0}
            pageSize={30}
            onChange={setPage}
          />
        </CardContent>
      </Card>
    </div>
  );
}

// ==================== Tab 2: 单票财报 ====================

function InvoiceReportsTab() {
  const [page, setPage] = useState(0);
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");
  const [searchKey, setSearchKey] = useState("");
  const [detailId, setDetailId] = useState<number | null>(null);

  const { data, isLoading } = useQuery({
    queryKey: ["reports-invoices", page, startDate, endDate, searchKey],
    queryFn: async () => {
      const params = new URLSearchParams({
        skip: String(page * 30),
        limit: "30",
      });
      if (startDate) params.set("start_date", startDate);
      if (endDate) params.set("end_date", endDate);
      const res = await api.get(`/v1/reports/invoices?${params}`);
      return res.data as { total: number; items: any[]; skip: number; limit: number };
    },
  });

  const { data: detailData } = useQuery({
    queryKey: ["invoice-report-detail", detailId],
    queryFn: async () => {
      if (!detailId) return null;
      const res = await api.get(`/v1/reports/invoices/${detailId}`);
      return res.data;
    },
    enabled: !!detailId,
  });

  const filtered = useMemo(() => {
    if (!data) return [];
    if (!searchKey) return data.items;
    return data.items.filter((item) =>
      (item.invoice_no || "").toLowerCase().includes(searchKey.toLowerCase()) ||
      (item.exporter_name || "").toLowerCase().includes(searchKey.toLowerCase()) ||
      (item.processing_plant_name || "").toLowerCase().includes(searchKey.toLowerCase())
    );
  }, [data, searchKey]);

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap items-end gap-3">
        <DateFilter
          startDate={startDate}
          endDate={endDate}
          onStartChange={setStartDate}
          onEndChange={setEndDate}
          onSearch={() => setPage(0)}
        />
        <div className="ml-auto">
          <Input
            placeholder="搜索发票号/供应商"
            className="h-8 w-48"
            value={searchKey}
            onChange={(e) => { setSearchKey(e.target.value); setPage(0); }}
          />
        </div>
      </div>

      <Card>
        <CardContent className="p-0">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead className="text-xs">发票号</TableHead>
                <TableHead className="text-xs">日期</TableHead>
                <TableHead className="text-xs">供应商</TableHead>
                <TableHead className="text-xs">批次</TableHead>
                <TableHead className="text-xs text-right">采购金额(USD)</TableHead>
                <TableHead className="text-xs text-right">采购成本(CNY)</TableHead>
                <TableHead className="text-xs text-right">销售净额(CNY)</TableHead>
                <TableHead className="text-xs text-right">净利润(CNY)</TableHead>
                <TableHead className="text-xs text-right">利润率</TableHead>
                <TableHead className="text-xs text-center">操作</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {isLoading ? (
                <TableRow>
                  <TableCell colSpan={10} className="text-center py-8">
                    <Loader2 className="h-5 w-5 animate-spin mx-auto" />
                  </TableCell>
                </TableRow>
              ) : filtered.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={10} className="text-center text-muted-foreground py-8">
                    暂无数据
                  </TableCell>
                </TableRow>
              ) : (
                filtered.map((item) => (
                  <TableRow key={item.invoice_id}>
                    <TableCell className="text-xs font-medium">{item.invoice_no}</TableCell>
                    <TableCell className="text-xs">{fmtDate(item.invoice_date)}</TableCell>
                    <TableCell className="text-xs">{item.processing_plant_name || item.exporter_name || "-"}</TableCell>
                    <TableCell className="text-xs">{item.batch_code || "-"}</TableCell>
                    <TableCell className="text-xs text-right">${Number(item.total_amount_usd || 0).toLocaleString()}</TableCell>
                    <TableCell className="text-xs text-right">{fmt$(item.purchase_cost_cny)}</TableCell>
                    <TableCell className="text-xs text-right">{fmt$(item.sales_net)}</TableCell>
                    <TableCell className={cn("text-xs text-right font-medium", clsProfit(Number(item.net_profit)))}>
                      {fmt$(item.net_profit)}
                    </TableCell>
                    <TableCell className={cn("text-xs text-right", clsProfit(Number(item.profit_margin || 0)))}>
                      {item.profit_margin !== null && item.profit_margin !== undefined
                        ? `${Number(item.profit_margin).toFixed(1)}%`
                        : "-"}
                    </TableCell>
                    <TableCell className="text-center">
                      <Dialog>
                        <DialogTrigger>
                          <Button variant="ghost" size="sm" className="h-7 px-2" onClick={() => setDetailId(item.invoice_id)}>
                            <Eye className="h-3.5 w-3.5" />
                          </Button>
                        </DialogTrigger>
                        <DialogContent className="max-w-[900px] max-h-[85vh] overflow-y-auto">
                          <DialogHeader>
                            <DialogTitle className="text-base">单票财报详情</DialogTitle>
                          </DialogHeader>
                          {detailData ? (
                            <div className="space-y-4 text-sm">
                              <div className="grid grid-cols-3 gap-3 text-xs">
                                <div><span className="text-muted-foreground">发票:</span> {detailData.invoice_no}</div>
                                <div><span className="text-muted-foreground">日期:</span> {fmtDate(detailData.invoice_date)}</div>
                                <div><span className="text-muted-foreground">批次:</span> {detailData.batch_name || "-"}</div>
                              </div>
                              <div className="border rounded-lg overflow-hidden">
                                <Table>
                                  <TableHeader>
                                    <TableRow className="bg-muted/50">
                                      <TableHead className="text-xs">日期</TableHead>
                                      <TableHead className="text-xs">客户</TableHead>
                                      <TableHead className="text-xs">规格</TableHead>
                                      <TableHead className="text-xs text-right">重量(kg)</TableHead>
                                      <TableHead className="text-xs text-right">单价</TableHead>
                                      <TableHead className="text-xs text-right">毛额(CNY)</TableHead>
                                      <TableHead className="text-xs text-right">净额(CNY)</TableHead>
                                    </TableRow>
                                  </TableHeader>
                                  <TableBody>
                                    {(detailData.sales || []).map((sale: any, idx: number) => (
                                      <TableRow key={idx}>
                                        <TableCell className="text-xs">{fmtDate(sale.sale_date)}</TableCell>
                                        <TableCell className="text-xs">{sale.customer_name || "-"}</TableCell>
                                        <TableCell className="text-xs">{sale.spec || "-"}</TableCell>
                                        <TableCell className="text-xs text-right">{Number(sale.weight_kg || 0).toLocaleString()}</TableCell>
                                        <TableCell className="text-xs text-right">{fmt$(sale.unit_price)}</TableCell>
                                        <TableCell className="text-xs text-right">{fmt$(sale.gross_amount)}</TableCell>
                                        <TableCell className="text-xs text-right font-medium">{fmt$(sale.net_amount)}</TableCell>
                                      </TableRow>
                                    ))}
                                  </TableBody>
                                </Table>
                              </div>
                              <div className="flex justify-end gap-4 text-xs font-medium">
                                <span>采购成本: {fmt$(detailData.purchase_cost_cny)}</span>
                                <span>总销售: {fmt$(detailData.total_sales_net)}</span>
                                <span className={clsProfit(Number(detailData.net_profit))}>
                                  净利润: {fmt$(detailData.net_profit)}
                                </span>
                              </div>
                            </div>
                          ) : (
                            <div className="py-8 text-center">
                              <Loader2 className="h-5 w-5 animate-spin mx-auto" />
                            </div>
                          )}
                        </DialogContent>
                      </Dialog>
                    </TableCell>
                  </TableRow>
                ))
              )}
            </TableBody>
          </Table>
          <SimplePagination
            current={page}
            total={data?.total || 0}
            pageSize={30}
            onChange={setPage}
          />
        </CardContent>
      </Card>
    </div>
  );
}

// ==================== Tab 3: 应收对账单 ====================

function ReceivableStatementsTab() {
  const [page, setPage] = useState(0);
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");
  const [detailCustomer, setDetailCustomer] = useState<any>(null);

  const { data, isLoading } = useQuery({
    queryKey: ["reports-receivable", page, startDate, endDate],
    queryFn: async () => {
      const params = new URLSearchParams({
        skip: String(page * 30),
        limit: "30",
      });
      if (startDate) params.set("start_date", startDate);
      if (endDate) params.set("end_date", endDate);
      const res = await api.get(`/v1/reports/receivable-statements?${params}`);
      return res.data as {
        total: number;
        items: any[];
        total_receivable: number;
        start_date: string;
        end_date: string;
      };
    },
  });

  return (
    <div className="space-y-3">
      <DateFilter
        startDate={startDate}
        endDate={endDate}
        onStartChange={setStartDate}
        onEndChange={setEndDate}
        onSearch={() => setPage(0)}
      />

      {data && (
        <div className="flex gap-4 text-xs text-muted-foreground">
          <span>周期: {data.start_date || "全部"} ~ {data.end_date || "全部"}</span>
          <span className="font-medium text-foreground">总应收: {fmt$(data.total_receivable)}</span>
        </div>
      )}

      <Card>
        <CardContent className="p-0">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead className="text-xs">客户名称</TableHead>
                <TableHead className="text-xs">客户代码</TableHead>
                <TableHead className="text-xs text-right">期初欠款(CNY)</TableHead>
                <TableHead className="text-xs text-right">本期销售(CNY)</TableHead>
                <TableHead className="text-xs text-right">本期收款(CNY)</TableHead>
                <TableHead className="text-xs text-right">期末欠款(CNY)</TableHead>
                <TableHead className="text-xs text-center">操作</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {isLoading ? (
                <TableRow>
                  <TableCell colSpan={7} className="text-center py-8">
                    <Loader2 className="h-5 w-5 animate-spin mx-auto" />
                  </TableCell>
                </TableRow>
              ) : !data || data.items.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={7} className="text-center text-muted-foreground py-8">
                    暂无数据
                  </TableCell>
                </TableRow>
              ) : (
                data.items.map((item) => (
                  <TableRow key={item.customer_id}>
                    <TableCell className="text-xs font-medium">{item.customer_name}</TableCell>
                    <TableCell className="text-xs">{item.customer_code || "-"}</TableCell>
                    <TableCell className="text-xs text-right">{fmt$(item.opening_balance)}</TableCell>
                    <TableCell className="text-xs text-right text-green-600">+{fmt$(item.current_sales)}</TableCell>
                    <TableCell className="text-xs text-right text-blue-600">-{fmt$(item.current_receipts)}</TableCell>
                    <TableCell className={cn("text-xs text-right font-medium", Number(item.closing_balance) > 0 ? "text-red-600" : "text-green-600")}>
                      {fmt$(item.closing_balance)}
                    </TableCell>
                    <TableCell className="text-center">
                      <Dialog>
                        <DialogTrigger>
                          <Button variant="ghost" size="sm" className="h-7 px-2" onClick={() => setDetailCustomer(item)}>
                            <Eye className="h-3.5 w-3.5" />
                          </Button>
                        </DialogTrigger>
                        <DialogContent className="max-w-[800px] max-h-[85vh] overflow-y-auto">
                          <DialogHeader>
                            <DialogTitle className="text-base">应收对账明细 - {item.customer_name}</DialogTitle>
                          </DialogHeader>
                          <div className="space-y-3 text-sm">
                            <div className="grid grid-cols-4 gap-3 text-xs bg-muted/50 p-3 rounded-lg">
                              <div><span className="text-muted-foreground">期初:</span> {fmt$(item.opening_balance)}</div>
                              <div><span className="text-muted-foreground">本期销售:</span> +{fmt$(item.current_sales)}</div>
                              <div><span className="text-muted-foreground">本期收款:</span> -{fmt$(item.current_receipts)}</div>
                              <div className={cn("font-medium", Number(item.closing_balance) > 0 ? "text-red-600" : "text-green-600")}>
                                期末: {fmt$(item.closing_balance)}
                              </div>
                            </div>
                            <div className="border rounded-lg overflow-hidden">
                              <Table>
                                <TableHeader>
                                  <TableRow className="bg-muted/50">
                                    <TableHead className="text-xs">日期</TableHead>
                                    <TableHead className="text-xs">类型</TableHead>
                                    <TableHead className="text-xs">单号</TableHead>
                                    <TableHead className="text-xs">说明</TableHead>
                                    <TableHead className="text-xs text-right">借方(+)</TableHead>
                                    <TableHead className="text-xs text-right">贷方(-)</TableHead>
                                    <TableHead className="text-xs text-right">余额</TableHead>
                                  </TableRow>
                                </TableHeader>
                                <TableBody>
                                  {(item.details || []).map((d: any, idx: number) => (
                                    <TableRow key={idx}>
                                      <TableCell className="text-xs">{fmtDate(d.date)}</TableCell>
                                      <TableCell className="text-xs">
                                        {d.type === "sale" ? "销售" : d.type === "receipt" ? "收款" : "期初"}
                                      </TableCell>
                                      <TableCell className="text-xs">{d.sale_no || "-"}</TableCell>
                                      <TableCell className="text-xs">{d.description || "-"}</TableCell>
                                      <TableCell className="text-xs text-right text-green-600">
                                        {Number(d.debit || 0) > 0 ? fmt$(d.debit) : ""}
                                      </TableCell>
                                      <TableCell className="text-xs text-right text-blue-600">
                                        {Number(d.credit || 0) > 0 ? fmt$(d.credit) : ""}
                                      </TableCell>
                                      <TableCell className={cn("text-xs text-right font-medium", Number(d.balance) > 0 ? "text-red-600" : "")}>
                                        {fmt$(d.balance)}
                                      </TableCell>
                                    </TableRow>
                                  ))}
                                </TableBody>
                              </Table>
                            </div>
                          </div>
                        </DialogContent>
                      </Dialog>
                    </TableCell>
                  </TableRow>
                ))
              )}
            </TableBody>
          </Table>
          <SimplePagination
            current={page}
            total={data?.total || 0}
            pageSize={30}
            onChange={setPage}
          />
        </CardContent>
      </Card>
    </div>
  );
}

// ==================== Tab 4: 应付对账单 ====================

function PayableStatementsTab() {
  const [page, setPage] = useState(0);
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");

  const { data, isLoading } = useQuery({
    queryKey: ["reports-payable", page, startDate, endDate],
    queryFn: async () => {
      const params = new URLSearchParams({
        skip: String(page * 30),
        limit: "30",
      });
      if (startDate) params.set("start_date", startDate);
      if (endDate) params.set("end_date", endDate);
      const res = await api.get(`/v1/reports/payable-statements?${params}`);
      return res.data as {
        total: number;
        items: any[];
        total_payable: number;
        start_date: string;
        end_date: string;
      };
    },
  });

  return (
    <div className="space-y-3">
      <DateFilter
        startDate={startDate}
        endDate={endDate}
        onStartChange={setStartDate}
        onEndChange={setEndDate}
        onSearch={() => setPage(0)}
      />

      {data && (
        <div className="flex gap-4 text-xs text-muted-foreground">
          <span>周期: {data.start_date || "全部"} ~ {data.end_date || "全部"}</span>
          <span className="font-medium text-foreground">总应付: {fmt$(data.total_payable)}</span>
        </div>
      )}

      <Card>
        <CardContent className="p-0">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead className="text-xs">供应商名称</TableHead>
                <TableHead className="text-xs">类型</TableHead>
                <TableHead className="text-xs text-right">期初欠款(CNY)</TableHead>
                <TableHead className="text-xs text-right">本期采购(CNY)</TableHead>
                <TableHead className="text-xs text-right">本期费用(CNY)</TableHead>
                <TableHead className="text-xs text-right">本期付款(CNY)</TableHead>
                <TableHead className="text-xs text-right">期末欠款(CNY)</TableHead>
                <TableHead className="text-xs text-center">操作</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {isLoading ? (
                <TableRow>
                  <TableCell colSpan={8} className="text-center py-8">
                    <Loader2 className="h-5 w-5 animate-spin mx-auto" />
                  </TableCell>
                </TableRow>
              ) : !data || data.items.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={8} className="text-center text-muted-foreground py-8">
                    暂无数据
                  </TableCell>
                </TableRow>
              ) : (
                data.items.map((item) => (
                  <TableRow key={item.supplier_id}>
                    <TableCell className="text-xs font-medium">{item.supplier_name}</TableCell>
                    <TableCell className="text-xs">
                      {item.supplier_type === "processing_plant" ? "加工厂" : item.supplier_type === "exporter" ? "出口商" : item.supplier_type}
                    </TableCell>
                    <TableCell className="text-xs text-right">{fmt$(item.opening_balance)}</TableCell>
                    <TableCell className="text-xs text-right text-red-600">+{fmt$(item.current_purchase)}</TableCell>
                    <TableCell className="text-xs text-right text-red-600">+{fmt$(item.current_expenses)}</TableCell>
                    <TableCell className="text-xs text-right text-green-600">-{fmt$(item.current_payments)}</TableCell>
                    <TableCell className={cn("text-xs text-right font-medium", Number(item.closing_balance) > 0 ? "text-red-600" : "text-green-600")}>
                      {fmt$(item.closing_balance)}
                    </TableCell>
                    <TableCell className="text-center">
                      <Dialog>
                        <DialogTrigger>
                          <Button variant="ghost" size="sm" className="h-7 px-2">
                            <Eye className="h-3.5 w-3.5" />
                          </Button>
                        </DialogTrigger>
                        <DialogContent className="max-w-[800px] max-h-[85vh] overflow-y-auto">
                          <DialogHeader>
                            <DialogTitle className="text-base">应付对账明细 - {item.supplier_name}</DialogTitle>
                          </DialogHeader>
                          <div className="space-y-3 text-sm">
                            <div className="grid grid-cols-5 gap-3 text-xs bg-muted/50 p-3 rounded-lg">
                              <div><span className="text-muted-foreground">期初:</span> {fmt$(item.opening_balance)}</div>
                              <div><span className="text-muted-foreground">采购:</span> +{fmt$(item.current_purchase)}</div>
                              <div><span className="text-muted-foreground">费用:</span> +{fmt$(item.current_expenses)}</div>
                              <div><span className="text-muted-foreground">付款:</span> -{fmt$(item.current_payments)}</div>
                              <div className={cn("font-medium", Number(item.closing_balance) > 0 ? "text-red-600" : "text-green-600")}>
                                期末: {fmt$(item.closing_balance)}
                              </div>
                            </div>
                            <div className="border rounded-lg overflow-hidden">
                              <Table>
                                <TableHeader>
                                  <TableRow className="bg-muted/50">
                                    <TableHead className="text-xs">日期</TableHead>
                                    <TableHead className="text-xs">类型</TableHead>
                                    <TableHead className="text-xs">发票号</TableHead>
                                    <TableHead className="text-xs">说明</TableHead>
                                    <TableHead className="text-xs text-right">借方(+)</TableHead>
                                    <TableHead className="text-xs text-right">贷方(-)</TableHead>
                                    <TableHead className="text-xs text-right">余额</TableHead>
                                  </TableRow>
                                </TableHeader>
                                <TableBody>
                                  {(item.details || []).map((d: any, idx: number) => (
                                    <TableRow key={idx}>
                                      <TableCell className="text-xs">{fmtDate(d.date)}</TableCell>
                                      <TableCell className="text-xs">
                                        {d.type === "invoice" ? "采购" : d.type === "exchange" ? "付款" : "期初"}
                                      </TableCell>
                                      <TableCell className="text-xs">{d.invoice_no || "-"}</TableCell>
                                      <TableCell className="text-xs">{d.description || "-"}</TableCell>
                                      <TableCell className="text-xs text-right text-red-600">
                                        {Number(d.debit || 0) > 0 ? fmt$(d.debit) : ""}
                                      </TableCell>
                                      <TableCell className="text-xs text-right text-green-600">
                                        {Number(d.credit || 0) > 0 ? fmt$(d.credit) : ""}
                                      </TableCell>
                                      <TableCell className={cn("text-xs text-right font-medium", Number(d.balance) > 0 ? "text-red-600" : "")}>
                                        {fmt$(d.balance)}
                                      </TableCell>
                                    </TableRow>
                                  ))}
                                </TableBody>
                              </Table>
                            </div>
                          </div>
                        </DialogContent>
                      </Dialog>
                    </TableCell>
                  </TableRow>
                ))
              )}
            </TableBody>
          </Table>
          <SimplePagination
            current={page}
            total={data?.total || 0}
            pageSize={30}
            onChange={setPage}
          />
        </CardContent>
      </Card>
    </div>
  );
}

// ==================== Tab 5: 三大报表 ====================

function FinancialStatementsTab() {
  const [periodType, setPeriodType] = useState("current_quarter");
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");
  const [retailRevenue, setRetailRevenue] = useState("");
  const [retailCost, setRetailCost] = useState("");

  const { data, isLoading } = useQuery({
    queryKey: ["financial-statements", periodType, startDate, endDate, retailRevenue, retailCost],
    queryFn: async () => {
      const params = new URLSearchParams({ period_type: periodType });
      if (periodType === "custom") {
        if (startDate) params.set("start_date", startDate);
        if (endDate) params.set("end_date", endDate);
      }
      if (retailRevenue) params.set("retail_revenue", retailRevenue);
      if (retailCost) params.set("retail_cost", retailCost);
      const res = await api.get(`/v1/reports/financial-statements?${params}`);
      return res.data as any;
    },
  });

  const periodOptions = [
    { value: "current_quarter", label: "本季度" },
    { value: "last_quarter", label: "上季度" },
    { value: "first_half", label: "上半年" },
    { value: "second_half", label: "下半年" },
    { value: "current_year", label: "本年度" },
    { value: "last_year", label: "上年度" },
    { value: "custom", label: "自定义" },
  ];

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-end gap-3">
        <div className="grid gap-1">
          <Label className="text-xs">报表周期</Label>
          <select
            className="h-8 w-32 rounded-md border border-input bg-background px-2 text-xs"
            value={periodType}
            onChange={(e) => setPeriodType(e.target.value)}
          >
            {periodOptions.map((o) => (
              <option key={o.value} value={o.value}>{o.label}</option>
            ))}
          </select>
        </div>
        {periodType === "custom" && (
          <>
            <div className="grid gap-1">
              <Label className="text-xs">开始日期</Label>
              <Input type="date" className="h-8 w-40" value={startDate} onChange={(e) => setStartDate(e.target.value)} />
            </div>
            <div className="grid gap-1">
              <Label className="text-xs">结束日期</Label>
              <Input type="date" className="h-8 w-40" value={endDate} onChange={(e) => setEndDate(e.target.value)} />
            </div>
          </>
        )}
        <div className="grid gap-1">
          <Label className="text-xs">零售收入(可选)</Label>
          <Input type="number" className="h-8 w-32" placeholder="0" value={retailRevenue} onChange={(e) => setRetailRevenue(e.target.value)} />
        </div>
        <div className="grid gap-1">
          <Label className="text-xs">零售成本(可选)</Label>
          <Input type="number" className="h-8 w-32" placeholder="0" value={retailCost} onChange={(e) => setRetailCost(e.target.value)} />
        </div>
      </div>

      {data?.meta && (
        <div className="text-xs text-muted-foreground flex items-center gap-2">
          <span className="font-medium text-foreground">{data.meta.company_name}</span>
          <span>|</span>
          <span>{data.meta.period_label}</span>
          <span>|</span>
          <span>生成时间: {data.meta.generated_at}</span>
          <Button variant="ghost" size="sm" className="h-6 ml-auto" onClick={() => window.print()}>
            <Printer className="h-3 w-3 mr-1" /> 打印
          </Button>
        </div>
      )}

      {isLoading ? (
        <div className="py-12 text-center">
          <Loader2 className="h-6 w-6 animate-spin mx-auto" />
          <p className="text-sm text-muted-foreground mt-2">正在计算财务报表...</p>
        </div>
      ) : data ? (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 print:grid-cols-1">
          {/* 利润表 */}
          <Card className="print:shadow-none print:border-black">
            <CardHeader className="pb-2">
              <CardTitle className="text-base text-center">{data.income_statement.title}</CardTitle>
              <p className="text-xs text-center text-muted-foreground">{data.income_statement.subtitle}</p>
            </CardHeader>
            <CardContent className="pt-0">
              <Table>
                <TableBody>
                  {(data.income_statement.items || []).map((item: any, idx: number) => (
                    <TableRow key={idx} className={cn(
                      "border-0",
                      item.is_spacer ? "h-2" : "",
                      item.is_total ? "border-t-2 border-black font-bold" : "",
                      item.is_highlight ? "bg-yellow-50 font-semibold" : "",
                      item.is_section ? "border-t border-gray-300" : ""
                    )}>
                      <TableCell className={cn(
                        "text-xs py-1",
                        item.is_header ? "font-semibold" : "",
                        item.is_deduction ? "text-red-600" : "",
                        item.indent === 1 ? "pl-6" : item.indent === 2 ? "pl-10" : ""
                      )}>
                        {item.label}
                        {item.note && <span className="text-[10px] text-muted-foreground ml-1">({item.note})</span>}
                      </TableCell>
                      <TableCell className={cn(
                        "text-xs text-right py-1 font-mono",
                        item.is_deduction ? "text-red-600" : "",
                        item.is_total ? "font-bold" : ""
                      )}>
                        {item.amount !== null && item.amount !== undefined ? fmt$(item.amount) : ""}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
              <div className="mt-3 text-xs text-muted-foreground text-center">
                利润率: {data.income_statement.summary?.profit_margin || 0}%
              </div>
            </CardContent>
          </Card>

          {/* 资产负债表 */}
          <Card className="print:shadow-none print:border-black">
            <CardHeader className="pb-2">
              <CardTitle className="text-base text-center">{data.balance_sheet.title}</CardTitle>
              <p className="text-xs text-center text-muted-foreground">{data.balance_sheet.subtitle}</p>
            </CardHeader>
            <CardContent className="pt-0">
              <Table>
                <TableBody>
                  {(data.balance_sheet.items || []).map((item: any, idx: number) => (
                    <TableRow key={idx} className={cn(
                      "border-0",
                      item.is_spacer ? "h-2" : "",
                      item.is_total ? "border-t-2 border-black font-bold" : "",
                      item.is_highlight ? "bg-yellow-50 font-semibold" : "",
                      item.is_section ? "border-t border-gray-300" : ""
                    )}>
                      <TableCell className={cn(
                        "text-xs py-1",
                        item.is_header ? "font-semibold" : "",
                        item.is_deduction ? "text-red-600" : "",
                        item.indent === 1 ? "pl-6" : ""
                      )}>
                        {item.label}
                        {item.note && <span className="text-[10px] text-muted-foreground ml-1">({item.note})</span>}
                      </TableCell>
                      <TableCell className={cn(
                        "text-xs text-right py-1 font-mono",
                        item.is_deduction ? "text-red-600" : "",
                        item.is_total ? "font-bold" : ""
                      )}>
                        {item.amount !== null && item.amount !== undefined ? fmt$(item.amount) : ""}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
              {data.balance_sheet.customer_debts && data.balance_sheet.customer_debts.length > 0 && (
                <div className="mt-3">
                  <p className="text-xs font-medium mb-1">TOP 5 欠款客户</p>
                  <div className="text-xs space-y-0.5">
                    {data.balance_sheet.customer_debts.map((c: any) => (
                      <div key={c.customer_id} className="flex justify-between">
                        <span>{c.customer_name}</span>
                        <span className="text-red-600">{fmt$(c.unpaid)}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </CardContent>
          </Card>

          {/* 现金流量表 */}
          <Card className="print:shadow-none print:border-black">
            <CardHeader className="pb-2">
              <CardTitle className="text-base text-center">{data.cash_flow.title}</CardTitle>
              <p className="text-xs text-center text-muted-foreground">{data.cash_flow.subtitle}</p>
            </CardHeader>
            <CardContent className="pt-0">
              <Table>
                <TableBody>
                  {(data.cash_flow.items || []).map((item: any, idx: number) => (
                    <TableRow key={idx} className={cn(
                      "border-0",
                      item.is_spacer ? "h-2" : "",
                      item.is_total ? "border-t-2 border-black font-bold" : "",
                      item.is_highlight ? "bg-yellow-50 font-semibold" : "",
                      item.is_section ? "border-t border-gray-300" : ""
                    )}>
                      <TableCell className={cn(
                        "text-xs py-1",
                        item.is_header ? "font-semibold" : "",
                        item.is_deduction ? "text-red-600" : "",
                        item.indent === 1 ? "pl-6" : ""
                      )}>
                        {item.label}
                      </TableCell>
                      <TableCell className={cn(
                        "text-xs text-right py-1 font-mono",
                        item.is_deduction ? "text-red-600" : "",
                        item.is_total ? "font-bold" : ""
                      )}>
                        {item.amount !== null && item.amount !== undefined ? fmt$(item.amount) : ""}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </CardContent>
          </Card>
        </div>
      ) : null}
    </div>
  );
}

// ==================== 主页面 ====================

export function ReportsPage() {
  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-2xl font-bold">报表中心</h1>
        <p className="text-sm text-muted-foreground">
          批次财报、单票财报、应收/应付对账单、三大财务报表
        </p>
      </div>

      <Tabs defaultValue="batches" className="w-full">
        <TabsList className="grid w-full grid-cols-5 h-10">
          <TabsTrigger value="batches" className="text-xs gap-1">
            <Package className="h-3.5 w-3.5" />
            批次财报
          </TabsTrigger>
          <TabsTrigger value="invoices" className="text-xs gap-1">
            <FileText className="h-3.5 w-3.5" />
            单票财报
          </TabsTrigger>
          <TabsTrigger value="receivable" className="text-xs gap-1">
            <ArrowDownLeft className="h-3.5 w-3.5" />
            应收对账
          </TabsTrigger>
          <TabsTrigger value="payable" className="text-xs gap-1">
            <ArrowUpRight className="h-3.5 w-3.5" />
            应付对账
          </TabsTrigger>
          <TabsTrigger value="financial" className="text-xs gap-1">
            <TrendingUp className="h-3.5 w-3.5" />
            三大报表
          </TabsTrigger>
        </TabsList>

        <TabsContent value="batches" className="mt-4">
          <BatchReportsTab />
        </TabsContent>
        <TabsContent value="invoices" className="mt-4">
          <InvoiceReportsTab />
        </TabsContent>
        <TabsContent value="receivable" className="mt-4">
          <ReceivableStatementsTab />
        </TabsContent>
        <TabsContent value="payable" className="mt-4">
          <PayableStatementsTab />
        </TabsContent>
        <TabsContent value="financial" className="mt-4">
          <FinancialStatementsTab />
        </TabsContent>
      </Tabs>
    </div>
  );
}
