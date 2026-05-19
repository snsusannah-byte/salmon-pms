import React, { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from "@/components/ui/table";
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from "@/components/ui/select";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  Search, Fish, Factory, Package, ArrowRight, ArrowLeftRight, Circle, CheckCircle2,
  AlertCircle, FileText, Ship, ClipboardList, ShoppingCart
} from "lucide-react";
import { toast } from "sonner";

// ==================== 类型 ====================
interface TraceSummary {
  total: number;
  in_progress: number;
  completed: number;
  total_source_weight_kg: number;
  total_sold_weight_kg: number;
}

interface TraceItem {
  id: number;
  trace_status: string;
  source_type: string;
  // 原料端
  source_invoice_id?: number;
  source_invoice_no?: string;
  source_batch_id?: number;
  source_batch_no?: string;
  source_product_id?: number;
  source_product_name?: string;
  source_weight_kg: number;
  // 中间环节
  internal_sale_id?: number;
  processor_name?: string;
  slaughter_record_id?: number;
  slaughter_date?: string;
  // 成品端
  finished_product_sale_id?: number;
  finished_customer_name?: string;
  finished_weight_kg: number;
  sold_weight_kg: number;
  created_at: string;
  updated_at: string;
}

interface ImportInvoice {
  id: number;
  invoice_no: string;
  invoice_date: string;
}

// ==================== API 函数 ====================
const fetchTraceSummary = async (): Promise<TraceSummary> => {
  const { data } = await api.get("/v1/traceability/traces/summary");
  return data;
};

const fetchTraces = async (params: Record<string, any>): Promise<{ total: number; items: TraceItem[] }> => {
  const { data } = await api.get("/v1/traceability/traces", { params });
  return data;
};

const fetchTraceByInvoice = async (invoiceId: number): Promise<TraceItem[]> => {
  const { data } = await api.get(`/v1/traceability/traces/by-invoice/${invoiceId}`);
  return data.items;
};

const fetchInvoices = async (): Promise<ImportInvoice[]> => {
  const { data } = await api.get("/v1/invoices?limit=500");
  return data.items;
};

// ==================== 辅助函数 ====================
const getStatusBadge = (status: string) => {
  switch (status) {
    case "completed":
      return <Badge className="bg-green-100 text-green-800 flex items-center gap-1"><CheckCircle2 className="h-3 w-3" />已完成</Badge>;
    case "in_progress":
      return <Badge className="bg-blue-100 text-blue-800 flex items-center gap-1"><Circle className="h-3 w-3" />进行中</Badge>;
    default:
      return <Badge className="bg-gray-100 text-gray-800">{status}</Badge>;
  }
};

const getSourceTypeLabel = (type: string) => {
  const map: Record<string, string> = { import: "进口", domestic: "国内采购" };
  return map[type] || type;
};

const fmt = (n?: number) => {
  if (n === undefined || n === null) return "-";
  return n.toLocaleString("zh-CN", { minimumFractionDigits: 2, maximumFractionDigits: 3 });
};

// ==================== 追溯链卡片 ====================
function TraceChainCard({ trace }: { trace: TraceItem }) {
  return (
    <Card className="mb-4">
      <CardContent className="p-4">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-2">
            <span className="text-sm font-medium text-gray-500">追溯链 #{trace.id}</span>
            {getStatusBadge(trace.trace_status)}
          </div>
          <span className="text-xs text-gray-400">{trace.created_at?.split("T")[0]}</span>
        </div>

        {/* 流程图 */}
        <div className="flex items-center gap-2 text-sm">
          {/* 原料端 */}
          <div className="flex-1 bg-orange-50 border border-orange-200 rounded-lg p-3">
            <div className="flex items-center gap-1 mb-1 text-orange-700">
              <Ship className="h-4 w-4" />
              <span className="font-medium">原料端</span>
            </div>
            <div className="text-xs text-gray-600 space-y-0.5">
              <div>发票: {trace.source_invoice_no || "-"}</div>
              <div>产品: {trace.source_product_name || "-"}</div>
              <div>重量: {fmt(trace.source_weight_kg)} kg</div>
            </div>
          </div>

          <ArrowRight className="h-4 w-4 text-gray-400 flex-shrink-0" />

          {/* 中间环节 */}
          <div className="flex-1 bg-blue-50 border border-blue-200 rounded-lg p-3">
            <div className="flex items-center gap-1 mb-1 text-blue-700">
              <Factory className="h-4 w-4" />
              <span className="font-medium">加工环节</span>
            </div>
            <div className="text-xs text-gray-600 space-y-0.5">
              <div>加工厂: {trace.processor_name || "-"}</div>
              <div>宰杀日期: {trace.slaughter_date || "-"}</div>
              <div>产出: {fmt(trace.finished_weight_kg)} kg</div>
            </div>
          </div>

          <ArrowRight className="h-4 w-4 text-gray-400 flex-shrink-0" />

          {/* 成品端 */}
          <div className="flex-1 bg-green-50 border border-green-200 rounded-lg p-3">
            <div className="flex items-center gap-1 mb-1 text-green-700">
              <ShoppingCart className="h-4 w-4" />
              <span className="font-medium">销售端</span>
            </div>
            <div className="text-xs text-gray-600 space-y-0.5">
              <div>客户: {trace.finished_customer_name || "-"}</div>
              <div>销售重量: {fmt(trace.sold_weight_kg)} kg</div>
              <div>完成度: {trace.source_weight_kg > 0 ? ((trace.sold_weight_kg / trace.source_weight_kg) * 100).toFixed(1) : 0}%</div>
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

// ==================== 追溯列表 ====================
function TraceList({ status }: { status?: string }) {
  const { data, isLoading } = useQuery({
    queryKey: ["traceability-traces", status],
    queryFn: () => fetchTraces({ status, limit: 100 }),
  });

  const items = data?.items || [];

  return (
    <div className="space-y-4">
      {isLoading ? (
        <div className="text-center py-8">加载中...</div>
      ) : items.length === 0 ? (
        <div className="text-center py-12 text-gray-500">
          <AlertCircle className="h-8 w-8 mx-auto mb-2 text-gray-400" />
          <p>暂无追溯记录</p>
          <p className="text-sm mt-1">追溯链会在业务操作（进口→内部销售→宰杀→成品销售）后自动生成</p>
        </div>
      ) : (
        items.map((trace) => <TraceChainCard key={trace.id} trace={trace} />)
      )}
    </div>
  );
}

// ==================== 按发票查询 ====================
function TraceByInvoice() {
  const [invoiceId, setInvoiceId] = useState("");
  const [selectedInvoice, setSelectedInvoice] = useState<number | null>(null);

  const { data: invoices } = useQuery({
    queryKey: ["invoices-for-trace"],
    queryFn: fetchInvoices,
  });

  const { data: traces, isLoading } = useQuery({
    queryKey: ["trace-by-invoice", selectedInvoice],
    queryFn: () => selectedInvoice ? fetchTraceByInvoice(selectedInvoice) : Promise.resolve([]),
    enabled: !!selectedInvoice,
  });

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-4">
        <div className="flex-1 max-w-sm">
          <Label className="mb-2 block">选择进口发票</Label>
          <Select
            value={selectedInvoice ? String(selectedInvoice) : ""}
            onValueChange={(v) => setSelectedInvoice(Number(v))}
          >
            <SelectTrigger>
              <SelectValue placeholder="选择发票..." />
            </SelectTrigger>
            <SelectContent>
              {invoices?.map((inv) => (
                <SelectItem key={inv.id} value={String(inv.id)}>
                  {inv.invoice_no} ({inv.invoice_date})
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
      </div>

      {isLoading && <div className="text-center py-8">查询中...</div>}

      {traces && traces.length > 0 && (
        <div className="space-y-4">
          <div className="text-sm text-gray-500">
            找到 {traces.length} 条追溯记录
          </div>
          {traces.map((trace) => <TraceChainCard key={trace.id} trace={trace} />)}
        </div>
      )}

      {traces && traces.length === 0 && selectedInvoice && (
        <div className="text-center py-8 text-gray-500">
          <AlertCircle className="h-8 w-8 mx-auto mb-2 text-gray-400" />
          <p>该发票暂无追溯记录</p>
          <p className="text-sm mt-1">这批鱼可能尚未完成成品销售流程</p>
        </div>
      )}
    </div>
  );
}

// ==================== 统计卡片 ====================
function SummaryCards({ summary }: { summary: TraceSummary }) {
  return (
    <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
      <Card>
        <CardContent className="p-4">
          <div className="flex items-center gap-2 mb-2">
            <ClipboardList className="h-4 w-4 text-blue-600" />
            <span className="text-sm text-gray-500">总追溯链</span>
          </div>
          <div className="text-2xl font-bold">{summary.total}</div>
        </CardContent>
      </Card>
      <Card>
        <CardContent className="p-4">
          <div className="flex items-center gap-2 mb-2">
            <Circle className="h-4 w-4 text-blue-600" />
            <span className="text-sm text-gray-500">进行中</span>
          </div>
          <div className="text-2xl font-bold">{summary.in_progress}</div>
        </CardContent>
      </Card>
      <Card>
        <CardContent className="p-4">
          <div className="flex items-center gap-2 mb-2">
            <CheckCircle2 className="h-4 w-4 text-green-600" />
            <span className="text-sm text-gray-500">已完成</span>
          </div>
          <div className="text-2xl font-bold">{summary.completed}</div>
        </CardContent>
      </Card>
      <Card>
        <CardContent className="p-4">
          <div className="flex items-center gap-2 mb-2">
            <FileText className="h-4 w-4 text-orange-600" />
            <span className="text-sm text-gray-500">原料总重量</span>
          </div>
          <div className="text-2xl font-bold">{fmt(summary.total_source_weight_kg)} <span className="text-sm font-normal">kg</span></div>
        </CardContent>
      </Card>
    </div>
  );
}

// ==================== 主页面 ====================
export function TraceabilityPage() {
  const [activeTab, setActiveTab] = useState("all");

  const { data: summary, isLoading: summaryLoading } = useQuery({
    queryKey: ["traceability-summary"],
    queryFn: fetchTraceSummary,
  });

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold flex items-center gap-2">
          <ArrowLeftRight className="h-6 w-6" />
          追溯查询
        </h1>
      </div>

      {/* 说明 */}
      <Card className="bg-blue-50 border-blue-200">
        <CardContent className="p-4">
          <div className="flex items-start gap-3">
            <Fish className="h-5 w-5 text-blue-600 mt-0.5" />
            <div className="text-sm text-blue-800">
              <p className="font-medium mb-1">追溯流程：进口鱼 → 内部销售 → 宰杀分切 → 成品销售</p>
              <p>系统会自动记录"这批进口鱼最终卖给了谁"。选择进口发票即可查看完整追溯链。</p>
            </div>
          </div>
        </CardContent>
      </Card>

      {summary && <SummaryCards summary={summary} />}

      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList className="grid w-full grid-cols-3 lg:w-auto lg:inline-flex">
          <TabsTrigger value="all">全部追溯</TabsTrigger>
          <TabsTrigger value="by-invoice">按发票查询</TabsTrigger>
          <TabsTrigger value="docs">操作说明</TabsTrigger>
        </TabsList>

        <TabsContent value="all" className="mt-4">
          <TraceList />
        </TabsContent>

        <TabsContent value="by-invoice" className="mt-4">
          <TraceByInvoice />
        </TabsContent>

        <TabsContent value="docs" className="mt-4">
          <Card>
            <CardHeader>
              <CardTitle>追溯系统使用说明</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4 text-sm">
              <div>
                <h3 className="font-semibold mb-2">追溯流程</h3>
                <ol className="list-decimal list-inside space-y-1 text-gray-600">
                  <li><strong>进口发票</strong>确认到港 → 系统自动创建追溯链起点</li>
                  <li>内部销售给加工厂（亘昌贸易/绍兴优逸） → 关联到追溯链</li>
                  <li><strong>宰杀记录</strong>创建 → 记录分切产出重量</li>
                  <li><strong>成品销售</strong>完成 → 关联终端客户，标记追溯完成</li>
                </ol>
              </div>
              <div>
                <h3 className="font-semibold mb-2">查询方式</h3>
                <ul className="list-disc list-inside space-y-1 text-gray-600">
                  <li><strong>按发票查询</strong>：输入进口发票号，查看这批鱼的完整流向</li>
                  <li><strong>按批次查询</strong>：通过批次号追踪</li>
                  <li><strong>按成品销售查询</strong>：反向追溯成品来自哪批进口鱼</li>
                </ul>
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}
