import { useState, useEffect, useMemo } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
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
import { Plus, Search, Pencil, Trash2, Loader2, X } from "lucide-react";
import { toast } from "sonner";
import { apiFetch, apiPost } from "@/lib/api";

// ==================== 类型 ====================
interface Series { id: number; code: string; name: string; }
interface ProductTemplate {
  id: number;
  code: string;
  name: string;
  series_name: string | null;
  series_id: number | null;
  is_active: boolean;
}
interface ProductSpec {
  id: number;
  template_id: number;
  code: string;
  name: string;
  total_weight_g: number | null;
  box_count: number;
  sort_order: number;
  parts_config: any | null;
  packagings_config: any | null;
}

/** 物料（来自物料管理 /v4/materials） */
interface Material {
  id: number;
  code: string;
  name: string;
  spec: string | null;
  unit: string;
  category_id: number | null;
  category_name?: string | null;
}

/** 物料分类 */
interface MaterialCategory {
  id: number;
  name: string;
  code: string;
}

// 包装物配置项（关联物料）
interface SpecPackagingItem {
  level: string;          // box / inner / bag / ice / label / other
  material_id: number | null;
  material_name: string;  // 冗余显示用
  quantity: number;
  unit: string;
}

// 内容物配置项
interface SpecPartItem {
  type: "part" | "material";  // part=固定部位, material=物料管理中的配料
  value: string;               // 部位名 或 物料名
  material_id: number | null;  // type=material时关联
  amount: number;
  unit: string;
}

// ==================== 常量 ====================
const EMPTY_SPEC = { code: "", name: "", total_weight_g: "", box_count: 1, sort_order: 0 };

const PART_OPTIONS = ["鱼腩", "中段", "鱼尾", "鱼头", "鱼皮"];

const PACKAGING_LEVEL_OPTIONS = [
  { value: "box", label: "外盒" },
  { value: "inner", label: "内托" },
  { value: "bag", label: "包装袋" },
  { value: "ice", label: "冰袋" },
  { value: "label", label: "标签" },
  { value: "other", label: "其他" },
];

const UNIT_OPTIONS = ["g", "只", "个", "片", "ml", "条", "包", "粒"];

// ==================== 组件 ====================
export function ProductTemplatePage() {
  // ---- 数据状态 ----
  const [seriesList, setSeriesList] = useState<Series[]>([]);
  const [templates, setTemplates] = useState<ProductTemplate[]>([]);
  const [selectedTpl, setSelectedTpl] = useState<ProductTemplate | null>(null);
  const [specs, setSpecs] = useState<ProductSpec[]>([]);
  const [loading, setLoading] = useState(true);
  const [specLoading, setSpecLoading] = useState(false);
  const [search, setSearch] = useState("");

  // 物料数据（用于下拉选择）
  const [materials, setMaterials] = useState<Material[]>([]);
  const [materialCategories, setMaterialCategories] = useState<MaterialCategory[]>([]);

  // SPU 弹窗
  const [tplDialog, setTplDialog] = useState(false);
  const [editingTpl, setEditingTpl] = useState<ProductTemplate | null>(null);
  const [tplForm, setTplForm] = useState({ code: "", name: "", series_id: "", notes: "" });
  const [tplSubmitting, setTplSubmitting] = useState(false);

  // 规格弹窗
  const [specDialog, setSpecDialog] = useState(false);
  const [editingSpec, setEditingSpec] = useState<ProductSpec | null>(null);
  const [specForm, setSpecForm] = useState(EMPTY_SPEC);
  const [specParts, setSpecParts] = useState<SpecPartItem[]>([]);
  const [specPackagings, setSpecPackagings] = useState<SpecPackagingItem[]>([]);
  const [submitting, setSubmitting] = useState(false);

  // ---- 计算属性：物料分组 ----
  const packagingMaterials = useMemo(() =>
    materials.filter(m => {
      const catName = (m.category_name || "").toLowerCase();
      return catName.includes("包装") || catName.includes("包材") || catName.includes("标签");
    }),
    [materials]
  );

  const ingredientMaterials = useMemo(() =>
    materials.filter(m => {
      const catName = (m.category_name || "").toLowerCase();
      return catName.includes("海鲜") || catName.includes("配料") || catName.includes("调料") || catName.includes("食品");
    }),
    [materials]
  );

  // ---- API 加载 ----
  const fetchSeries = async () => {
    const res = await apiFetch("/v1/finished-products/series");
    const items = Array.isArray(res.data) ? res.data : (res.data?.items || []);
    if (res.ok) setSeriesList(items);
  };

  const fetchTemplates = async () => {
    setLoading(true);
    const res = await apiFetch("/v1/finished-products/templates");
    const items = res.data?.items || [];
    if (res.ok && items.length > 0) {
      setTemplates(items);
      if (!selectedTpl) setSelectedTpl(items[0]);
      else {
        const updated = items.find((t: ProductTemplate) => t.id === selectedTpl.id);
        if (updated) setSelectedTpl(updated);
      }
    } else if (res.ok) {
      setTemplates([]);
      setSelectedTpl(null);
    }
    setLoading(false);
  };

  const fetchSpecs = async (templateId: number) => {
    setSpecLoading(true);
    const res = await apiFetch(`/v1/finished-products/templates/${templateId}/specs`);
    if (res.ok && Array.isArray(res.data)) setSpecs(res.data);
    else setSpecs([]);
    setSpecLoading(false);
  };

  const fetchMaterials = async () => {
    const res = await apiFetch("/v4/materials?limit=500");
    const items = res.data?.items || [];
    if (res.ok) setMaterials(items);
  };

  const fetchMaterialCategories = async () => {
    const res = await apiFetch("/v4/material-categories?limit=100");
    const items = res.data?.items || [];
    if (res.ok) setMaterialCategories(items);
  };

  useEffect(() => {
    fetchSeries();
    fetchTemplates();
    fetchMaterials();
    fetchMaterialCategories();
  }, []);
  useEffect(() => { if (selectedTpl) fetchSpecs(selectedTpl.id); }, [selectedTpl?.id]);

  // 将 category_name 注入物料列表
  useEffect(() => {
    if (materials.length && materialCategories.length) {
      const catMap = new Map(materialCategories.map(c => [c.id, c.name]));
      setMaterials(prev => prev.map(m => ({
        ...m,
        category_name: m.category_id ? catMap.get(m.category_id) || null : null,
      })));
    }
  }, [materialCategories]);

  const filtered = templates.filter(t =>
    t.code.toLowerCase().includes(search.toLowerCase()) ||
    t.name.includes(search)
  );

  const getSeriesName = (seriesId: number | null) => {
    if (!seriesId) return "-";
    const s = seriesList.find(s => s.id === seriesId);
    return s?.name || "-";
  };

  // ==================== SPU CRUD ====================
  const openTplCreate = () => {
    setEditingTpl(null);
    setTplForm({ code: "", name: "", series_id: "", notes: "" });
    setTplDialog(true);
  };
  const openTplEdit = (t: ProductTemplate) => {
    setEditingTpl(t);
    setTplForm({ code: t.code, name: t.name, series_id: String(t.series_id || ""), notes: "" });
    setTplDialog(true);
  };
  const handleSaveTemplate = async () => {
    if (!tplForm.code || !tplForm.name) { toast.error("编码和名称必填"); return; }
    setTplSubmitting(true);
    const url = editingTpl ? `/v1/finished-products/templates/${editingTpl.id}` : "/v1/finished-products/templates";
    const payload = {
      code: tplForm.code,
      name: tplForm.name,
      series_id: tplForm.series_id ? Number(tplForm.series_id) : null,
      spec: null,
    };
    let res;
    if (editingTpl) {
      res = await apiFetch(url, { method: "PUT", body: JSON.stringify(payload) }, "SPU 更新成功");
    } else {
      res = await apiPost(url, payload, "SPU 创建成功");
    }
    setTplSubmitting(false);
    if (res.ok) { setTplDialog(false); fetchTemplates(); }
  };
  const handleDeleteTemplate = async (t: ProductTemplate) => {
    if (!confirm(`确认删除 SPU ${t.code} - ${t.name}？`)) return;
    const res = await apiFetch(`/v1/finished-products/templates/${t.id}`, { method: "DELETE" }, "删除成功");
    if (res.ok) { fetchTemplates(); setSelectedTpl(null); }
  };

  // ==================== 规格 CRUD ====================
  const openSpecCreate = () => {
    setEditingSpec(null);
    setSpecForm(EMPTY_SPEC);
    setSpecParts([]);
    setSpecPackagings([]);
    setSpecDialog(true);
  };

  const openSpecEdit = (s: ProductSpec) => {
    setEditingSpec(s);
    setSpecForm({
      code: s.code,
      name: s.name,
      total_weight_g: s.total_weight_g ? String(s.total_weight_g) : "",
      box_count: s.box_count,
      sort_order: s.sort_order,
    });

    // 解析内容物
    let parts: SpecPartItem[] = [];
    if (s.parts_config) {
      try {
        const parsed = typeof s.parts_config === "string" ? JSON.parse(s.parts_config) : s.parts_config;
        if (Array.isArray(parsed)) {
          parts = parsed.map((p: any) => ({
            type: p.type || "part",
            value: p.value || p.part || "",
            material_id: p.material_id ?? null,
            amount: p.amount ?? p.g ?? 0,
            unit: p.unit || "g",
          }));
        }
      } catch { /* ignore */ }
    }
    setSpecParts(parts.length > 0 ? parts : []);

    // 解析包装物
    let pkgs: SpecPackagingItem[] = [];
    if (s.packagings_config) {
      try {
        const parsed = typeof s.packagings_config === "string" ? JSON.parse(s.packagings_config) : s.packagings_config;
        if (Array.isArray(parsed)) {
          pkgs = parsed.map((p: any) => ({
            level: p.level || "other",
            material_id: p.material_id ?? null,
            material_name: p.material_name || "",
            quantity: p.quantity ?? 1,
            unit: p.unit || "个",
          }));
        }
      } catch { /* ignore */ }
    }
    setSpecPackagings(pkgs.length > 0 ? pkgs : []);
    setSpecDialog(true);
  };

  const handleSaveSpec = async () => {
    if (!selectedTpl || !specForm.code || !specForm.name) return;
    setSubmitting(true);
    const partsConfig = specParts.length > 0 ? JSON.stringify(specParts) : null;
    const pkgConfig = specPackagings.length > 0 ? JSON.stringify(specPackagings) : null;
    const payload = {
      code: specForm.code,
      name: specForm.name,
      total_weight_g: specForm.total_weight_g ? Number(specForm.total_weight_g) : null,
      box_count: Number(specForm.box_count),
      sort_order: Number(specForm.sort_order),
      parts_config: partsConfig,
      packagings_config: pkgConfig,
    };
    let res;
    if (editingSpec) {
      res = await apiFetch(
        `/v1/finished-products/templates/${selectedTpl.id}/specs/${editingSpec.id}`,
        { method: "PUT", body: JSON.stringify(payload) },
        "规格更新成功"
      );
    } else {
      res = await apiPost(
        `/v1/finished-products/templates/${selectedTpl.id}/specs`,
        payload,
        "规格创建成功"
      );
    }
    setSubmitting(false);
    if (res.ok) { setSpecDialog(false); fetchSpecs(selectedTpl.id); }
  };

  const handleDeleteSpec = async (s: ProductSpec) => {
    if (!selectedTpl) return;
    if (!confirm(`确认删除规格 ${s.code} - ${s.name}？`)) return;
    const res = await apiFetch(`/v1/finished-products/templates/${selectedTpl.id}/specs/${s.id}`, { method: "DELETE" }, "删除成功");
    if (res.ok) fetchSpecs(selectedTpl.id);
  };

  // ==================== UI 辅助 ====================
  const getMaterialName = (id: number | null) => {
    if (!id) return "";
    const m = materials.find(x => x.id === id);
    return m ? `${m.name} (${m.code})` : "";
  };

  const getMaterialUnit = (id: number | null) => {
    if (!id) return "个";
    const m = materials.find(x => x.id === id);
    return m?.unit || "个";
  };

  const handleAddPart = () => {
    setSpecParts([...specParts, { type: "part", value: "", material_id: null, amount: 0, unit: "g" }]);
  };

  const handleAddIngredient = () => {
    setSpecParts([...specParts, { type: "material", value: "", material_id: null, amount: 0, unit: "个" }]);
  };

  const handleAddPackaging = () => {
    setSpecPackagings([...specPackagings, { level: "box", material_id: null, material_name: "", quantity: 1, unit: "个" }]);
  };

  // ==================== 渲染 ====================
  return (
    <div className="h-full flex flex-col gap-4 p-4">
      {/* 顶部 */}
      <div className="flex-none space-y-3">
        <div className="flex items-center justify-between">
          <h2 className="text-xl font-bold">SPU 与规格管理</h2>
          <Button onClick={openTplCreate}><Plus className="h-4 w-4 mr-1" />新建 SPU</Button>
        </div>
        <div className="flex items-center gap-2">
          <Search className="h-4 w-4 text-muted-foreground" />
          <Input placeholder="搜索 SPU 编码或名称..." value={search} onChange={e => setSearch(e.target.value)} className="max-w-sm" />
        </div>
      </div>

      {/* 左右布局 */}
      <div className="flex-1 flex gap-4 min-h-0">
        {/* 左侧 SPU 列表 */}
        <div className="w-1/3 border rounded-lg overflow-hidden flex flex-col">
          <div className="flex-1 overflow-auto">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead className="sticky top-0 bg-background z-10">SPU</TableHead>
                  <TableHead className="sticky top-0 bg-background z-10">系列</TableHead>
                  <TableHead className="sticky top-0 bg-background z-10 text-right">操作</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {loading ? (
                  <TableRow><TableCell colSpan={3} className="text-center py-8"><Loader2 className="h-5 w-5 animate-spin mx-auto" /></TableCell></TableRow>
                ) : filtered.length === 0 ? (
                  <TableRow><TableCell colSpan={3} className="text-center py-8 text-muted-foreground">暂无数据，点击"新建 SPU"创建</TableCell></TableRow>
                ) : (
                  filtered.map(t => (
                    <TableRow key={t.id} className={selectedTpl?.id === t.id ? "bg-primary/10 cursor-pointer" : "cursor-pointer"} onClick={() => setSelectedTpl(t)}>
                      <TableCell>
                        <div className="font-medium">{t.name}</div>
                        <div className="text-xs text-muted-foreground">{t.code}</div>
                      </TableCell>
                      <TableCell><Badge variant="outline">{getSeriesName(t.series_id)}</Badge></TableCell>
                      <TableCell className="text-right space-x-1">
                        <Button variant="ghost" size="icon" onClick={e => { e.stopPropagation(); openTplEdit(t); }}><Pencil className="h-4 w-4" /></Button>
                        <Button variant="ghost" size="icon" onClick={e => { e.stopPropagation(); handleDeleteTemplate(t); }}><Trash2 className="h-4 w-4 text-destructive" /></Button>
                      </TableCell>
                    </TableRow>
                  ))
                )}
              </TableBody>
            </Table>
          </div>
        </div>

        {/* 右侧规格列表 */}
        <div className="flex-1 border rounded-lg overflow-hidden flex flex-col">
          <div className="flex-none px-4 py-3 border-b flex items-center justify-between">
            <div>
              <span className="font-medium">{selectedTpl?.name || "请选择 SPU"}</span>
              {selectedTpl && <span className="text-muted-foreground text-sm ml-2">规格列表</span>}
            </div>
            <Button size="sm" onClick={openSpecCreate} disabled={!selectedTpl}><Plus className="h-4 w-4 mr-1" />添加规格</Button>
          </div>
          <div className="flex-1 overflow-auto">
            {specLoading ? (
              <div className="flex items-center justify-center py-8"><Loader2 className="h-5 w-5 animate-spin" /></div>
            ) : (
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead className="sticky top-0 bg-background z-10">编码</TableHead>
                    <TableHead className="sticky top-0 bg-background z-10">名称</TableHead>
                    <TableHead className="sticky top-0 bg-background z-10">重量</TableHead>
                    <TableHead className="sticky top-0 bg-background z-10">盒数</TableHead>
                    <TableHead className="sticky top-0 bg-background z-10">内容物</TableHead>
                    <TableHead className="sticky top-0 bg-background z-10 text-right">操作</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {specs.length === 0 ? (
                    <TableRow><TableCell colSpan={6} className="text-center py-8 text-muted-foreground">该 SPU 暂无规格</TableCell></TableRow>
                  ) : (
                    specs.map(s => (
                      <TableRow key={s.id}>
                        <TableCell className="font-medium">{s.code}</TableCell>
                        <TableCell>{s.name}</TableCell>
                        <TableCell>{s.total_weight_g ? `${s.total_weight_g}g` : "-"}</TableCell>
                        <TableCell>{s.box_count}</TableCell>
                        <TableCell className="max-w-[200px] truncate">
                          {(() => {
                            try {
                              const p = typeof s.parts_config === "string" ? JSON.parse(s.parts_config) : s.parts_config;
                              if (Array.isArray(p)) return p.map((x: any) => `${x.value || x.part}${x.amount ?? x.g ?? ""}${x.unit || "g"}`).join("+");
                            } catch { /* ignore */ }
                            return "-";
                          })()}
                        </TableCell>
                        <TableCell className="text-right space-x-1">
                          <Button variant="ghost" size="icon" onClick={() => openSpecEdit(s)}><Pencil className="h-4 w-4" /></Button>
                          <Button variant="ghost" size="icon" onClick={() => handleDeleteSpec(s)}><Trash2 className="h-4 w-4 text-destructive" /></Button>
                        </TableCell>
                      </TableRow>
                    ))
                  )}
                </TableBody>
              </Table>
            )}
          </div>
          <div className="flex-none px-4 py-2 border-t bg-muted/30 text-sm text-muted-foreground">共 {specs.length} 个规格</div>
        </div>
      </div>

      {/* ==================== SPU 弹窗 ==================== */}
      <Dialog open={tplDialog} onOpenChange={setTplDialog}>
        <DialogContent>
          <DialogHeader><DialogTitle>{editingTpl ? "编辑 SPU" : "新建 SPU"}</DialogTitle></DialogHeader>
          <div className="space-y-4 py-2">
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2"><Label>编码 <span className="text-red-500">*</span></Label><Input value={tplForm.code} onChange={e => setTplForm({...tplForm, code: e.target.value})} placeholder="如 SASH-001" disabled={!!editingTpl} /></div>
              <div className="space-y-2"><Label>系列</Label>
                <Select value={tplForm.series_id} onValueChange={v => setTplForm({...tplForm, series_id: v})}>
                  <SelectTrigger><SelectValue placeholder="选择系列">{seriesList.find(s => String(s.id) === tplForm.series_id)?.name || <span className="text-muted-foreground">选择系列</span>}</SelectValue></SelectTrigger>
                  <SelectContent>{seriesList.map(s => <SelectItem key={s.id} value={String(s.id)}>{s.name}</SelectItem>)}</SelectContent>
                </Select>
              </div>
            </div>
            <div className="space-y-2"><Label>名称 <span className="text-red-500">*</span></Label><Input value={tplForm.name} onChange={e => setTplForm({...tplForm, name: e.target.value})} placeholder="如 三文鱼刺身" /></div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setTplDialog(false)}>取消</Button>
            <Button onClick={handleSaveTemplate} disabled={tplSubmitting || !tplForm.code || !tplForm.name}>{tplSubmitting && <Loader2 className="h-4 w-4 mr-1 animate-spin" />}{editingTpl ? "保存" : "创建"}</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* ==================== 规格弹窗（新版） ==================== */}
      <Dialog open={specDialog} onOpenChange={setSpecDialog}>
        <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
          <DialogHeader><DialogTitle>{editingSpec ? "编辑规格" : "添加规格"}</DialogTitle></DialogHeader>
          <div className="space-y-4 py-2">
            {/* 基础信息 */}
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2"><Label>编码 <span className="text-red-500">*</span></Label><Input value={specForm.code} onChange={e => setSpecForm({...specForm, code: e.target.value})} placeholder="如 TP-003" disabled={!!editingSpec} /></div>
              <div className="space-y-2"><Label>盒数</Label><Input type="number" value={specForm.box_count} onChange={e => setSpecForm({...specForm, box_count: Number(e.target.value)})} /></div>
            </div>
            <div className="space-y-2"><Label>名称 <span className="text-red-500">*</span></Label><Input value={specForm.name} onChange={e => setSpecForm({...specForm, name: e.target.value})} placeholder="如 鱼腩200g+中段200g" /></div>
            <div className="space-y-2"><Label>总重量 (g)</Label><Input type="number" value={specForm.total_weight_g} onChange={e => setSpecForm({...specForm, total_weight_g: e.target.value})} placeholder="自动计算或手动填写" /></div>

            {/* ── 通用包装物（从物料管理选择） ── */}
            <div className="border rounded-lg p-3 space-y-2">
              <div className="flex items-center justify-between">
                <Label className="text-sm font-medium">通用包装物</Label>
                <Button variant="outline" size="sm" onClick={handleAddPackaging}><Plus className="h-3 w-3 mr-1" />添加</Button>
              </div>
              {specPackagings.length === 0 && (
                <p className="text-xs text-muted-foreground">
                  从物料管理中选择包装物（如外盒、内托、冰袋等）
                </p>
              )}
              {specPackagings.map((pkg, i) => (
                <div key={i} className="grid grid-cols-12 gap-2 items-center">
                  {/* 级别 */}
                  <div className="col-span-3">
                    <Select value={pkg.level} onValueChange={v => {
                      const n = [...specPackagings]; n[i] = { ...pkg, level: v }; setSpecPackagings(n);
                    }}>
                      <SelectTrigger className="text-xs"><SelectValue /></SelectTrigger>
                      <SelectContent>
                        {PACKAGING_LEVEL_OPTIONS.map(o => (
                          <SelectItem key={o.value} value={o.value} className="text-xs">{o.label}</SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                  {/* 物料选择 */}
                  <div className="col-span-4">
                    <Select
                      value={pkg.material_id ? String(pkg.material_id) : ""}
                      onValueChange={v => {
                        const mid = v ? Number(v) : null;
                        const mat = materials.find(m => m.id === mid);
                        const n = [...specPackagings];
                        n[i] = {
                          ...pkg,
                          material_id: mid,
                          material_name: mat?.name || "",
                          unit: mat?.unit || "个",
                        };
                        setSpecPackagings(n);
                      }}
                    >
                      <SelectTrigger className="text-xs">
                        <SelectValue placeholder="选择物料">{pkg.material_id ? getMaterialName(pkg.material_id) : <span className="text-muted-foreground">选择物料</span>}</SelectValue>
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="" disabled className="text-xs text-muted-foreground">—— 包装物料 ——</SelectItem>
                        {packagingMaterials.map(m => (
                          <SelectItem key={m.id} value={String(m.id)} className="text-xs">{m.name} ({m.code}) · {m.unit}</SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                  {/* 数量 */}
                  <div className="col-span-2">
                    <Input type="number" placeholder="数量" value={pkg.quantity || ""} onChange={e => {
                      const n = [...specPackagings]; n[i] = { ...pkg, quantity: Number(e.target.value) }; setSpecPackagings(n);
                    }} className="text-xs" />
                  </div>
                  {/* 单位（只读，来自物料） */}
                  <div className="col-span-2">
                    <Input value={pkg.unit} disabled className="text-xs bg-muted" title="单位跟随所选物料" />
                  </div>
                  {/* 删除 */}
                  <div className="col-span-1 flex justify-end">
                    <Button variant="ghost" size="icon" className="text-destructive h-7 w-7" onClick={() => setSpecPackagings(specPackagings.filter((_, idx) => idx !== i))}>
                      <X className="h-4 w-4" />
                    </Button>
                  </div>
                </div>
              ))}
            </div>

            {/* ── 内容物配置（部位 + 配料） ── */}
            <div className="border rounded-lg p-3 space-y-2">
              <div className="flex items-center justify-between">
                <Label className="text-sm font-medium">内容物配置（部位 / 配料）</Label>
                <div className="flex gap-2">
                  <Button variant="outline" size="sm" onClick={handleAddPart}><Plus className="h-3 w-3 mr-1" />部位</Button>
                  <Button variant="outline" size="sm" onClick={handleAddIngredient}><Plus className="h-3 w-3 mr-1" />配料</Button>
                </div>
              </div>
              {specParts.length === 0 && <p className="text-xs text-muted-foreground">添加部位或配料（如中段130g、去尾甜虾15只）</p>}
              {specParts.map((p, i) => (
                <div key={i} className="grid grid-cols-12 gap-2 items-center">
                  {/* 类型标识 + 选择 */}
                  <div className="col-span-4">
                    {p.type === "part" ? (
                      <Select value={p.value} onValueChange={v => {
                        const n = [...specParts]; n[i] = { ...p, value: v }; setSpecParts(n);
                      }}>
                        <SelectTrigger className="text-xs"><SelectValue placeholder="选择部位" /></SelectTrigger>
                        <SelectContent>
                          {PART_OPTIONS.map(o => <SelectItem key={o} value={o} className="text-xs">{o}</SelectItem>)}
                        </SelectContent>
                      </Select>
                    ) : (
                      <Select
                        value={p.material_id ? String(p.material_id) : ""}
                        onValueChange={v => {
                          const mid = v ? Number(v) : null;
                          const mat = materials.find(m => m.id === mid);
                          const n = [...specParts];
                          n[i] = {
                            ...p,
                            material_id: mid,
                            value: mat?.name || "",
                            unit: mat?.unit || "个",
                          };
                          setSpecParts(n);
                        }}
                      >
                        <SelectTrigger className="text-xs">
                          <SelectValue placeholder="选择配料">{p.material_id ? getMaterialName(p.material_id) : <span className="text-muted-foreground">选择配料</span>}</SelectValue>
                        </SelectTrigger>
                        <SelectContent>
                          {/* 海鲜/配料分类 */}
                          <SelectItem value="" disabled className="text-xs text-muted-foreground">—— 海鲜/配料 ——</SelectItem>
                          {ingredientMaterials.map(m => (
                            <SelectItem key={m.id} value={String(m.id)} className="text-xs">{m.name} ({m.code}) · {m.unit}</SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    )}
                  </div>
                  {/* 数量 */}
                  <div className="col-span-3">
                    <Input type="number" placeholder="数量" value={p.amount || ""} onChange={e => {
                      const n = [...specParts]; n[i] = { ...p, amount: Number(e.target.value) }; setSpecParts(n);
                    }} className="text-xs" />
                  </div>
                  {/* 单位 */}
                  <div className="col-span-3">
                    {p.type === "part" ? (
                      <Select value={p.unit} onValueChange={v => { const n = [...specParts]; n[i] = { ...p, unit: v }; setSpecParts(n); }}>
                        <SelectTrigger className="text-xs"><SelectValue /></SelectTrigger>
                        <SelectContent>{UNIT_OPTIONS.map(o => <SelectItem key={o} value={o} className="text-xs">{o}</SelectItem>)}</SelectContent>
                      </Select>
                    ) : (
                      <Input value={p.unit} disabled className="text-xs bg-muted" title="单位跟随所选物料" />
                    )}
                  </div>
                  {/* 删除 + 类型切换 */}
                  <div className="col-span-2 flex justify-end gap-1">
                    <Button variant="ghost" size="sm" className="h-7 px-2 text-xs text-muted-foreground" onClick={() => {
                      const n = [...specParts];
                      const isPart = n[i].type === "part";
                      n[i] = { ...n[i], type: isPart ? "material" : "part", value: "", material_id: null, unit: isPart ? "个" : "g" };
                      setSpecParts(n);
                    }}>
                      {p.type === "part" ? "切配料" : "切部位"}
                    </Button>
                    <Button variant="ghost" size="icon" className="text-destructive h-7 w-7" onClick={() => setSpecParts(specParts.filter((_, idx) => idx !== i))}>
                      <X className="h-4 w-4" />
                    </Button>
                  </div>
                </div>
              ))}
              {specParts.length > 0 && (
                <div className="text-xs text-muted-foreground border-t pt-2 flex items-center gap-2">
                  <span>重量合计: <span className="font-medium">{specParts.filter(p => p.unit === "g").reduce((sum, p) => sum + (p.amount || 0), 0)}g</span></span>
                  <Button variant="link" size="sm" className="h-auto p-0 text-xs" onClick={() => {
                    const total = specParts.filter(p => p.unit === "g").reduce((sum, p) => sum + (p.amount || 0), 0);
                    if (total > 0) setSpecForm({ ...specForm, total_weight_g: String(total) });
                  }}>填入总重量</Button>
                </div>
              )}
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setSpecDialog(false)}>取消</Button>
            <Button onClick={handleSaveSpec} disabled={submitting || !specForm.code || !specForm.name}>
              {submitting && <Loader2 className="h-4 w-4 mr-1 animate-spin" />}{editingSpec ? "保存" : "创建"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
