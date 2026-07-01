import React, { useState, useEffect, useMemo } from "react";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter,
} from "@/components/ui/dialog";
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from "@/components/ui/select";
import { ComboBox } from "@/components/ui/combobox";
import { Plus, Trash2 } from "lucide-react";

interface Material {
  id: number;
  code: string;
  name: string;
  spec: string | null;
  unit: string;
  items_per_box: number | null;
  material_category_id: number | null;
}

interface Supplier {
  id: number;
  name: string;
}

interface Warehouse {
  id: number;
  name: string;
}

interface PurchaseItem {
  product_id: number;
  product_name: string;
  box_count: number;
  items_per_box: number;
  total_qty: number;
  unit: string;
  quoted_unit_price: number | null;
  actual_amount: number;
  notes: string;
}

interface MaterialPurchaseDialogProps {
  open: boolean;
  onClose: () => void;
  preSelectedMaterial?: Material | null;
  onSuccess?: () => void;
}

export default function MaterialPurchaseDialog({
  open,
  onClose,
  preSelectedMaterial,
  onSuccess,
}: MaterialPurchaseDialogProps) {
  const [orderDate, setOrderDate] = useState<string>(
    new Date().toISOString().split("T")[0]
  );
  const [supplierId, setSupplierId] = useState<string>("");
  const [warehouseId, setWarehouseId] = useState<string>("");
  const [categoryFilter, setCategoryFilter] = useState<string>("all");
  const [notes, setNotes] = useState("");
  const [items, setItems] = useState<PurchaseItem[]>([]);

  // 查询物料分类
  const { data: categories = [] } = useQuery<{id: number; name: string}[]>({
    queryKey: ["material-categories-for-purchase"],
    queryFn: async () => {
      const res = await api.get("/v1/material-categories");
      const arr = Array.isArray(res.data) ? res.data : res.data?.items || [];
      return arr;
    },
    enabled: open,
  });

  // 查询物料列表（从物料管理接口获取）
  const { data: materials = [] } = useQuery<Material[]>({
    queryKey: ["materials-for-purchase"],
    queryFn: async () => {
      const res = await api.get("/v1/materials?limit=500");
      const data = res.data;
      // 兼容两种格式：{items: [...]} 或 [...]
      return data?.items || data || [];
    },
    enabled: open,
  });

  // 查询供应商
  const { data: suppliers = [] } = useQuery<Supplier[]>({
    queryKey: ["suppliers-for-purchase"],
    queryFn: async () => {
      const res = await api.get("/v4/suppliers?limit=500");
      const arr = Array.isArray(res.data) ? res.data : res.data?.data || [];
      return arr;
    },
    enabled: open,
  });

  // 查询仓库
  const { data: warehouses = [] } = useQuery<Warehouse[]>({
    queryKey: ["warehouses-for-purchase"],
    queryFn: async () => {
      const res = await api.get("/v1/warehouse-v2/warehouses");
      const arr = Array.isArray(res.data) ? res.data : res.data?.items || [];
      return arr;
    },
    enabled: open,
  });

  // 默认选择国内整包仓（必须在 warehouses 声明之后）
  useEffect(() => {
    if (open && warehouses.length > 0 && !warehouseId) {
      const defaultWarehouse = warehouses.find((w) => w.name === "国内整包仓" || w.name.includes("整包"));
      if (defaultWarehouse) {
        setWarehouseId(String(defaultWarehouse.id));
      }
    }
  }, [open, warehouses]);

  // 预选中物料时自动添加一行
  useEffect(() => {
    if (open && preSelectedMaterial && items.length === 0) {
      addItem(preSelectedMaterial);
    }
  }, [open, preSelectedMaterial]);

  // 按分类筛选物料
  const filteredMaterials = useMemo(() => {
    if (categoryFilter === "all") return materials;
    return materials.filter((m) => String(m.material_category_id) === categoryFilter);
  }, [materials, categoryFilter]);

  const addItem = () => {
    // 添加空行，让用户自己选择物料
    setItems((prev) => [
      ...prev,
      {
        product_id: 0,
        product_name: "",
        box_count: 0,
        items_per_box: 0,
        total_qty: 0,
        unit: "",
        quoted_unit_price: null,
        actual_amount: 0,
        notes: "",
      },
    ]);
  };

  const removeItem = (index: number) => {
    setItems((prev) => prev.filter((_, i) => i !== index));
  };

  const updateItem = (index: number, field: keyof PurchaseItem, value: any) => {
    setItems((prev) => {
      const next = [...prev];
      const item = { ...next[index], [field]: value };

      // 自动计算总数量
      if (field === "box_count" || field === "items_per_box") {
        item.total_qty = item.box_count * item.items_per_box;
      }

      next[index] = item;
      return next;
    });
  };

  const actualTotal = useMemo(() => {
    return items.reduce((sum, item) => sum + (item.actual_amount || 0), 0);
  }, [items]);

  const quotedTotal = useMemo(() => {
    return items.reduce((sum, item) => {
      if (item.quoted_unit_price && item.total_qty) {
        return sum + item.quoted_unit_price * item.total_qty;
      }
      return sum;
    }, 0);
  }, [items]);

  const handleSubmit = async () => {
    if (!supplierId || isNaN(Number(supplierId))) {
      toast.error("请选择有效的供应商");
      return;
    }
    if (items.length === 0) {
      toast.error("请添加采购明细");
      return;
    }
    for (const item of items) {
      if (!item.product_id || item.box_count <= 0 || item.actual_amount <= 0) {
        toast.error("请完善采购明细");
        return;
      }
    }

    try {
      const payload = {
        order_date: orderDate,
        supplier_id: Number(supplierId),
        warehouse_id: warehouseId ? Number(warehouseId) : null,
        quoted_total: quotedTotal > 0 ? quotedTotal : null,
        actual_total: actualTotal,
        notes,
        items: items.map((item) => ({
          product_id: item.product_id,
          box_count: item.box_count,
          items_per_box: item.items_per_box,
          // 空值传null，不能传空字符串
          quoted_unit_price: item.quoted_unit_price && item.quoted_unit_price > 0 ? item.quoted_unit_price : null,
          actual_amount: item.actual_amount,
          notes: item.notes || null,
        })),
      };

      await api.post("/v1/material-purchases", payload);
      toast.success("采购单创建成功");
      onSuccess?.();
      onClose();
      // 重置表单
      setItems([]);
      setSupplierId("");
      setWarehouseId("");
      setCategoryFilter("all");
      setNotes("");
      setOrderDate(new Date().toISOString().split("T")[0]);
    } catch (error: any) {
      // 处理422等错误，detail可能是对象或字符串
      const detail = error.response?.data?.detail;
      let msg = "创建失败";
      try {
        if (typeof detail === "string") {
          msg = detail;
        } else if (Array.isArray(detail) && detail.length > 0) {
          // Pydantic validation errors
          const first = detail[0];
          if (first && typeof first === "object") {
            const loc = first.loc?.join?.(".") || "";
            const errMsg = first.msg || "";
            msg = (loc ? `${loc}: ` : "") + errMsg;
          } else {
            msg = String(first);
          }
        } else if (typeof detail === "object" && detail !== null) {
          msg = JSON.stringify(detail);
        } else if (error.message) {
          msg = error.message;
        }
      } catch (_) {
        msg = "创建失败";
      }
      toast.error(msg);
      console.error("Create purchase order failed:", error.response?.data);
    }
  };

  return (
    <Dialog open={open} onOpenChange={(v) => !v && onClose()}>
      <DialogContent className="max-w-4xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>物料采购入库</DialogTitle>
        </DialogHeader>

        <div className="space-y-4 py-4">
          {/* 采购单头信息 */}
          <div className="grid grid-cols-3 gap-3">
            <div className="space-y-2">
              <Label>日期 <span className="text-red-500">*</span></Label>
              <Input
                type="date"
                value={orderDate}
                onChange={(e) => setOrderDate(e.target.value)}
              />
            </div>
            <div className="space-y-2">
              <Label>供应商 <span className="text-red-500">*</span></Label>
              <ComboBox
                value={supplierId}
                options={suppliers.map((s) => ({ value: String(s.id), label: s.name }))}
                placeholder="选择供应商..."
                onChange={(v) => setSupplierId(v)}
              />
            </div>
            <div className="space-y-2">
              <Label>入库仓库</Label>
              <Select value={warehouseId} onValueChange={setWarehouseId}>
                <SelectTrigger>
                  <SelectValue placeholder="选择仓库">
                    {warehouseId ? warehouses.find(w => String(w.id) === warehouseId)?.name : "选择仓库"}
                  </SelectValue>
                </SelectTrigger>
                <SelectContent>
                  {warehouses.map((w) => (
                    <SelectItem key={w.id} value={String(w.id)}>
                      {w.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>

          {/* 采购明细 */}
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <Label>采购明细</Label>
              <div className="flex items-center gap-2">
                <Select value={categoryFilter} onValueChange={setCategoryFilter}>
                  <SelectTrigger className="w-[140px]">
                    <SelectValue placeholder="全部分类">
                      {categoryFilter === "all"
                        ? "全部分类"
                        : categories.find((c) => String(c.id) === categoryFilter)?.name || "全部分类"}
                    </SelectValue>
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">全部分类</SelectItem>
                    {categories.map((cat) => (
                      <SelectItem key={cat.id} value={String(cat.id)}>
                        {cat.name}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
                <Button variant="outline" size="sm" onClick={() => addItem()}>
                  <Plus className="h-4 w-4 mr-1" />
                  添加物料
                </Button>
              </div>
            </div>

            {items.length === 0 ? (
              <div className="text-center py-8 text-muted-foreground border rounded-lg">
                点击"添加物料"开始录入
              </div>
            ) : (
              <div className="space-y-3">
                {items.map((item, idx) => (
                  <div
                    key={idx}
                    className="border rounded-lg p-3 space-y-3 relative"
                  >
                    <Button
                      variant="ghost"
                      size="sm"
                      className="absolute top-2 right-2 text-red-500"
                      onClick={() => removeItem(idx)}
                    >
                      <Trash2 className="h-4 w-4" />
                    </Button>

                    <div className="grid grid-cols-4 gap-3">
                      <div className="space-y-1">
                        <Label className="text-xs">物料</Label>
                        <ComboBox
                          value={String(item.product_id)}
                          options={filteredMaterials.map((m) => ({
                            value: String(m.id),
                            label: m.name,
                          }))}
                          placeholder="选择物料..."
                          onChange={(v) => {
                            const m = filteredMaterials.find((x) => String(x.id) === v);
                            if (m) {
                              updateItem(idx, "product_id", m.id);
                              updateItem(idx, "product_name", m.name);
                              updateItem(idx, "items_per_box", m.items_per_box || 1);
                              updateItem(idx, "unit", m.unit);
                              updateItem(idx, "total_qty", (m.items_per_box || 1) * item.box_count);
                            }
                          }}
                        />
                      </div>
                      <div className="space-y-1">
                        <Label className="text-xs">箱数</Label>
                        <Input
                          type="number"
                          min={1}
                          value={item.box_count}
                          onChange={(e) =>
                            updateItem(idx, "box_count", Number(e.target.value) || 0)
                          }
                        />
                      </div>
                      <div className="space-y-1">
                        <Label className="text-xs">每箱数量</Label>
                        <Input
                          type="number"
                          min={1}
                          value={item.items_per_box}
                          onChange={(e) =>
                            updateItem(idx, "items_per_box", Number(e.target.value) || 0)
                          }
                        />
                      </div>
                      <div className="space-y-1">
                        <Label className="text-xs">总数量</Label>
                        <div className="h-10 flex items-center px-3 border rounded-md bg-muted/50 text-sm">
                          {item.total_qty} {item.unit}
                        </div>
                      </div>
                    </div>

                    <div className="grid grid-cols-3 gap-3">
                      <div className="space-y-1">
                        <Label className="text-xs">报价单价（/{item.unit}）</Label>
                        <Input
                          type="number"
                          step="0.0001"
                          value={item.quoted_unit_price ?? ""}
                          placeholder="可选"
                          onChange={(e) =>
                            updateItem(idx, "quoted_unit_price", e.target.value ? Number(e.target.value) : null)
                          }
                        />
                      </div>
                      <div className="space-y-1">
                        <Label className="text-xs">实付金额（元）</Label>
                        <Input
                          type="number"
                          step="0.01"
                          value={item.actual_amount}
                          onChange={(e) =>
                            updateItem(idx, "actual_amount", Number(e.target.value) || 0)
                          }
                        />
                      </div>
                      <div className="space-y-1">
                        <Label className="text-xs">核算单价</Label>
                        <div className="h-10 flex items-center px-3 border rounded-md bg-muted/50 text-sm">
                          {item.total_qty > 0
                            ? `¥${(Math.ceil((item.actual_amount / item.total_qty) * 100) / 100).toFixed(2)}/${item.unit}`
                            : "—"}
                        </div>
                      </div>
                    </div>

                    <div className="space-y-1">
                      <Label className="text-xs">备注</Label>
                      <Input
                        value={item.notes}
                        onChange={(e) => updateItem(idx, "notes", e.target.value)}
                        placeholder="选填"
                      />
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* 金额汇总 */}
          {items.length > 0 && (
            <div className="border rounded-lg p-3 space-y-2">
              <div className="flex justify-between text-sm">
                <span className="text-muted-foreground">报价总金额：</span>
                <span>¥{quotedTotal.toFixed(2)}</span>
              </div>
              <div className="flex justify-between text-sm font-medium">
                <span>实付总金额：</span>
                <span className="text-lg">¥{actualTotal.toFixed(2)}</span>
              </div>
            </div>
          )}

          <div className="space-y-2">
            <Label>备注</Label>
            <Input
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              placeholder="采购单备注..."
            />
          </div>
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={onClose}>
            取消
          </Button>
          <Button onClick={handleSubmit} disabled={items.length === 0}>
            确认创建
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
