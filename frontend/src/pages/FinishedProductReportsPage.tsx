import React, { useMemo } from "react";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { cn } from "@/lib/utils";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Badge } from "@/components/ui/badge";
import { Loader2 } from "lucide-react";
import {
  TrendingUp,
  DollarSign,
  ShoppingCart,
  CreditCard,
  AlertCircle,
  Award,
  BarChart3,
  Users,
} from "lucide-react";

// ==================== 类型定义 ====================

interface Sale {
  id: number;
  sale_date: string;
  customer_id: number;
  customer_name: string | null;
  product_id: number;
  product_name: string | null;
  quantity: number;  // 份数
  unit_price: string;
  gross_amount: string;
  net_amount: string;
  paid_amount: string;
  total_weight_kg: number | null;  // V3: 总重量
  status: string;
}

interface ProductStat {
  product_name: string;
  quantity: number;
  revenue: number;
  weight_kg: number;
}

interface CustomerStat {
  customer_name: string;
  order_count: number;
  total_amount: number;
  unpaid_amount: number;
}

// ==================== 工具函数 ====================

function fmt$(v: number) {
  return `¥${v.toLocaleString()}`;
}

// ==================== 主页面组件 ====================

export function FinishedProductReportsPage() {
  // 获取真实销售数据
  const { data: salesData, isLoading } = useQuery({
    queryKey: ["finished-product-sales-reports"],
    queryFn: async () => {
      const res = await api.get("/v1/finished-product-sales/?limit=500");
      return res.data.items as Sale[];
    },
  });

  const sales = salesData || [];

  // Tab 1 统计数据
  const totalRevenue = sales.reduce((sum, d) => sum + Number(d.gross_amount), 0);
  const totalQuantity = sales.reduce((sum, d) => sum + d.quantity, 0);
  const totalWeight = sales.reduce((sum, d) => sum + (d.total_weight_kg || 0), 0);
  const totalReceipts = sales.reduce((sum, d) => sum + Number(d.paid_amount), 0);
  const totalUnpaid = totalRevenue - totalReceipts;

  // Tab 2 产品统计
  const productStats = useMemo(() => {
    const map = new Map<string, ProductStat>();
    sales.forEach((s) => {
      const name = s.product_name || `产品#${s.product_id}`;
      const existing = map.get(name);
      if (existing) {
        existing.quantity += s.quantity;
        existing.revenue += Number(s.gross_amount);
        existing.weight_kg += (s.total_weight_kg || 0);
      } else {
        map.set(name, {
          product_name: name,
          quantity: s.quantity,
          revenue: Number(s.gross_amount),
          weight_kg: s.total_weight_kg || 0,
        });
      }
    });
    return Array.from(map.values()).sort((a, b) => b.revenue - a.revenue);
  }, [sales]);

  const totalProductRevenue = productStats.reduce((sum, p) => sum + p.revenue, 0);
  const topProduct = productStats[0];

  // Tab 3 客户统计
  const customerStats = useMemo(() => {
    const map = new Map<string, CustomerStat>();
    sales.forEach((s) => {
      const name = s.customer_name || `客户#${s.customer_id}`;
      const existing = map.get(name);
      if (existing) {
        existing.order_count += 1;
        existing.total_amount += Number(s.gross_amount);
        existing.unpaid_amount += (Number(s.gross_amount) - Number(s.paid_amount));
      } else {
        map.set(name, {
          customer_name: name,
          order_count: 1,
          total_amount: Number(s.gross_amount),
          unpaid_amount: Number(s.gross_amount) - Number(s.paid_amount),
        });
      }
    });
    return Array.from(map.values()).sort((a, b) => b.total_amount - a.total_amount);
  }, [sales]);

  const topCustomer = customerStats[0];
  const totalUnpaidByCustomers = customerStats.reduce((sum, c) => sum + c.unpaid_amount, 0);

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* 标题 */}
      <div>
        <h1 className="text-2xl font-bold">成品销售报表</h1>
        <p className="text-sm text-muted-foreground">
          共 {sales.length} 条销售记录 · 总份数 {totalQuantity.toLocaleString()} · 总重量 {totalWeight.toFixed(1)}kg
        </p>
      </div>

      <Tabs defaultValue="overview">
        <TabsList className="grid w-full grid-cols-3">
          <TabsTrigger value="overview">
            <BarChart3 className="h-4 w-4 mr-1" />
            销售概览
          </TabsTrigger>
          <TabsTrigger value="products">
            <ShoppingCart className="h-4 w-4 mr-1" />
            产品销售分析
          </TabsTrigger>
          <TabsTrigger value="customers">
            <Users className="h-4 w-4 mr-1" />
            客户分析
          </TabsTrigger>
        </TabsList>

        {/* ===== Tab 1: 销售概览 ===== */}
        <TabsContent value="overview" className="space-y-6 pt-4">
          {/* 4个统计卡片 */}
          <div className="grid grid-cols-4 gap-4">
            <Card>
              <CardContent className="p-4">
                <div className="flex items-center justify-between">
                  <div className="space-y-1">
                    <p className="text-sm text-muted-foreground">总销售额</p>
                    <p className="text-2xl font-bold">{fmt$(totalRevenue)}</p>
                  </div>
                  <div className="p-3 bg-blue-100 rounded-full">
                    <DollarSign className="h-5 w-5 text-blue-600" />
                  </div>
                </div>
                <div className="mt-2 flex items-center text-xs text-green-600">
                  <TrendingUp className="h-3 w-3 mr-1" />
                  <span>{sales.length} 笔订单</span>
                </div>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="p-4">
                <div className="flex items-center justify-between">
                  <div className="space-y-1">
                    <p className="text-sm text-muted-foreground">总销量</p>
                    <p className="text-2xl font-bold">{totalQuantity.toLocaleString()} 份</p>
                  </div>
                  <div className="p-3 bg-green-100 rounded-full">
                    <ShoppingCart className="h-5 w-5 text-green-600" />
                  </div>
                </div>
                <div className="mt-2 text-xs text-muted-foreground">
                  总重量 {totalWeight.toFixed(1)} kg
                </div>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="p-4">
                <div className="flex items-center justify-between">
                  <div className="space-y-1">
                    <p className="text-sm text-muted-foreground">总收款</p>
                    <p className="text-2xl font-bold text-green-600">{fmt$(totalReceipts)}</p>
                  </div>
                  <div className="p-3 bg-emerald-100 rounded-full">
                    <CreditCard className="h-5 w-5 text-emerald-600" />
                  </div>
                </div>
                <div className="mt-2 text-xs text-muted-foreground">
                  收款率 {totalRevenue > 0 ? ((totalReceipts / totalRevenue) * 100).toFixed(1) : 0}%
                </div>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="p-4">
                <div className="flex items-center justify-between">
                  <div className="space-y-1">
                    <p className="text-sm text-muted-foreground">未收款金额</p>
                    <p className={cn("text-2xl font-bold", totalUnpaid > 0 && "text-orange-600")}>
                      {fmt$(totalUnpaid)}
                    </p>
                  </div>
                  <div className="p-3 bg-orange-100 rounded-full">
                    <AlertCircle className="h-5 w-5 text-orange-600" />
                  </div>
                </div>
                <div className="mt-2 text-xs text-muted-foreground">
                  占比 {totalRevenue > 0 ? ((totalUnpaid / totalRevenue) * 100).toFixed(1) : 0}%
                </div>
              </CardContent>
            </Card>
          </div>

          {/* 每日明细表格 */}
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-base">销售明细</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="border rounded-md max-h-[400px] overflow-y-auto">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>日期</TableHead>
                      <TableHead>客户</TableHead>
                      <TableHead>产品</TableHead>
                      <TableHead className="text-right">份数</TableHead>
                      <TableHead className="text-right">重量(kg)</TableHead>
                      <TableHead className="text-right">销售额</TableHead>
                      <TableHead className="text-right">收款额</TableHead>
                      <TableHead className="text-right">未收款</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {[...sales].reverse().map((d) => {
                      const dayUnpaid = Number(d.gross_amount) - Number(d.paid_amount);
                      return (
                        <TableRow key={d.id}>
                          <TableCell className="text-sm">{d.sale_date}</TableCell>
                          <TableCell className="text-sm">{d.customer_name || "-"}</TableCell>
                          <TableCell className="text-sm">{d.product_name || "-"}</TableCell>
                          <TableCell className="text-sm text-right">{d.quantity}</TableCell>
                          <TableCell className="text-sm text-right">{d.total_weight_kg?.toFixed(1) || "-"}</TableCell>
                          <TableCell className="text-sm text-right font-medium">{fmt$(Number(d.gross_amount))}</TableCell>
                          <TableCell className="text-sm text-right text-green-600">{fmt$(Number(d.paid_amount))}</TableCell>
                          <TableCell className={cn("text-sm text-right", dayUnpaid > 0 && "text-orange-600")}>
                            {fmt$(dayUnpaid)}
                          </TableCell>
                        </TableRow>
                      );
                    })}
                  </TableBody>
                </Table>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* ===== Tab 2: 产品销售分析 ===== */}
        <TabsContent value="products" className="space-y-6 pt-4">
          {/* 畅销产品卡片 */}
          <div className="grid grid-cols-3 gap-4">
            <Card className="bg-gradient-to-br from-yellow-50 to-amber-50 border-yellow-200">
              <CardContent className="p-4">
                <div className="flex items-center gap-2 mb-2">
                  <Award className="h-5 w-5 text-amber-600" />
                  <span className="text-sm font-medium text-amber-800">销售冠军</span>
                </div>
                <p className="text-lg font-bold">{topProduct?.product_name || "-"}</p>
                <p className="text-sm text-muted-foreground mt-1">
                  销售额 {fmt$(topProduct?.revenue || 0)} · {topProduct?.quantity || 0} 份 · {topProduct?.weight_kg.toFixed(1) || 0}kg
                </p>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="p-4">
                <p className="text-sm text-muted-foreground">总销售份数</p>
                <p className="text-2xl font-bold">
                  {productStats.reduce((s, p) => s + p.quantity, 0).toLocaleString()} 份
                </p>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="p-4">
                <p className="text-sm text-muted-foreground">总销售额</p>
                <p className="text-2xl font-bold">{fmt$(totalProductRevenue)}</p>
              </CardContent>
            </Card>
          </div>

          {/* 产品销售表格 */}
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-base">产品销售排行</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="border rounded-md">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead className="w-[50px]">排名</TableHead>
                      <TableHead>产品名称</TableHead>
                      <TableHead className="text-right">销售份数</TableHead>
                      <TableHead className="text-right">重量(kg)</TableHead>
                      <TableHead className="text-right">销售额</TableHead>
                      <TableHead className="text-right">占比</TableHead>
                      <TableHead className="w-[200px]">占比图</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {productStats.map((product, index) => {
                      const pct = totalProductRevenue > 0 ? (product.revenue / totalProductRevenue) * 100 : 0;
                      const isTop3 = index < 3;
                      return (
                        <TableRow key={product.product_name} className={cn(isTop3 && "bg-amber-50/40")}>
                          <TableCell>
                            {index < 3 ? (
                              <Badge variant={index === 0 ? "default" : "secondary"} className={cn(index === 0 && "bg-amber-500")}>
                                {index + 1}
                              </Badge>
                            ) : (
                              <span className="text-sm text-muted-foreground ml-2">{index + 1}</span>
                            )}
                          </TableCell>
                          <TableCell className="font-medium">{product.product_name}</TableCell>
                          <TableCell className="text-right">{product.quantity.toLocaleString()}</TableCell>
                          <TableCell className="text-right">{product.weight_kg.toFixed(1)}</TableCell>
                          <TableCell className="text-right font-medium">{fmt$(product.revenue)}</TableCell>
                          <TableCell className="text-right text-muted-foreground">{pct.toFixed(1)}%</TableCell>
                          <TableCell>
                            <div className="w-full bg-muted rounded-full h-2 overflow-hidden">
                              <div
                                className={cn(
                                  "h-full rounded-full transition-all",
                                  index === 0 ? "bg-amber-500" : index === 1 ? "bg-slate-400" : index === 2 ? "bg-orange-400" : "bg-blue-400"
                                )}
                                style={{ width: `${Math.max(pct, 2)}%` }}
                              />
                            </div>
                          </TableCell>
                        </TableRow>
                      );
                    })}
                  </TableBody>
                </Table>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* ===== Tab 3: 客户分析 ===== */}
        <TabsContent value="customers" className="space-y-6 pt-4">
          {/* 头部统计 */}
          <div className="grid grid-cols-3 gap-4">
            <Card className="bg-gradient-to-br from-blue-50 to-indigo-50 border-blue-200">
              <CardContent className="p-4">
                <div className="flex items-center gap-2 mb-2">
                  <Award className="h-5 w-5 text-blue-600" />
                  <span className="text-sm font-medium text-blue-800">最佳客户</span>
                </div>
                <p className="text-lg font-bold">{topCustomer?.customer_name || "-"}</p>
                <p className="text-sm text-muted-foreground mt-1">
                  贡献 {fmt$(topCustomer?.total_amount || 0)} · {topCustomer?.order_count || 0} 笔订单
                </p>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="p-4">
                <p className="text-sm text-muted-foreground">客户总数</p>
                <p className="text-2xl font-bold">{customerStats.length} 家</p>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="p-4">
                <p className="text-sm text-muted-foreground">客户总欠款</p>
                <p className={cn("text-2xl font-bold", totalUnpaidByCustomers > 0 && "text-orange-600")}>
                  {fmt$(totalUnpaidByCustomers)}
                </p>
              </CardContent>
            </Card>
          </div>

          {/* 客户分析表格 */}
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-base">客户购买排行</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="border rounded-md">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead className="w-[50px]">排名</TableHead>
                      <TableHead>客户名称</TableHead>
                      <TableHead className="text-right">购买次数</TableHead>
                      <TableHead className="text-right">购买金额</TableHead>
                      <TableHead className="text-right">未付金额</TableHead>
                      <TableHead className="text-right">信用状况</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {customerStats.map((customer, index) => {
                      const creditStatus =
                        customer.unpaid_amount === 0
                          ? { label: "优秀", color: "bg-green-100 text-green-800" }
                          : customer.unpaid_amount / customer.total_amount < 0.3
                          ? { label: "良好", color: "bg-blue-100 text-blue-800" }
                          : customer.unpaid_amount / customer.total_amount < 0.6
                          ? { label: "一般", color: "bg-yellow-100 text-yellow-800" }
                          : { label: "关注", color: "bg-red-100 text-red-800" };

                      return (
                        <TableRow key={customer.customer_name}>
                          <TableCell>
                            <Badge variant={index === 0 ? "default" : "secondary"} className={cn(index === 0 && "bg-blue-500")}>
                              {index + 1}
                            </Badge>
                          </TableCell>
                          <TableCell className="font-medium">{customer.customer_name}</TableCell>
                          <TableCell className="text-right">{customer.order_count} 笔</TableCell>
                          <TableCell className="text-right font-medium">{fmt$(customer.total_amount)}</TableCell>
                          <TableCell className={cn("text-right", customer.unpaid_amount > 0 && "text-orange-600 font-medium")}>
                            {fmt$(customer.unpaid_amount)}
                          </TableCell>
                          <TableCell className="text-right">
                            <Badge variant="outline" className={cn(creditStatus.color)}>
                              {creditStatus.label}
                            </Badge>
                          </TableCell>
                        </TableRow>
                      );
                    })}
                  </TableBody>
                </Table>
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}
