import React, { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
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
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  Search, Plus, Package, ArrowDown, Boxes, Fish, Wrench,
  ClipboardList, CheckCircle2, Circle, AlertCircle,
} from "lucide-react";
import { toast } from "sonner";

// ==================== 类型 ====================
interface PurchaseOrder {
  id: number;
  order_no: string;
  order_date: string;
  supplier_name: string;
  main_product_type: string;
  warehouse_name: string;
  has_accessories: boolean;
  total_qty: number;
  total_amount: number;
  status: string;
  notes?: string;
}

interface PurchaseOrderItem {
  id: number;
  product_name: string;
  product_category: string;
  item_type: string;
  qty: number;
  unit: string;
  unit_price: number;
  total_amount: number;
  received_qty: number;
}

interface Supplier {
  id: number;
  name: string;
}

interface Product {
  id: number;
  name: string;
  category: string;
  unit: string;
}

// ==================== 辅助函数 ====================
const getStatusBadge = (status: string) => {
  const map: Record<string, string> = {
    pending: "bg-yellow-100 text-yellow-800",
    partial: "bg-blue-100 text-blue-800",
    completed: "bg-green-100 text-green-800",
    cancelled: "bg-gray-100 text-gray-600",
  };
  const labelMap: Record<string, string> = {
    pending: "待入库",
    partial: "部分入库",
    completed: "已完成",
    cancelled: "已取消",
  };
  return { className: map[status] || "bg-gray-100", label: labelMap[status] || status };
};

const fmtN = (n?: number) => {
  if (n === undefined || n === null) return "-";
  return n.toLocaleString("zh-CN", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
};

const typeMap: Record<string, string> = {
  import_whole_fish: "进口整鱼",
  domestic_whole_fish: "国内整鱼",
  packaging: "包装物",
  shrimp_whole: "甜虾整包",
  scallop_whole: "北极贝整包",
  accessory: "辅料",
};

// ==================== API 函数 ====================
const fetchPurchaseOrders = async (params: Record<string, any>) => {
  const { data } = await api.get("/v1/purchase-orders", { params });
  return data;
};

const fetchSuppliers = async () => {
  const { data } = await api.get("/v1/companies?type=supplier&limit=500");
  return data.items;
};

const fetchProducts = async () => {
  const { data } = await api.get("/v1/products?limit=500");
  return data.items;
};

// ==================== 新建采购单弹窗 ====================
function CreateOrderDialog({
  open, onOpenChange, onSuccess,
}: {
  open: boolean;
  onOpenChange: (v: boolean) => void;
  onSuccess: () => void;
}) {
  const queryClient = useQueryClient();
  const [supplierId, setSupplierId] = useState("");
  const [productType, setProductType] = useState("domestic_whole_fish");
  const [orderDate, setOrderDate] = useState(new Date().toISOString().split("T")[0]);
  const [notes, setNotes] = useState("");
  const [items, setItems] = useState<Array<{
    product_id: string;
    qty: string;
    unit: string;
    unit_price: string;
    item_type: string;
  }>>([{ product_id: "", qty: "", unit: "box", unit_price: "", item_type: "main" }]);

  const { data: suppliers } = useQuery({
    queryKey: ["suppliers-for-po"],
    queryFn: fetchSuppliers,
    enabled: open,
  });

  const { data: products } = useQuery({
    queryKey: ["products-for-po"],
    queryFn: fetchProducts,
    enabled: open,
  });

  const createMutation = useMutation({
    mutationFn: async (payload: any) => {
      const { data } = await api.post("/v1/purchase-orders", payload);
      return data;
    },
    onSuccess: () => {
      toast.success("采购单创建成功");
      queryClient.invalidateQueries({ queryKey: ["purchase-orders"] });
      onOpenChange(false);
      onSuccess();
    },
    onError: (err: any) => {
      toast.error(err.response?.data?.detail || "创建失败");
    },
  });

  const handleAddItem = () => {
    setItems([...items, { product_id: "", qty: "", unit: "box", unit_price: "", item_type: "main" }]);
  };

  const handleRemoveItem = (index: number) => {
    setItems(items.filter((_, i) => i !== index));
  };

  const handleItemChange = (index: number, field: string, value: string) => {
    const newItems = [...items];
    newItems[index] = { ...newItems[index], [field]: value };
    setItems(newItems);
  };

  const handleSubmit = () => {
    if (!supplierId) {
      toast.error("请选择供应商");
      return;
    }
    const validItems = items.filter((i) => i.product_id && i.qty && i.unit_price);
    if (validItems.length === 0) {
      toast.error("请至少添加一个采购项");
      return;
    }

    const totalQty = validItems.reduce((sum, i) => sum + Number(i.qty), 0);
    const totalAmount = validItems.reduce((sum, i) => sum + Number(i.qty) * Number(i.unit_price), 0);

    createMutation.mutate({
      supplier_id: Number(supplierId),
      main_product_type: productType,
      main_warehouse_id: productType === "packaging" || productType === "accessory" ? 5 : 2, // FL-MATERIAL 或 ZB-DOMESTIC
      order_date: orderDate,
      has_accessories: validItems.some((i) => i.item_type === "accessory"),
      total_qty: totalQty,
      total_amount: totalAmount,
      notes: notes || undefined,
      items: validItems.map((i) => ({
        product_id: Number(i.product_id),
        qty: Number(i.qty),
        unit: i.unit,
        unit_price: Number(i.unit_price),
        item_type: i.item_type,
      })),
    });
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-3xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Package className="h-5 w-5" />
            新建采购单
          </DialogTitle>
        </DialogHeader>

        <div className="space-y-4">
          {/* 基本信息 */}
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label>供应商 *</Label>
              <Select value={supplierId} onValueChange={setSupplierId}>
                <SelectTrigger>
                  <SelectValue placeholder="选择供应商" />
                </SelectTrigger>
                <SelectContent>
                  {suppliers?.map((s: Supplier) => (
                    <SelectItem key={s.id} value={String(s.id)}>{s.name}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label>采购类型</Label>
              <Select value={productType} onValueChange={setProductType}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="domestic_whole_fish">国内整鱼（三文鱼）</SelectItem>
                  <SelectItem value="import_whole_fish">进口整鱼（三文鱼）</SelectItem>
                  <SelectItem value="shrimp_whole">甜虾整包</SelectItem>
                  <SelectItem value="scallop_whole">北极贝整包</SelectItem>
                  <SelectItem value="packaging">包装物</SelectItem>
                  <SelectItem value="accessory">辅料/消耗品</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>

          <div className="space-y-2">
            <Label>采购日期</Label>
            <Input type="date" value={orderDate} onChange={(e) => setOrderDate(e.target.value)} />
          </div>

          {/* 采购明细 */}
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <Label>采购明细</Label>
              <Button variant="outline" size="sm" onClick={handleAddItem}>
                <Plus className="h-4 w-4 mr-1" />添加项
              </Button>
            </div>

            <div className="border rounded-md">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>产品</TableHead>
                    <TableHead>类型</TableHead>
                    <TableHead className="text-right">数量</TableHead>
                    <TableHead>单位</TableHead>
                    <TableHead className="text-right">单价</TableHead>
                    <TableHead className="text-right">小计</TableHead>
                    <TableHead className="w-[60px]"></TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {items.map((item, index) => (
                    <TableRow key={index}>
                      <TableCell>
                        <Select value={item.product_id} onValueChange={(v) => handleItemChange(index, "product_id", v)}>
                          <SelectTrigger className="w-[200px]">
                            <SelectValue placeholder="选择产品" />
                          </SelectTrigger>
                          <SelectContent>
                            {products?.map((p: Product) => (
                              <SelectItem key={p.id} value={String(p.id)}>{p.name}</SelectItem>
                            ))}
                          </SelectContent>
                        </Select>
                      </TableCell>
                      <TableCell>
                        <Select value={item.item_type} onValueChange={(v) => handleItemChange(index, "item_type", v)}>
                          <SelectTrigger className="w-[100px]">
                            <SelectValue />
                          </SelectTrigger>
                          <SelectContent>
                            <SelectItem value="main">主产品</SelectItem>
                            <SelectItem value="accessory">搭配品</SelectItem>
                            <SelectItem value="material">辅料</SelectItem>
                          </SelectContent>
                        </Select>
                      </TableCell>
                      <TableCell>
                        <Input
                          type="number"
                          value={item.qty}
                          onChange={(e) => handleItemChange(index, "qty", e.target.value)}
                          className="w-24 text-right"
                        />
                      </TableCell>
                      <TableCell>
                        <Select value={item.unit} onValueChange={(v) => handleItemChange(index, "unit", v)}>
                          <SelectTrigger className="w-[80px]">
                            <SelectValue />
                          </SelectTrigger>
                          <SelectContent>
                            <SelectItem value="box">箱</SelectItem>
                            <SelectItem value="kg">kg</SelectItem>
                            <SelectItem value="piece">条</SelectItem>
                            <SelectItem value="board">板</SelectItem>
                            <SelectItem value="plate">盘</SelectItem>
                            <SelectItem value="个">个</SelectItem>
                            <SelectItem value="卷">卷</SelectItem>
                          </SelectContent>
                        </Select>
                      </TableCell>
                      <TableCell>
                        <Input
                          type="number"
                          value={item.unit_price}
                          onChange={(e) => handleItemChange(index, "unit_price", e.target.value)}
                          className="w-28 text-right"
                        />
                      </TableCell>
                      <TableCell className="text-right font-medium">
                        ¥{fmtN(Number(item.qty || 0) * Number(item.unit_price || 0))}
                      </TableCell>
                      <TableCell>
                        {items.length > 1 && (
                          <Button variant="ghost" size="sm" onClick={() => handleRemoveItem(index)}>
                            ×
                          </Button>
                        )}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          </div>

          <div className="space-y-2">
            <Label>备注</Label>
            <Input value={notes} onChange={(e) => setNotes(e.target.value)} />
          </div>
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>取消</Button>
          <Button onClick={handleSubmit} disabled={createMutation.isPending}>
            {createMutation.isPending ? "创建中..." : "创建采购单"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

// ==================== 主页面 ====================
export function PurchaseOrderPage() {
  const [activeTab, setActiveTab] = useState("list");
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("");
  const [createOpen, setCreateOpen] = useState(false);
  const [page, setPage] = useState(1);
  const PAGE_SIZE = 20;

  const { data, isLoading } = useQuery({
    queryKey: ["purchase-orders", page, search, statusFilter],
    queryFn: () =>
      fetchPurchaseOrders({
        skip: (page - 1) * PAGE_SIZE,
        limit: PAGE_SIZE,
        search: search || undefined,
        status: statusFilter || undefined,
      }),
  });

  const orders: PurchaseOrder[] = data?.items || [];
  const total = data?.total || 0;
  const totalPages = Math.ceil(total / PAGE_SIZE) || 1;

  return (
    <div className="p-6 space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold flex items-center gap-2">
          <Package className="h-6 w-6" />
          采购入库管理
        </h1>
        <Button onClick={() => setCreateOpen(true)}>
          <Plus className="h-4 w-4 mr-1" />
          新建采购单
        </Button>
      </div>

      <CreateOrderDialog
        open={createOpen}
        onOpenChange={setCreateOpen}
        onSuccess={() => setPage(1)}
      />

      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList>
          <TabsTrigger value="list">采购单列表</TabsTrigger>
          <TabsTrigger value="summary">采购统计</TabsTrigger>
        </TabsList>

        <TabsContent value="list" className="space-y-4">
          {/* 筛选栏 */}
          <div className="flex items-center gap-2">
            <div className="relative flex-1 max-w-sm">
              <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
              <Input
                placeholder="搜索采购单号..."
                className="pl-9"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
              />
            </div>
            <Select value={statusFilter} onValueChange={setStatusFilter}>
              <SelectTrigger className="w-32">
                <SelectValue placeholder="状态" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="">全部</SelectItem>
                <SelectItem value="pending">待入库</SelectItem>
                <SelectItem value="partial">部分入库</SelectItem>
                <SelectItem value="completed">已完成</SelectItem>
                <SelectItem value="cancelled">已取消</SelectItem>
              </SelectContent>
            </Select>
          </div>

          {/* 表格 */}
          <div className="border rounded-md">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>采购单号</TableHead>
                  <TableHead>日期</TableHead>
                  <TableHead>供应商</TableHead>
                  <TableHead>类型</TableHead>
                  <TableHead>仓库</TableHead>
                  <TableHead className="text-right">数量</TableHead>
                  <TableHead className="text-right">金额</TableHead>
                  <TableHead>状态</TableHead>
                  <TableHead className="w-[100px]">操作</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {isLoading ? (
                  <TableRow>
                    <TableCell colSpan={9} className="text-center py-8">加载中...</TableCell>
                  </TableRow>
                ) : orders.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={9} className="text-center py-8 text-muted-foreground">暂无采购单</TableCell>
                  </TableRow>
                ) : (
                  orders.map((order) => {
                    const status = getStatusBadge(order.status);
                    return (
                      <TableRow key={order.id}>
                        <TableCell className="font-medium">{order.order_no}</TableCell>
                        <TableCell>{order.order_date}</TableCell>
                        <TableCell>{order.supplier_name}</TableCell>
                        <TableCell>{typeMap[order.main_product_type] || order.main_product_type}</TableCell>
                        <TableCell>{order.warehouse_name}</TableCell>
                        <TableCell className="text-right">{order.total_qty}</TableCell>
                        <TableCell className="text-right">¥{fmtN(order.total_amount)}</TableCell>
                        <TableCell>
                          <Badge className={status.className}>{status.label}</Badge>
                        </TableCell>
                        <TableCell>
                          <Button variant="ghost" size="sm">详情</Button>
                        </TableCell>
                      </TableRow>
                    );
                  })
                )}
              </TableBody>
            </Table>
          </div>

          {/* 分页 */}
          {totalPages > 1 && (
            <div className="flex items-center justify-center gap-2">
              <Button variant="outline" size="sm" onClick={() => setPage(1)} disabled={page === 1}>首页</Button>
              <Button variant="outline" size="sm" onClick={() => setPage((p) => Math.max(1, p - 1))} disabled={page === 1}>上一页</Button>
              <span className="text-sm text-muted-foreground">第 {page} / {totalPages} 页</span>
              <Button variant="outline" size="sm" onClick={() => setPage((p) => Math.min(totalPages, p + 1))} disabled={page === totalPages}>下一页</Button>
              <Button variant="outline" size="sm" onClick={() => setPage(totalPages)} disabled={page === totalPages}>尾页</Button>
            </div>
          )}
        </TabsContent>

        <TabsContent value="summary">
          <Card>
            <CardHeader>
              <CardTitle>采购统计</CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-muted-foreground">统计功能开发中...</p>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}
