import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
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
} from "@/components/ui/dialog";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Search, Eye, Phone, MapPin, CreditCard, TrendingUp, DollarSign, Package } from "lucide-react";
import { toast } from "sonner";

interface Customer {
  id: number;
  name: string;
  code: string | null;
  type: string;
  contact_person: string | null;
  phone: string | null;
  address: string | null;
  credit_limit: number | null;
  credit_balance: number | null;
  is_credit_enabled: boolean;
  monthly_purchase_limit: number | null;
  monthly_purchase_amount: number | null;
  notes: string | null;
  created_at: string;
}

interface CustomerSale {
  id: number;
  sale_no: string;
  sale_date: string;
  spec: string | null;
  box_count: number;
  weight_kg: number;
  unit_price: number;
  gross_amount: number;
  net_amount: number;
  paid_amount: number;
  status: string;
}

interface CustomerSummary {
  total_sales: number;
  total_paid: number;
  total_unpaid: number;
  sales_count: number;
  last_sale_date: string | null;
}

function fmt$(v: number | string | null | undefined) {
  const n = Number(v ?? 0);
  if (Number.isNaN(n)) return "¥0.00";
  return `¥${n.toLocaleString("zh-CN", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

function fmtDate(d: string | null | undefined) {
  if (!d) return "-";
  return new Date(d).toLocaleDateString("zh-CN");
}

export function CustomersPage() {
  const qc = useQueryClient();
  const [search, setSearch] = useState("");
  const [detailId, setDetailId] = useState<number | null>(null);
  const [detailOpen, setDetailOpen] = useState(false);

  const { data: customers, isLoading } = useQuery({
    queryKey: ["customers", search],
    queryFn: async () => {
      const params = new URLSearchParams();
      params.set("type", "customer");
      params.set("limit", "500");
      if (search) params.set("search", search);
      const res = await api.get(`/v1/companies/?${params.toString()}`);
      return res.data.items as Customer[];
    },
  });

  const { data: summary } = useQuery({
    queryKey: ["customer-summary", detailId],
    queryFn: async () => {
      if (!detailId) return null;
      // Get sales for this customer
      const res = await api.get(`/v1/sales/?customer_id=${detailId}&limit=500`);
      const sales = res.data.items as CustomerSale[];
      
      const total_sales = sales.reduce((sum, s) => sum + Number(s.net_amount || 0), 0);
      const total_paid = sales.reduce((sum, s) => sum + Number(s.paid_amount || 0), 0);
      const total_unpaid = total_sales - total_paid;
      
      return {
        total_sales,
        total_paid,
        total_unpaid,
        sales_count: sales.length,
        last_sale_date: sales.length > 0 ? sales[0].sale_date : null,
        sales,
      } as CustomerSummary & { sales: CustomerSale[] };
    },
    enabled: !!detailId,
  });

  const customer = customers?.find((c) => c.id === detailId);

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">客户管理</h1>
          <p className="text-sm text-muted-foreground">客户信息、信用额度、销售记录</p>
        </div>
      </div>

      {/* Search */}
      <div className="flex gap-4">
        <div className="relative max-w-sm">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <Input
            placeholder="搜索客户名称、编号..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="pl-9"
          />
        </div>
      </div>

      {/* Customer List */}
      <Card>
        <CardContent className="p-0">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead className="text-xs">客户名称</TableHead>
                <TableHead className="text-xs">编号</TableHead>
                <TableHead className="text-xs">联系人</TableHead>
                <TableHead className="text-xs">电话</TableHead>
                <TableHead className="text-xs text-right">信用额度</TableHead>
                <TableHead className="text-xs text-right">已用信用</TableHead>
                <TableHead className="text-xs text-right">月度限额</TableHead>
                <TableHead className="text-xs text-center">操作</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {isLoading ? (
                <TableRow>
                  <TableCell colSpan={8} className="text-center py-8">加载中...</TableCell>
                </TableRow>
              ) : customers?.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={8} className="text-center text-muted-foreground py-8">
                    暂无客户数据
                  </TableCell>
                </TableRow>
              ) : (
                customers?.map((c) => (
                  <TableRow key={c.id}>
                    <TableCell className="text-sm font-medium">{c.name}</TableCell>
                    <TableCell className="text-xs">{c.code || "-"}</TableCell>
                    <TableCell className="text-xs">{c.contact_person || "-"}</TableCell>
                    <TableCell className="text-xs">{c.phone || "-"}</TableCell>
                    <TableCell className="text-xs text-right">
                      {c.is_credit_enabled ? fmt$(c.credit_limit) : "-"}
                    </TableCell>
                    <TableCell className="text-xs text-right">
                      {c.is_credit_enabled ? (
                        <span className={c.credit_balance && c.credit_balance < 0 ? "text-red-600" : ""}>
                          {fmt$(c.credit_balance)}
                        </span>
                      ) : "-"}
                    </TableCell>
                    <TableCell className="text-xs text-right">
                      {c.monthly_purchase_limit ? fmt$(c.monthly_purchase_limit) : "-"}
                    </TableCell>
                    <TableCell className="text-center">
                      <Button
                        variant="ghost"
                        size="sm"
                        className="h-7 px-2"
                        onClick={() => { setDetailId(c.id); setDetailOpen(true); }}
                      >
                        <Eye className="h-3.5 w-3.5" />
                      </Button>
                    </TableCell>
                  </TableRow>
                ))
              )}
            </TableBody>
          </Table>
        </CardContent>
      </Card>

      {/* Detail Dialog */}
      <Dialog open={detailOpen} onOpenChange={(open) => { setDetailOpen(open); if (!open) setDetailId(null); }}>
        <DialogContent className="max-w-[800px] max-h-[85vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle className="text-base">客户详情 - {customer?.name}</DialogTitle>
          </DialogHeader>
          
          {customer ? (
            <div className="space-y-4 text-sm">
              {/* Basic Info */}
              <div className="grid grid-cols-2 gap-3">
                <Card>
                  <CardHeader className="pb-2">
                    <CardTitle className="text-sm">基本信息</CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-2 text-xs">
                    <div className="flex justify-between">
                      <span className="text-muted-foreground">编号</span>
                      <span>{customer.code || "-"}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-muted-foreground">联系人</span>
                      <span>{customer.contact_person || "-"}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-muted-foreground">电话</span>
                      <span>{customer.phone || "-"}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-muted-foreground">地址</span>
                      <span>{customer.address || "-"}</span>
                    </div>
                  </CardContent>
                </Card>

                <Card>
                  <CardHeader className="pb-2">
                    <CardTitle className="text-sm">信用信息</CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-2 text-xs">
                    <div className="flex justify-between">
                      <span className="text-muted-foreground">信用额度</span>
                      <span>{customer.is_credit_enabled ? fmt$(customer.credit_limit) : "未启用"}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-muted-foreground">已用信用</span>
                      <span className={customer.credit_balance && customer.credit_balance < 0 ? "text-red-600" : ""}>
                        {customer.is_credit_enabled ? fmt$(customer.credit_balance) : "-"}
                      </span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-muted-foreground">月度限额</span>
                      <span>{fmt$(customer.monthly_purchase_limit)}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-muted-foreground">本月采购</span>
                      <span>{fmt$(customer.monthly_purchase_amount)}</span>
                    </div>
                  </CardContent>
                </Card>
              </div>

              {/* Sales Summary */}
              {summary && (
                <div className="grid grid-cols-4 gap-3">
                  <Card>
                    <CardContent className="p-3">
                      <div className="text-xs text-muted-foreground">总销售额</div>
                      <div className="text-lg font-bold">{fmt$(summary.total_sales)}</div>
                    </CardContent>
                  </Card>
                  <Card>
                    <CardContent className="p-3">
                      <div className="text-xs text-muted-foreground">已收款</div>
                      <div className="text-lg font-bold text-green-600">{fmt$(summary.total_paid)}</div>
                    </CardContent>
                  </Card>
                  <Card>
                    <CardContent className="p-3">
                      <div className="text-xs text-muted-foreground">未收款</div>
                      <div className="text-lg font-bold text-red-600">{fmt$(summary.total_unpaid)}</div>
                    </CardContent>
                  </Card>
                  <Card>
                    <CardContent className="p-3">
                      <div className="text-xs text-muted-foreground">销售笔数</div>
                      <div className="text-lg font-bold">{summary.sales_count}</div>
                    </CardContent>
                  </Card>
                </div>
              )}

              {/* Sales History */}
              {summary?.sales && summary.sales.length > 0 && (
                <div className="border rounded-lg overflow-hidden">
                  <p className="text-xs font-semibold px-3 py-2 bg-muted/50">销售记录</p>
                  <Table>
                    <TableHeader>
                      <TableRow className="bg-muted/50">
                        <TableHead className="text-xs">日期</TableHead>
                        <TableHead className="text-xs">单号</TableHead>
                        <TableHead className="text-xs">规格</TableHead>
                        <TableHead className="text-xs text-right">箱数</TableHead>
                        <TableHead className="text-xs text-right">重量(kg)</TableHead>
                        <TableHead className="text-xs text-right">单价</TableHead>
                        <TableHead className="text-xs text-right">净额</TableHead>
                        <TableHead className="text-xs text-right">已付</TableHead>
                        <TableHead className="text-xs">状态</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {summary.sales.map((sale) => (
                        <TableRow key={sale.id}>
                          <TableCell className="text-xs">{fmtDate(sale.sale_date)}</TableCell>
                          <TableCell className="text-xs">{sale.sale_no}</TableCell>
                          <TableCell className="text-xs">{sale.spec || "-"}</TableCell>
                          <TableCell className="text-xs text-right">{sale.box_count}</TableCell>
                          <TableCell className="text-xs text-right">{Number(sale.weight_kg || 0).toLocaleString()}</TableCell>
                          <TableCell className="text-xs text-right">{fmt$(sale.unit_price)}</TableCell>
                          <TableCell className="text-xs text-right font-medium">{fmt$(sale.net_amount)}</TableCell>
                          <TableCell className="text-xs text-right">{fmt$(sale.paid_amount)}</TableCell>
                          <TableCell className="text-xs">
                            <Badge variant="outline" className="text-[10px] h-5">
                              {sale.status === "fully_paid" ? "已付清" : sale.status === "partial_paid" ? "部分付款" : "未付款"}
                            </Badge>
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </div>
              )}
            </div>
          ) : (
            <div className="py-8 text-center">加载中...</div>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
}
