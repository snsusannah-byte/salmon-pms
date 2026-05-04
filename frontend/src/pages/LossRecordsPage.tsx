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
import { Card, CardContent } from "@/components/ui/card";
import {
  Plus, Search, Pencil, Trash2, AlertTriangle, TrendingDown, ClipboardList, Calendar,
} from "lucide-react";
import { toast } from "sonner";

// ==================== 类型 ====================
interface LossRecord {
  id: number;
  loss_date: string;
  loss_type: "spoilage" | "inventory_diff" | "expired" | "other";
  slaughter_date: string | null;
  product_id: number | null;
  product_name: string | null;
  weight_kg: number;
  quantity: number;
  reason: string;
  notes: string;
}

interface LossForm {
  loss_date: string;
  loss_type: "spoilage" | "inventory_diff" | "expired" | "other";
  slaughter_date: string;
  product_id: string;
  weight_kg: number;
  quantity: number;
  reason: string;
  notes: string;
}

interface SlaughterDateOption {
  date: string;
  available_meat_kg: number;
}

interface ProductOption {
  id: number;
  name: string;
}

const lossTypeMap: Record<string, { label: string; color: string }> = {
  spoilage: { label: "变质报废", color: "bg-red-100 text-red-800" },
  inventory_diff: { label: "盘点差异", color: "bg-orange-100 text-orange-800" },
  expired: { label: "过期处理", color: "bg-gray-100 text-gray-800" },
  other: { label: "其他", color: "bg-blue-100 text-blue-800" },
};

const lossTypeOptions = [
  { value: "spoilage", label: "变质报废" },
  { value: "inventory_diff", label: "盘点差异" },
  { value: "expired", label: "过期处理" },
  { value: "other", label: "其他" },
];

// ==================== API ====================
const lossApi = {
  list: async (params: Record<string, any>) => {
    const { data } = await api.get("/v1/loss-records/", { params });
    return data;
  },
  create: async (body: any) => {
    const { data } = await api.post("/v1/loss-records/", body);
    return data;
  },
  update: async (id: number, body: any) => {
    const { data } = await api.put(`/v1/loss-records/${id}`, body);
    return data;
  },
  delete: async (id: number) => {
    const { data } = await api.delete(`/v1/loss-records/${id}`);
    return data;
  },
  slaughterDates: async () => {
    const { data } = await api.get("/v1/daily-slaughter/options/slaughter-dates");
    return data;
  },
  products: async () => {
    const { data } = await api.get("/v1/products");
    return data;
  },
};

function fmtWeight(v: number) {
  return `${v.toFixed(3)} kg`;
}

const defaultForm: LossForm = {
  loss_date: new Date().toISOString().split("T")[0],
  loss_type: "spoilage",
  slaughter_date: "",
  product_id: "",
  weight_kg: 0,
  quantity: 0,
  reason: "",
  notes: "",
};

export function LossRecordsPage() {
  const qc = useQueryClient();
  const [search, setSearch] = useState("");
  const [typeFilter, setTypeFilter] = useState("all");
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [form, setForm] = useState<LossForm>({ ...defaultForm });
  const [deleteId, setDeleteId] = useState<number | null>(null);

  const { data, isLoading } = useQuery({
    queryKey: ["loss-records", typeFilter],
    queryFn: () => lossApi.list({ loss_type: typeFilter === "all" ? "" : typeFilter, limit: 100 }),
  });

  const { data: slaughterDatesData } = useQuery({
    queryKey: ["slaughter-dates"],
    queryFn: lossApi.slaughterDates,
  });

  const { data: productsData } = useQuery({
    queryKey: ["products-loss"],
    queryFn: lossApi.products,
  });

  const records: LossRecord[] = data?.items || [];
  const slaughterDates: SlaughterDateOption[] = slaughterDatesData || [];
  const products: ProductOption[] = productsData?.items || productsData || [];

  // 统计
  const stats = useMemo(() => {
    const now = new Date();
    const thisMonth = records.filter((r) => {
      const d = new Date(r.loss_date);
      return d.getFullYear() === now.getFullYear() && d.getMonth() === now.getMonth();
    });
    return {
      totalWeight: thisMonth.reduce((s, r) => s + r.weight_kg, 0),
      spoilage: thisMonth.filter((r) => r.loss_type === "spoilage").reduce((s, r) => s + r.weight_kg, 0),
      inventoryDiff: thisMonth.filter((r) => r.loss_type === "inventory_diff").reduce((s, r) => s + r.weight_kg, 0),
      expired: thisMonth.filter((r) => r.loss_type === "expired").reduce((s, r) => s + r.weight_kg, 0),
    };
  }, [records]);

  const createMutation = useMutation({
    mutationFn: lossApi.create,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["loss-records"] });
      setDialogOpen(false);
      setForm({ ...defaultForm });
      toast.success("创建成功");
    },
    onError: (err: any) => toast.error(err.response?.data?.detail || "创建失败"),
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, body }: { id: number; body: any }) => lossApi.update(id, body),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["loss-records"] });
      setDialogOpen(false);
      setEditingId(null);
      setForm({ ...defaultForm });
      toast.success("更新成功");
    },
    onError: (err: any) => toast.error(err.response?.data?.detail || "更新失败"),
  });

  const deleteMutation = useMutation({
    mutationFn: lossApi.delete,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["loss-records"] });
      setDeleteId(null);
      toast.success("删除成功");
    },
    onError: (err: any) => toast.error(err.response?.data?.detail || "删除失败"),
  });

  function handleSave() {
    const body = {
      ...form,
      slaughter_date: form.slaughter_date || null,
      product_id: form.product_id ? Number(form.product_id) : null,
    };
    if (editingId) {
      updateMutation.mutate({ id: editingId, body });
    } else {
      createMutation.mutate(body);
    }
  }

  function handleEdit(r: LossRecord) {
    setEditingId(r.id);
    setForm({
      loss_date: r.loss_date,
      loss_type: r.loss_type,
      slaughter_date: r.slaughter_date || "",
      product_id: r.product_id ? String(r.product_id) : "",
      weight_kg: r.weight_kg,
      quantity: r.quantity,
      reason: r.reason,
      notes: r.notes,
    });
    setDialogOpen(true);
  }

  function handleNew() {
    setEditingId(null);
    setForm({ ...defaultForm });
    setDialogOpen(true);
  }

  const filteredRecords = records.filter((r) => {
    if (search) {
      return r.loss_date.includes(search) || r.reason?.includes(search) || r.product_name?.includes(search);
    }
    return true;
  });

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">损耗处理</h1>
        <p className="text-sm text-muted-foreground">变质报废、盘点差异、过期处理登记</p>
      </div>

      {/* 统计卡片 */}
      <div className="grid grid-cols-4 gap-4">
        <Card><CardContent className="p-4">
          <div className="flex items-center justify-between">
            <div className="space-y-1"><p className="text-sm text-muted-foreground">本月损耗重量</p><p className="text-2xl font-bold">{fmtWeight(stats.totalWeight)}</p></div>
            <div className="p-3 bg-red-100 rounded-full"><TrendingDown className="h-5 w-5 text-red-600" /></div>
          </div>
        </CardContent></Card>
        <Card><CardContent className="p-4">
          <div className="flex items-center justify-between">
            <div className="space-y-1"><p className="text-sm text-muted-foreground">变质报废</p><p className="text-2xl font-bold">{fmtWeight(stats.spoilage)}</p></div>
            <div className="p-3 bg-orange-100 rounded-full"><AlertTriangle className="h-5 w-5 text-orange-600" /></div>
          </div>
        </CardContent></Card>
        <Card><CardContent className="p-4">
          <div className="flex items-center justify-between">
            <div className="space-y-1"><p className="text-sm text-muted-foreground">盘点差异</p><p className="text-2xl font-bold">{fmtWeight(stats.inventoryDiff)}</p></div>
            <div className="p-3 bg-amber-100 rounded-full"><ClipboardList className="h-5 w-5 text-amber-600" /></div>
          </div>
        </CardContent></Card>
        <Card><CardContent className="p-4">
          <div className="flex items-center justify-between">
            <div className="space-y-1"><p className="text-sm text-muted-foreground">过期处理</p><p className="text-2xl font-bold">{fmtWeight(stats.expired)}</p></div>
            <div className="p-3 bg-gray-100 rounded-full"><Calendar className="h-5 w-5 text-gray-600" /></div>
          </div>
        </CardContent></Card>
      </div>

      {/* 工具栏 */}
      <div className="flex items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <div className="relative">
            <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
            <Input placeholder="搜索日期、原因或产品..." className="pl-9 w-72" value={search} onChange={(e) => setSearch(e.target.value)} />
          </div>
          <Select value={typeFilter} onValueChange={(v) => setTypeFilter(v ?? "")}>
            <SelectTrigger className="w-40"><SelectValue placeholder="损耗类型" /></SelectTrigger>
            <SelectContent>
              <SelectItem value="all">全部类型</SelectItem>
              {lossTypeOptions.map((o) => (<SelectItem key={o.value} value={o.value}>{o.label}</SelectItem>))}
            </SelectContent>
          </Select>
        </div>
        <Button onClick={handleNew}><Plus className="h-4 w-4 mr-1" />登记损耗</Button>
      </div>

      {/* 表格 */}
      <div className="border rounded-md">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>日期</TableHead>
              <TableHead>类型</TableHead>
              <TableHead>关联宰杀日</TableHead>
              <TableHead>产品</TableHead>
              <TableHead className="text-right">重量(kg)</TableHead>
              <TableHead className="text-right">数量</TableHead>
              <TableHead>原因</TableHead>
              <TableHead className="w-[100px]">操作</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {isLoading ? (
              <TableRow><TableCell colSpan={8} className="text-center py-8">加载中...</TableCell></TableRow>
            ) : filteredRecords.length === 0 ? (
              <TableRow><TableCell colSpan={8} className="text-center py-8 text-muted-foreground">暂无记录</TableCell></TableRow>
            ) : filteredRecords.map((r) => {
              const typeInfo = lossTypeMap[r.loss_type] || lossTypeMap.other;
              return (
                <TableRow key={r.id}>
                  <TableCell className="font-medium">{r.loss_date}</TableCell>
                  <TableCell><Badge className={cn(typeInfo.color)}>{typeInfo.label}</Badge></TableCell>
                  <TableCell className="text-sm text-muted-foreground">{r.slaughter_date || "-"}</TableCell>
                  <TableCell className="text-sm">{r.product_name || "-"}</TableCell>
                  <TableCell className="text-right">{r.weight_kg.toFixed(3)}</TableCell>
                  <TableCell className="text-right">{r.quantity || "-"}</TableCell>
                  <TableCell className="text-sm max-w-[200px] truncate">{r.reason}</TableCell>
                  <TableCell>
                    <div className="flex items-center gap-1">
                      <Button variant="ghost" size="icon" className="h-8 w-8" onClick={() => handleEdit(r)}><Pencil className="h-4 w-4" /></Button>
                      <Button variant="ghost" size="icon" className="h-8 w-8" onClick={() => setDeleteId(r.id)}><Trash2 className="h-4 w-4" /></Button>
                    </div>
                  </TableCell>
                </TableRow>
              );
            })}
          </TableBody>
        </Table>
      </div>

      {/* 新建/编辑弹窗 */}
      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <DialogContent className="max-w-lg">
          <DialogHeader><DialogTitle>{editingId ? "编辑损耗记录" : "登记损耗"}</DialogTitle></DialogHeader>
          <div className="space-y-4 py-4">
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2"><Label>损耗日期</Label><Input type="date" value={form.loss_date} onChange={(e) => setForm({ ...form, loss_date: e.target.value })} /></div>
              <div className="space-y-2"><Label>损耗类型</Label>
                <Select value={form.loss_type} onValueChange={(v: any) => setForm({ ...form, loss_type: v })}>
                  <SelectTrigger><SelectValue /></SelectTrigger>
                  <SelectContent>
                    {lossTypeOptions.map((o) => (<SelectItem key={o.value} value={o.value}>{o.label}</SelectItem>))}
                  </SelectContent>
                </Select>
              </div>
            </div>

            <div className="space-y-2">
              <Label>关联宰杀日期（可选）</Label>
              <Select value={form.slaughter_date} onValueChange={(v) => setForm({ ...form, slaughter_date: v ?? "" })}>
                <SelectTrigger><SelectValue placeholder="选择宰杀日期" /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="">不关联</SelectItem>
                  {slaughterDates.map((sd) => (
                    <SelectItem key={sd.date} value={sd.date}>{sd.date} (可用{sd.available_meat_kg.toFixed(1)}kg)</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-2">
              <Label>关联产品（可选）</Label>
              <Select value={form.product_id} onValueChange={(v) => setForm({ ...form, product_id: v ?? "" })}>
                <SelectTrigger><SelectValue placeholder="选择产品" /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="">不关联</SelectItem>
                  {products.map((p) => (<SelectItem key={p.id} value={String(p.id)}>{p.name}</SelectItem>))}
                </SelectContent>
              </Select>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2"><Label>重量(kg)</Label><Input type="number" step="0.001" value={form.weight_kg} onChange={(e) => setForm({ ...form, weight_kg: Number(e.target.value) })} /></div>
              <div className="space-y-2"><Label>数量</Label><Input type="number" value={form.quantity} onChange={(e) => setForm({ ...form, quantity: Number(e.target.value) })} /></div>
            </div>

            <div className="space-y-2"><Label>原因</Label>
              <textarea
                className="flex min-h-[60px] w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
                value={form.reason}
                onChange={(e) => setForm({ ...form, reason: e.target.value })}
                placeholder="填写损耗原因..."
              />
            </div>

            <div className="space-y-2"><Label>备注</Label>
              <textarea
                className="flex min-h-[60px] w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
                value={form.notes}
                onChange={(e) => setForm({ ...form, notes: e.target.value })}
              />
            </div>

            <div className="bg-blue-50 border border-blue-200 rounded-md p-3 text-xs text-blue-700">
              <p>💡 提示：如果填写了宰杀日期，将扣减对应日期的可用肉；如果填写了产品，将扣减对应产品的仓库库存。</p>
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setDialogOpen(false)}>取消</Button>
            <Button onClick={handleSave} disabled={createMutation.isPending || updateMutation.isPending}>
              {(createMutation.isPending || updateMutation.isPending) ? "保存中..." : "保存"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* 删除确认 */}
      <Dialog open={!!deleteId} onOpenChange={() => setDeleteId(null)}>
        <DialogContent className="max-w-sm">
          <DialogHeader><DialogTitle>确认删除</DialogTitle></DialogHeader>
          <p className="text-sm text-muted-foreground">确定删除这条损耗记录吗？</p>
          <DialogFooter>
            <Button variant="outline" onClick={() => setDeleteId(null)}>取消</Button>
            <Button variant="destructive" onClick={() => deleteId && deleteMutation.mutate(deleteId)} disabled={deleteMutation.isPending}>删除</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
