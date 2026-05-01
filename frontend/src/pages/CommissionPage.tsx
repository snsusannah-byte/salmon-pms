import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
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
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Search, Calculator, UserCog, TrendingUp } from "lucide-react";

interface CommissionRecord {
  id: number;
  salesperson_id: number;
  salesperson_name: string;
  sale_id: number;
  sale_date: string;
  customer_name: string;
  sale_amount: number;
  commission_rate: number;
  commission_amount: number;
  status: string; // pending / paid
  paid_date: string | null;
  notes: string | null;
}

interface CommissionSummary {
  total_pending: number;
  total_paid: number;
  total_amount: number;
}

export function CommissionPage() {
  const [search, setSearch] = useState("");
  const [month, setMonth] = useState(() => {
    const now = new Date();
    return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}`;
  });

  const { data: records, isLoading } = useQuery({
    queryKey: ["commissions", month, search],
    queryFn: async () => {
      const params = new URLSearchParams();
      params.set("month", month);
      if (search) params.set("search", search);
      const res = await api.get(`/v1/commissions/?${params.toString()}`);
      return res.data as { items: CommissionRecord[]; summary: CommissionSummary };
    },
  });

  const { data: salespersons } = useQuery({
    queryKey: ["salespersons"],
    queryFn: async () => {
      const res = await api.get("/v1/salespersons/");
      return res.data.items as { id: number; name: string; commission_rate: number }[];
    },
  });

  return (
    <div className="space-y-6">
      {/* 标题 */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">提成管理</h1>
          <p className="text-sm text-muted-foreground">业务员销售提成统计与发放</p>
        </div>
      </div>

      {/* 汇总卡片 */}
      <div className="grid grid-cols-3 gap-4">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium">待发放提成</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-orange-600">
              ¥{Number(records?.summary?.total_pending ?? 0).toLocaleString()}
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium">已发放提成</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-green-600">
              ¥{Number(records?.summary?.total_paid ?? 0).toLocaleString()}
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium">提成总额</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              ¥{Number(records?.summary?.total_amount ?? 0).toLocaleString()}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* 筛选 */}
      <div className="flex gap-4">
        <div className="relative max-w-sm">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <Input
            placeholder="搜索业务员、客户..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="pl-9"
          />
        </div>
        <div className="space-y-2">
          <Label className="text-xs">月份</Label>
          <Input
            type="month"
            value={month}
            onChange={(e) => setMonth(e.target.value)}
            className="w-40"
          />
        </div>
      </div>

      {/* 业务员提成概览 */}
      <div className="border rounded-lg">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>业务员</TableHead>
              <TableHead>默认提成比例</TableHead>
              <TableHead>本月销售额</TableHead>
              <TableHead>本月提成</TableHead>
              <TableHead>待发放</TableHead>
              <TableHead>已发放</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {salespersons?.map((sp) => {
              const spRecords = records?.items.filter((r) => r.salesperson_id === sp.id) ?? [];
              const totalSale = spRecords.reduce((sum, r) => sum + r.sale_amount, 0);
              const totalCommission = spRecords.reduce((sum, r) => sum + r.commission_amount, 0);
              const pending = spRecords.filter((r) => r.status === "pending").reduce((sum, r) => sum + r.commission_amount, 0);
              const paid = spRecords.filter((r) => r.status === "paid").reduce((sum, r) => sum + r.commission_amount, 0);
              return (
                <TableRow key={sp.id}>
                  <TableCell className="font-medium">
                    <div className="flex items-center gap-2">
                      <UserCog className="h-4 w-4 text-blue-500" />
                      {sp.name}
                    </div>
                  </TableCell>
                  <TableCell>{sp.commission_rate}%</TableCell>
                  <TableCell>¥{totalSale.toLocaleString()}</TableCell>
                  <TableCell className="font-medium">¥{totalCommission.toLocaleString()}</TableCell>
                  <TableCell className="text-orange-600">¥{pending.toLocaleString()}</TableCell>
                  <TableCell className="text-green-600">¥{paid.toLocaleString()}</TableCell>
                </TableRow>
              );
            })}
          </TableBody>
        </Table>
      </div>

      {/* 明细表格 */}
      <div className="border rounded-lg">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>日期</TableHead>
              <TableHead>业务员</TableHead>
              <TableHead>客户</TableHead>
              <TableHead>销售金额</TableHead>
              <TableHead>提成比例</TableHead>
              <TableHead>提成金额</TableHead>
              <TableHead>状态</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {isLoading ? (
              <TableRow>
                <TableCell colSpan={7} className="text-center py-8">加载中...</TableCell>
              </TableRow>
            ) : records?.items.length === 0 ? (
              <TableRow>
                <TableCell colSpan={7} className="text-center py-8 text-muted-foreground">
                  暂无提成记录
                </TableCell>
              </TableRow>
            ) : (
              records?.items.map((r) => (
                <TableRow key={r.id}>
                  <TableCell className="text-sm">{r.sale_date}</TableCell>
                  <TableCell className="font-medium">{r.salesperson_name}</TableCell>
                  <TableCell>{r.customer_name}</TableCell>
                  <TableCell>¥{r.sale_amount.toLocaleString()}</TableCell>
                  <TableCell>{r.commission_rate}%</TableCell>
                  <TableCell className="font-medium">¥{r.commission_amount.toLocaleString()}</TableCell>
                  <TableCell>
                    {r.status === "pending" ? (
                      <Badge variant="secondary" className="bg-orange-100 text-orange-800">待发放</Badge>
                    ) : (
                      <Badge variant="secondary" className="bg-green-100 text-green-800">已发放</Badge>
                    )}
                  </TableCell>
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </div>
    </div>
  );
}
