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
import {
  PieChart,
  Pie,
  Cell,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from "recharts";

const customsStatusMap: Record<string, { label: string; color: string; chartColor: string }> = {
  PENDING_SHIPMENT: { label: "未报关", color: "bg-gray-100 text-gray-800", chartColor: "#6b7280" },
  IN_TRANSIT: { label: "运输中", color: "bg-blue-100 text-blue-800", chartColor: "#3b82f6" },
  PENDING_CUSTOMS: { label: "待报关", color: "bg-yellow-100 text-yellow-800", chartColor: "#eab308" },
  CUSTOMS_PROCESSING: { label: "报关中", color: "bg-orange-100 text-orange-800", chartColor: "#f97316" },
  CLEARED: { label: "已清关", color: "bg-green-100 text-green-800", chartColor: "#22c55e" },
  PICKED_UP: { label: "已提货", color: "bg-purple-100 text-purple-800", chartColor: "#a855f7" },
  pending_shipment: { label: "未报关", color: "bg-gray-100 text-gray-800", chartColor: "#6b7280" },
  in_transit: { label: "运输中", color: "bg-blue-100 text-blue-800", chartColor: "#3b82f6" },
  pending_customs: { label: "待报关", color: "bg-yellow-100 text-yellow-800", chartColor: "#eab308" },
  customs_processing: { label: "报关中", color: "bg-orange-100 text-orange-800", chartColor: "#f97316" },
  cleared: { label: "已清关", color: "bg-green-100 text-green-800", chartColor: "#22c55e" },
  picked_up: { label: "已提货", color: "bg-purple-100 text-purple-800", chartColor: "#a855f7" },
};

const batchStatusMap: Record<string, { label: string; color: string; chartColor: string }> = {
  OPEN: { label: "开放", color: "bg-green-100 text-green-800", chartColor: "#22c55e" },
  LOCKED: { label: "已锁定", color: "bg-orange-100 text-orange-800", chartColor: "#f97316" },
  SETTLED: { label: "已结算", color: "bg-blue-100 text-blue-800", chartColor: "#3b82f6" },
  open: { label: "开放", color: "bg-green-100 text-green-800", chartColor: "#22c55e" },
  locked: { label: "已锁定", color: "bg-orange-100 text-orange-800", chartColor: "#f97316" },
  settled: { label: "已结算", color: "bg-blue-100 text-blue-800", chartColor: "#3b82f6" },
};

const companyColors: Record<string, string> = {
  processing_plant: "#3b82f6",
  fish_farm: "#22c55e",
  exporter: "#a855f7",
  supplier: "#f97316",
  customer: "#06b6d4",
  customs_broker: "#ec4899",
  logistics: "#6366f1",
  internal: "#8b5cf6",
};

const companyLabels: Record<string, string> = {
  processing_plant: "加工厂",
  fish_farm: "渔场",
  exporter: "出口商",
  supplier: "供应商",
  customer: "客户",
  customs_broker: "报关行",
  logistics: "物流",
  internal: "内部",
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

  const { data: monthlyTrend } = useQuery({
    queryKey: ["dashboard-monthly-trend"],
    queryFn: async () => {
      const res = await api.get("/v1/dashboard/invoice-monthly-trend?months=6");
      return res.data;
    },
  });

  // 报关状态饼图数据
  const customsPieData =
    customsBreakdown?.map((item: any) => ({
      name: customsStatusMap[item.status]?.label || item.status,
      value: item.count,
      color: customsStatusMap[item.status]?.chartColor || "#6b7280",
    })) || [];

  // 批次状态饼图数据
  const batchPieData = summary?.batches
    ? [
        { name: "开放", value: summary.batches.open || 0, color: "#22c55e" },
        { name: "已锁定", value: summary.batches.locked || 0, color: "#f97316" },
        { name: "已结算", value: summary.batches.settled || 0, color: "#3b82f6" },
      ].filter((d) => d.value > 0)
    : [];

  // 主体类型柱状图数据
  const companyBarData = summary?.companies?.breakdown
    ? Object.entries(summary.companies.breakdown).map(([type, count]) => ({
        name: companyLabels[type] || type,
        count: count as number,
        color: companyColors[type] || "#6b7280",
      }))
    : [];

  const totalCustoms = customsPieData.reduce((sum: number, d: any) => sum + d.value, 0) || 1;
  const totalBatches = batchPieData.reduce((sum: number, d: any) => sum + d.value, 0) || 1;

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

      {/* 第二行：月度趋势 + 报关状态饼图 */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {/* 发票月度趋势 */}
        <Card>
          <CardHeader className="flex flex-row items-center justify-between">
            <CardTitle className="text-sm font-medium">发票月度趋势</CardTitle>
            <BarChart3 className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent className="h-[260px]">
            {monthlyTrend?.length > 0 ? (
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={monthlyTrend} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                  <XAxis
                    dataKey="month"
                    tick={{ fontSize: 12 }}
                    stroke="#6b7280"
                  />
                  <YAxis
                    tick={{ fontSize: 12 }}
                    stroke="#6b7280"
                    tickFormatter={(v) => `$${(v / 1000).toFixed(0)}k`}
                  />
                  <Tooltip
                    formatter={(value: any) => [`$${Number(value).toLocaleString()}`, "金额"]}
                    contentStyle={{ borderRadius: "8px", fontSize: "12px" }}
                  />
                  <Bar dataKey="amount" fill="#3b82f6" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            ) : (
              <div className="flex items-center justify-center h-full text-sm text-muted-foreground">
                暂无月度数据
              </div>
            )}
          </CardContent>
        </Card>

        {/* 报关状态饼图 */}
        <Card>
          <CardHeader>
            <CardTitle className="text-sm font-medium">报关状态分布</CardTitle>
          </CardHeader>
          <CardContent className="h-[260px]">
            {customsPieData.length > 0 ? (
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={customsPieData}
                    cx="50%"
                    cy="50%"
                    innerRadius={60}
                    outerRadius={90}
                    paddingAngle={3}
                    dataKey="value"
                  >
                    {customsPieData.map((entry: any, index: number) => (
                      <Cell key={`cell-${index}`} fill={entry.color} />
                    ))}
                  </Pie>
                  <Tooltip
                    formatter={(value: any, name: any) => [
                      `${value} 张 (${((value / totalCustoms) * 100).toFixed(1)}%)`,
                      name,
                    ]}
                    contentStyle={{ borderRadius: "8px", fontSize: "12px" }}
                  />
                  <Legend
                    verticalAlign="bottom"
                    height={36}
                    iconType="circle"
                    formatter={(value: any) => (
                      <span className="text-xs text-muted-foreground">{value}</span>
                    )}
                  />
                </PieChart>
              </ResponsiveContainer>
            ) : (
              <div className="flex items-center justify-center h-full text-sm text-muted-foreground">
                暂无报关数据
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      {/* 第三行：批次状态 + 主体分布 */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {/* 批次状态饼图 */}
        <Card>
          <CardHeader>
            <CardTitle className="text-sm font-medium">批次状态分布</CardTitle>
          </CardHeader>
          <CardContent className="h-[260px]">
            {batchPieData.length > 0 ? (
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={batchPieData}
                    cx="50%"
                    cy="50%"
                    innerRadius={60}
                    outerRadius={90}
                    paddingAngle={3}
                    dataKey="value"
                  >
                    {batchPieData.map((entry: any, index: number) => (
                      <Cell key={`cell-${index}`} fill={entry.color} />
                    ))}
                  </Pie>
                  <Tooltip
                    formatter={(value: any, name: any) => [
                      `${value} 个 (${((value / totalBatches) * 100).toFixed(1)}%)`,
                      name,
                    ]}
                    contentStyle={{ borderRadius: "8px", fontSize: "12px" }}
                  />
                  <Legend
                    verticalAlign="bottom"
                    height={36}
                    iconType="circle"
                    formatter={(value: any) => (
                      <span className="text-xs text-muted-foreground">{value}</span>
                    )}
                  />
                </PieChart>
              </ResponsiveContainer>
            ) : (
              <div className="flex items-center justify-center h-full text-sm text-muted-foreground">
                暂无批次数据
              </div>
            )}
          </CardContent>
        </Card>

        {/* 主体类型柱状图 */}
        <Card>
          <CardHeader>
            <CardTitle className="text-sm font-medium">主体类型分布</CardTitle>
          </CardHeader>
          <CardContent className="h-[260px]">
            {companyBarData.length > 0 ? (
              <ResponsiveContainer width="100%" height="100%">
                <BarChart
                  data={companyBarData}
                  layout="vertical"
                  margin={{ top: 10, right: 10, left: 10, bottom: 0 }}
                >
                  <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" horizontal={false} />
                  <XAxis type="number" tick={{ fontSize: 12 }} stroke="#6b7280" />
                  <YAxis
                    type="category"
                    dataKey="name"
                    tick={{ fontSize: 12 }}
                    stroke="#6b7280"
                    width={70}
                  />
                  <Tooltip
                    formatter={(value: any) => [value, "数量"]}
                    contentStyle={{ borderRadius: "8px", fontSize: "12px" }}
                  />
                  <Bar dataKey="count" radius={[0, 4, 4, 0]}>
                    {companyBarData.map((entry: any, index: number) => (
                      <Cell key={`cell-${index}`} fill={entry.color} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            ) : (
              <div className="flex items-center justify-center h-full text-sm text-muted-foreground">
                暂无主体数据
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      {/* 第四行：最近发票 + 最近批次 */}
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
              <div className="text-sm text-muted-foreground text-center py-4">暂无发票</div>
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
              <div className="text-sm text-muted-foreground text-center py-4">暂无批次</div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
