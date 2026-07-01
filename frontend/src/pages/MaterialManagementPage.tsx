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
import { toast } from "sonner";
import {
  Plus, Search, Pencil, Trash2, Store, Star,
} from "lucide-react";

// ==================== 类型 ====================
interface MaterialCategory {
  id: number;
  name: string;
  code: string | null;
}

interface Material {
  id: number;
  code: string;
  name: string;
  spec: string | null;
  unit: string;
  category: MaterialCategory | null;
  is_active: boolean;
  param?: string | null;
  remark?: string | null;
}

// ==================== 主页面 ====================
export function MaterialManagementPage() {
  const qc = useQueryClient();
  const [search, setSearch] = useState("");
  const [categoryFilter, setCategoryFilter] = useState<string>("all");
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [deleteId, setDeleteId] = useState<number | null>(null);

  // 分类管理弹窗
  const [catDialogOpen, setCatDialogOpen] = useState(false);
  const [catForm, setCatForm] = useState({ id: null as number | null, name: "", code: "" });

  // 表单
  const [formCode, setFormCode] = useState("");
  const [formName, setFormName] = useState("");
  const [formSpec, setFormSpec] = useState("");
  const [formUnit, setFormUnit] = useState("个");
  const [formCategoryId, setFormCategoryId] = useState("");
  const [formParam, setFormParam] = useState("");
  const [formRemark, setFormRemark] = useState("");
  const [formIsActive, setFormIsActive] = useState(true);

  // 数据查询
  const { data: materialsData, isLoading: mLoading } = useQuery({
    queryKey: ["materials"],
    queryFn: async () => {
      const res = await api.get("/v1/materials/?limit=500");
      return res.data.items as Material[];
    },
  });

  const { data: categoriesData } = useQuery({
    queryKey: ["material-categories"],
    queryFn: async () => {
      const res = await api.get("/v1/material-categories");
      const arr = Array.isArray(res.data) ? res.data : res.data?.items || [];
      return arr as MaterialCategory[];
    },
  });

  const materials = materialsData || [];
  const categories = categoriesData || [];

  // 筛选
  const filtered = useMemo(() => {
    let result = materials;
    if (categoryFilter !== "all") {
      result = result.filter((m) => m.category?.id === Number(categoryFilter));
    }
    if (!search.trim()) return result;
    const s = search.trim().toLowerCase();
    return result.filter(
      (m) =>
        m.name.toLowerCase().includes(s) ||
        m.code.toLowerCase().includes(s) ||
        (m.spec ?? "").toLowerCase().includes(s) ||
        (m.category?.name ?? "").toLowerCase().includes(s)
    );
  }, [materials, categoryFilter, search]);

  // CRUD Mutations
  const createMutation = useMutation({
    mutationFn: async (payload: any) => {
      const res = await api.post("/v1/products/", payload);
      return res.data;
    },
  });

  const updateMutation = useMutation({
    mutationFn: async ({ id, payload }: { id: number; payload: any }) => {
      await api.put(`/v1/products/${id}`, payload);
    },
  });

  const deleteMutation = useMutation({
    mutationFn: (id: number) => api.delete(`/v1/products/${id}`),
  });

  // 分类管理 Mutations
  const catCreateMutation = useMutation({
    mutationFn: async (payload: any) => {
      const res = await api.post("/v1/material-categories", payload);
      return res.data;
    },
  });

  const catUpdateMutation = useMutation({
    mutationFn: async ({ id, payload }: { id: number; payload: any }) => {
      await api.put(`/v1/material-categories/${id}`, payload);
    },
  });

  const catDeleteMutation = useMutation({
    mutationFn: (id: number) => api.delete(`/v1/material-categories/${id}`),
  });

  function resetForm() {
    setFormCode("");
    setFormName("");
    setFormSpec("");
    setFormUnit("个");
    setFormCategoryId("");
    setFormParam("");
    setFormRemark("");
    setFormIsActive(true);
    setEditingId(null);
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
    setFormCategoryId(m.category?.id ? String(m.category.id) : "");
    setFormParam(m.param ?? "");
    setFormRemark(m.remark ?? "");
    setFormIsActive(m.is_active);
    setDialogOpen(true);
  }

  async function handleSubmit() {
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
      material_category_id: formCategoryId ? Number(formCategoryId) : null,
      param: formParam.trim() || null,
      remark: formRemark.trim() || null,
    };
    try {
      if (editingId) {
        await updateMutation.mutateAsync({ id: editingId, payload });
        toast.success("物料更新成功");
      } else {
        await createMutation.mutateAsync(payload);
        toast.success("物料创建成功");
      }
      await qc.invalidateQueries({ queryKey: ["materials"] });
      setDialogOpen(false);
      resetForm();
    } catch (err: any) {
      toast.error(err.response?.data?.detail || "操作失败");
    }
  }

  async function handleDeleteConfirm() {
    if (!deleteId) return;
    try {
      await deleteMutation.mutateAsync(deleteId);
      await qc.invalidateQueries({ queryKey: ["materials"] });
      setDeleteId(null);
      toast.success("物料已删除");
    } catch (err: any) {
      toast.error(err.response?.data?.detail || "删除失败");
    }
  }

  // 分类管理
  function openCatDialog() {
    setCatForm({ id: null, name: "", code: "" });
    setCatDialogOpen(true);
  }

  function openCatEdit(cat: MaterialCategory) {
    setCatForm({ id: cat.id, name: cat.name, code: cat.code || "" });
    setCatDialogOpen(true);
  }

  async function handleCatSubmit() {
    if (!catForm.name.trim()) {
      toast.error("分类名称不能为空");
      return;
    }
    const payload = {
      name: catForm.name.trim(),
      code: catForm.code.trim() || undefined,
    };
    try {
      if (catForm.id) {
        await catUpdateMutation.mutateAsync({ id: catForm.id, payload });
        toast.success("分类更新成功");
      } else {
        await catCreateMutation.mutateAsync(payload);
        toast.success("分类创建成功");
      }
      await qc.invalidateQueries({ queryKey: ["material-categories"] });
      await qc.invalidateQueries({ queryKey: ["materials"] });
      setCatDialogOpen(false);
    } catch (err: any) {
      toast.error(err.response?.data?.detail || "操作失败");
    }
  }

  async function handleCatDelete(id: number) {
    try {
      await catDeleteMutation.mutateAsync(id);
      await qc.invalidateQueries({ queryKey: ["material-categories"] });
      toast.success("分类已删除");
    } catch (err: any) {
      toast.error(err.response?.data?.detail || "删除失败");
    }
  }

  return (
    <div className="space-y-4">
      {/* 标题栏 */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">物料管理</h1>
          <p className="text-sm text-muted-foreground">成品包装物、标签、配套产品等物料管理</p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" onClick={openCatDialog}>
            <Store className="h-4 w-4 mr-1" />
            管理分类
          </Button>
          <Button onClick={openCreate}>
            <Plus className="h-4 w-4 mr-1" />
            新增物料
          </Button>
        </div>
      </div>

      {/* 搜索 + 分类筛选 */}
      <div className="flex items-center gap-3">
        <div className="relative flex-1 max-w-sm">
          <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
          <Input
            placeholder="搜索物料名称、编码..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="pl-9"
          />
        </div>
        <Select value={categoryFilter} onValueChange={setCategoryFilter}>
          <SelectTrigger className="w-[160px]">
            <SelectValue placeholder="全部分类">
              {categoryFilter === "all" ? "全部分类" : categories.find((c) => String(c.id) === categoryFilter)?.name || "全部分类"}
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
        <span className="text-sm text-muted-foreground">共 {filtered.length} 种物料</span>
      </div>

      {/* 物料列表 */}
      <div className="border rounded-lg">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>编码</TableHead>
              <TableHead>物料名称</TableHead>
              <TableHead>物料分类</TableHead>
              <TableHead>规格</TableHead>
              <TableHead>参数</TableHead>
              <TableHead>备注</TableHead>
              <TableHead className="w-[100px]">操作</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {mLoading ? (
              <TableRow>
                <TableCell colSpan={7} className="text-center py-8">加载中...</TableCell>
              </TableRow>
            ) : filtered.length === 0 ? (
              <TableRow>
                <TableCell colSpan={7} className="text-center py-8 text-muted-foreground">
                  暂无物料
                </TableCell>
              </TableRow>
            ) : (
              filtered.map((m) => (
                <TableRow key={m.id} className={cn(!m.is_active && "opacity-50")}>
                  <TableCell className="font-mono text-xs text-muted-foreground">{m.code}</TableCell>
                  <TableCell className="font-medium">{m.name}</TableCell>
                  <TableCell>
                    {m.category ? (
                      <span className="text-sm">{m.category.name}</span>
                    ) : (
                      <span className="text-xs text-muted-foreground">-</span>
                    )}
                  </TableCell>
                  <TableCell className="text-muted-foreground">{m.spec ?? "-"}</TableCell>
                  <TableCell className="text-muted-foreground">{m.param ?? "-"}</TableCell>
                  <TableCell className="text-muted-foreground">{m.remark ?? "-"}</TableCell>
                  <TableCell>
                    <div className="flex gap-1">
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

      {/* ===== 新增/编辑物料弹窗 ===== */}
      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>{editingId ? "编辑物料" : "新增物料"}</DialogTitle>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label>物料编码</Label>
                <Input value={formCode} onChange={(e) => setFormCode(e.target.value)} placeholder="留空自动生成" />
              </div>
              <div className="space-y-2">
                <Label>物料名称 <span className="text-red-500">*</span></Label>
                <Input value={formName} onChange={(e) => setFormName(e.target.value)} placeholder="如: 真空袋" />
              </div>
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label>物料分类</Label>
                <Select value={formCategoryId} onValueChange={(v) => setFormCategoryId(v)}>
                  <SelectTrigger>
                    <SelectValue placeholder="选择分类">
                      {formCategoryId
                        ? categories.find((c) => String(c.id) === formCategoryId)?.name || "选择分类"
                        : "选择分类"}
                    </SelectValue>
                  </SelectTrigger>
                  <SelectContent>
                    {categories.map((cat) => (
                      <SelectItem key={cat.id} value={String(cat.id)}>{cat.name}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-2">
                <Label>规格</Label>
                <Input value={formSpec} onChange={(e) => setFormSpec(e.target.value)} placeholder="如: 食品级透明" />
              </div>
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label>参数</Label>
                <Input value={formParam} onChange={(e) => setFormParam(e.target.value)} placeholder="如: 200g" />
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
            <div className="space-y-2">
              <Label>备注</Label>
              <Input value={formRemark} onChange={(e) => setFormRemark(e.target.value)} placeholder="备注信息" />
            </div>
            <div className="space-y-2">
              <Label>状态</Label>
              <Select value={formIsActive ? "active" : "inactive"} onValueChange={(v) => setFormIsActive(v === "active")}>
                <SelectTrigger>
                  <SelectValue>{formIsActive ? "启用" : "停用"}</SelectValue>
                </SelectTrigger>
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

      {/* ===== 分类管理弹窗 ===== */}
      <Dialog open={catDialogOpen} onOpenChange={setCatDialogOpen}>
        <DialogContent className="max-w-lg max-h-[80vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>物料分类管理</DialogTitle>
          </DialogHeader>
          <div className="space-y-4 py-4">
            {/* 新增/编辑分类表单 */}
            <div className="border rounded-lg p-3 space-y-3">
              <div className="grid grid-cols-2 gap-3">
                <div className="space-y-2">
                  <Label>分类名称 <span className="text-red-500">*</span></Label>
                  <Input
                    value={catForm.name}
                    onChange={(e) => setCatForm({ ...catForm, name: e.target.value })}
                    placeholder="如: 包装物"
                  />
                </div>
                <div className="space-y-2">
                  <Label>分类编码 <span className="text-muted-foreground text-xs">(留空自动生成)</span></Label>
                  <Input
                    value={catForm.code}
                    onChange={(e) => setCatForm({ ...catForm, code: e.target.value })}
                    placeholder="如: BZ 或自动生成"
                  />
                </div>
              </div>
              <div className="flex justify-end">
                <Button size="sm" onClick={handleCatSubmit} disabled={catCreateMutation.isPending || catUpdateMutation.isPending}>
                  {catForm.id ? "保存修改" : "新增分类"}
                </Button>
              </div>
            </div>

            {/* 分类列表 */}
            <div className="border rounded-lg">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>编码</TableHead>
                    <TableHead>名称</TableHead>
                    <TableHead className="w-[80px]">操作</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {categories.length === 0 ? (
                    <TableRow>
                      <TableCell colSpan={3} className="text-center py-4 text-muted-foreground">
                        暂无分类
                      </TableCell>
                    </TableRow>
                  ) : (
                    categories.map((cat) => (
                      <TableRow key={cat.id}>
                        <TableCell className="font-mono text-xs text-muted-foreground">{cat.code || "-"}</TableCell>
                        <TableCell>{cat.name}</TableCell>
                        <TableCell>
                          <div className="flex gap-1">
                            <Button variant="ghost" size="icon" className="h-7 w-7" onClick={() => openCatEdit(cat)}>
                              <Pencil className="h-3 w-3" />
                            </Button>
                            <Button variant="ghost" size="icon" className="h-7 w-7 text-red-500" onClick={() => handleCatDelete(cat.id)}>
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
          </div>
        </DialogContent>
      </Dialog>

      {/* ===== 删除确认 ===== */}
      <Dialog open={!!deleteId} onOpenChange={() => setDeleteId(null)}>
        <DialogContent className="max-w-sm">
          <DialogHeader><DialogTitle>确认删除</DialogTitle></DialogHeader>
          <p className="text-sm text-muted-foreground">确定要删除这条物料吗？此操作不可撤销。</p>
          <DialogFooter>
            <Button variant="outline" onClick={() => setDeleteId(null)}>取消</Button>
            <Button variant="destructive" onClick={handleDeleteConfirm} disabled={deleteMutation.isPending}>删除</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}

export default MaterialManagementPage;
