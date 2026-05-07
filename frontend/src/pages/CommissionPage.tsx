import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
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
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "@/components/ui/dialog";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Checkbox } from "@/components/ui/checkbox";
import { Search, Calculator, UserCog, TrendingUp, Wallet, CheckCircle } from "lucide-react";
import { toast } from "sonner";

interface CommissionRecord {
  id: number;
  salesperson_id: number;
  salesperson_name: string;
  sale_id: number;
  sale_date: string;
  customer_name: string;
  sale_amount: number;
  weight_kg: number;
  commission_rate: number; // 元/kg
  commission_amount: number;
  status: string;
  paid_date: string | null;
  notes: string | null;
}

interface CommissionSummary {
  total_pending: number;
  total_paid: number;
  total_amount: number;
}

export function CommissionPage() {
  const qc = useQueryClient();
  const [search, setSearch] = useState("");
  const [month, setMonth] = useState(() => {
    const now = new Date();
    return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}`;
  });
  const [selectedIds, setSelectedIds] = useState<Set<number>>(new Set());
  const [payDialogOpen, setPayDialogOpen] = useState(false);
  const [payTargetSp, setPayTargetSp] = useState<{ id: number; name: string } | null>(null);

  const { data: records, isLoading } = useQuery({
    queryKey: ["commissions", month, search],
    queryFn: async () => {
      const params = new URLSearchParams();
      params.set("month", month);
      if (search) params.set("search", search);
      const res = await api.get(`/v1/salespersons/commissions/?${params.toString()}`);
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

  const payMutation = useMutation({
    mutationFn: async ({ spId, recordIds }: { spId: number; recordIds: number[] }) => {
      const res = await api.post(`/v1/salespersons/${spId}/pay-commission`, recordIds);
      return res.data;
    },
    onSuccess: (data) => {
      toast.success(`成功发放 ${data.paid_count} 笔提成`);
      qc.invalidateQueries({ queryKey: ["commissions"] });
      setSelectedIds(new Set());
      setPayDialogOpen(false);
      setPayTargetSp(null);
    },
    onError: (err: any) => {
      toast.error(err.response?.data?.detail || "发放失败");
    },
  });

  const pendingRecords = records?.items.filter((r) => r.status === "pending") ?? [];

  function toggleSelect(id: number) {
    const next = new Set(selectedIds);
    if (next.has(id)) next.delete(id);
    else next.add(id);
    setSelectedIds(next);
  }

  function toggleSelectAll() {
    const pendingIds = pendingRecords.map((r) => r.id);
    if (selectedIds.size === pendingIds.length && pendingIds.length > 0) {
      setSelectedIds(new Set());
    } else {
      setSelectedIds(new Set(pendingIds));
    }
  }

  function handlePayClick(spId: number, spName: string) {
    const ids = pendingRecords.filter((r) => r.salesperson_id === spId).map((r) => r.id);
    if (ids.length === 0) {
      toast.info("该业务员没有待发放提成");
      return;
    }
    setPayTargetSp({ id: spId, name: spName });
    setPayDialogOpen(true);
  }

  function handleConfirmPay() {
    if (!payTargetSp) return;
    const ids = pendingRecords
      .filter((r) => r.salesperson_id === payTargetSp.id)
      .map((r) => r.id);
    payMutation.mutate({ spId: payTargetSp.id, recordIds: ids });
  }

  return (
    <div className="space-y-6">
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

      <Tabs defaultValue="overview">
        <TabsList className="grid w-full grid-cols-2">
          <TabsTrigger value="overview">业务员概览</TabsTrigger>
          <TabsTrigger value="records">提成明细</TabsTrigger>
        </TabsList>

        <TabsContent value="overview" className="space-y-4 mt-4">
          {/* 筛选 */}
          <div className="flex gap-4">
            <div className="relative max-w-sm">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
              <Input
                placeholder="搜索业务员..."
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
                  <TableHead>默认提成单价</TableHead>
                  <TableHead>本月销售额</TableHead>
                  <TableHead>本月销售重量</TableHead>
                  <TableHead>本月提成</TableHead>
                  <TableHead>待发放</TableHead>
                  <TableHead>已发放</TableHead>
                  <TableHead className="text-right">操作</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {salespersons?.map((sp) => {
                  const spRecords = records?.items.filter((r) => r.salesperson_id === sp.id) ?? [];
                  const totalSale = spRecords.reduce((sum, r) => sum + r.sale_amount, 0);
                  const totalWeight = spRecords.reduce((sum, r) => sum + r.weight_kg, 0);
                  const totalCommission = spRecords.reduce((sum, r) => sum + r.commission_amount, 0);
                  const pending = spRecords
                    .filter((r) => r.status === "pending")
                    .reduce((sum, r) => sum + r.commission_amount, 0);
                  const paid = spRecords
                    .filter((r) => r.status === "paid")
                    .reduce((sum, r) => sum + r.commission_amount, 0);
                  return (
                    <TableRow key={sp.id}>
                      <TableCell className="font-medium">
                        <div className="flex items-center gap-2">
                          <UserCog className="h-4 w-4 text-blue-500" />
                          {sp.name}
                        </div>
                      </TableCell>
                      <TableCell>¥{sp.commission_rate}/kg</TableCell>
                      <TableCell>¥{totalSale.toLocaleString()}</TableCell>
                      <TableCell>{totalWeight.toFixed(1)} kg</TableCell>
                      <TableCell className="font-medium">
                        ¥{totalCommission.toLocaleString()}
                      </TableCell>
                      <TableCell className="text-orange-600">
                        ¥{pending.toLocaleString()}
                      </TableCell>
                      <TableCell className="text-green-600">
                        ¥{paid.toLocaleString()}
                      </TableCell>
                      <TableCell className="text-right">
                        <Button
                          size="sm"
                          variant="outline"
                          disabled={pending <= 0 || payMutation.isPending}
                          onClick={() => handlePayClick(sp.id, sp.name)}
                        >
                          <Wallet className="h-3 w-3 mr-1" />
                          发放
                        </Button>
                      </TableCell>
                    </TableRow>
                  );
                })}
              </TableBody>
            </Table>
          </div>
        </TabsContent>

        <TabsContent value="records" className="space-y-4 mt-4">
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

          {/* 明细表格 */}
          <div className="border rounded-lg">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead className="w-10">
                    <Checkbox
                      checked={
                        pendingRecords.length > 0 && selectedIds.size === pendingRecords.length
                      }
                      onCheckedChange={toggleSelectAll}
                    />
                  </TableHead>
                  <TableHead>日期</TableHead>
                  <TableHead>业务员</TableHead>
                  <TableHead>客户</TableHead>
                  <TableHead>销售重量</TableHead>
                  <TableHead>提成单价</TableHead>
                  <TableHead>提成金额</TableHead>
                  <TableHead>状态</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {isLoading ? (
                  <TableRow>
                    <TableCell colSpan={8} className="text-center py-8">
                      加载中...
                    </TableCell>
                  </TableRow>
                ) : records?.items.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={8} className="text-center py-8 text-muted-foreground">
                      暂无提成记录
                    </TableCell>
                  </TableRow>
                ) : (
                  records?.items.map((r) => (
                    <TableRow key={r.id}>
                      <TableCell>
                        {r.status === "pending" && (
                          <Checkbox
                            checked={selectedIds.has(r.id)}
                            onCheckedChange={() => toggleSelect(r.id)}
                          />
                        )}
                      </TableCell>
                      <TableCell className="text-sm">{r.sale_date}</TableCell>
                      <TableCell className="font-medium">{r.salesperson_name}</TableCell>
                      <TableCell>{r.customer_name}</TableCell>
                      <TableCell>{r.weight_kg?.toFixed(1) ?? 0} kg</TableCell>
                      <TableCell>¥{r.commission_rate}/kg</TableCell>
                      <TableCell className="font-medium">
                        ¥{r.commission_amount.toLocaleString()}
                      </TableCell>
                      <TableCell>
                        {r.status === "pending" ? (
                          <Badge variant="secondary" className="bg-orange-100 text-orange-800">
                            待发放
                          </Badge>
                        ) : (
                          <Badge variant="secondary" className="bg-green-100 text-green-800">
                            已发放
                          </Badge>
                        )}
                      </TableCell>
                    </TableRow>
                  ))
                )}
              </TableBody>
            </Table>
          </div>
        </TabsContent>
      </Tabs>

      {/* 发放确认弹窗 */}
      <Dialog open={payDialogOpen} onOpenChange={setPayDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>确认发放提成</DialogTitle>
          </DialogHeader>
          <div className="space-y-2 text-sm">
            <p>
              业务员：<span className="font-medium">{payTargetSp?.name}</span>
            </p>
            <p>
              待发放笔数：
              <span className="font-medium">
                {pendingRecords.filter((r) => r.salesperson_id === payTargetSp?.id).length} 笔
              </span>
            </p>
            <p>
              待发放金额：
              <span className="font-medium text-orange-600">
                ¥
                {pendingRecords
                  .filter((r) => r.salesperson_id === payTargetSp?.id)
                  .reduce((sum, r) => sum + r.commission_amount, 0)
                  .toLocaleString()}
              </span>
            </p>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setPayDialogOpen(false)}>
              取消
            </Button>
            <Button
              onClick={handleConfirmPay}
              disabled={payMutation.isPending}
            >
              {payMutation.isPending ? "发放中..." : "确认发放"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
