import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
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
import { Badge } from "@/components/ui/badge";
import { Plus, Search, Pencil, Trash2, UserCog } from "lucide-react";
import { toast } from "sonner";

interface Salesperson {
  id: number;
  name: string;
  phone: string | null;
  email: string | null;
  commission_rate: number; // 提成比例 %
  is_active: boolean;
  notes: string | null;
  created_at: string;
}

export function SalespersonPage() {
  const queryClient = useQueryClient();
  const [search, setSearch] = useState("");
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editing, setEditing] = useState<Salesperson | null>(null);
  const [deleteTarget, setDeleteTarget] = useState<Salesperson | null>(null);

  const [formName, setFormName] = useState("");
  const [formPhone, setFormPhone] = useState("");
  const [formEmail, setFormEmail] = useState("");
  const [formRate, setFormRate] = useState("");
  const [formNotes, setFormNotes] = useState("");

  const { data, isLoading } = useQuery({
    queryKey: ["salespersons", search],
    queryFn: async () => {
      const params = new URLSearchParams();
      if (search) params.set("search", search);
      const res = await api.get(`/v1/salespersons/?${params.toString()}`);
      return res.data as { total: number; items: Salesperson[] };
    },
  });

  const createMutation = useMutation({
    mutationFn: (payload: any) => api.post("/v1/salespersons/", payload),
    onSuccess: () => {
      toast.success("业务员创建成功");
      queryClient.invalidateQueries({ queryKey: ["salespersons"] });
      setDialogOpen(false);
      resetForm();
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.detail ?? "创建失败");
    },
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, payload }: { id: number; payload: any }) =>
      api.put(`/v1/salespersons/${id}`, payload),
    onSuccess: () => {
      toast.success("业务员更新成功");
      queryClient.invalidateQueries({ queryKey: ["salespersons"] });
      setDialogOpen(false);
      resetForm();
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.detail ?? "更新失败");
    },
  });

  const deleteMutation = useMutation({
    mutationFn: (id: number) => api.delete(`/v1/salespersons/${id}`),
    onSuccess: () => {
      toast.success("已删除");
      queryClient.invalidateQueries({ queryKey: ["salespersons"] });
      setDeleteTarget(null);
    },
  });

  const resetForm = () => {
    setFormName("");
    setFormPhone("");
    setFormEmail("");
    setFormRate("");
    setFormNotes("");
    setEditing(null);
  };

  const openCreate = () => {
    resetForm();
    setDialogOpen(true);
  };

  const openEdit = (sp: Salesperson) => {
    setEditing(sp);
    setFormName(sp.name);
    setFormPhone(sp.phone ?? "");
    setFormEmail(sp.email ?? "");
    setFormRate(String(sp.commission_rate));
    setFormNotes(sp.notes ?? "");
    setDialogOpen(true);
  };

  const handleSubmit = () => {
    if (!formName.trim()) {
      toast.error("名称不能为空");
      return;
    }
    const payload = {
      name: formName,
      phone: formPhone || null,
      email: formEmail || null,
      commission_rate: formRate ? parseFloat(formRate) : 0,
      is_active: true,
      notes: formNotes || null,
    };
    if (editing) {
      updateMutation.mutate({ id: editing.id, payload });
    } else {
      createMutation.mutate(payload);
    }
  };

  return (
    <div className="space-y-6">
      {/* 标题 */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">业务员管理</h1>
          <p className="text-sm text-muted-foreground">
            共 {data?.total ?? 0} 人
          </p>
        </div>
        <Button onClick={openCreate}>
          <Plus className="h-4 w-4 mr-2" />
          新增业务员
        </Button>
      </div>

      {/* 搜索 */}
      <div className="relative max-w-sm">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
        <Input
          placeholder="搜索名称..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="pl-9"
        />
      </div>

      {/* 表格 */}
      <div className="border rounded-lg">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>姓名</TableHead>
              <TableHead>电话</TableHead>
              <TableHead>邮箱</TableHead>
              <TableHead>提成比例</TableHead>
              <TableHead>状态</TableHead>
              <TableHead>备注</TableHead>
              <TableHead className="w-[120px]">操作</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {isLoading ? (
              <TableRow>
                <TableCell colSpan={7} className="text-center py-8">
                  加载中...
                </TableCell>
              </TableRow>
            ) : (data?.items?.length ?? 0) === 0 ? (
              <TableRow>
                <TableCell colSpan={7} className="text-center py-8 text-muted-foreground">
                  暂无业务员
                </TableCell>
              </TableRow>
            ) : (
              data?.items.map((sp) => (
                <TableRow key={sp.id}>
                  <TableCell className="font-medium">
                    <div className="flex items-center gap-2">
                      <UserCog className="h-4 w-4 text-blue-500" />
                      {sp.name}
                    </div>
                  </TableCell>
                  <TableCell className="text-sm">{sp.phone ?? "-"}</TableCell>
                  <TableCell className="text-sm">{sp.email ?? "-"}</TableCell>
                  <TableCell className="text-sm font-medium">{sp.commission_rate}%</TableCell>
                  <TableCell>
                    {sp.is_active ? (
                      <Badge variant="secondary" className="bg-green-100 text-green-800">在职</Badge>
                    ) : (
                      <Badge variant="secondary" className="bg-gray-100 text-gray-800">停用</Badge>
                    )}
                  </TableCell>
                  <TableCell className="text-sm text-muted-foreground">{sp.notes ?? "-"}</TableCell>
                  <TableCell>
                    <div className="flex gap-1">
                      <Button variant="ghost" size="icon" className="h-8 w-8" onClick={() => openEdit(sp)}>
                        <Pencil className="h-4 w-4" />
                      </Button>
                      <Button variant="ghost" size="icon" className="h-8 w-8 text-red-500" onClick={() => setDeleteTarget(sp)}>
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

      {/* 弹窗 */}
      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle>{editing ? "编辑业务员" : "新增业务员"}</DialogTitle>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <Label>姓名 *</Label>
              <Input value={formName} onChange={(e) => setFormName(e.target.value)} placeholder="业务员姓名" />
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label>电话</Label>
                <Input value={formPhone} onChange={(e) => setFormPhone(e.target.value)} placeholder="联系电话" />
              </div>
              <div className="space-y-2">
                <Label>邮箱</Label>
                <Input value={formEmail} onChange={(e) => setFormEmail(e.target.value)} placeholder="邮箱" />
              </div>
            </div>
            <div className="space-y-2">
              <Label>默认提成比例 (%)</Label>
              <Input type="number" step="0.01" value={formRate} onChange={(e) => setFormRate(e.target.value)} placeholder="如: 2.5" />
            </div>
            <div className="space-y-2">
              <Label>备注</Label>
              <Input value={formNotes} onChange={(e) => setFormNotes(e.target.value)} placeholder="其他说明..." />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setDialogOpen(false)}>取消</Button>
            <Button onClick={handleSubmit}>{editing ? "保存" : "创建"}</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* 删除确认 */}
      <Dialog open={!!deleteTarget} onOpenChange={() => setDeleteTarget(null)}>
        <DialogContent className="max-w-sm">
          <DialogHeader>
            <DialogTitle>确认删除</DialogTitle>
          </DialogHeader>
          <p className="py-4">确定删除业务员「{deleteTarget?.name}」吗？</p>
          <DialogFooter>
            <Button variant="outline" onClick={() => setDeleteTarget(null)}>取消</Button>
            <Button variant="destructive" onClick={() => deleteTarget && deleteMutation.mutate(deleteTarget.id)}>
              删除
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
