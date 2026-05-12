import { useState } from "react";
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
import { Badge } from "@/components/ui/badge";
import { toast } from "sonner";
import { Plus, Pencil, Trash2, Search, Tag } from "lucide-react";

interface Brand {
  id: number;
  name: string;
  code: string | null;
  company_id: number | null;
  company_name: string | null;
  is_oem: boolean;
  is_active: boolean;
  notes: string | null;
}

export function BrandsPage() {
  const qc = useQueryClient();
  const [search, setSearch] = useState("");
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editingBrand, setEditingBrand] = useState<Brand | null>(null);
  const [deleteId, setDeleteId] = useState<number | null>(null);

  // 表单
  const [formName, setFormName] = useState("");
  const [formCode, setFormCode] = useState("");
  const [formIsOem, setFormIsOem] = useState(false);
  const [formIsActive, setFormIsActive] = useState(true);
  const [formNotes, setFormNotes] = useState("");

  const { data, isLoading } = useQuery({
    queryKey: ["brands"],
    queryFn: async () => {
      const res = await api.get("/v1/brands/?limit=500");
      return res.data.items as Brand[];
    },
  });

  const brands = data || [];

  const filtered = search.trim()
    ? brands.filter(
        (b) =>
          b.name.toLowerCase().includes(search.toLowerCase()) ||
          (b.code ?? "").toLowerCase().includes(search.toLowerCase())
      )
    : brands;

  const createMutation = useMutation({
    mutationFn: async (payload: any) => {
      const res = await api.post("/v1/brands/", payload);
      return res.data;
    },
  });

  const updateMutation = useMutation({
    mutationFn: async ({ id, payload }: { id: number; payload: any }) => {
      await api.put(`/v1/brands/${id}`, payload);
    },
  });

  const deleteMutation = useMutation({
    mutationFn: (id: number) => api.delete(`/v1/brands/${id}`),
  });

  function resetForm() {
    setFormName("");
    setFormCode("");
    setFormIsOem(false);
    setFormIsActive(true);
    setFormNotes("");
    setEditingBrand(null);
  }

  function openCreate() {
    resetForm();
    setDialogOpen(true);
  }

  function openEdit(b: Brand) {
    setEditingBrand(b);
    setFormName(b.name);
    setFormCode(b.code ?? "");
    setFormIsOem(b.is_oem);
    setFormIsActive(b.is_active);
    setFormNotes(b.notes ?? "");
    setDialogOpen(true);
  }

  async function handleSubmit() {
    if (!formName.trim()) {
      toast.error("品牌名称不能为空");
      return;
    }
    const payload = {
      name: formName.trim(),
      code: formCode.trim() || null,
      is_oem: formIsOem,
      is_active: formIsActive,
      notes: formNotes.trim() || null,
    };
    try {
      if (editingBrand) {
        await updateMutation.mutateAsync({ id: editingBrand.id, payload });
        toast.success("品牌更新成功");
      } else {
        await createMutation.mutateAsync(payload);
        toast.success("品牌创建成功");
      }
      await qc.invalidateQueries({ queryKey: ["brands"] });
      setDialogOpen(false);
      resetForm();
    } catch (err: any) {
      toast.error(err.response?.data?.detail || "操作失败");
    }
  }

  async function handleDelete() {
    if (!deleteId) return;
    try {
      await deleteMutation.mutateAsync(deleteId);
      await qc.invalidateQueries({ queryKey: ["brands"] });
      setDeleteId(null);
      toast.success("品牌已删除");
    } catch (err: any) {
      toast.error(err.response?.data?.detail || "删除失败");
    }
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">品牌管理</h1>
          <p className="text-sm text-muted-foreground">自有品牌 + OEM代工客户品牌</p>
        </div>
        <Button onClick={openCreate}>
          <Plus className="h-4 w-4 mr-1" />
          新增品牌
        </Button>
      </div>

      <div className="flex items-center gap-3">
        <div className="relative flex-1 max-w-sm">
          <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
          <Input
            placeholder="搜索品牌名称或编码..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="pl-9"
          />
        </div>
        <span className="text-sm text-muted-foreground">共 {filtered.length} 个品牌</span>
      </div>

      <div className="border rounded-lg">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>品牌名称</TableHead>
              <TableHead>编码</TableHead>
              <TableHead>类型</TableHead>
              <TableHead>状态</TableHead>
              <TableHead className="w-[120px]">操作</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {isLoading ? (
              <TableRow>
                <TableCell colSpan={5} className="text-center py-8">加载中...</TableCell>
              </TableRow>
            ) : filtered.length === 0 ? (
              <TableRow>
                <TableCell colSpan={5} className="text-center py-8 text-muted-foreground">
                  暂无品牌，点击右上角"新增品牌"创建
                </TableCell>
              </TableRow>
            ) : (
              filtered.map((b) => (
                <TableRow key={b.id} className={!b.is_active ? "opacity-50" : ""}>
                  <TableCell className="font-medium">
                    <div className="flex items-center gap-2">
                      <Tag className="h-4 w-4 text-muted-foreground" />
                      {b.name}
                    </div>
                  </TableCell>
                  <TableCell className="font-mono text-xs text-muted-foreground">{b.code ?? "-"}</TableCell>
                  <TableCell>
                    {b.is_oem ? (
                      <Badge variant="secondary" className="bg-purple-100 text-purple-700">OEM代工</Badge>
                    ) : (
                      <Badge variant="secondary" className="bg-blue-100 text-blue-700">自有品牌</Badge>
                    )}
                  </TableCell>
                  <TableCell>
                    {b.is_active ? (
                      <Badge variant="secondary" className="bg-green-100 text-green-800">启用</Badge>
                    ) : (
                      <Badge variant="secondary" className="bg-gray-100 text-gray-800">停用</Badge>
                    )}
                  </TableCell>
                  <TableCell>
                    <div className="flex gap-1">
                      <Button variant="ghost" size="icon" className="h-8 w-8" onClick={() => openEdit(b)}>
                        <Pencil className="h-4 w-4" />
                      </Button>
                      <Button variant="ghost" size="icon" className="h-8 w-8 text-red-500" onClick={() => setDeleteId(b.id)}>
                        <Trash2 className="h-4 w-4" />
                      </Button>
                    </div>
                  </TableCell>
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </div>

      {/* 新增/编辑弹窗 */}
      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <DialogContent className="max-w-lg">
          <DialogHeader>
            <DialogTitle>{editingBrand ? "编辑品牌" : "新增品牌"}</DialogTitle>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label>品牌名称 <span className="text-red-500">*</span></Label>
                <Input value={formName} onChange={(e) => setFormName(e.target.value)} placeholder="如：林深见鹿" />
              </div>
              <div className="space-y-2">
                <Label>品牌编码</Label>
                <Input value={formCode} onChange={(e) => setFormCode(e.target.value)} placeholder="如：LL" />
              </div>
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label>类型</Label>
                <div className="flex items-center gap-3 h-10">
                  <label className="flex items-center gap-2 text-sm cursor-pointer">
                    <input type="radio" name="brand_type" checked={!formIsOem} onChange={() => setFormIsOem(false)} className="h-4 w-4" />
                    自有品牌
                  </label>
                  <label className="flex items-center gap-2 text-sm cursor-pointer">
                    <input type="radio" name="brand_type" checked={formIsOem} onChange={() => setFormIsOem(true)} className="h-4 w-4" />
                    OEM代工
                  </label>
                </div>
              </div>
              <div className="space-y-2">
                <Label>状态</Label>
                <div className="flex items-center gap-3 h-10">
                  <label className="flex items-center gap-2 text-sm cursor-pointer">
                    <input type="radio" name="brand_status" checked={formIsActive} onChange={() => setFormIsActive(true)} className="h-4 w-4" />
                    启用
                  </label>
                  <label className="flex items-center gap-2 text-sm cursor-pointer">
                    <input type="radio" name="brand_status" checked={!formIsActive} onChange={() => setFormIsActive(false)} className="h-4 w-4" />
                    停用
                  </label>
                </div>
              </div>
            </div>
            <div className="space-y-2">
              <Label>备注</Label>
              <Input value={formNotes} onChange={(e) => setFormNotes(e.target.value)} placeholder="可选" />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setDialogOpen(false)}>取消</Button>
            <Button onClick={handleSubmit}>{editingBrand ? "保存修改" : "创建品牌"}</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* 删除确认 */}
      <Dialog open={!!deleteId} onOpenChange={() => setDeleteId(null)}>
        <DialogContent className="max-w-sm">
          <DialogHeader><DialogTitle>确认删除</DialogTitle></DialogHeader>
          <p className="text-sm text-muted-foreground">确定要删除这个品牌吗？已关联产品的品牌字段会被清空。</p>
          <DialogFooter>
            <Button variant="outline" onClick={() => setDeleteId(null)}>取消</Button>
            <Button variant="destructive" onClick={handleDelete}>删除</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
