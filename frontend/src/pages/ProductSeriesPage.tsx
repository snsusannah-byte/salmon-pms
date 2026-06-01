import { useState, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "@/components/ui/dialog";
import { Plus, Search, Pencil, Trash2, Loader2 } from "lucide-react";
import { toast } from "sonner";
import { apiFetch, apiPost } from "@/lib/api";

interface ProductSeries {
  id: number;
  code: string;
  name: string;
  sort_order: number;
  is_active: boolean;
  notes: string | null;
}

export function ProductSeriesPage() {
  const [series, setSeries] = useState<ProductSeries[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editing, setEditing] = useState<ProductSeries | null>(null);
  const [form, setForm] = useState({ code: "", name: "", sort_order: 0, notes: "" });
  const [submitting, setSubmitting] = useState(false);

  const fetchSeries = async () => {
    setLoading(true);
    const res = await apiFetch("/v1/finished-products/series");
    if (res.ok && Array.isArray(res.data)) {
      setSeries(res.data);
    }
    setLoading(false);
  };

  useEffect(() => {
    fetchSeries();
  }, []);

  const filtered = series.filter(
    (s) =>
      s.code.toLowerCase().includes(search.toLowerCase()) ||
      s.name.includes(search)
  );

  const openCreate = () => {
    setEditing(null);
    setForm({ code: "", name: "", sort_order: 0, notes: "" });
    setDialogOpen(true);
  };

  const openEdit = (item: ProductSeries) => {
    setEditing(item);
    setForm({
      code: item.code,
      name: item.name,
      sort_order: item.sort_order,
      notes: item.notes || "",
    });
    setDialogOpen(true);
  };

  const handleSubmit = async () => {
    setSubmitting(true);
    let res;
    if (editing) {
      res = await apiFetch(`/v1/finished-products/series/${editing.id}`, {
        method: "PUT", body: JSON.stringify({
          ...form,
          sort_order: Number(form.sort_order)
        })
      }, "更新成功");
    } else {
      res = await apiPost("/v1/finished-products/series", {
        ...form,
        sort_order: Number(form.sort_order)
      }, "创建成功");
    }
    setSubmitting(false);
    if (res.ok) {
      setDialogOpen(false);
      fetchSeries();
    }
  };

  const handleDelete = async (item: ProductSeries) => {
    if (!confirm(`确认删除系列 ${item.code} - ${item.name}？`)) return;
    const res = await apiFetch(`/v1/finished-products/series/${item.id}`, { method: "DELETE" }, "删除成功");
    if (res.ok) fetchSeries();
  };

  return (
    <div className="h-full flex flex-col gap-4 p-4">
      {/* 功能区 */}
      <div className="flex-none space-y-3">
        <div className="flex items-center justify-between">
          <h2 className="text-xl font-bold">产品系列</h2>
          <Button onClick={openCreate}>
            <Plus className="h-4 w-4 mr-1" />
            新建系列
          </Button>
        </div>
        <div className="flex items-center gap-2">
          <Search className="h-4 w-4 text-muted-foreground" />
          <Input
            placeholder="搜索编码或名称..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="max-w-sm"
          />
        </div>
      </div>

      {/* 列表区 */}
      <div className="flex-1 flex flex-col min-h-0 border rounded-lg overflow-hidden">
        <div className="flex-1 overflow-auto">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead className="sticky top-0 bg-background z-10">编码</TableHead>
                <TableHead className="sticky top-0 bg-background z-10">名称</TableHead>
                <TableHead className="sticky top-0 bg-background z-10">排序</TableHead>
                <TableHead className="sticky top-0 bg-background z-10">状态</TableHead>
                <TableHead className="sticky top-0 bg-background z-10">备注</TableHead>
                <TableHead className="sticky top-0 bg-background z-10 text-right">操作</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {loading ? (
                <TableRow>
                  <TableCell colSpan={6} className="text-center py-8">
                    <Loader2 className="h-5 w-5 animate-spin mx-auto" />
                  </TableCell>
                </TableRow>
              ) : filtered.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={6} className="text-center py-8 text-muted-foreground">
                    暂无数据
                  </TableCell>
                </TableRow>
              ) : (
                filtered.map((s) => (
                  <TableRow key={s.id}>
                    <TableCell className="font-medium">{s.code}</TableCell>
                    <TableCell>{s.name}</TableCell>
                    <TableCell>{s.sort_order}</TableCell>
                    <TableCell>
                      <Badge variant={s.is_active ? "default" : "secondary"}>
                        {s.is_active ? "启用" : "停用"}
                      </Badge>
                    </TableCell>
                    <TableCell className="text-muted-foreground text-sm">{s.notes}</TableCell>
                    <TableCell className="text-right space-x-1">
                      <Button variant="ghost" size="icon" onClick={() => openEdit(s)}>
                        <Pencil className="h-4 w-4" />
                      </Button>
                      <Button variant="ghost" size="icon" onClick={() => handleDelete(s)}>
                        <Trash2 className="h-4 w-4 text-destructive" />
                      </Button>
                    </TableCell>
                  </TableRow>
                ))
              )}
            </TableBody>
          </Table>
        </div>
        <div className="flex-none px-4 py-2 border-t bg-muted/30 text-sm text-muted-foreground">
          共 {filtered.length} 条
        </div>
      </div>

      {/* 弹窗 */}
      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{editing ? "编辑系列" : "新建系列"}</DialogTitle>
          </DialogHeader>
          <div className="space-y-4 py-2">
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <label className="text-sm font-medium">编码</label>
                <Input
                  value={form.code}
                  onChange={(e) => setForm({ ...form, code: e.target.value })}
                  placeholder="如 CX"
                  disabled={!!editing}
                />
              </div>
              <div className="space-y-2">
                <label className="text-sm font-medium">排序</label>
                <Input
                  type="number"
                  value={form.sort_order}
                  onChange={(e) => setForm({ ...form, sort_order: Number(e.target.value) })}
                />
              </div>
            </div>
            <div className="space-y-2">
              <label className="text-sm font-medium">名称</label>
              <Input
                value={form.name}
                onChange={(e) => setForm({ ...form, name: e.target.value })}
                placeholder="如 纯享装"
              />
            </div>
            <div className="space-y-2">
              <label className="text-sm font-medium">备注</label>
              <Input
                value={form.notes}
                onChange={(e) => setForm({ ...form, notes: e.target.value })}
                placeholder="场景描述..."
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setDialogOpen(false)}>
              取消
            </Button>
            <Button onClick={handleSubmit} disabled={submitting || !form.code || !form.name}>
              {submitting && <Loader2 className="h-4 w-4 mr-1 animate-spin" />}
              {editing ? "保存" : "创建"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
