import React, { useState, useMemo } from "react";
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
import { toast } from "sonner";
import {
  Plus, Search, Pencil, Trash2, Package, ArrowDown, Boxes,
} from "lucide-react";

// ==================== 类型 ====================
interface Material {
  id: number;
  code: string;
  name: string;
  spec: string | null;
  unit: string;
  supplier_id: number | null;
  supplier_name: string | null;
  stock_quantity: number;
  lead_time_days: number | null;
  last_purchase_price: number | null;
  is_active: boolean;
}

interface Supplier {
  id: number;
  name: string;
  code: string | null;
  contact: string | null;
  phone: string | null;
}

interface PurchaseRecord {
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
}

const fmtMoney = (v: number | null) => (v == null ? "-" : `¥${v.toFixed(2)}`);

// ==================== 主页面 ====================
export function MaterialManagementPage() {
  const qc = useQueryClient();
  const [activeTab, setActiveTab] = useState("materials");
  const [search, setSearch] = useState("");
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [deleteId, setDeleteId] = useState<number | null>(null);

  // 表单
  const [formCode, setFormCode] = useState("");
  const [formName, setFormName] = useState("");
  const [formSpec, setFormSpec] = useState("");
  const [formUnit, setFormUnit] = useState("个");
  const [formSupplierId, setFormSupplierId] = useState("");
  const [formLeadTime, setFormLeadTime] = useState("");
  const [formLastPrice, setFormLastPrice] = useState("");
  const [formIsActive, setFormIsActive] = useState(true);

  // 入库弹窗
  const [inDialogOpen, setInDialogOpen] = useState(false);
  const [inMaterial, setInMaterial] = useState<Material | null>(null);
  const [inQty, setInQty] = useState("");
  const [inPrice, setInPrice] = useState("");
  const [inDate, setInDate] = useState(new Date().toISOString().split("T")[0]);

  // 数据查询
  const { data: materialsData, isLoading: mLoading } = useQuery({
    queryKey: ["materials"],
    queryFn: async () => {
      const res = await api.get("/v1/materials/?limit=500");
      return res.data.items as Material[];
    },
  });

  const { data: suppliersData } = useQuery({
    queryKey: ["suppliers"],
    queryFn: async () => {
      const res = await api.get("/v1/companies/?type=supplier&limit=500");
      return res.data.items as Supplier[];
    },
  });

  const { data: purchaseData } = useQuery({
    queryKey: ["purchase-records"],
    queryFn: async () => {
      const res = await api.get("/v1/warehouse/purchase-orders/?limit=500");
      return res.data.items as PurchaseRecord[];
    },
  });

  const materials = materialsData || [];
  const suppliers = suppliersData || [];
  const purchases = purchaseData || [];

  // 供应商名称映射
  const supplierMap = useMemo(() => {
    const map = new Map<number, string>();
    suppliers.forEach((s) => map.set(s.id, s.name));
    return map;
  }, [suppliers]);

  // 给物料附加供应商名称
  const materialsWithSupplier = useMemo(() => {
    return materials.map((m) => ({
      ...m,
      supplier_name: m.supplier_id ? supplierMap.get(m.supplier_id) || null : null,
    }));
  }, [materials, supplierMap]);

  // 筛选
  const filtered = useMemo(() => {
    if (!search.trim()) return materialsWithSupplier;
    const s = search.trim().toLowerCase();
    return materialsWithSupplier.filter(
      (m) =>
        m.name.toLowerCase().includes(s) ||
        m.code.toLowerCase().includes(s) ||
        (m.spec ?? "").toLowerCase().includes(s) ||
        (m.supplier_name ?? "").toLowerCase().includes(s)
    );
  }, [materialsWithSupplier, search]);

  // CRUD Mutations
  const createMutation = useMutation({
    mutationFn: async (payload: any) => {
      const res = await api.post("/v1/products/", payload);
      return res.data;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["materials"] });
      setDialogOpen(false);
      resetForm();
      toast.success("物料创建成功");
    },
    onError: (err: any) => toast.error(err.response?.data?.detail || "创建失败"),
  });

  const updateMutation = useMutation({
    mutationFn: async ({ id, payload }: { id: number; payload: any }) => {
      await api.put(`/v1/products/${id}`, payload);
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["materials"] });
      setDialogOpen(false);
      setEditingId(null);
      resetForm();
      toast.success("物料更新成功");
    },
    onError: (err: any) => toast.error(err.response?.data?.detail || "更新失败"),
  });

  const deleteMutation = useMutation({
    mutationFn: (id: number) => api.delete(`/v1/products/${id}`),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["materials"] });
      setDeleteId(null);
      toast.success("物料已删除");
    },
    onError: (err: any) => toast.error(err.response?.data?.detail || "删除失败"),
  });

  // 采购入库 Mutation
  const inboundMutation = useMutation({
    mutationFn: async (payload: any) => {
      await api.post("/v1/warehouse/purchase-orders/", payload);
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["materials"] });
      qc.invalidateQueries({ queryKey: ["purchase-records"] });
      setInDialogOpen(false);
      resetInbound();
      toast.success("采购入库成功");
    },
    onError: (err: any) => toast.error(err.response?.data?.detail || "入库失败"),
  });

  function resetForm() {
    setFormCode("");
    setFormName("");
    setFormSpec("");
    setFormUnit("个");
    setFormSupplierId("");
    setFormLeadTime("");
    setFormLastPrice("");
    setFormIsActive(true);
    setEditingId(null);
  }

  function resetInbound() {
    setInMaterial(null);
    setInQty("");
    setInPrice("");
    setInDate(new Date().toISOString().split("T")[0]);
  }

  function openCreate() {
    resetForm();
    setDialogOpen(true);
  }

  function openEdit(m: Material) {
    setEditingId(m.id);
    setFormCode(m.code);
    setFormName(m.name);
    setFormSpec(m.spec ?? "");
    setFormUnit(m.unit);
    setFormSupplierId(m.supplier_id ? String(m.supplier_id) : "");
    setFormLeadTime(m.lead_time_days ? String(m.lead_time_days) : "");
    setFormLastPrice(m.last_purchase_price ? String(m.last_purchase_price) : "");
    setFormIsActive(m.is_active);
    setDialogOpen(true);
  }

  function openInbound(m: Material) {
    setInMaterial(m);
    setInDialogOpen(true);
  }

  function handleSubmit() {
    if (!formName.trim()) {
      toast.error("物料名称不能为空");
      return;
    }
    const payload: any = {
      category: "bom_material",
      code: formCode.trim() || undefined,
      name: formName.trim(),
      spec: formSpec.trim() || null,
      unit: formUnit,
      is_active: formIsActive,
      supplier_id: formSupplierId ? parseInt(formSupplierId) : null,
      lead_time_days: formLeadTime ? parseInt(formLeadTime) : null,
      last_purchase_price: formLastPrice ? parseFloat(formLastPrice) : null,
    };
    if (editingId) {
      updateMutation.mutate({ id: editingId, payload });
    } else {
      createMutation.mutate(payload);
    }
  }

  function handleInboundSubmit() {
    if (!inMaterial) return;
    const qty = Number(inQty);
    const price = Number(inPrice);
    if (!qty || qty <= 0) {
      toast.error("请输入入库数量");
      return;
    }
    const payload = {
      order_date: inDate,
      product_id: inMaterial.id,
      supplier_id: inMaterial.supplier_id || (suppliers[0]?.id ?? 1),
      batch_no: `PO-${inDate.replace(/-/g, "")}-${Math.floor(Math.random() * 1000)}`,
      quantity: qty,
      unit: inMaterial.unit,
      unit_price: price || 0,
      lead_time_days: inMaterial.lead_time_days || 3,
      warehouse_location: "A1-物料库",
      warehouse_type: "finished",
      inbound_type: "purchase",
    };
    inboundMutation.mutate(payload);
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">物料管理</h1>
          <p className="text-sm text-muted-foreground">包装物料与配套产品管理</p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" onClick={() => setActiveTab("inbound")}>
            <ArrowDown className="h-4 w-4 mr-1" />
            采购入库
          </Button>
          <Button onClick={openCreate}>
            <Plus className="h-4 w-4 mr-1" />
            新增物料
          </Button>
        </div>
      </div>

      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList className="grid w-full grid-cols-2">
          <TabsTrigger value="materials">
            <Package className="h-4 w-4 mr-1" />
            物料清单
          </TabsTrigger>
          <TabsTrigger value="inbound">
            <ArrowDown className="h-4 w-4 mr-1" />
            采购入库记录
          </TabsTrigger>
        </TabsList>

        {/* ===== Tab 1: 物料清单 ===== */}
        <TabsContent value="materials" className="space-y-4 pt-4">
          <div className="flex items-center gap-3">
            <div className="relative flex-1 max-w-sm">
              <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
              <Input
                placeholder="搜索物料名称、编码或规格..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                className="pl-9"
              />
            </div>
            <span className="text-sm text-muted-foreground">共 {filtered.length} 种物料</span>
          </div>

          <div className="border rounded-lg">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>编码</TableHead>
                  <TableHead>物料名称</TableHead>
                  <TableHead>规格</TableHead>
                  <TableHead>供应商</TableHead>
                  <TableHead className="text-right">当前库存</TableHead>
                  <TableHead className="text-right">供货周期</TableHead>
                  <TableHead className="text-right">最近采购价</TableHead>
                  <TableHead>状态</TableHead>
                  <TableHead className="w-[140px]">操作</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {mLoading ? (
                  <TableRow>
                    <TableCell colSpan={9} className="text-center py-8">加载中...</TableCell>
                  </TableRow>
                ) : filtered.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={9} className="text-center py-8 text-muted-foreground">
                      暂无物料，点击右上角"新增物料"创建
                    </TableCell>
                  </TableRow>
                ) : (
                  filtered.map((m) => (
                    <TableRow key={m.id} className={cn(!m.is_active && "opacity-50")}>
                      <TableCell className="font-mono text-xs text-muted-foreground">{m.code}</TableCell>
                      <TableCell className="font-medium">{m.name}</TableCell>
                      <TableCell className="text-muted-foreground">{m.spec ?? "-"}</TableCell>
                      <TableCell>{m.supplier_name ?? "-"}</TableCell>
                      <TableCell className="text-right">{m.stock_quantity} {m.unit}</TableCell>
                      <TableCell className="text-right">{m.lead_time_days ? `${m.lead_time_days}天` : "-"}</TableCell>
                      <TableCell className="text-right">{fmtMoney(m.last_purchase_price)}</TableCell>
                      <TableCell>
                        {m.is_active ? (
                          <Badge variant="secondary" className="bg-green-100 text-green-800">启用</Badge>
                        ) : (
                          <Badge variant="secondary" className="bg-gray-100 text-gray-800">停用</Badge>
                        )}
                      </TableCell>
                      <TableCell>
                        <div className="flex gap-1">
                          <Button variant="ghost" size="sm" className="h-7 text-xs" onClick={() => openInbound(m)}>
                            <ArrowDown className="h-3 w-3 mr-1" />入库
                          </Button>
                          <Button variant="ghost" size="icon" className="h-7 w-7" onClick={() => openEdit(m)}>
                            <Pencil className="h-3 w-3" />
                          </Button>
                          <Button variant="ghost" size="icon" className="h-7 w-7 text-red-500" onClick={() => setDeleteId(m.id)}>
                            <Trash2 className="h-3 w-3" />
                          </Button>
                        </div>
                      </TableCell>
                    </TableRow>
                  ))
                )}
              </TableBody>
            </Table>
          </div>
        </TabsContent>

        {/* ===== Tab 2: 采购入库记录 ===== */}
        <TabsContent value="inbound" className="space-y-4 pt-4">
          <div className="flex items-center justify-between">
            <h3 className="text-lg font-semibold">采购入库记录</h3>
            <span className="text-sm text-muted-foreground">共 {purchases.length} 条记录</span>
          </div>
          <div className="border rounded-lg">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>日期</TableHead>
                  <TableHead>物料</TableHead>
                  <TableHead>供应商</TableHead>
                  <TableHead>批次号</TableHead>
                  <TableHead className="text-right">数量</TableHead>
                  <TableHead className="text-right">单价</TableHead>
                  <TableHead className="text-right">总价</TableHead>
                  <TableHead>库位</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {purchases.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={8} className="text-center py-8 text-muted-foreground">
                      暂无采购入库记录
                    </TableCell>
                  </TableRow>
                ) : (
                  purchases.map((p) => (
                    <TableRow key={p.id}>
                      <TableCell>{p.order_date}</TableCell>
                      <TableCell className="font-medium">{p.product_name}</TableCell>
                      <TableCell>{p.supplier_name}</TableCell>
                      <TableCell className="font-mono text-xs">{p.batch_no}</TableCell>
                      <TableCell className="text-right">{p.quantity} {p.unit}</TableCell>
                      <TableCell className="text-right">{fmtMoney(p.unit_price)}</TableCell>
                      <TableCell className="text-right font-medium">{fmtMoney(p.total_amount)}</TableCell>
                      <TableCell className="text-muted-foreground">{p.warehouse_location}</TableCell>
                    </TableRow>
                  ))
                )}
              </TableBody>
            </Table>
          </div>
        </TabsContent>
      </Tabs>

      {/* ===== 新增/编辑物料弹窗 ===== */}
      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <DialogContent className="max-w-lg">
          <DialogHeader>
            <DialogTitle>{editingId ? "编辑物料" : "新增物料"}</DialogTitle>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label>物料编码</Label>
                <Input value={formCode} onChange={(e) => setFormCode(e.target.value)} placeholder="留空自动生成" className="text-muted-foreground" />
              </div>
              <div className="space-y-2">
                <Label>物料名称 *</Label>
                <Input value={formName} onChange={(e) => setFormName(e.target.value)} placeholder="如: 真空袋" />
              </div>
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label>规格</Label>
                <Input value={formSpec} onChange={(e) => setFormSpec(e.target.value)} placeholder="如: 食品级透明" />
              </div>
              <div className="space-y-2">
                <Label>单位</Label>
                <Select value={formUnit} onValueChange={(v) => setFormUnit(v ?? "个")}>
                  <SelectTrigger><SelectValue /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="个">个</SelectItem>
                    <SelectItem value="张">张</SelectItem>
                    <SelectItem value="套">套</SelectItem>
                    <SelectItem value="卷">卷</SelectItem>
                    <SelectItem value="kg">kg</SelectItem>
                    <SelectItem value="箱">箱</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label>供应商</Label>
                <Select value={formSupplierId} onValueChange={(v) => setFormSupplierId(v ?? "")}>
                  <SelectTrigger><SelectValue placeholder="选择供应商" /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="">无</SelectItem>
                    {suppliers.map((s) => (
                      <SelectItem key={s.id} value={String(s.id)}>{s.name}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-2">
                <Label>供货周期(天)</Label>
                <Input type="number" value={formLeadTime} onChange={(e) => setFormLeadTime(e.target.value)} placeholder="如: 3" />
              </div>
            </div>
            <div className="space-y-2">
              <Label>最近采购价(元)</Label>
              <Input type="number" step="0.01" value={formLastPrice} onChange={(e) => setFormLastPrice(e.target.value)} placeholder="如: 0.50" />
            </div>
            <div className="space-y-2">
              <Label>状态</Label>
              <Select value={formIsActive ? "active" : "inactive"} onValueChange={(v) => setFormIsActive(v === "active")}>
                <SelectTrigger><SelectValue /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="active">启用</SelectItem>
                  <SelectItem value="inactive">停用</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setDialogOpen(false)}>取消</Button>
            <Button onClick={handleSubmit} disabled={createMutation.isPending || updateMutation.isPending}>
              {editingId ? "保存修改" : "创建物料"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* ===== 采购入库弹窗 ===== */}
      <Dialog open={inDialogOpen} onOpenChange={setInDialogOpen}>
        <DialogContent className="max-w-sm">
          <DialogHeader>
            <DialogTitle>采购入库 — {inMaterial?.name}</DialogTitle>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <Label>入库日期</Label>
              <Input type="date" value={inDate} onChange={(e) => setInDate(e.target.value)} />
            </div>
            <div className="space-y-2">
              <Label>入库数量 *</Label>
              <div className="flex items-center gap-2">
                <Input type="number" value={inQty} onChange={(e) => setInQty(e.target.value)} placeholder={`当前库存: ${inMaterial?.stock_quantity ?? 0}`} />
                <span className="text-sm text-muted-foreground shrink-0">{inMaterial?.unit}</span>
              </div>
            </div>
            <div className="space-y-2">
              <Label>采购单价(元)</Label>
              <Input type="number" step="0.01" value={inPrice} onChange={(e) => setInPrice(e.target.value)} placeholder={`上次: ${inMaterial?.last_purchase_price ?? "-"}`} />
            </div>
            <div className="bg-muted p-3 rounded-md text-sm space-y-1">
              <div className="flex justify-between">
                <span className="text-muted-foreground">供应商</span>
                <span>{inMaterial?.supplier_name ?? "-"}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">当前库存</span>
                <span>{inMaterial?.stock_quantity ?? 0} {inMaterial?.unit}</span>
              </div>
              <div className="flex justify-between font-medium">
                <span>入库后库存</span>
                <span>{(inMaterial?.stock_quantity ?? 0) + (Number(inQty) || 0)} {inMaterial?.unit}</span>
              </div>
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setInDialogOpen(false)}>取消</Button>
            <Button onClick={handleInboundSubmit} disabled={inboundMutation.isPending}>确认入库</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* ===== 删除确认 ===== */}
      <Dialog open={!!deleteId} onOpenChange={() => setDeleteId(null)}>
        <DialogContent className="max-w-sm">
          <DialogHeader><DialogTitle>确认删除</DialogTitle></DialogHeader>
          <p className="text-sm text-muted-foreground">确定要删除这条物料吗？此操作不可撤销。</p>
          <DialogFooter>
            <Button variant="outline" onClick={() => setDeleteId(null)}>取消</Button>
            <Button variant="destructive" onClick={() => deleteId && deleteMutation.mutate(deleteId)} disabled={deleteMutation.isPending}>删除</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
