import { useState, Fragment } from "react";
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
import { toast } from "sonner";
import { Plus, Search, Pencil, Trash2, ChevronDown, ChevronUp, Package, Layers, Tag } from "lucide-react";

// ==================== 类型 ====================
interface TemplatePart {
  id?: number;
  part_name: string;
  weight_g: number;
  boxes: number;
  sort_order: number;
}

interface TemplateBOM {
  id?: number;
  material_id: number;
  material_name?: string | null;
  quantity: number;
  unit: string;
  notes?: string | null;
}

interface TemplatePackaging {
  id?: number;
  level: string;
  material_id: number;
  material_name?: string | null;
  quantity: number;
  unit: string;
  notes?: string | null;
}

interface ProductTemplate {
  id: number;
  code: string;
  name: string;
  spec: string | null;
  unit: string;
  unit_weight_kg: number | null;
  portion_weight_g: number | null;
  portion_boxes: number | null;
  series_code: string | null;
  series_name: string | null;
  is_active: boolean;
  notes: string | null;
  parts: TemplatePart[];
  boms: TemplateBOM[];
  packagings: TemplatePackaging[];
  variant_count: number;
}

interface ProductVariant {
  id: number;
  template_id: number;
  template_name: string;
  brand_id: number | null;
  brand_name: string | null;
  brand_is_oem: boolean;
  code: string;
  name: string;
  cost_price: number | null;
  suggested_retail_price: number | null;
  wholesale_price: number | null;
  min_price: number | null;
  stock_quantity: number;
  safety_stock: number;
  is_active: boolean;
}

interface MaterialOption {
  id: number;
  name: string;
  code: string;
  unit: string;
}

interface BrandOption {
  id: number;
  name: string;
  code: string | null;
  is_oem: boolean;
}

const BOM_UNITS = ["g", "只", "条", "个", "盒", "份"];

export function FinishedProductsPage() {
  const qc = useQueryClient();
  const [search, setSearch] = useState("");
  const [expandedId, setExpandedId] = useState<number | null>(null);

  // 模板弹窗
  const [templateDialogOpen, setTemplateDialogOpen] = useState(false);
  const [editingTemplate, setEditingTemplate] = useState<ProductTemplate | null>(null);

  // 变体弹窗
  const [variantDialogOpen, setVariantDialogOpen] = useState(false);
  const [variantTemplateId, setVariantTemplateId] = useState<number | null>(null);
  const [editingVariant, setEditingVariant] = useState<ProductVariant | null>(null);

  // 删除确认弹窗
  const [deleteTemplateId, setDeleteTemplateId] = useState<number | null>(null);
  const [deleteVariantInfo, setDeleteVariantInfo] = useState<{templateId: number, variantId: number} | null>(null);

  // 模板表单
  const [formName, setFormName] = useState("");
  const [formSpec, setFormSpec] = useState("");
  const [formUnitWeight, setFormUnitWeight] = useState("");
  const [formPortionWeight, setFormPortionWeight] = useState("");
  const [formPortionBoxes, setFormPortionBoxes] = useState("");
  const [formSeriesCode, setFormSeriesCode] = useState("");
  const [formSeriesName, setFormSeriesName] = useState("");
  const [formParts, setFormParts] = useState<TemplatePart[]>([]);
  const [formBOMs, setFormBOMs] = useState<TemplateBOM[]>([]);
  const [formPackagings, setFormPackagings] = useState<TemplatePackaging[]>([]);

  // 变体表单
  const [formBrandId, setFormBrandId] = useState("");
  const [formCostPrice, setFormCostPrice] = useState("");
  const [formRetailPrice, setFormRetailPrice] = useState("");
  const [formWholesalePrice, setFormWholesalePrice] = useState("");
  const [formMinPrice, setFormMinPrice] = useState("");
  const [formStock, setFormStock] = useState("0");
  const [formSafetyStock, setFormSafetyStock] = useState("0");
  const [formVariantPackagings, setFormVariantPackagings] = useState<{level: string; material_id: number; material_name?: string; quantity: number; unit: string; is_override: boolean}[]>([]);
  const [formVariantAccessories, setFormVariantAccessories] = useState<{accessory_id: number; accessory_name?: string; quantity: number; unit: string}[]>([]);

  // 数据查询
  const { data: templatesData, isLoading } = useQuery({
    queryKey: ["finished-product-templates"],
    queryFn: async () => {
      const res = await api.get("/v1/finished-products/templates?limit=500");
      return res.data.items as ProductTemplate[];
    },
  });

  const { data: variantsData } = useQuery({
    queryKey: ["finished-product-variants", expandedId],
    queryFn: async () => {
      if (!expandedId) return [];
      const res = await api.get(`/v1/finished-products/templates/${expandedId}/variants?limit=500`);
      return res.data.items as ProductVariant[];
    },
    enabled: !!expandedId,
  });

  const { data: materialsData } = useQuery({
    queryKey: ["materials-for-finished"],
    queryFn: async () => {
      const res = await api.get("/v1/materials/?limit=500");
      return res.data.items as MaterialOption[];
    },
  });

  const { data: brandsData } = useQuery({
    queryKey: ["brands-for-finished"],
    queryFn: async () => {
      const res = await api.get("/v1/brands/?limit=500");
      return res.data.items as BrandOption[];
    },
  });

  const templates = templatesData || [];
  const variants = variantsData || [];
  const materials = materialsData || [];
  const brands = brandsData || [];

  const filtered = search.trim()
    ? templates.filter(
        (t) =>
          t.name.toLowerCase().includes(search.toLowerCase()) ||
          t.code.toLowerCase().includes(search.toLowerCase())
      )
    : templates;

  // Mutations
  const createTemplateMutation = useMutation({
    mutationFn: async (payload: any) => {
      const res = await api.post("/v1/finished-products/templates", payload);
      return res.data;
    },
  });

  const updateTemplateMutation = useMutation({
    mutationFn: async ({ id, payload }: { id: number; payload: any }) => {
      await api.put(`/v1/finished-products/templates/${id}`, payload);
    },
  });

  const deleteTemplateMutation = useMutation({
    mutationFn: (id: number) => api.delete(`/v1/finished-products/templates/${id}`),
  });

  const createVariantMutation = useMutation({
    mutationFn: async ({ templateId, payload }: { templateId: number; payload: any }) => {
      const res = await api.post(`/v1/finished-products/templates/${templateId}/variants`, payload);
      return res.data;
    },
  });

  const deleteVariantMutation = useMutation({
    mutationFn: ({ templateId, variantId }: { templateId: number; variantId: number }) =>
      api.delete(`/v1/finished-products/templates/${templateId}/variants/${variantId}`),
  });

  function resetTemplateForm() {
    setFormName("");
    setFormSpec("");
    setFormUnitWeight("");
    setFormPortionWeight("");
    setFormPortionBoxes("");
    setFormSeriesCode("");
    setFormSeriesName("");
    setFormParts([]);
    setFormBOMs([]);
    setFormPackagings([]);
    setEditingTemplate(null);
  }

  function resetVariantForm() {
    setFormBrandId("");
    setFormCostPrice("");
    setFormRetailPrice("");
    setFormWholesalePrice("");
    setFormMinPrice("");
    setFormStock("0");
    setFormSafetyStock("0");
    setFormVariantPackagings([]);
    setFormVariantAccessories([]);
    setEditingVariant(null);
  }

  function openCreateTemplate() {
    resetTemplateForm();
    setTemplateDialogOpen(true);
  }

  async function openEditTemplate(t: ProductTemplate) {
    try {
      // 获取完整模板详情（列表中 packagings/boms 为空）
      const res = await api.get(`/v1/finished-products/templates/${t.id}`);
      const full = res.data as ProductTemplate;
      
      setEditingTemplate(full);
      setFormName(full.name);
      setFormSpec(full.spec ?? "");
      setFormUnitWeight(full.unit_weight_kg?.toString() ?? "");
      setFormPortionWeight(full.portion_weight_g?.toString() ?? "");
      setFormPortionBoxes(full.portion_boxes?.toString() ?? "");
      setFormSeriesCode(full.series_code ?? "");
      setFormSeriesName(full.series_name ?? "");
      setFormParts(full.parts.map((p) => ({ ...p, boxes: p.boxes ?? 1 })));
      setFormBOMs(full.boms.map((b) => ({ ...b, material_name: b.material_name })));
      setFormPackagings(full.packagings.map((p) => ({ ...p, material_name: p.material_name })));
      setTemplateDialogOpen(true);
    } catch (err: any) {
      toast.error("加载模板详情失败");
    }
  }

  function openCreateVariant(templateId: number) {
    const template = templates.find(t => t.id === templateId);
    resetVariantForm();
    setVariantTemplateId(templateId);
    if (template?.packagings) {
      setFormVariantPackagings(template.packagings.map(p => ({
        level: p.level,
        material_id: p.material_id,
        material_name: p.material_name,
        quantity: p.quantity,
        unit: p.unit,
        is_override: false,
      })));
    }
    if (template?.boms) {
      setFormVariantAccessories(template.boms.map(b => ({
        accessory_id: b.material_id,
        accessory_name: b.material_name,
        quantity: b.quantity,
        unit: b.unit,
      })));
    }
    setVariantDialogOpen(true);
  }

  async function handleSubmitTemplate() {
    if (!formName.trim()) {
      toast.error("模板名称不能为空");
      return;
    }
    if (formParts.length === 0) {
      toast.error("请至少添加一个部位");
      return;
    }
    const payload = {
      name: formName.trim(),
      spec: formSpec.trim() || null,
      unit_weight_kg: formUnitWeight ? Number(formUnitWeight) : null,
      portion_weight_g: formPortionWeight ? Number(formPortionWeight) : null,
      portion_boxes: formPortionBoxes ? Number(formPortionBoxes) : null,
      series_code: formSeriesCode.trim() || null,
      series_name: formSeriesName.trim() || null,
      parts: formParts.map((p) => ({ part_name: p.part_name, weight_g: p.weight_g, boxes: p.boxes ?? 1, sort_order: p.sort_order })),
      boms: formBOMs.map((b) => ({ material_id: b.material_id, quantity: b.quantity, unit: b.unit, notes: b.notes })),
      packagings: formPackagings.map((p) => ({ level: p.level, material_id: p.material_id, quantity: p.quantity, unit: p.unit, notes: p.notes })),
    };
    try {
      if (editingTemplate) {
        await updateTemplateMutation.mutateAsync({ id: editingTemplate.id, payload });
        toast.success("模板更新成功");
      } else {
        await createTemplateMutation.mutateAsync(payload);
        toast.success("模板创建成功");
      }
      await qc.invalidateQueries({ queryKey: ["finished-product-templates"] });
      setTemplateDialogOpen(false);
      resetTemplateForm();
    } catch (err: any) {
      toast.error(err.response?.data?.detail || "操作失败");
    }
  }

  async function handleSubmitVariant() {
    if (!formBrandId) {
      toast.error("请选择品牌");
      return;
    }
    if (!variantTemplateId) return;
    const payload = {
      brand_id: Number(formBrandId),
      cost_price: formCostPrice ? Number(formCostPrice) : null,
      suggested_retail_price: formRetailPrice ? Number(formRetailPrice) : null,
      wholesale_price: formWholesalePrice ? Number(formWholesalePrice) : null,
      min_price: formMinPrice ? Number(formMinPrice) : null,
      stock_quantity: Number(formStock) || 0,
      safety_stock: Number(formSafetyStock) || 0,
      packagings: formVariantPackagings.map(p => ({
        level: p.level,
        material_id: p.material_id,
        quantity: p.quantity,
        unit: p.unit,
        is_override: p.is_override,
      })),
      accessories: formVariantAccessories.map(a => ({
        accessory_id: a.accessory_id,
        quantity: a.quantity,
        unit: a.unit,
      })),
    };
    try {
      await createVariantMutation.mutateAsync({ templateId: variantTemplateId, payload });
      await qc.invalidateQueries({ queryKey: ["finished-product-variants", variantTemplateId] });
      await qc.invalidateQueries({ queryKey: ["finished-product-templates"] });
      setVariantDialogOpen(false);
      resetVariantForm();
      toast.success("品牌变体创建成功");
    } catch (err: any) {
      toast.error(err.response?.data?.detail || "操作失败");
    }
  }

  async function handleDeleteTemplate() {
    if (!deleteTemplateId) return;
    try {
      await deleteTemplateMutation.mutateAsync(deleteTemplateId);
      await qc.invalidateQueries({ queryKey: ["finished-product-templates"] });
      setDeleteTemplateId(null);
      toast.success("模板已删除");
    } catch (err: any) {
      toast.error(err.response?.data?.detail || "删除失败");
    }
  }

  async function handleDeleteVariant() {
    if (!deleteVariantInfo) return;
    try {
      await deleteVariantMutation.mutateAsync(deleteVariantInfo);
      await qc.invalidateQueries({ queryKey: ["finished-product-variants", deleteVariantInfo.templateId] });
      await qc.invalidateQueries({ queryKey: ["finished-product-templates"] });
      setDeleteVariantInfo(null);
      toast.success("变体已删除");
    } catch (err: any) {
      toast.error(err.response?.data?.detail || "删除失败");
    }
  }

  function handleAddPart() {
    setFormParts([...formParts, { part_name: "", weight_g: 0, boxes: 1, sort_order: formParts.length }]);
  }

  function handleAddBOM() {
    setFormBOMs([...formBOMs, { material_id: 0, quantity: 1, unit: "个" }]);
  }

  function handleAddPackaging(level: string) {
    setFormPackagings([...formPackagings, { level, material_id: 0, quantity: 1, unit: "个" }]);
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">成品定义</h1>
          <p className="text-sm text-muted-foreground">模板（SPU）+ 品牌变体（SKU）管理</p>
        </div>
        <Button onClick={openCreateTemplate}>
          <Plus className="h-4 w-4 mr-1" />
          新建模板
        </Button>
      </div>

      <div className="flex items-center gap-3">
        <div className="relative flex-1 max-w-sm">
          <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
          <Input
            placeholder="搜索模板名称或编码..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="pl-9"
          />
        </div>
        <span className="text-sm text-muted-foreground">共 {filtered.length} 个模板</span>
      </div>

      <div className="border rounded-lg">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead className="w-[40px]"></TableHead>
              <TableHead>编码</TableHead>
              <TableHead>模板名称（SPU）</TableHead>
              <TableHead>规格</TableHead>
              <TableHead>部位</TableHead>
              <TableHead>变体数</TableHead>
              <TableHead className="w-[180px]">操作</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {isLoading ? (
              <TableRow>
                <TableCell colSpan={7} className="text-center py-8">加载中...</TableCell>
              </TableRow>
            ) : filtered.length === 0 ? (
              <TableRow>
                <TableCell colSpan={7} className="text-center py-8 text-muted-foreground">
                  暂无模板，点击右上角"新建模板"创建
                </TableCell>
              </TableRow>
            ) : (
              filtered.map((t) => (
                <Fragment key={t.id}>
                  <TableRow className={!t.is_active ? "opacity-50" : ""}>
                    <TableCell>
                      <Button variant="ghost" size="icon" className="h-6 w-6" onClick={() => setExpandedId(expandedId === t.id ? null : t.id)}>
                        {expandedId === t.id ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
                      </Button>
                    </TableCell>
                    <TableCell className="font-mono text-xs text-muted-foreground">{t.code}</TableCell>
                    <TableCell className="font-medium">{t.name}</TableCell>
                    <TableCell className="text-sm text-muted-foreground">{t.spec ?? "-"}</TableCell>
                    <TableCell className="text-sm">
                      {t.parts.map((p) => `${p.part_name}${p.weight_g}g`).join("+") || "-"}
                    </TableCell>
                    <TableCell>
                      {t.variant_count > 0 ? (
                        <Badge variant="secondary">{t.variant_count} 个品牌</Badge>
                      ) : (
                        <span className="text-xs text-muted-foreground">无变体</span>
                      )}
                    </TableCell>
                    <TableCell>
                      <div className="flex gap-1">
                        <Button variant="ghost" size="sm" className="h-7 text-xs" onClick={() => openCreateVariant(t.id)}>
                          <Plus className="h-3 w-3 mr-1" />添加品牌
                        </Button>
                        <Button variant="ghost" size="icon" className="h-7 w-7" onClick={() => openEditTemplate(t)}>
                          <Pencil className="h-3 w-3" />
                        </Button>
                        <Button variant="ghost" size="icon" className="h-7 w-7 text-red-500" onClick={() => setDeleteTemplateId(t.id)}>
                          <Trash2 className="h-3 w-3" />
                        </Button>
                      </div>
                    </TableCell>
                  </TableRow>
                  {/* 展开显示品牌变体 */}
                  {expandedId === t.id && (
                    <TableRow key={`expand-${t.id}`}>
                      <TableCell colSpan={7} className="bg-slate-50 py-3">
                        <div className="space-y-3">
                          <div className="text-xs font-medium text-muted-foreground flex items-center gap-1">
                            <Tag className="h-3 w-3" />品牌变体（SKU）
                          </div>
                          {variants.length === 0 ? (
                            <div className="text-sm text-muted-foreground text-center py-4">
                              暂无品牌变体，点击"添加品牌"创建
                            </div>
                          ) : (
                            <div className="grid grid-cols-3 gap-3">
                              {variants.map((v) => (
                                <div key={v.id} className="bg-white border rounded p-3 space-y-2">
                                  <div className="flex items-center justify-between">
                                    <div className="flex items-center gap-2">
                                      <span className="font-medium">{v.brand_name ?? "无品牌"}</span>
                                      {v.brand_is_oem && (
                                        <Badge variant="secondary" className="text-[10px] bg-purple-100 text-purple-700">OEM</Badge>
                                      )}
                                    </div>
                                    <Button variant="ghost" size="icon" className="h-5 w-5 text-red-500" onClick={() => setDeleteVariantInfo({ templateId: t.id, variantId: v.id })}>
                                      <Trash2 className="h-3 w-3" />
                                    </Button>
                                  </div>
                                  <div className="text-xs text-muted-foreground">{v.code}</div>
                                  <div className="grid grid-cols-2 gap-2 text-xs">
                                    <div>库存: <span className="font-medium">{v.stock_quantity}</span></div>
                                    <div>安全: {v.safety_stock}</div>
                                    {v.cost_price && <div>成本: ¥{v.cost_price.toFixed(2)}</div>}
                                    {v.suggested_retail_price && <div>零售: ¥{v.suggested_retail_price.toFixed(2)}</div>}
                                  </div>
                                </div>
                              ))}
                            </div>
                          )}
                        </div>
                      </TableCell>
                    </TableRow>
                  )}
                </Fragment>
              ))
            )}
          </TableBody>
        </Table>
      </div>

      {/* ===== 模板弹窗 ===== */}
      <Dialog open={templateDialogOpen} onOpenChange={setTemplateDialogOpen}>
        <DialogContent className="max-w-3xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>{editingTemplate ? "编辑模板" : "新建模板（SPU）"}</DialogTitle>
          </DialogHeader>
          <div className="space-y-4 py-4">
            {/* 基本信息 */}
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label>模板名称 <span className="text-red-500">*</span></Label>
                <Input value={formName} onChange={(e) => setFormName(e.target.value)} placeholder="如：鱼腩200g+中段200g" />
              </div>
              <div className="space-y-2">
                <Label>规格</Label>
                <Input value={formSpec} onChange={(e) => setFormSpec(e.target.value)} placeholder="如：挪威进口、刺身级" />
              </div>
            </div>

            {/* 部位 */}
            <div className="border rounded-lg p-3 space-y-2">
              <div className="flex items-center justify-between">
                <Label className="text-sm font-medium flex items-center gap-1"><Layers className="h-4 w-4" />部位配置</Label>
                <Button variant="outline" size="sm" onClick={handleAddPart}><Plus className="h-3 w-3 mr-1" />添加部位</Button>
              </div>
              {formParts.length === 0 && <p className="text-xs text-muted-foreground">至少添加一个部位</p>}
              {formParts.map((p, i) => (
                <div key={i} className="grid grid-cols-4 gap-2">
                  <Select value={p.part_name} onValueChange={(v) => {
                    const updated = [...formParts]; updated[i] = { ...p, part_name: v }; setFormParts(updated);
                  }}>
                    <SelectTrigger className="text-xs"><SelectValue placeholder="选择部位" /></SelectTrigger>
                    <SelectContent>
                      <SelectItem value="鱼腩" className="text-xs">鱼腩</SelectItem>
                      <SelectItem value="中段" className="text-xs">中段</SelectItem>
                      <SelectItem value="鱼尾" className="text-xs">鱼尾</SelectItem>
                      <SelectItem value="鱼头" className="text-xs">鱼头</SelectItem>
                      <SelectItem value="鱼皮" className="text-xs">鱼皮</SelectItem>
                    </SelectContent>
                  </Select>
                  <Input type="number" placeholder="重量(g)" value={p.weight_g || ""} onChange={(e) => {
                    const updated = [...formParts]; updated[i] = { ...p, weight_g: Number(e.target.value) }; setFormParts(updated);
                  }} />
                  <Input type="number" placeholder="盒数" value={p.boxes || ""} onChange={(e) => {
                    const updated = [...formParts]; updated[i] = { ...p, boxes: Number(e.target.value) || 1 }; setFormParts(updated);
                  }} />
                  <Button variant="ghost" size="icon" className="text-red-500" onClick={() => setFormParts(formParts.filter((_, idx) => idx !== i))}><Trash2 className="h-4 w-4" /></Button>
                </div>
              ))}
              {/* 自动计算 */}
              {formParts.length > 0 && (
                <div className="grid grid-cols-2 gap-4 pt-2 border-t">
                  <div className="space-y-1">
                    <Label className="text-xs text-muted-foreground">单份重量(g)</Label>
                    <div className="h-8 flex items-center px-3 rounded bg-muted text-sm font-medium">
                      {(() => {
                        const totalWeight = formParts.reduce((sum, p) => sum + (p.weight_g || 0), 0);
                        const totalBoxes = formParts.reduce((sum, p) => sum + (p.boxes || 1), 0);
                        return `${totalWeight}g（${totalBoxes}盒）`;
                      })()}
                    </div>
                  </div>
                  <div className="space-y-1">
                    <Label className="text-xs text-muted-foreground">份内盒数</Label>
                    <div className="h-8 flex items-center px-3 rounded bg-muted text-sm font-medium">
                      {(() => {
                        const total = formParts.reduce((sum, p) => sum + (p.boxes || 1), 0);
                        return `${total} 盒`;
                      })()}
                    </div>
                  </div>
                </div>
              )}
            </div>

            {/* 通用BOM */}
            <div className="border rounded-lg p-3 space-y-2">
              <div className="flex items-center justify-between">
                <Label className="text-sm font-medium flex items-center gap-1"><Package className="h-4 w-4" />通用物料（所有品牌共用）</Label>
                <Button variant="outline" size="sm" onClick={handleAddBOM}><Plus className="h-3 w-3 mr-1" />添加物料</Button>
              </div>
              {formBOMs.map((b, i) => (
                <div key={i} className="grid grid-cols-4 gap-2">
                  <Select value={String(b.material_id)} onValueChange={(v) => {
                    const mat = materials.find((m) => m.id === Number(v));
                    const updated = [...formBOMs]; updated[i] = { ...b, material_id: Number(v), material_name: mat?.name, unit: mat?.unit ?? "个" }; setFormBOMs(updated);
                  }}>
                    <SelectTrigger className="text-xs">
                      <SelectValue placeholder="选择物料">
                        {(() => {
                          const mat = materials.find((m) => m.id === b.material_id);
                          return mat ? mat.name : (b.material_id ? `物料${b.material_id}` : "选择物料");
                        })()}
                      </SelectValue>
                    </SelectTrigger>
                    <SelectContent>
                      {materials.map((m) => <SelectItem key={m.id} value={String(m.id)} className="text-xs">{m.name}</SelectItem>)}
                    </SelectContent>
                  </Select>
                  <Input type="number" placeholder="用量" value={b.quantity} onChange={(e) => {
                    const updated = [...formBOMs]; updated[i] = { ...b, quantity: Number(e.target.value) }; setFormBOMs(updated);
                  }} />
                  <Select value={b.unit || "个"} onValueChange={(v) => {
                    const updated = [...formBOMs]; updated[i] = { ...b, unit: v }; setFormBOMs(updated);
                  }}>
                    <SelectTrigger className="text-xs"><SelectValue /></SelectTrigger>
                    <SelectContent>
                      {BOM_UNITS.map((u) => <SelectItem key={u} value={u} className="text-xs">{u}</SelectItem>)}
                    </SelectContent>
                  </Select>
                  <Button variant="ghost" size="icon" className="text-red-500" onClick={() => setFormBOMs(formBOMs.filter((_, idx) => idx !== i))}><Trash2 className="h-4 w-4" /></Button>
                </div>
              ))}
            </div>

            {/* 盒装包装物 */}
            <div className="border rounded-lg p-3 space-y-2">
              <div className="flex items-center justify-between">
                <Label className="text-sm font-medium flex items-center gap-1"><Package className="h-4 w-4" />盒装包装物（每盒）</Label>
                <Button variant="outline" size="sm" onClick={() => handleAddPackaging("box")}><Plus className="h-3 w-3 mr-1" />添加</Button>
              </div>
              {formPackagings.filter(p => p.level === "box").length === 0 && <p className="text-xs text-muted-foreground">暂无盒装包装物</p>}
              {formPackagings.filter(p => p.level === "box").map((p, i) => {
                const globalIdx = formPackagings.findIndex(fp => fp === p);
                return (
                  <div key={globalIdx} className="grid grid-cols-3 gap-2">
                    <Select value={String(p.material_id)} onValueChange={(v) => {
                      const mat = materials.find((m) => m.id === Number(v));
                      const updated = [...formPackagings]; updated[globalIdx] = { ...p, material_id: Number(v), material_name: mat?.name, unit: mat?.unit ?? "个" }; setFormPackagings(updated);
                    }}>
                      <SelectTrigger className="text-xs">
                        <SelectValue placeholder="选择物料">
                          {(() => {
                            const mat = materials.find((m) => m.id === p.material_id);
                            return mat ? mat.name : (p.material_id ? `物料${p.material_id}` : "选择物料");
                          })()}
                        </SelectValue>
                      </SelectTrigger>
                      <SelectContent>{materials.map((m) => <SelectItem key={m.id} value={String(m.id)} className="text-xs">{m.name}</SelectItem>)}</SelectContent>
                    </Select>
                    <Input type="number" placeholder="用量" value={p.quantity} onChange={(e) => {
                      const updated = [...formPackagings]; updated[globalIdx] = { ...p, quantity: Number(e.target.value) }; setFormPackagings(updated);
                    }} />
                    <Button variant="ghost" size="icon" className="text-red-500" onClick={() => setFormPackagings(formPackagings.filter((_, idx) => idx !== globalIdx))}><Trash2 className="h-4 w-4" /></Button>
                  </div>
                );
              })}
            </div>

            {/* 分装包装物 */}
            <div className="border rounded-lg p-3 space-y-2">
              <div className="flex items-center justify-between">
                <Label className="text-sm font-medium flex items-center gap-1"><Package className="h-4 w-4" />分装包装物（每份 = 份内盒数 × 盒级 + 外箱）</Label>
                <Button variant="outline" size="sm" onClick={() => handleAddPackaging("portion")}><Plus className="h-3 w-3 mr-1" />添加</Button>
              </div>
              {formPackagings.filter(p => p.level === "portion").length === 0 && <p className="text-xs text-muted-foreground">暂无分装包装物</p>}
              {formPackagings.filter(p => p.level === "portion").map((p, i) => {
                const globalIdx = formPackagings.findIndex(fp => fp === p);
                return (
                  <div key={globalIdx} className="grid grid-cols-3 gap-2">
                    <Select value={String(p.material_id)} onValueChange={(v) => {
                      const mat = materials.find((m) => m.id === Number(v));
                      const updated = [...formPackagings]; updated[globalIdx] = { ...p, material_id: Number(v), material_name: mat?.name, unit: mat?.unit ?? "个" }; setFormPackagings(updated);
                    }}>
                      <SelectTrigger className="text-xs">
                        <SelectValue placeholder="选择物料">
                          {(() => {
                            const mat = materials.find((m) => m.id === p.material_id);
                            return mat ? mat.name : (p.material_id ? `物料${p.material_id}` : "选择物料");
                          })()}
                        </SelectValue>
                      </SelectTrigger>
                      <SelectContent>{materials.map((m) => <SelectItem key={m.id} value={String(m.id)} className="text-xs">{m.name}</SelectItem>)}</SelectContent>
                    </Select>
                    <Input type="number" placeholder="用量" value={p.quantity} onChange={(e) => {
                      const updated = [...formPackagings]; updated[globalIdx] = { ...p, quantity: Number(e.target.value) }; setFormPackagings(updated);
                    }} />
                    <Button variant="ghost" size="icon" className="text-red-500" onClick={() => setFormPackagings(formPackagings.filter((_, idx) => idx !== globalIdx))}><Trash2 className="h-4 w-4" /></Button>
                  </div>
                );
              })}
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setTemplateDialogOpen(false)}>取消</Button>
            <Button onClick={handleSubmitTemplate}>{editingTemplate ? "保存修改" : "创建模板"}</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* ===== 变体弹窗 ===== */}
      <Dialog open={variantDialogOpen} onOpenChange={setVariantDialogOpen}>
        <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>添加品牌变体（SKU）</DialogTitle>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <Label>品牌 <span className="text-red-500">*</span></Label>
              <Select value={formBrandId} onValueChange={setFormBrandId}>
                <SelectTrigger>
                  <SelectValue placeholder="选择品牌">
                    {(() => {
                      const b = brands.find((x) => String(x.id) === formBrandId);
                      return b ? `${b.name} ${b.is_oem ? "(OEM)" : ""}` : "选择品牌";
                    })()}
                  </SelectValue>
                </SelectTrigger>
                <SelectContent>
                  {brands.map((b) => (
                    <SelectItem key={b.id} value={String(b.id)}>
                      <div className="flex items-center gap-2">
                        {b.name}
                        {b.is_oem && <Badge variant="secondary" className="text-[10px] bg-purple-100 text-purple-700">OEM</Badge>}
                      </div>
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label>成本价</Label>
                <Input type="number" step="0.01" value={formCostPrice} onChange={(e) => setFormCostPrice(e.target.value)} placeholder="自动计算或手动输入" />
              </div>
              <div className="space-y-2">
                <Label>建议零售价</Label>
                <Input type="number" step="0.01" value={formRetailPrice} onChange={(e) => setFormRetailPrice(e.target.value)} />
              </div>
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label>批发价</Label>
                <Input type="number" step="0.01" value={formWholesalePrice} onChange={(e) => setFormWholesalePrice(e.target.value)} />
              </div>
              <div className="space-y-2">
                <Label>最低价</Label>
                <Input type="number" step="0.01" value={formMinPrice} onChange={(e) => setFormMinPrice(e.target.value)} />
              </div>
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label>初始库存</Label>
                <Input type="number" value={formStock} onChange={(e) => setFormStock(e.target.value)} />
              </div>
              <div className="space-y-2">
                <Label>安全库存</Label>
                <Input type="number" value={formSafetyStock} onChange={(e) => setFormSafetyStock(e.target.value)} />
              </div>
            </div>

            {/* 品牌专属包装物 */}
            <div className="border rounded-lg p-3 space-y-2 bg-blue-50/30">
              <div className="flex items-center justify-between">
                <Label className="text-sm font-medium flex items-center gap-1"><Package className="h-4 w-4" />品牌专属包装物</Label>
                <span className="text-xs text-muted-foreground">可覆盖或追加通用包装</span>
              </div>
              {formVariantPackagings.length === 0 && <p className="text-xs text-muted-foreground">继承模板通用包装</p>}
              {formVariantPackagings.map((p, i) => (
                <div key={i} className="grid grid-cols-5 gap-2 items-center bg-white rounded p-2">
                  <div className="text-xs text-muted-foreground">{p.level === "box" ? "盒装" : "分装"}</div>
                  <Select value={String(p.material_id)} onValueChange={(v) => {
                    const mat = materials.find((m) => m.id === Number(v));
                    const updated = [...formVariantPackagings]; updated[i] = { ...p, material_id: Number(v), material_name: mat?.name }; setFormVariantPackagings(updated);
                  }}>
                    <SelectTrigger className="text-xs h-8">
                      <SelectValue>{p.material_name || "选择物料"}</SelectValue>
                    </SelectTrigger>
                    <SelectContent>{materials.map((m) => <SelectItem key={m.id} value={String(m.id)} className="text-xs">{m.name}</SelectItem>)}</SelectContent>
                  </Select>
                  <Input type="number" className="h-8 text-xs" value={p.quantity} onChange={(e) => {
                    const updated = [...formVariantPackagings]; updated[i] = { ...p, quantity: Number(e.target.value) }; setFormVariantPackagings(updated);
                  }} />
                  <div className="flex items-center gap-1 text-xs">
                    <input type="checkbox" checked={p.is_override} onChange={(e) => {
                      const updated = [...formVariantPackagings]; updated[i] = { ...p, is_override: e.target.checked }; setFormVariantPackagings(updated);
                    }} className="h-3 w-3" />
                    <span>覆盖</span>
                  </div>
                  <Button variant="ghost" size="icon" className="h-7 w-7 text-red-500" onClick={() => setFormVariantPackagings(formVariantPackagings.filter((_, idx) => idx !== i))}>
                    <Trash2 className="h-3 w-3" />
                  </Button>
                </div>
              ))}
              <Button variant="outline" size="sm" className="w-full text-xs" onClick={() => setFormVariantPackagings([...formVariantPackagings, { level: "box", material_id: 0, quantity: 1, unit: "个", is_override: true }])}>
                <Plus className="h-3 w-3 mr-1" />添加品牌专属包装
              </Button>
            </div>

            {/* 品牌专属配套 */}
            <div className="border rounded-lg p-3 space-y-2 bg-green-50/30">
              <div className="flex items-center justify-between">
                <Label className="text-sm font-medium flex items-center gap-1"><Tag className="h-4 w-4" />品牌专属配套</Label>
                <span className="text-xs text-muted-foreground">如赠品、附加产品</span>
              </div>
              {formVariantAccessories.length === 0 && <p className="text-xs text-muted-foreground">暂无配套产品</p>}
              {formVariantAccessories.map((a, i) => (
                <div key={i} className="grid grid-cols-4 gap-2 items-center bg-white rounded p-2">
                  <Select value={String(a.accessory_id)} onValueChange={(v) => {
                    const mat = materials.find((m) => m.id === Number(v));
                    const updated = [...formVariantAccessories]; updated[i] = { ...a, accessory_id: Number(v), accessory_name: mat?.name }; setFormVariantAccessories(updated);
                  }}>
                    <SelectTrigger className="text-xs h-8">
                      <SelectValue>{a.accessory_name || "选择配套"}</SelectValue>
                    </SelectTrigger>
                    <SelectContent>{materials.map((m) => <SelectItem key={m.id} value={String(m.id)} className="text-xs">{m.name}</SelectItem>)}</SelectContent>
                  </Select>
                  <Input type="number" className="h-8 text-xs" value={a.quantity} onChange={(e) => {
                    const updated = [...formVariantAccessories]; updated[i] = { ...a, quantity: Number(e.target.value) }; setFormVariantAccessories(updated);
                  }} />
                  <div className="text-xs text-muted-foreground">{a.unit}</div>
                  <Button variant="ghost" size="icon" className="h-7 w-7 text-red-500" onClick={() => setFormVariantAccessories(formVariantAccessories.filter((_, idx) => idx !== i))}>
                    <Trash2 className="h-3 w-3" />
                  </Button>
                </div>
              ))}
              <Button variant="outline" size="sm" className="w-full text-xs" onClick={() => setFormVariantAccessories([...formVariantAccessories, { accessory_id: 0, quantity: 1, unit: "个" }])}>
                <Plus className="h-3 w-3 mr-1" />添加配套产品
              </Button>
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setVariantDialogOpen(false)}>取消</Button>
            <Button onClick={handleSubmitVariant}>创建变体</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* ===== 删除模板确认弹窗 ===== */}
      <Dialog open={!!deleteTemplateId} onOpenChange={() => setDeleteTemplateId(null)}>
        <DialogContent className="max-w-sm">
          <DialogHeader><DialogTitle>确认删除模板</DialogTitle></DialogHeader>
          <p className="text-sm text-muted-foreground">确定要删除此模板吗？所有品牌变体也会被删除。</p>
          <DialogFooter>
            <Button variant="outline" onClick={() => setDeleteTemplateId(null)}>取消</Button>
            <Button variant="destructive" onClick={handleDeleteTemplate}>删除</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* ===== 删除变体确认弹窗 ===== */}
      <Dialog open={!!deleteVariantInfo} onOpenChange={() => setDeleteVariantInfo(null)}>
        <DialogContent className="max-w-sm">
          <DialogHeader><DialogTitle>确认删除品牌变体</DialogTitle></DialogHeader>
          <p className="text-sm text-muted-foreground">确定要删除此品牌变体吗？</p>
          <DialogFooter>
            <Button variant="outline" onClick={() => setDeleteVariantInfo(null)}>取消</Button>
            <Button variant="destructive" onClick={handleDeleteVariant}>删除</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
