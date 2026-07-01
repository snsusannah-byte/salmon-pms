import React, { useState, useMemo } from "react";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from "@/components/ui/table";
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from "@/components/ui/select";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from "@/components/ui/dialog";
import {
  Search, Package, Warehouse, ArrowDown, ArrowUp, AlertTriangle,
  Boxes, Fish, Shrimp, Wrench, Recycle, Plus, X
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
  notes?: string | null;
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
  lead_time?: number;
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

const getProductCategoryLabel = (category: string) => {
  const map: Record<string, string> = {
    whole_fish: "整鱼",
    fillet: "鱼柳",
    finished_product: "成品",
    byproduct: "副产品",
    packaging: "包装物料",
    accessory: "配套",
    bom_material: "BOM物料",
  };
  return map[category] || category;
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

const fmt = (n?: number | string | null, digits = 2) => {
  if (n === undefined || n === null || n === "") return "-";
  const num = Number(n);
  if (isNaN(num)) return "-";
  return num.toLocaleString("zh-CN", { minimumFractionDigits: digits, maximumFractionDigits: digits });
};

// ==================== 产品汇总库存查询 ====================
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
  const [selectedWarehouse, setSelectedWarehouse] = useState<string>("");
  const [selectedProduct, setSelectedProduct] = useState<{
    product_id: number;
    product_name: string;
    product_category: string;
  } | null>(null);
  const [movementDialogOpen, setMovementDialogOpen] = useState(false);
  const [movementStock, setMovementStock] = useState<{
    warehouse_id: number;
    warehouse_name: string;
    product_id: number;
    product_name: string;
  } | null>(null);

  const { data, isLoading } = useQuery({
    queryKey: ["warehouse-v2-stocks", warehouseId, productId, isBelowWarning],
    queryFn: () => fetchStocks({ warehouse_id: warehouseId, product_id: productId, is_below_warning: isBelowWarning, limit: 500 }),
  });

  const items: Stock[] = data?.items || [];

  // 按产品汇总（确保所有数值为 Number 类型，防止字符串拼接）
  const groupedByProduct = useMemo(() => {
    const map = new Map<number, { product_id: number; product_name: string; product_category: string; unit: string; total_current: number; total_available: number; total_cost: number; avg_unit_cost: number; details: Stock[]; is_below_warning: boolean; warehouse_names: string[]; lead_time?: number }>();
    items.forEach((s) => {
      const qty = Number(s.current_qty) || 0;
      const avail = Number(s.available_qty) || 0;
      const cost = Number(s.total_cost) || 0;
      const uCost = Number(s.unit_cost) || 0;
      const existing = map.get(s.product_id);
      if (existing) {
        existing.total_current += qty;
        existing.total_available += avail;
        existing.total_cost += cost;
        existing.details.push(s);
        if (!existing.warehouse_names.includes(s.warehouse_name)) {
          existing.warehouse_names.push(s.warehouse_name);
        }
        if (s.is_below_warning) existing.is_below_warning = true;
        // 如果有更新的 lead_time，更新它
        if (s.lead_time !== undefined && s.lead_time !== null) {
          existing.lead_time = s.lead_time;
        }
      } else {
        map.set(s.product_id, {
          product_id: s.product_id,
          product_name: s.product_name,
          product_category: s.product_category,
          unit: s.unit,
          total_current: qty,
          total_available: avail,
          total_cost: cost,
          avg_unit_cost: uCost,
          details: [s],
          is_below_warning: s.is_below_warning,
          warehouse_names: [s.warehouse_name],
          lead_time: s.lead_time,
        });
      }
    });
    // 重新计算平均成本
    map.forEach((g) => {
      if (g.total_current > 0) {
        g.avg_unit_cost = g.total_cost / g.total_current;
      }
    });
    return Array.from(map.values());
  }, [items]);

  const filtered = groupedByProduct.filter((g) => {
    const matchSearch = g.product_name?.toLowerCase().includes(search.toLowerCase()) ||
      g.product_category?.toLowerCase().includes(search.toLowerCase());
    const matchWarehouse = !selectedWarehouse || g.warehouse_names.includes(selectedWarehouse);
    return matchSearch && matchWarehouse;
  });

  return (
    <div className="h-full flex flex-col gap-4">
      {/* 搜索栏 */}
      <div className="flex items-center gap-4">
        <div className="relative flex-1 max-w-sm">
          <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-gray-400" />
          <Input
            placeholder="搜索产品名称或分类..."
            className="pl-8"
            value={search}
            onChange={(e) => { setSearch(e.target.value); setSelectedProduct(null); }}
          />
        </div>
        <Select value={selectedWarehouse} onValueChange={(v) => { setSelectedWarehouse(v ?? ""); setSelectedProduct(null); }}>
          <SelectTrigger className="w-40">
            <SelectValue placeholder="选择仓库" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="">全部仓库</SelectItem>
            {(() => {
              const whSet = new Set<string>();
              items.forEach((s) => whSet.add(s.warehouse_name));
              return Array.from(whSet).map((name) => (
                <SelectItem key={name} value={name}>{name}</SelectItem>
              ));
            })()}
          </SelectContent>
        </Select>
        <span className="text-sm text-gray-500">共 {filtered.length} 种产品</span>
      </div>

      {/* 上部：产品汇总列表 */}
      <div className="flex-1 flex flex-col min-h-0 border rounded-lg overflow-hidden">
        <div className="overflow-auto">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead className="sticky top-0 bg-background z-10">产品名称</TableHead>
                <TableHead className="sticky top-0 bg-background z-10">分类</TableHead>
                <TableHead className="sticky top-0 bg-background z-10">仓库</TableHead>
                <TableHead className="sticky top-0 bg-background z-10 text-right">总库存数量</TableHead>
                <TableHead className="sticky top-0 bg-background z-10 text-right">可用数量</TableHead>
                <TableHead className="sticky top-0 bg-background z-10 text-right">平均成本</TableHead>
                <TableHead className="sticky top-0 bg-background z-10 text-right">总成本</TableHead>
                <TableHead className="sticky top-0 bg-background z-10 text-right">到货周期</TableHead>
                <TableHead className="sticky top-0 bg-background z-10">状态</TableHead>
                <TableHead className="sticky top-0 bg-background z-10 text-center">操作记录</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {isLoading ? (
                <TableRow>
                  <TableCell colSpan={9} className="text-center py-8">加载中...</TableCell>
                </TableRow>
              ) : filtered.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={9} className="text-center py-8 text-gray-500">暂无库存记录</TableCell>
                </TableRow>
              ) : (
                filtered.map((g) => (
                  <TableRow
                    key={g.product_id}
                    className={cn(
                      "cursor-pointer transition-colors",
                      selectedProduct?.product_id === g.product_id && "bg-primary/10 hover:bg-primary/15"
                    )}
                    onClick={() => setSelectedProduct(
                      selectedProduct?.product_id === g.product_id ? null : {
                        product_id: g.product_id,
                        product_name: g.product_name,
                        product_category: g.product_category,
                      }
                    )}
                  >
                    <TableCell className="font-medium">{g.product_name}</TableCell>
                    <TableCell>
                      <Badge variant="outline">{getProductCategoryLabel(g.product_category)}</Badge>
                    </TableCell>
                    <TableCell>
                      <div className="flex flex-wrap gap-1">
                        {g.warehouse_names.map((name) => (
                          <Badge key={name} variant="secondary" className="text-xs">{name}</Badge>
                        ))}
                      </div>
                    </TableCell>
                    <TableCell className="text-right">
                      <span className={g.is_below_warning ? "text-red-600 font-semibold" : ""}>
                        {fmt(g.total_current)} {g.unit}
                      </span>
                    </TableCell>
                    <TableCell className="text-right">{fmt(g.total_available)} {g.unit}</TableCell>
                    <TableCell className="text-right">¥{fmt(g.avg_unit_cost)}</TableCell>
                    <TableCell className="text-right">¥{fmt(g.total_cost)}</TableCell>
                    <TableCell className="text-right">
                      {g.lead_time !== undefined && g.lead_time !== null ? (
                        <span className={g.lead_time > 7 ? "text-orange-600 font-semibold" : "text-green-600"}>
                          {g.lead_time}天
                        </span>
                      ) : (
                        <span className="text-gray-400">-</span>
                      )}
                    </TableCell>
                    <TableCell>
                      {g.is_below_warning ? (
                        <Badge className="bg-red-100 text-red-800 flex items-center gap-1">
                          <AlertTriangle className="h-3 w-3" />
                          预警
                        </Badge>
                      ) : (
                        <Badge className="bg-green-100 text-green-800">正常</Badge>
                      )}
                    </TableCell>
                    <TableCell className="text-center">
                      <Button variant="ghost" size="sm" className="h-6 px-2 text-blue-600" onClick={(e) => { e.stopPropagation(); setMovementStock({ warehouse_id: undefined, warehouse_name: '全部仓库', product_id: g.product_id, product_name: g.product_name }); setMovementDialogOpen(true); }}>
                        查看
                      </Button>
                    </TableCell>
                  </TableRow>
                ))
              )}
            </TableBody>
          </Table>
        </div>
      </div>

      {/* 下部：选中产品的库存明细 */}
      {selectedProduct && (
        <div className="flex-none border rounded-lg bg-background">
          <div className="p-3 space-y-2">
            {/* 详情头部 */}
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <h3 className="font-semibold text-base">{selectedProduct.product_name} — 库存明细</h3>
                <Badge variant="outline">{getProductCategoryLabel(selectedProduct.product_category)}</Badge>
              </div>
              <Button variant="ghost" size="icon" className="h-8 w-8" onClick={() => setSelectedProduct(null)}>
                <X className="h-4 w-4" />
              </Button>
            </div>

            <div className="border rounded-md overflow-hidden">
              <Table>
                <TableHeader>
                  <TableRow className="bg-muted/30">
                    <TableHead className="text-xs h-7">仓库</TableHead>
                    <TableHead className="text-xs h-7">批次号</TableHead>
                    <TableHead className="text-xs h-7 text-right">当前数量</TableHead>
                    <TableHead className="text-xs h-7 text-right">可用数量</TableHead>
                    <TableHead className="text-xs h-7 text-right">单位成本</TableHead>
                    <TableHead className="text-xs h-7 text-right">总成本</TableHead>
                    <TableHead className="text-xs h-7">最后入库</TableHead>
                    <TableHead className="text-xs h-7">最后出库</TableHead>
                    <TableHead className="text-xs h-7">状态</TableHead>
                  <TableHead className="text-xs h-7 text-center">操作记录</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {(() => {
                    const details = groupedByProduct.find(g => g.product_id === selectedProduct.product_id)?.details || [];
                    return details.map((s) => (
                      <TableRow key={s.id} className="h-7">
                        <TableCell className="text-sm py-0.5">
                          <div className="flex items-center gap-1">
                            {getWarehouseIcon("")}
                            <span>{s.warehouse_name}</span>
                          </div>
                        </TableCell>
                        <TableCell className="text-sm py-0.5 font-mono text-xs">{s.batch_no || "-"}</TableCell>
                        <TableCell className="text-sm py-0.5 text-right">
                          <span className={s.is_below_warning ? "text-red-600 font-semibold" : ""}>
                            {fmt(s.current_qty)} {s.unit}
                          </span>
                        </TableCell>
                        <TableCell className="text-sm py-0.5 text-right">{fmt(s.available_qty)} {s.unit}</TableCell>
                        <TableCell className="text-sm py-0.5 text-right">¥{fmt(s.unit_cost)}</TableCell>
                        <TableCell className="text-sm py-0.5 text-right">¥{fmt(s.total_cost)}</TableCell>
                        <TableCell className="text-sm py-0.5">{s.last_in_date || "-"}</TableCell>
                        <TableCell className="text-sm py-0.5">{s.last_out_date || "-"}</TableCell>
                        <TableCell className="text-sm py-0.5">
                          {s.is_below_warning ? (
                            <Badge className="bg-red-100 text-red-800 text-xs">
                              <AlertTriangle className="h-3 w-3 mr-1" />
                              预警
                            </Badge>
                          ) : (
                            <Badge className="bg-green-100 text-green-800 text-xs">正常</Badge>
                          )}
                        </TableCell>
                        <TableCell className="text-sm py-0.5 text-center">
                          <Button variant="ghost" size="sm" className="h-6 px-2 text-blue-600" onClick={(e) => { e.stopPropagation(); setMovementStock({ warehouse_id: s.warehouse_id, warehouse_name: s.warehouse_name, product_id: s.product_id, product_name: s.product_name }); setMovementDialogOpen(true); }}>
                            查看
                          </Button>
                        </TableCell>
                      </TableRow>
                    ));
                  })()}
                  <TableRow className="bg-muted/20 font-medium h-7">
                    <TableCell className="text-sm py-0.5" colSpan={2}>合计</TableCell>
                    <TableCell className="text-sm py-0.5 text-right">
                      {fmt(groupedByProduct.find(g => g.product_id === selectedProduct.product_id)?.total_current || 0)}
                    </TableCell>
                    <TableCell className="text-sm py-0.5 text-right">
                      {fmt(groupedByProduct.find(g => g.product_id === selectedProduct.product_id)?.total_available || 0)}
                    </TableCell>
                    <TableCell className="text-sm py-0.5 text-right">-</TableCell>
                    <TableCell className="text-sm py-0.5 text-right">
                      ¥{fmt(groupedByProduct.find(g => g.product_id === selectedProduct.product_id)?.total_cost || 0)}
                    </TableCell>
                    <TableCell colSpan={4} />
                  </TableRow>
                </TableBody>
              </Table>
            </div>
          </div>
        </div>
      )}
      {/* 操作记录弹窗 */}
      <Dialog open={movementDialogOpen} onOpenChange={setMovementDialogOpen}>
        <DialogContent className="max-w-4xl">
          <DialogHeader>
            <DialogTitle>操作记录 — {movementStock?.product_name}（{movementStock?.warehouse_name}）</DialogTitle>
          </DialogHeader>
          <StockMovementDialogContent warehouseId={movementStock?.warehouse_id} productId={movementStock?.product_id} />
          <DialogFooter>
            <Button variant="outline" onClick={() => setMovementDialogOpen(false)}>关闭</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}

// ==================== 操作记录弹窗内容 ====================
function StockMovementDialogContent({ warehouseId, productId }: { warehouseId?: number; productId?: number }) {
  const { data, isLoading } = useQuery({
    queryKey: ["warehouse-v2-movements-dialog", warehouseId, productId],
    queryFn: () =>
      fetchMovements({ warehouse_id: warehouseId, product_id: productId, limit: 500 }),
    enabled: !!productId,
  });

  const items: StockMovement[] = data?.items || [];

  return (
    <div className="border rounded-md overflow-x-auto">
      <Table className="min-w-full">
        <TableHeader>
          <TableRow>
            <TableHead className="text-xs whitespace-nowrap">日期</TableHead>
            <TableHead className="text-xs whitespace-nowrap">类型</TableHead>
            <TableHead className="text-xs whitespace-nowrap text-right">变动数量</TableHead>
            <TableHead className="text-xs whitespace-nowrap text-right">变动前</TableHead>
            <TableHead className="text-xs whitespace-nowrap text-right">变动后</TableHead>
            <TableHead className="text-xs whitespace-nowrap">关联单据</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {isLoading ? (
            <TableRow><TableCell colSpan={6} className="text-center py-4">加载中...</TableCell></TableRow>
          ) : items.length === 0 ? (
            <TableRow><TableCell colSpan={6} className="text-center py-4 text-gray-400">暂无操作记录</TableCell></TableRow>
          ) : (
            items.map((m) => (
              <TableRow key={m.id}>
                <TableCell className="text-sm whitespace-nowrap">{m.movement_date}</TableCell>
                <TableCell className="text-sm whitespace-nowrap">
                  <Badge className={getMovementTypeBadge(m.movement_type)}>
                    {getMovementTypeLabel(m.movement_type)}
                  </Badge>
                </TableCell>
                <TableCell className={`text-sm whitespace-nowrap text-right font-medium ${m.qty_change > 0 ? "text-green-600" : "text-red-600"}`}>
                  {m.qty_change > 0 ? "+" : ""}{fmt(m.qty_change)} {m.unit}
                </TableCell>
                <TableCell className="text-sm whitespace-nowrap text-right text-gray-500">{fmt(m.qty_before)}</TableCell>
                <TableCell className="text-sm whitespace-nowrap text-right">{fmt(m.qty_after)}</TableCell>
                <TableCell className="text-sm whitespace-nowrap text-gray-500">{m.ref_no || "-"}</TableCell>
              </TableRow>
            ))
          )}
        </TableBody>
      </Table>
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
        <Select value={movementType} onValueChange={(val) => setMovementType(val ?? "")}>
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
  const [inboundOpen, setInboundOpen] = useState(false);
  const [outboundOpen, setOutboundOpen] = useState(false);
  const [transferOpen, setTransferOpen] = useState(false);

  return (
    <div className="p-6 space-y-6 h-full flex flex-col">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold flex items-center gap-2">
          <Warehouse className="h-6 w-6" />
          仓库管理
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

      <StockList />
    </div>
  );
}

// ==================== 国内整包仓明细 ====================
interface DomesticStock {
  id: number;
  inbound_no: string;
  batch_no: string;
  product_name: string;
  product_spec: string;
  slaughter_date: string | null;
  factory: string | null;
  box_count: number;
  current_weight: number;
  available_weight: number;
  original_box_count: number;
  original_weight: number;
  unit_cost: number;
  total_cost: number;
  inbound_date: string | null;
  source_no: string;
  movement_count: number;
  movements?: {
    id: number;
    movement_type: string;
    movement_date: string;
    qty_change: number;
    qty_before: number;
    qty_after: number;
    unit: string;
    ref_type: string;
    ref_no: string;
    notes: string;
    business_type: string;
    related_party: string;
  }[];
}

const fetchDomesticStocks = async (params: Record<string, any>) => {
  const { data } = await api.get("/v1/warehouse-v2/domestic-stocks", { params });
  return data;
};

function DomesticStockList() {
  const [search, setSearch] = useState("");
  const [movementOpen, setMovementOpen] = useState(false);
  const [movementData, setMovementData] = useState<DomesticStock | null>(null);
  const { data, isLoading } = useQuery({
    queryKey: ["warehouse-v2-domestic-stocks"],
    queryFn: () => fetchDomesticStocks({ limit: 500 }),
  });

  const items: DomesticStock[] = data?.items || [];
  const filtered = items.filter((s) =>
    s.product_name?.toLowerCase().includes(search.toLowerCase()) ||
    s.batch_no?.toLowerCase().includes(search.toLowerCase()) ||
    s.factory?.toLowerCase().includes(search.toLowerCase())
  );

  return (
    <div>
      <div className="flex items-center gap-4 mb-4">
        <div className="relative flex-1 max-w-sm">
          <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-gray-400" />
          <Input
            placeholder="搜索产品/批次/加工厂..."
            className="pl-8"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>
        <span className="text-sm text-gray-500">共 {filtered.length} 条</span>
      </div>

      <div className="border rounded-md overflow-x-auto">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>仓库</TableHead>
              <TableHead>产品名称</TableHead>
              <TableHead>批次</TableHead>
              <TableHead>宰杀日期</TableHead>
              <TableHead>加工厂</TableHead>
              <TableHead>规格</TableHead>
              <TableHead className="text-right">库存箱数</TableHead>
              <TableHead className="text-right">库存重量</TableHead>
              <TableHead className="text-right">原始箱数</TableHead>
              <TableHead className="text-right">原始重量</TableHead>
              <TableHead className="text-right">操作记录</TableHead>
              <TableHead className="text-right">入库金额</TableHead>
              <TableHead>入库日期</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {isLoading ? (
              <TableRow>
                <TableCell colSpan={13} className="text-center py-8">加载中...</TableCell>
              </TableRow>
            ) : filtered.length === 0 ? (
              <TableRow>
                <TableCell colSpan={13} className="text-center py-8 text-gray-500">暂无国内整包仓入库记录</TableCell>
              </TableRow>
            ) : (
              filtered.map((s) => (
                <TableRow key={s.id}>
                  <TableCell>
                    <div className="flex items-center gap-1">
                      {getWarehouseIcon("WHOLE_PACKAGE")}
                      <span className="text-sm">国内整包仓</span>
                    </div>
                  </TableCell>
                  <TableCell className="font-medium">{s.product_name}</TableCell>
                  <TableCell className="font-mono text-xs">{s.batch_no || "-"}</TableCell>
                  <TableCell>{s.slaughter_date || "-"}</TableCell>
                  <TableCell>{s.factory || "-"}</TableCell>
                  <TableCell>{s.product_spec || "-"}</TableCell>
                  <TableCell className="text-right">{s.box_count || "-"}</TableCell>
                  <TableCell className="text-right font-medium">{fmt(s.current_weight)} kg</TableCell>
                  <TableCell className="text-right text-gray-500">{s.original_box_count || "-"}</TableCell>
                  <TableCell className="text-right text-gray-500">{fmt(s.original_weight)} kg</TableCell>
                  <TableCell className="text-right">
                    <Button variant="ghost" size="sm" className="h-6 px-2 text-blue-600" onClick={() => { setMovementData(s); setMovementOpen(true); }}>
                      查看
                    </Button>
                  </TableCell>
                  <TableCell className="text-right font-medium">¥{fmt(s.total_cost)}</TableCell>
                  <TableCell>{s.inbound_date || "-"}</TableCell>
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </div>

      {/* 操作记录弹窗 */}
      <Dialog open={movementOpen} onOpenChange={setMovementOpen}>
        <DialogContent className="max-w-2xl">
          <DialogHeader>
            <DialogTitle>操作记录 — {movementData?.product_name} {movementData?.batch_no}</DialogTitle>
          </DialogHeader>
          <div className="border rounded-md">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>操作时间</TableHead>
                  <TableHead>单据编号</TableHead>
                  <TableHead>业务类型</TableHead>
                  <TableHead className="text-right">数量</TableHead>
                  <TableHead>备注</TableHead>
                  <TableHead>操作人</TableHead>
                  <TableHead>供应商/客户</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {movementData?.movements?.length === 0 ? (
                  <TableRow><TableCell colSpan={7} className="text-center py-4 text-gray-400">暂无记录</TableCell></TableRow>
                ) : (
                  movementData?.movements?.map((m) => (
                    <TableRow key={m.id}>
                      <TableCell>{m.movement_date}</TableCell>
                      <TableCell className="font-mono text-xs">{m.ref_no || "-"}</TableCell>
                      <TableCell>
                        <Badge className={getMovementTypeBadge(m.movement_type)}>{m.business_type || getMovementTypeLabel(m.movement_type)}</Badge>
                      </TableCell>
                      <TableCell className={`text-right font-medium ${m.qty_change > 0 ? "text-green-600" : "text-red-600"}`}>
                        {m.qty_change > 0 ? "+" : ""}{fmt(m.qty_change)} {m.unit}
                      </TableCell>
                      <TableCell className="text-sm text-gray-500">{m.notes || "-"}</TableCell>
                      <TableCell className="text-sm text-gray-500">-</TableCell>
                      <TableCell className="text-sm">{m.related_party || "-"}</TableCell>
                    </TableRow>
                  ))
                )}
              </TableBody>
            </Table>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setMovementOpen(false)}>关闭</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}

export default WarehouseV2Page;
