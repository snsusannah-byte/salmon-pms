import React, { useState, useMemo, useRef, useEffect } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from "@/components/ui/table";
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter,
} from "@/components/ui/dialog";
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from "@/components/ui/select";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Card, CardContent } from "@/components/ui/card";
import {
  Plus, Search, Trash2, AlertTriangle, Package, Warehouse, Truck, ArrowDown, ArrowUp,
  Fish, Boxes, Pencil, Check, X, Loader2,
} from "lucide-react";
import { toast } from "sonner";

// ==================== 类型 ====================
interface Stock {
  id: number;
  product_id: number;
  product_name: string;
  category: string;
  current_quantity: number;
  available_quantity: number;
  cost_price: number;
  warning_line: number;
  last_purchase_date: string;
  unit: string;
  warehouse_type: string;
}

interface PurchaseOrder {
  id: number;
  order_date: string;
  product_id: number;
  product_name: string;
  supplier_id: number;
  supplier_name: string;
  batch_no: string;
  quantity: number;
  unit: string;
  unit_price: number;
  total_amount: number;
  lead_time_days: number;
  warehouse_location: string;
  warehouse_type: string;
  inbound_type: string;
}

interface Product {
  id: number;
  name: string;
  category: string;
  unit: string;
}

interface Supplier {
  id: number;
  name: string;
}

interface InventoryItem {
  id: number;
  code: string;
  name: string;
  spec: string | null;
  stock_quantity: number;
  safety_stock: number;
  is_active: boolean;
  unit: string;
  portion_weight_g: number | null;
  portion_boxes: number | null;
  series_code?: string | null;
  series_name?: string | null;
}

function getInventoryStatus(item: InventoryItem): { label: string; color: string } {
  if (!item.is_active) return { label: "停用", color: "bg-gray-100 text-gray-600 border-gray-200" };
  if (item.stock_quantity <= 0) return { label: "缺货", color: "bg-red-100 text-red-800 border-red-300" };
  if (item.stock_quantity < item.safety_stock) return { label: "低库存", color: "bg-orange-100 text-orange-800 border-orange-300" };
  return { label: "正常", color: "bg-green-100 text-green-800 border-green-200" };
}

// ==================== API ====================
const warehouseApi = {
  stocks: async (params: Record<string, any>) => {
    const { data } = await api.get("/v1/warehouse/stocks", { params });
    return data;
  },
  warnings: async () => {
    const { data } = await api.get("/v1/warehouse/stocks/warnings");
    return data;
  },
  purchaseOrders: async (params: Record<string, any>) => {
    const { data } = await api.get("/v1/warehouse/purchase-orders", { params });
    return data;
  },
  createPurchaseOrder: async (body: any) => {
    const { data } = await api.post("/v1/warehouse/purchase-orders", body);
    return data;
  },
  deletePurchaseOrder: async (id: number) => {
    const { data } = await api.delete(`/v1/warehouse/purchase-orders/${id}`);
    return data;
  },
  stockIn: async (body: any) => {
    const { data } = await api.post("/v1/warehouse/stocks/in", body);
    return data;
  },
  stockOut: async (body: any) => {
    const { data } = await api.post("/v1/warehouse/stocks/out", body);
    return data;
  },
  products: async () => {
    const { data } = await api.get("/v1/products");
    return data;
  },
  suppliers: async () => {
    const { data } = await api.get("/v1/suppliers");
    return data;
  },
};

function fmtMoney(v: number) {
  return `¥${v.toFixed(2)}`;
}

const categoryMap: Record<string, string> = {
  whole_fish: "整鱼",
  fillet: "鱼柳",
  packaging: "包装物料",
  accessory: "配套",
  byproduct: "副产品",
  finished_product: "成品",
  bom_material: "BOM物料",
};

const categoryOptions = [
  { value: "all", label: "全部分类" },
  { value: "whole_fish", label: "整鱼" },
  { value: "fillet", label: "鱼柳" },
  { value: "packaging", label: "包装物料" },
  { value: "accessory", label: "配套" },
  { value: "byproduct", label: "副产品" },
  { value: "finished_product", label: "成品" },
];

export function WarehousePage() {
  const qc = useQueryClient();
  const [tab, setTab] = useState("stocks");
  const [search, setSearch] = useState("");
  const [categoryFilter, setCategoryFilter] = useState("all");
  const [warehouseFilter, setWarehouseFilter] = useState("all");
  const [poDialogOpen, setPoDialogOpen] = useState(false);
  const [inOutDialogOpen, setInOutDialogOpen] = useState(false);
  const [inOutType, setInOutType] = useState<"in" | "out">("in");
  const [deletePoId, setDeletePoId] = useState<number | null>(null);

  // 成品库存查询
  const [finishedSearch, setFinishedSearch] = useState("");

  // 表单
  const [poForm, setPoForm] = useState({
    order_date: new Date().toISOString().split("T")[0],
    product_id: "",
    supplier_id: "",
    batch_no: "",
    quantity: 0,
    unit: "kg",
    unit_price: 0,
    total_amount: 0,
    lead_time_days: 7,
    warehouse_location: "",
    warehouse_type: "finished",
    inbound_type: "purchase",
  });

  const [inOutForm, setInOutForm] = useState({
    product_id: "",
    quantity: 0,
    reason: "",
  });

  // 查询
  const { data: stocksData, isLoading: stocksLoading } = useQuery({
    queryKey: ["warehouse-stocks", categoryFilter, warehouseFilter],
    queryFn: () => warehouseApi.stocks({ 
      category: categoryFilter === "all" ? "" : categoryFilter, 
      warehouse_type: warehouseFilter === "all" ? "" : warehouseFilter,
      limit: 100 
    }),
  });
  const { data: warningsData, isLoading: warningsLoading } = useQuery({
    queryKey: ["warehouse-warnings"],
    queryFn: warehouseApi.warnings,
  });
  const { data: poData, isLoading: poLoading } = useQuery({
    queryKey: ["warehouse-po"],
    queryFn: () => warehouseApi.purchaseOrders({ limit: 100 }),
  });
  const { data: productsData } = useQuery({ queryKey: ["products"], queryFn: warehouseApi.products });
  const { data: suppliersData } = useQuery({ queryKey: ["suppliers"], queryFn: warehouseApi.suppliers });

  // 成品库存查询
  const { data: finishedInventoryData, isLoading: finishedLoading } = useQuery({
    queryKey: ["finished-products-inventory"],
    queryFn: async () => {
      const res = await api.get("/v1/products/?category=finished_product&limit=500");
      return res.data.items as InventoryItem[];
    },
  });
  const { data: lowStockData } = useQuery({
    queryKey: ["products-low-stock"],
    queryFn: async () => {
      const res = await api.get("/v1/products/low-stock");
      return res.data as InventoryItem[];
    },
  });

  // 更新成品库存
  const updateStockMutation = useMutation({
    mutationFn: async ({ id, stock_quantity }: { id: number; stock_quantity: number }) => {
      await api.put(`/v1/products/${id}`, { stock_quantity });
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["finished-products-inventory"] });
      qc.invalidateQueries({ queryKey: ["products-low-stock"] });
      toast.success("库存数量已更新");
    },
    onError: (err: any) => toast.error(err.response?.data?.detail || "更新失败"),
  });

  const stocks: Stock[] = stocksData?.items || [];
  const warnings: Stock[] = warningsData?.items || [];
  const purchaseOrders: PurchaseOrder[] = poData?.items || [];
  const products: Product[] = productsData?.items || productsData || [];
  const suppliers: Supplier[] = suppliersData?.items || suppliersData || [];

  // 成品库存数据
  const finishedInventory = finishedInventoryData || [];
  const finishedFiltered = useMemo(() => {
    if (!finishedSearch.trim()) return finishedInventory;
    const s = finishedSearch.trim().toLowerCase();
    return finishedInventory.filter(
      (item) =>
        item.name?.toLowerCase().includes(s) ||
        item.code?.toLowerCase().includes(s) ||
        (item.spec ?? "").toLowerCase().includes(s)
    );
  }, [finishedInventory, finishedSearch]);

  const finishedStats = useMemo(() => {
    const active = finishedInventory.filter((i) => i.is_active);
    return {
      totalSKU: active.length,
      totalStock: active.reduce((sum, i) => sum + i.stock_quantity, 0),
      lowStockCount: (lowStockData?.length ?? active.filter((i) => i.stock_quantity < i.safety_stock).length),
    };
  }, [finishedInventory, lowStockData]);

  // 统计
  const stats = useMemo(() => {
    return {
      totalCategories: new Set(stocks.map((s) => s.category)).size,
      wholeFishQty: stocks.filter((s) => s.category === "whole_fish").reduce((sum, s) => sum + s.current_quantity, 0),
      filletQty: stocks.filter((s) => s.category === "fillet").reduce((sum, s) => sum + s.current_quantity, 0),
      warningCount: warnings.length,
    };
  }, [stocks, warnings]);

  // Mutations
  const createPoMutation = useMutation({
    mutationFn: warehouseApi.createPurchaseOrder,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["warehouse-po"] });
      qc.invalidateQueries({ queryKey: ["warehouse-stocks"] });
      qc.invalidateQueries({ queryKey: ["warehouse-warnings"] });
      setPoDialogOpen(false);
      resetPoForm();
      toast.success("采购入库成功");
    },
    onError: (err: any) => toast.error(err.response?.data?.detail || "创建失败"),
  });

  const deletePoMutation = useMutation({
    mutationFn: warehouseApi.deletePurchaseOrder,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["warehouse-po"] });
      qc.invalidateQueries({ queryKey: ["warehouse-stocks"] });
      setDeletePoId(null);
      toast.success("删除成功");
    },
    onError: (err: any) => toast.error(err.response?.data?.detail || "删除失败"),
  });

  const stockInOutMutation = useMutation({
    mutationFn: ({ type, body }: { type: "in" | "out"; body: any }) =>
      type === "in" ? warehouseApi.stockIn(body) : warehouseApi.stockOut(body),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["warehouse-stocks"] });
      qc.invalidateQueries({ queryKey: ["warehouse-warnings"] });
      setInOutDialogOpen(false);
      setInOutForm({ product_id: "", quantity: 0, reason: "" });
      toast.success(inOutType === "in" ? "入库成功" : "出库成功");
    },
    onError: (err: any) => toast.error(err.response?.data?.detail || "操作失败"),
  });

  function resetPoForm() {
    setPoForm({
      order_date: new Date().toISOString().split("T")[0],
      product_id: "",
      supplier_id: "",
      batch_no: "",
      quantity: 0,
      unit: "kg",
      unit_price: 0,
      total_amount: 0,
      lead_time_days: 7,
      warehouse_location: "",
      warehouse_type: "finished",
      inbound_type: "purchase",
    });
  }

  function handleCreatePo() {
    createPoMutation.mutate({
      ...poForm,
      product_id: Number(poForm.product_id),
      supplier_id: Number(poForm.supplier_id),
    });
  }

  function handleStockInOut() {
    stockInOutMutation.mutate({
      type: inOutType,
      body: {
        product_id: Number(inOutForm.product_id),
        quantity: inOutForm.quantity,
        reason: inOutForm.reason,
      },
    });
  }

  const filteredStocks = stocks.filter((s) => {
    if (search) return s.product_name.toLowerCase().includes(search.toLowerCase());
    return true;
  });

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">成品仓库</h1>
        <p className="text-sm text-muted-foreground">库存管理与采购入库</p>
      </div>

      {/* 统计卡片 */}
      <div className="grid grid-cols-4 gap-4">
        <Card><CardContent className="p-4">
          <div className="flex items-center justify-between">
            <div className="space-y-1"><p className="text-sm text-muted-foreground">库存品类数</p><p className="text-2xl font-bold">{stats.totalCategories} 类</p></div>
            <div className="p-3 bg-blue-100 rounded-full"><Package className="h-5 w-5 text-blue-600" /></div>
          </div>
        </CardContent></Card>
        <Card><CardContent className="p-4">
          <div className="flex items-center justify-between">
            <div className="space-y-1"><p className="text-sm text-muted-foreground">整鱼库存</p><p className="text-2xl font-bold">{stats.wholeFishQty.toFixed(1)} kg</p></div>
            <div className="p-3 bg-green-100 rounded-full"><Fish className="h-5 w-5 text-green-600" /></div>
          </div>
        </CardContent></Card>
        <Card><CardContent className="p-4">
          <div className="flex items-center justify-between">
            <div className="space-y-1"><p className="text-sm text-muted-foreground">鱼柳库存</p><p className="text-2xl font-bold">{stats.filletQty.toFixed(1)} kg</p></div>
            <div className="p-3 bg-amber-100 rounded-full"><Warehouse className="h-5 w-5 text-amber-600" /></div>
          </div>
        </CardContent></Card>
        <Card><CardContent className="p-4">
          <div className="flex items-center justify-between">
            <div className="space-y-1"><p className="text-sm text-muted-foreground">预警商品数</p><p className={cn("text-2xl font-bold", stats.warningCount > 0 && "text-red-600")}>{stats.warningCount} 个</p></div>
            <div className="p-3 bg-red-100 rounded-full"><AlertTriangle className="h-5 w-5 text-red-600" /></div>
          </div>
        </CardContent></Card>
      </div>

      <Tabs value={tab} onValueChange={setTab}>
        <TabsList className="grid w-full grid-cols-4">
          <TabsTrigger value="stocks">库存查询</TabsTrigger>
          <TabsTrigger value="finished">成品库存</TabsTrigger>
          <TabsTrigger value="purchase">入库记录</TabsTrigger>
          <TabsTrigger value="warnings">库存预警</TabsTrigger>
        </TabsList>

        {/* Tab 1: 库存查询 */}
        <TabsContent value="stocks" className="space-y-4 pt-4">
          <div className="flex items-center justify-between gap-4">
            <div className="flex items-center gap-3">
              <div className="relative">
                <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
                <Input placeholder="搜索产品..." className="pl-9 w-64" value={search} onChange={(e) => setSearch(e.target.value)} />
              </div>
              <Select value={categoryFilter} onValueChange={(v) => setCategoryFilter(v ?? "")}>
                <SelectTrigger className="w-40"><SelectValue /></SelectTrigger>
                <SelectContent>
                  {categoryOptions.map((o) => (<SelectItem key={o.value} value={o.value}>{o.label}</SelectItem>))}
                </SelectContent>
              </Select>
              <Select value={warehouseFilter} onValueChange={(v) => setWarehouseFilter(v ?? "")}>
                <SelectTrigger className="w-40"><SelectValue placeholder="仓库筛选" /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">全部仓库</SelectItem>
                  <SelectItem value="whole_fish">整鱼仓库</SelectItem>
                  <SelectItem value="finished">成品仓库</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="flex gap-2">
              <Button variant="outline" onClick={() => { setInOutType("in"); setInOutDialogOpen(true); }}><ArrowDown className="h-4 w-4 mr-1" />入库</Button>
              <Button variant="outline" onClick={() => { setInOutType("out"); setInOutDialogOpen(true); }}><ArrowUp className="h-4 w-4 mr-1" />出库</Button>
              <Button onClick={() => setPoDialogOpen(true)}><Plus className="h-4 w-4 mr-1" />采购入库</Button>
            </div>
          </div>
          <div className="border rounded-md">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>产品</TableHead>
                  <TableHead>分类</TableHead>
                  <TableHead>仓库</TableHead>
                  <TableHead className="text-right">当前库存</TableHead>
                  <TableHead className="text-right">可用库存</TableHead>
                  <TableHead className="text-right">成本单价</TableHead>
                  <TableHead className="text-right">预警线</TableHead>
                  <TableHead>状态</TableHead>
                  <TableHead>最后入库</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {stocksLoading ? <TableRow><TableCell colSpan={9} className="text-center py-8">加载中...</TableCell></TableRow> :
                 filteredStocks.length === 0 ? <TableRow><TableCell colSpan={9} className="text-center py-8 text-muted-foreground">暂无数据</TableCell></TableRow> :
                 filteredStocks.map((s) => (
                  <TableRow key={s.id}>
                    <TableCell className="font-medium">{s.product_name}</TableCell>
                    <TableCell>{categoryMap[s.category] || s.category}</TableCell>
                    <TableCell>
                      <Badge variant="outline" className={cn(s.warehouse_type === "whole_fish" ? "text-blue-600 border-blue-200" : "text-amber-600 border-amber-200")}>
                        {s.warehouse_type === "whole_fish" ? "整鱼仓" : "成品仓"}
                      </Badge>
                    </TableCell>
                    <TableCell className="text-right">{s.current_quantity.toFixed(1)} {s.unit}</TableCell>
                    <TableCell className="text-right">{s.available_quantity.toFixed(1)} {s.unit}</TableCell>
                    <TableCell className="text-right">{fmtMoney(s.cost_price)}</TableCell>
                    <TableCell className="text-right">{s.warning_line.toFixed(1)}</TableCell>
                    <TableCell>
                      <Badge className={cn(s.available_quantity >= s.warning_line ? "bg-green-100 text-green-800" : "bg-red-100 text-red-800")}>
                        {s.available_quantity >= s.warning_line ? "正常" : "预警"}
                      </Badge>
                    </TableCell>
                    <TableCell className="text-sm text-muted-foreground">{s.last_purchase_date || "-"}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        </TabsContent>

        {/* Tab 2: 成品库存查询 */}
        <TabsContent value="finished" className="space-y-4 pt-4">
          {/* 成品统计卡片 */}
          <div className="grid grid-cols-3 gap-4">
            <Card>
              <CardContent className="p-4 flex items-center gap-4">
                <div className="p-3 bg-blue-100 rounded-full">
                  <Boxes className="h-6 w-6 text-blue-600" />
                </div>
                <div>
                  <p className="text-sm text-muted-foreground">总SKU数</p>
                  <p className="text-2xl font-bold">{finishedStats.totalSKU}</p>
                </div>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="p-4 flex items-center gap-4">
                <div className="p-3 bg-green-100 rounded-full">
                  <Package className="h-6 w-6 text-green-600" />
                </div>
                <div>
                  <p className="text-sm text-muted-foreground">总库存份数</p>
                  <p className="text-2xl font-bold">{finishedStats.totalStock.toLocaleString()}</p>
                </div>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="p-4 flex items-center gap-4">
                <div className="p-3 bg-red-100 rounded-full">
                  <AlertTriangle className="h-6 w-6 text-red-600" />
                </div>
                <div>
                  <p className="text-sm text-muted-foreground">低库存预警</p>
                  <p className={cn("text-2xl font-bold", finishedStats.lowStockCount > 0 && "text-red-600")}>{finishedStats.lowStockCount}</p>
                </div>
              </CardContent>
            </Card>
          </div>

          {/* 搜索 */}
          <div className="flex gap-4">
            <div className="relative flex-1 max-w-sm">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
              <Input
                placeholder="搜索编码、名称或规格..."
                value={finishedSearch}
                onChange={(e) => setFinishedSearch(e.target.value)}
                className="pl-9"
              />
            </div>
          </div>

          {/* 成品库存表格 */}
          <div className="border rounded-lg">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>编码</TableHead>
                  <TableHead>名称</TableHead>
                  <TableHead>规格</TableHead>
                  <TableHead className="text-right">库存份数</TableHead>
                  <TableHead className="text-right">安全库存</TableHead>
                  <TableHead>状态</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {finishedLoading ? (
                  <TableRow>
                    <TableCell colSpan={6} className="text-center py-8">
                      <Loader2 className="h-6 w-6 animate-spin mx-auto text-muted-foreground" />
                    </TableCell>
                  </TableRow>
                ) : finishedFiltered.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={6} className="text-center py-8 text-muted-foreground">
                      暂无数据
                    </TableCell>
                  </TableRow>
                ) : (
                  finishedFiltered.map((item) => {
                    const status = getInventoryStatus(item);
                    const isLow = item.is_active && item.stock_quantity < item.safety_stock;
                    const isOutOfStock = item.is_active && item.stock_quantity <= 0;
                    return (
                      <TableRow
                        key={item.id}
                        className={cn(
                          isOutOfStock && "bg-red-50",
                          isLow && !isOutOfStock && "bg-orange-50/60",
                          !item.is_active && "bg-gray-50/60 opacity-60"
                        )}
                      >
                        <TableCell className="font-mono text-sm">{item.code}</TableCell>
                        <TableCell className="font-medium">{item.name}</TableCell>
                        <TableCell className="text-muted-foreground">
                          {item.spec || `${item.series_code ?? ""}${item.portion_weight_g ?? ""}${item.portion_boxes ?? ""}` || "-"}
                        </TableCell>
                        <TableCell className="text-right">
                          <EditableStock
                            value={item.stock_quantity}
                            isLow={isLow}
                            isOutOfStock={isOutOfStock}
                            onUpdate={(v) => updateStockMutation.mutate({ id: item.id, stock_quantity: v })}
                            isPending={updateStockMutation.isPending && updateStockMutation.variables?.id === item.id}
                          />
                        </TableCell>
                        <TableCell className="text-right text-muted-foreground">{item.safety_stock}</TableCell>
                        <TableCell>
                          <Badge variant="outline" className={cn(status.color)}>
                            {status.label}
                          </Badge>
                        </TableCell>
                      </TableRow>
                    );
                  })
                )}
              </TableBody>
            </Table>
          </div>
        </TabsContent>

        {/* Tab 3: 入库记录 */}
        <TabsContent value="purchase" className="space-y-4 pt-4">
          <div className="border rounded-md">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>日期</TableHead>
                  <TableHead>批次号</TableHead>
                  <TableHead>产品</TableHead>
                  <TableHead>供应商</TableHead>
                  <TableHead className="text-right">数量</TableHead>
                  <TableHead className="text-right">单价</TableHead>
                  <TableHead className="text-right">总金额</TableHead>
                  <TableHead>仓库</TableHead>
                  <TableHead>类型</TableHead>
                  <TableHead>库位</TableHead>
                  <TableHead className="w-[80px]">操作</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {poLoading ? <TableRow><TableCell colSpan={9} className="text-center py-8">加载中...</TableCell></TableRow> :
                 purchaseOrders.length === 0 ? <TableRow><TableCell colSpan={11} className="text-center py-8 text-muted-foreground">暂无记录</TableCell></TableRow> :
                 purchaseOrders.map((po) => (
                  <TableRow key={po.id}>
                    <TableCell>{po.order_date}</TableCell>
                    <TableCell className="font-medium">{po.batch_no}</TableCell>
                    <TableCell>{po.product_name}</TableCell>
                    <TableCell>{po.supplier_name}</TableCell>
                    <TableCell className="text-right">{po.quantity} {po.unit}</TableCell>
                    <TableCell className="text-right">{fmtMoney(po.unit_price)}</TableCell>
                    <TableCell className="text-right font-medium">{fmtMoney(po.total_amount)}</TableCell>
                    <TableCell>
                      <Badge variant="outline" className={cn(po.warehouse_type === "whole_fish" ? "text-blue-600 border-blue-200" : "text-amber-600 border-amber-200")}>
                        {po.warehouse_type === "whole_fish" ? "整鱼仓" : "成品仓"}
                      </Badge>
                    </TableCell>
                    <TableCell>
                      <Badge variant="outline" className={cn(po.inbound_type === "purchase" ? "text-green-600 border-green-200" : "text-purple-600 border-purple-200")}>
                        {po.inbound_type === "purchase" ? "采购" : "调拨"}
                      </Badge>
                    </TableCell>
                    <TableCell className="text-sm">{po.warehouse_location}</TableCell>
                    <TableCell>
                      <Button variant="ghost" size="icon" className="h-8 w-8" onClick={() => setDeletePoId(po.id)}><Trash2 className="h-4 w-4" /></Button>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        </TabsContent>

        {/* Tab 3: 库存预警 */}
        <TabsContent value="warnings" className="space-y-4 pt-4">
          <div className="border rounded-md">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>产品</TableHead>
                  <TableHead>分类</TableHead>
                  <TableHead className="text-right">当前库存</TableHead>
                  <TableHead className="text-right">预警线</TableHead>
                  <TableHead className="text-right">缺口</TableHead>
                  <TableHead>状态</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {warningsLoading ? <TableRow><TableCell colSpan={6} className="text-center py-8">加载中...</TableCell></TableRow> :
                 warnings.length === 0 ? <TableRow><TableCell colSpan={6} className="text-center py-8 text-muted-foreground">暂无预警商品</TableCell></TableRow> :
                 warnings.map((w) => {
                   const gap = Math.max(0, w.warning_line - w.available_quantity);
                   return (
                    <TableRow key={w.id}>
                      <TableCell className="font-medium">{w.product_name}</TableCell>
                      <TableCell>{categoryMap[w.category] || w.category}</TableCell>
                      <TableCell className="text-right">{w.current_quantity.toFixed(1)} {w.unit}</TableCell>
                      <TableCell className="text-right">{w.warning_line.toFixed(1)}</TableCell>
                      <TableCell className="text-right text-red-600 font-medium">{gap.toFixed(1)}</TableCell>
                      <TableCell><Badge className="bg-red-100 text-red-800">库存不足</Badge></TableCell>
                    </TableRow>
                   );
                 })}
              </TableBody>
            </Table>
          </div>
        </TabsContent>
      </Tabs>

      {/* 采购入库弹窗 */}
      <Dialog open={poDialogOpen} onOpenChange={setPoDialogOpen}>
        <DialogContent className="max-w-lg">
          <DialogHeader><DialogTitle>采购入库</DialogTitle></DialogHeader>
          <div className="space-y-4 py-4">
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2"><Label>入库日期</Label><Input type="date" value={poForm.order_date} onChange={(e) => setPoForm({ ...poForm, order_date: e.target.value })} /></div>
              <div className="space-y-2"><Label>批次号</Label><Input value={poForm.batch_no} onChange={(e) => setPoForm({ ...poForm, batch_no: e.target.value })} placeholder="PO-20260504-001" /></div>
            </div>
            <div className="space-y-2">
              <Label>产品</Label>
              <Select value={poForm.product_id} onValueChange={(v) => {
                const p = products.find((x) => String(x.id) === (v ?? ""));
                setPoForm({ ...poForm, product_id: v ?? "", unit: p?.unit || "kg" });
              }}>
                <SelectTrigger><SelectValue placeholder="选择产品" /></SelectTrigger>
                <SelectContent>
                  {products.map((p) => (<SelectItem key={p.id} value={String(p.id)}>{p.name} ({categoryMap[p.category] || p.category})</SelectItem>))}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label>供应商</Label>
              <Select value={poForm.supplier_id} onValueChange={(v) => setPoForm({ ...poForm, supplier_id: v ?? "" })}>
                <SelectTrigger><SelectValue placeholder="选择供应商" /></SelectTrigger>
                <SelectContent>
                  {suppliers.map((s) => (<SelectItem key={s.id} value={String(s.id)}>{s.name}</SelectItem>))}
                </SelectContent>
              </Select>
            </div>
            <div className="grid grid-cols-3 gap-4">
              <div className="space-y-2"><Label>数量</Label><Input type="number" value={poForm.quantity} onChange={(e) => setPoForm({ ...poForm, quantity: Number(e.target.value) })} /></div>
              <div className="space-y-2"><Label>单位</Label><Input value={poForm.unit} onChange={(e) => setPoForm({ ...poForm, unit: e.target.value })} /></div>
              <div className="space-y-2"><Label>单价</Label><Input type="number" step="0.01" value={poForm.unit_price} onChange={(e) => setPoForm({ ...poForm, unit_price: Number(e.target.value) })} /></div>
            </div>
            <div className="bg-muted/50 rounded-md p-3 flex justify-between">
              <span className="text-sm text-muted-foreground">总金额</span>
              <span className="font-bold">{fmtMoney(poForm.quantity * poForm.unit_price)}</span>
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2"><Label>供货周期(天)</Label><Input type="number" value={poForm.lead_time_days} onChange={(e) => setPoForm({ ...poForm, lead_time_days: Number(e.target.value) })} /></div>
              <div className="space-y-2"><Label>库位</Label><Input value={poForm.warehouse_location} onChange={(e) => setPoForm({ ...poForm, warehouse_location: e.target.value })} placeholder="A1-冷藏库" /></div>
            <div className="space-y-2">
              <Label>所在仓库</Label>
              <Select value={poForm.warehouse_type} onValueChange={(v) => setPoForm({ ...poForm, warehouse_type: v ?? "" })}>
                <SelectTrigger><SelectValue /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="whole_fish">整鱼仓库</SelectItem>
                  <SelectItem value="finished">成品仓库</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label>入库类型</Label>
              <Select value={poForm.inbound_type} onValueChange={(v) => setPoForm({ ...poForm, inbound_type: v ?? "" })}>
                <SelectTrigger><SelectValue /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="purchase">外部采购</SelectItem>
                  <SelectItem value="transfer">内部调拨</SelectItem>
                </SelectContent>
              </Select>
            </div>
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setPoDialogOpen(false)}>取消</Button>
            <Button onClick={handleCreatePo} disabled={createPoMutation.isPending}>{createPoMutation.isPending ? "保存中..." : "确认入库"}</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* 入库/出库弹窗 */}
      <Dialog open={inOutDialogOpen} onOpenChange={setInOutDialogOpen}>
        <DialogContent className="max-w-sm">
          <DialogHeader><DialogTitle>{inOutType === "in" ? "直接入库" : "直接出库"}</DialogTitle></DialogHeader>
          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <Label>产品</Label>
              <Select value={inOutForm.product_id} onValueChange={(v) => setInOutForm({ ...inOutForm, product_id: v ?? "" })}>
                <SelectTrigger><SelectValue placeholder="选择产品" /></SelectTrigger>
                <SelectContent>
                  {products.map((p) => (<SelectItem key={p.id} value={String(p.id)}>{p.name}</SelectItem>))}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label>数量</Label>
              <Input type="number" value={inOutForm.quantity} onChange={(e) => setInOutForm({ ...inOutForm, quantity: Number(e.target.value) })} />
            </div>
            <div className="space-y-2">
              <Label>原因</Label>
              <Input value={inOutForm.reason} onChange={(e) => setInOutForm({ ...inOutForm, reason: e.target.value })} />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setInOutDialogOpen(false)}>取消</Button>
            <Button onClick={handleStockInOut} disabled={stockInOutMutation.isPending}>确认</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* 删除确认 */}
      <Dialog open={!!deletePoId} onOpenChange={() => setDeletePoId(null)}>
        <DialogContent className="max-w-sm">
          <DialogHeader><DialogTitle>确认删除</DialogTitle></DialogHeader>
          <p className="text-sm text-muted-foreground">确定删除该入库记录吗？</p>
          <DialogFooter>
            <Button variant="outline" onClick={() => setDeletePoId(null)}>取消</Button>
            <Button variant="destructive" onClick={() => deletePoId && deletePoMutation.mutate(deletePoId)} disabled={deletePoMutation.isPending}>删除</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}

// ==================== 可编辑库存数量组件 ====================

function EditableStock({
  value,
  isLow,
  isOutOfStock,
  onUpdate,
  isPending,
}: {
  value: number;
  isLow: boolean;
  isOutOfStock: boolean;
  onUpdate: (v: number) => void;
  isPending?: boolean;
}) {
  const [editing, setEditing] = useState(false);
  const [editValue, setEditValue] = useState(String(value));
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (editing && inputRef.current) {
      inputRef.current.focus();
      inputRef.current.select();
    }
  }, [editing]);

  const handleStartEdit = () => {
    setEditing(true);
    setEditValue(String(value));
  };

  const handleSave = () => {
    const newVal = Number(editValue);
    if (isNaN(newVal) || newVal < 0) {
      toast.error("请输入有效的库存份数");
      setEditValue(String(value));
      setEditing(false);
      return;
    }
    if (newVal !== value) {
      onUpdate(newVal);
    }
    setEditing(false);
  };

  const handleCancel = () => {
    setEditValue(String(value));
    setEditing(false);
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter") handleSave();
    if (e.key === "Escape") handleCancel();
  };

  if (isPending) {
    return (
      <div className="flex items-center justify-end">
        <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />
      </div>
    );
  }

  if (editing) {
    return (
      <div className="flex items-center gap-1 justify-end">
        <Input
          ref={inputRef}
          type="number"
          value={editValue}
          onChange={(e) => setEditValue(e.target.value)}
          onKeyDown={handleKeyDown}
          onBlur={handleSave}
          className="h-7 w-24 text-right text-sm"
          min={0}
        />
        <Button variant="ghost" size="icon" className="h-7 w-7 text-green-600" onMouseDown={(e) => { e.preventDefault(); handleSave(); }}>
          <Check className="h-3 w-3" />
        </Button>
        <Button variant="ghost" size="icon" className="h-7 w-7 text-red-500" onMouseDown={(e) => { e.preventDefault(); handleCancel(); }}>
          <X className="h-3 w-3" />
        </Button>
      </div>
    );
  }

  return (
    <div className="flex items-center gap-1 justify-end group">
      <span
        className={cn(
          "font-medium tabular-nums cursor-pointer hover:bg-muted px-2 py-1 rounded transition-colors",
          isOutOfStock && "text-red-600 font-bold",
          isLow && !isOutOfStock && "text-orange-600"
        )}
        onClick={handleStartEdit}
        title="点击修改库存份数"
      >
        {value.toLocaleString()}
      </span>
      <Pencil className="h-3 w-3 text-muted-foreground opacity-0 group-hover:opacity-100 cursor-pointer transition-opacity" onClick={handleStartEdit} />
    </div>
  );
}
