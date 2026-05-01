import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
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
  Boxes,
  DollarSign,
  Users,
  Ship,
  FileText,
  Weight,
  Package,
  BarChart3,
} from "lucide-react";

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

const batchStatusMap: Record<string, { label: string; color: string }> = {
  OPEN: { label: "开放", color: "bg-green-100 text-green-800" },
  LOCKED: { label: "已锁定", color: "bg-orange-100 text-orange-800" },
  SETTLED: { label: "已结算", color: "bg-blue-100 text-blue-800" },
  // 兼容旧数据
  open: { label: "开放", color: "bg-green-100 text-green-800" },
  locked: { label: "已锁定", color: "bg-orange-100 text-orange-800" },
  settled: { label: "已结算", color: "bg-blue-100 text-blue-800" },
};

export function DashboardPage() {
  const { data: summary, isLoading: summaryLoading } = useQuery({
    queryKey: ["dashboard-summary"],
    queryFn: async () => {
      const res = await api.get("/v1/dashboard/summary");
      return res.data;
    },
  });

  const { data: recentInvoices } = useQuery({
    queryKey: ["dashboard-recent-invoices"],
    queryFn: async () => {
      const res = await api.get("/v1/dashboard/recent-invoices");
      return res.data;
    },
  });

  const { data: recentBatches } = useQuery({
    queryKey: ["dashboard-recent-batches"],
    queryFn: async () => {
      const res = await api.get("/v1/dashboard/recent-batches");
      return res.data;
    },
  });

  const { data: customsBreakdown } = useQuery({
    queryKey: ["dashboard-customs-breakdown"],
    queryFn: async () => {
      const res = await api.get("/v1/dashboard/customs-status-breakdown");
      return res.data;
    },
  });

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">数据看板</h1>

      {/* 核心指标 */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium">总批次</CardTitle>
            <Boxes className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {summaryLoading ? "-" : summary?.batches?.total ?? 0}
            </div>
            <div className="flex gap-2 mt-1">
              {summary?.batches?.open > 0 && (
                <span className="text-xs text-green-600">开放 {summary.batches.open}</span>
              )}
              {summary?.batches?.locked > 0 && (
                <span className="text-xs text-orange-600">锁定 {summary.batches.locked}</span>
              )}
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium">发票总额 (USD)</CardTitle>
            <DollarSign className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {summaryLoading
                ? "-"
                : `$${Number(summary?.invoices?.total_amount_usd ?? 0).toLocaleString()}`}
            </div>
            <div className="text-xs text-muted-foreground mt-1">
              {summary?.invoices?.total ?? 0} 张发票
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium">本月进口</CardTitle>
            <Ship className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {summaryLoading
                ? "-"
                : `$${Number(summary?.invoices?.this_month_amount ?? 0).toLocaleString()}`}
            </div>
            <div className="text-xs text-muted-foreground mt-1">
              {summary?.invoices?.this_month_count ?? 0} 张发票
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium">库存总重</CardTitle>
            <Weight className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {summaryLoading
                ? "-"
                : `${Number(summary?.inventory?.total_weight_kg ?? 0).toLocaleString()} kg`}
            </div>
            <div className="text-xs text-muted-foreground mt-1">
              {summary?.invoices?.total_boxes ?? 0} 总箱数
            </div>
          </CardContent>
        </Card>
      </div>

      {/* 第二行：主体分布 + 报关状态 */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {/* 主体类型分布 */}
        <Card>
          <CardHeader>
            <CardTitle className="text-sm font-medium">主体类型分布</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-2 gap-2">
              {summary?.companies?.breakdown && Object.entries(summary.companies.breakdown).map(([type, count]) => {
                const labels: Record<string, string> = {
                  processing_plant: "加工厂",
                  fish_farm: "渔场",
                  exporter: "出口商",
                  supplier: "供应商",
                  customer: "客户",
                  customs_broker: "报关行",
                  logistics: "物流",
                  internal: "内部",
                };
                return (
                  <div key={type} className="flex items-center justify-between p-2 bg-muted/50 rounded-md">
                    <span className="text-sm text-muted-foreground">{labels[type] ?? type}</span>
                    <span className="text-sm font-semibold">{count as number}</span>
                  </div>
                );
              })}
            </div>
          </CardContent>
        </Card>

        {/* 报关状态分布 */}
        <Card>
          <CardHeader>
            <CardTitle className="text-sm font-medium">报关状态分布</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              {customsBreakdown?.map((item: any) => {
                const info = customsStatusMap[item.status] ?? { label: item.status, color: "" };
                return (
                  <div key={item.status} className="flex items-center justify-between">
                    <Badge variant="secondary" className={info.color}>
                      {info.label}
                    </Badge>
                    <span className="text-sm font-semibold">{item.count}</span>
                  </div>
                );
              })}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* 第三行：最近发票 + 最近批次 */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {/* 最近发票 */}
        <Card>
          <CardHeader className="flex flex-row items-center justify-between">
            <CardTitle className="text-sm font-medium">最近发票</CardTitle>
            <FileText className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            {recentInvoices?.length > 0 ? (
              <div className="border rounded-md overflow-hidden">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead className="text-xs">发票号</TableHead>
                      <TableHead className="text-xs">日期</TableHead>
                      <TableHead className="text-xs text-right">金额</TableHead>
                      <TableHead className="text-xs">状态</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {recentInvoices.map((inv: any) => {
                      const customsInfo = customsStatusMap[inv.customs_status] ?? { label: inv.customs_status, color: "" };
                      return (
                        <TableRow key={inv.id}>
                          <TableCell className="text-sm font-medium">{inv.invoice_no}</TableCell>
                          <TableCell className="text-sm">{inv.invoice_date}</TableCell>
                          <TableCell className="text-sm text-right">
                            ${Number(inv.total_amount_usd).toLocaleString()}
                          </TableCell>
                          <TableCell>
                            <Badge variant="secondary" className={`text-xs ${customsInfo.color}`}>
                              {customsInfo.label}
                            </Badge>
                          </TableCell>
                        </TableRow>
                      );
                    })}
                  </TableBody>
                </Table>
              </div>
            ) : (
              <div className="text-sm text-muted-foreground text-center py-4">
                暂无发票
              </div>
            )}
          </CardContent>
        </Card>

        {/* 最近批次 */}
        <Card>
          <CardHeader className="flex flex-row items-center justify-between">
            <CardTitle className="text-sm font-medium">最近批次</CardTitle>
            <Package className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            {recentBatches?.length > 0 ? (
              <div className="border rounded-md overflow-hidden">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead className="text-xs">批次编号</TableHead>
                      <TableHead className="text-xs">批次名称</TableHead>
                      <TableHead className="text-xs">日期</TableHead>
                      <TableHead className="text-xs">状态</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {recentBatches.map((batch: any) => {
                      const statusInfo = batchStatusMap[batch.status] ?? { label: batch.status, color: "" };
                      return (
                        <TableRow key={batch.id}>
                          <TableCell className="text-sm font-medium text-muted-foreground">{batch.batch_code}</TableCell>
                          <TableCell className="text-sm">{batch.batch_name}</TableCell>
                          <TableCell className="text-sm">{batch.batch_date}</TableCell>
                          <TableCell>
                            <Badge variant="secondary" className={`text-xs ${statusInfo.color}`}>
                              {statusInfo.label}
                            </Badge>
                          </TableCell>
                        </TableRow>
                      );
                    })}
                  </TableBody>
                </Table>
              </div>
            ) : (
              <div className="text-sm text-muted-foreground text-center py-4">
                暂无批次
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
