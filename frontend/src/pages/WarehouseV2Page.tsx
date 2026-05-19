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
  Search, Package, Warehouse, ArrowDown, ArrowUp, AlertTriangle,
  Boxes, Fish, Shrimp, Wrench, Recycle, Plus
} from "lucide-react";
import { toast } from "sonner";
import { StockInboundDialog, StockOutboundDialog, StockTransferDialog } from "@/components/StockOperationDialogs";

// ==================== 类型 ====================
interface Warehouse {
  id: number;
  code: string;
  name: string;
  type: string;
  business_scope: string;
  is_active: boolean;
}

interface Stock {
  id: number;
  warehouse_id: number;
  warehouse_name: string;
  product_id: number;
  product_name: string;
  product_category: string;
  batch_id?: number;
  batch_no?: string;
  current_qty: number;
  reserved_qty: number;
  available_qty: number;
  unit_cost?: number;
  total_cost?: number;
  unit: string;
  warning_threshold: number;
  is_below_warning: boolean;
  last_in_date?: string;
  last_out_date?: string;
  location?: string;
}

interface StockSummary {
  warehouse_id: number;
  warehouse_name: string;
  warehouse_type: string;
  product_count: number;
  total_qty: number;
  total_cost: number;
}

interface StockMovement {
  id: number;
  warehouse_name: string;
  product_name: string;
  movement_type: string;
  movement_date: string;
  qty_change: number;
  qty_before: number;
  qty_after: number;
  unit: string;
  ref_type: string;
  ref_no?: string;
}

// ==================== API 函数 ====================
const fetchWarehouses = async () => {
  const { data } = await api.get("/v1/warehouse-v2/warehouses");
  return data.items as Warehouse[];
};

const fetchStocks = async (params: Record<string, any>) => {
  const { data } = await api.get("/v1/warehouse-v2/stocks", { params });
  return data;
};

const fetchStockSummary = async () => {
  const { data } = await api.get("/v1/warehouse-v2/stocks/summary");
  return data.items as StockSummary[];
};

const fetchMovements = async (params: Record<string, any>) => {
  const { data } = await api.get("/v1/warehouse-v2/movements", { params });
  return data;
};

// ==================== 辅助函数 ====================
const getWarehouseIcon = (type: string) => {
  switch (type) {
    case "WHOLE_PACKAGE": return <Boxes className="h-4 w-4" />;
    case "SUB_PACKAGE": return <Fish className="h-4 w-4" />;
    case "ACCESSORY": return <Wrench className="h-4 w-4" />;
    case "BYPRODUCT": return <Recycle className="h-4 w-4" />;
    case "FINISHED": return <Package className="h-4 w-4" />;
    default: return <Warehouse className="h-4 w-4" />;
  }
};

const getWarehouseTypeLabel = (type: string) => {
  const map: Record<string, string> = {
    WHOLE_PACKAGE: "整包仓",
    SUB_PACKAGE: "分包仓",
    ACCESSORY: "辅料仓",
    BYPRODUCT: "副产品仓",
    FINISHED: "成品仓",
  };
  return map[type] || type;
};

const getBusinessScopeLabel = (scope: string) => {
  const map: Record<string, string> = {
    IMPORT: "进口单证",
    DOMESTIC: "国内业务",
    ALL: "通用",
  };
  return map[scope] || scope;
};

const getMovementTypeLabel = (type: string) => {
  const map: Record<string, string> = {
    inbound: "入库",
    outbound: "出库",
    transfer_in: "调拨入",
    transfer_out: "调拨出",
    adjustment: "盘点调整",
  };
  return map[type] || type;
};

const getMovementTypeBadge = (type: string) => {
  const variantMap: Record<string, string> = {
    inbound: "bg-green-100 text-green-800",
    outbound: "bg-red-100 text-red-800",
    transfer_in: "bg-blue-100 text-blue-800",
    transfer_out: "bg-orange-100 text-orange-800",
    adjustment: "bg-yellow-100 text-yellow-800",
  };
  return variantMap[type] || "bg-gray-100 text-gray-800";
};

const fmt = (n?: number) => {
  if (n === undefined || n === null) return "-";
  return n.toLocaleString("zh-CN", { minimumFractionDigits: 2, maximumFractionDigits: 3 });
};

// ==================== 库存汇总卡片 ====================
function SummaryCards({ summary }: { summary: StockSummary[] }) {
  return (
    <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4 mb-6">
      {summary.map((s) => (
        <Card key={s.warehouse_id} className="cursor-pointer hover:shadow-md transition-shadow">
          <CardContent className="p-4">
            <div className="flex items-center gap-2 mb-2">
              {getWarehouseIcon(s.warehouse_type)}
              <span className="text-sm font-medium text-gray-600">{s.warehouse_name}</span>
            </div>
            <div className="text-2xl font-bold">{s.product_count}</div>
            <div className="text-xs text-gray-500">种产品</div>
            <div className="mt-2 text-sm">
              <span className="text-gray-500">数量: </span>
              <span className="font-semibold">{fmt(s.total_qty)}</span>
            </div>
            <div className="text-sm">
              <span className="text-gray-500">金额: </span>
              <span className="font-semibold">¥{fmt(s.total_cost)}</span>
            </div>
          </CardContent>
        </Card>
      ))}
    </div>
  );
}

// ==================== 库存列表 ====================
function StockList({
  warehouseId,
  productId,
  isBelowWarning,
}: {
  warehouseId?: number;
  productId?: number;
  isBelowWarning?: boolean;
}) {
  const [search, setSearch] = useState("");
  const { data, isLoading } = useQuery({
    queryKey: ["warehouse-v2-stocks", warehouseId, productId, isBelowWarning],
    queryFn: () => fetchStocks({ warehouse_id: warehouseId, product_id: productId, is_below_warning: isBelowWarning, limit: 500 }),
  });

  const items: Stock[] = data?.items || [];
  const filtered = items.filter((s) =>
    s.product_name?.toLowerCase().includes(search.toLowerCase()) ||
    s.warehouse_name?.toLowerCase().includes(search.toLowerCase())
  );

  return (
    <div>
      <div className="flex items-center gap-4 mb-4">
        <div className="relative flex-1 max-w-sm">
          <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-gray-400" />
          <Input
            placeholder="搜索产品或仓库..."
            className="pl-8"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>
        <span className="text-sm text-gray-500">共 {filtered.length} 条</span>
      </div>

      <div className="border rounded-md">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>仓库</TableHead>
              <TableHead>产品</TableHead>
              <TableHead>分类</TableHead>
              <TableHead className="text-right">当前数量</TableHead>
              <TableHead className="text-right">可用数量</TableHead>
              <TableHead className="text-right">单位成本</TableHead>
              <TableHead className="text-right">总成本</TableHead>
              <TableHead>状态</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {isLoading ? (
              <TableRow>
                <TableCell colSpan={8} className="text-center py-8">加载中...</TableCell>
              </TableRow>
            ) : filtered.length === 0 ? (
              <TableRow>
                <TableCell colSpan={8} className="text-center py-8 text-gray-500">暂无库存记录</TableCell>
              </TableRow>
            ) : (
              filtered.map((s) => (
                <TableRow key={s.id}>
                  <TableCell>
                    <div className="flex items-center gap-1">
                      {getWarehouseIcon("")}
                      <span className="text-sm">{s.warehouse_name}</span>
                    </div>
                  </TableCell>
                  <TableCell className="font-medium">{s.product_name}</TableCell>
                  <TableCell>
                    <Badge variant="outline">{s.product_category}</Badge>
                  </TableCell>
                  <TableCell className="text-right">{fmt(s.current_qty)} {s.unit}</TableCell>
                  <TableCell className="text-right">{fmt(s.available_qty)} {s.unit}</TableCell>
                  <TableCell className="text-right">¥{fmt(s.unit_cost)}</TableCell>
                  <TableCell className="text-right">¥{fmt(s.total_cost)}</TableCell>
                  <TableCell>
                    {s.is_below_warning ? (
                      <Badge className="bg-red-100 text-red-800 flex items-center gap-1">
                        <AlertTriangle className="h-3 w-3" />
                        预警
                      </Badge>
                    ) : (
                      <Badge className="bg-green-100 text-green-800">正常</Badge>
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

// ==================== 库存变动列表 ====================
function MovementList() {
  const [movementType, setMovementType] = useState<string>("");
  const { data, isLoading } = useQuery({
    queryKey: ["warehouse-v2-movements", movementType],
    queryFn: () => fetchMovements({ movement_type: movementType || undefined, limit: 200 }),
  });

  const items: StockMovement[] = data?.items || [];

  return (
    <div>
      <div className="flex items-center gap-4 mb-4">
        <Select value={movementType} onValueChange={setMovementType}>
          <SelectTrigger className="w-40">
            <SelectValue placeholder="变动类型" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="">全部</SelectItem>
            <SelectItem value="inbound">入库</SelectItem>
            <SelectItem value="outbound">出库</SelectItem>
            <SelectItem value="transfer_in">调拨入</SelectItem>
            <SelectItem value="transfer_out">调拨出</SelectItem>
            <SelectItem value="adjustment">盘点调整</SelectItem>
          </SelectContent>
        </Select>
        <span className="text-sm text-gray-500">共 {items.length} 条</span>
      </div>

      <div className="border rounded-md">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>日期</TableHead>
              <TableHead>仓库</TableHead>
              <TableHead>产品</TableHead>
              <TableHead>类型</TableHead>
              <TableHead className="text-right">变动数量</TableHead>
              <TableHead className="text-right">变动前</TableHead>
              <TableHead className="text-right">变动后</TableHead>
              <TableHead>关联单据</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {isLoading ? (
              <TableRow><TableCell colSpan={8} className="text-center py-8">加载中...</TableCell></TableRow>
            ) : items.length === 0 ? (
              <TableRow><TableCell colSpan={8} className="text-center py-8 text-gray-500">暂无变动记录</TableCell></TableRow>
            ) : (
              items.map((m) => (
                <TableRow key={m.id}>
                  <TableCell>{m.movement_date}</TableCell>
                  <TableCell>{m.warehouse_name}</TableCell>
                  <TableCell>{m.product_name}</TableCell>
                  <TableCell>
                    <Badge className={getMovementTypeBadge(m.movement_type)}>
                      {getMovementTypeLabel(m.movement_type)}
                    </Badge>
                  </TableCell>
                  <TableCell className={`text-right font-medium ${m.qty_change > 0 ? "text-green-600" : "text-red-600"}`}>
                    {m.qty_change > 0 ? "+" : ""}{fmt(m.qty_change)} {m.unit}
                  </TableCell>
                  <TableCell className="text-right text-gray-500">{fmt(m.qty_before)}</TableCell>
                  <TableCell className="text-right">{fmt(m.qty_after)}</TableCell>
                  <TableCell className="text-sm text-gray-500">
                    {m.ref_type} {m.ref_no}
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

// ==================== 仓库定义列表 ====================
function WarehouseListView() {
  const { data } = useQuery({
    queryKey: ["warehouse-v2-warehouses"],
    queryFn: fetchWarehouses,
  });

  const items = data || [];

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
      {items.map((w) => (
        <Card key={w.id} className={!w.is_active ? "opacity-60" : ""}>
          <CardHeader className="pb-2">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                {getWarehouseIcon(w.type)}
                <CardTitle className="text-lg">{w.name}</CardTitle>
              </div>
              <Badge variant={w.is_active ? "default" : "secondary"}>
                {w.is_active ? "启用" : "停用"}
              </Badge>
            </div>
          </CardHeader>
          <CardContent>
            <div className="space-y-2 text-sm">
              <div className="flex justify-between">
                <span className="text-gray-500">编码</span>
                <span className="font-mono">{w.code}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-500">类型</span>
                <span>{getWarehouseTypeLabel(w.type)}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-500">业务范围</span>
                <span>{getBusinessScopeLabel(w.business_scope)}</span>
              </div>
              {w.notes && (
                <div className="text-gray-500 pt-2 border-t">{w.notes}</div>
              )}
            </div>
          </CardContent>
        </Card>
      ))}
    </div>
  );
}

// ==================== 主页面 ====================
export function WarehouseV2Page() {
  const [activeTab, setActiveTab] = useState("stocks");
  const [inboundOpen, setInboundOpen] = useState(false);
  const [outboundOpen, setOutboundOpen] = useState(false);
  const [transferOpen, setTransferOpen] = useState(false);

  const { data: summary } = useQuery({
    queryKey: ["warehouse-v2-summary"],
    queryFn: fetchStockSummary,
  });

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold flex items-center gap-2">
          <Warehouse className="h-6 w-6" />
          仓库管理V2
        </h1>
        <div className="flex items-center gap-2">
          <Button variant="outline" size="sm" onClick={() => setInboundOpen(true)}>
            <ArrowDown className="h-4 w-4 mr-1 text-green-600" />
            入库
          </Button>
          <Button variant="outline" size="sm" onClick={() => setOutboundOpen(true)}>
            <ArrowUp className="h-4 w-4 mr-1 text-red-600" />
            出库
          </Button>
          <Button variant="outline" size="sm" onClick={() => setTransferOpen(true)}>
            <Boxes className="h-4 w-4 mr-1 text-blue-600" />
            调拨
          </Button>
        </div>
      </div>

      <StockInboundDialog open={inboundOpen} onOpenChange={setInboundOpen} />
      <StockOutboundDialog open={outboundOpen} onOpenChange={setOutboundOpen} />
      <StockTransferDialog open={transferOpen} onOpenChange={setTransferOpen} />

      {summary && <SummaryCards summary={summary} />}

      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList className="grid w-full grid-cols-4 lg:w-auto lg:inline-flex">
          <TabsTrigger value="stocks">库存查询</TabsTrigger>
          <TabsTrigger value="movements">库存变动</TabsTrigger>
          <TabsTrigger value="warehouses">仓库定义</TabsTrigger>
          <TabsTrigger value="docs">操作说明</TabsTrigger>
        </TabsList>

        <TabsContent value="stocks" className="mt-4">
          <StockList />
        </TabsContent>

        <TabsContent value="movements" className="mt-4">
          <MovementList />
        </TabsContent>

        <TabsContent value="warehouses" className="mt-4">
          <WarehouseListView />
        </TabsContent>

        <TabsContent value="docs" className="mt-4">
          <Card>
            <CardHeader>
              <CardTitle>仓库模块使用说明</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4 text-sm">
              <div>
                <h3 className="font-semibold mb-1">仓库类型</h3>
                <ul className="list-disc list-inside space-y-1 text-gray-600">
                  <li><strong>整包仓</strong>：按箱管理（进口/国内采购的整鱼）</li>
                  <li><strong>分包仓</strong>：按条/板/只管理（分切后的产品）</li>
                  <li><strong>辅料仓</strong>：包装物、消耗品</li>
                  <li><strong>副产品仓</strong>：鱼头、鱼尾、鱼骨、边角料</li>
                </ul>
              </div>
              <div>
                <h3 className="font-semibold mb-1">业务流程</h3>
                <ol className="list-decimal list-inside space-y-1 text-gray-600">
                  <li>进口发票到港 → 入库到 ZB-IMPORT（整包仓）</li>
                  <li>整鱼销售 → 从 ZB-IMPORT 出库</li>
                  <li>调拨到分包仓 → ZB-IMPORT → FB-FISH（箱→条）</li>
                  <li>分包仓单条销售 → 从 FB-FISH 出库</li>
                </ol>
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}
