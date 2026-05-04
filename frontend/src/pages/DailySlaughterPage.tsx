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
  Plus, Search, Pencil, Trash2, Lock, Unlock, AlertTriangle,
  Fish, FileBarChart, TrendingUp, Scale,
  Calendar, List,
  ChevronLeft, ChevronRight,
} from "lucide-react";
import { toast } from "sonner";

// ==================== 类型 ====================
interface SlaughterRecord {
  id: number;
  slaughter_date: string;
  slaughter_type: "whole_fish" | "fillet";
  fish_count: number;
  total_weight_kg: number;
  meat_weight_kg: number;
  byproduct_head_count: number;
  byproduct_tail_count: number;
  byproduct_bone_count: number;
  byproduct_trim_weight_kg: number;
  loss_weight_kg: number;
  cost_price_per_kg: number;
  available_meat_kg: number;
  is_locked: boolean;
  notes: string;
  created_at: string;
}

interface SlaughterForm {
  slaughter_date: string;
  slaughter_type: "whole_fish" | "fillet";
  fish_count: number;
  total_weight_kg: number;
  meat_weight_kg: number;
  byproduct_head_count: number;
  byproduct_tail_count: number;
  byproduct_bone_count: number;
  byproduct_trim_weight_kg: number;
  loss_weight_kg: number;
  cost_price_per_kg: number;
  notes: string;
}

const defaultForm: SlaughterForm = {
  slaughter_date: new Date().toISOString().split("T")[0],
  slaughter_type: "whole_fish",
  fish_count: 0,
  total_weight_kg: 0,
  meat_weight_kg: 0,
  byproduct_head_count: 0,
  byproduct_tail_count: 0,
  byproduct_bone_count: 0,
  byproduct_trim_weight_kg: 0,
  loss_weight_kg: 0,
  cost_price_per_kg: 0,
  notes: "",
};

// ==================== API ====================
const slaughterApi = {
  list: async (params: Record<string, any>) => {
    const { data } = await api.get("/v1/daily-slaughter/", { params });
    return data;
  },
  create: async (body: SlaughterForm) => {
    const { data } = await api.post("/v1/daily-slaughter/", body);
    return data;
  },
  update: async (id: number, body: SlaughterForm) => {
    const { data } = await api.put(`/v1/daily-slaughter/${id}`, body);
    return data;
  },
  delete: async (id: number) => {
    const { data } = await api.delete(`/v1/daily-slaughter/${id}`);
    return data;
  },
  lock: async (id: number) => {
    const { data } = await api.post(`/v1/daily-slaughter/${id}/lock`);
    return data;
  },
};

// ==================== 工具 ====================
function fmtPct(v: number) {
  return `${v.toFixed(1)}%`;
}
function fmtWeight(v: number) {
  return `${v.toFixed(3)}`;
}
function fmtMoney(v: number) {
  return `¥${v.toFixed(2)}`;
}

// ==================== 日历组件 ====================
function SlaughterCalendar({
  records,
  currentMonth,
  onMonthChange,
  onDayClick,
}: {
  records: SlaughterRecord[];
  currentMonth: Date;
  onMonthChange: (d: Date) => void;
  onDayClick: (dateStr: string) => void;
}) {
  const year = currentMonth.getFullYear();
  const month = currentMonth.getMonth();

  // 第一天是星期几
  const firstDayOfMonth = new Date(year, month, 1).getDay();
  // 当月天数
  const daysInMonth = new Date(year, month + 1, 0).getDate();
  // 上月天数（用于填充）
  const daysInPrevMonth = new Date(year, month, 0).getDate();

  const calendarDays: Array<{
    day: number;
    isCurrentMonth: boolean;
    isToday: boolean;
    record?: SlaughterRecord;
  }> = [];

  // 填充上月末尾
  for (let i = firstDayOfMonth - 1; i >= 0; i--) {
    calendarDays.push({
      day: daysInPrevMonth - i,
      isCurrentMonth: false,
      isToday: false,
    });
  }

  // 当月
  const todayStr = new Date().toISOString().split("T")[0];
  for (let day = 1; day <= daysInMonth; day++) {
    const dateStr = `${year}-${String(month + 1).padStart(2, "0")}-${String(day).padStart(2, "0")}`;
    const record = records.find((r) => r.slaughter_date === dateStr);
    calendarDays.push({
      day,
      isCurrentMonth: true,
      isToday: dateStr === todayStr,
      record,
    });
  }

  // 填充下月开头（凑满6行×7列=42个格子，或者至少5行）
  const remaining = 42 - calendarDays.length;
  for (let day = 1; day <= remaining; day++) {
    calendarDays.push({
      day,
      isCurrentMonth: false,
      isToday: false,
    });
  }

  const weekDays = ["日", "一", "二", "三", "四", "五", "六"];

  return (
    <div className="space-y-4">
      {/* 月份导航 */}
      <div className="flex items-center justify-between">
        <Button variant="outline" size="sm" onClick={() => onMonthChange(new Date(year, month - 1, 1))}>
          <ChevronLeft className="h-4 w-4" />
        </Button>
        <h3 className="text-lg font-bold">
          {year}年{month + 1}月
        </h3>
        <Button variant="outline" size="sm" onClick={() => onMonthChange(new Date(year, month + 1, 1))}>
          <ChevronRight className="h-4 w-4" />
        </Button>
      </div>

      {/* 星期标题 */}
      <div className="grid grid-cols-7 gap-1">
        {weekDays.map((d) => (
          <div key={d} className="text-center text-sm font-medium text-muted-foreground py-2">
            {d}
          </div>
        ))}
      </div>

      {/* 日期格子 */}
      <div className="grid grid-cols-7 gap-1">
        {calendarDays.map((item, idx) => {
          const dateStr = item.isCurrentMonth
            ? `${year}-${String(month + 1).padStart(2, "0")}-${String(item.day).padStart(2, "0")}`
            : "";

          return (
            <div
              key={idx}
              className={cn(
                "min-h-[100px] border rounded-md p-2 cursor-pointer transition-colors hover:bg-muted/50",
                !item.isCurrentMonth && "bg-gray-50/50 text-muted-foreground/50",
                item.isToday && "border-blue-400 bg-blue-50/50",
                item.record && "border-green-300 bg-green-50/30 hover:bg-green-50/60"
              )}
              onClick={() => item.isCurrentMonth && onDayClick(dateStr)}
            >
              <div className="flex items-center justify-between mb-1">
                <span className={cn(
                  "text-sm font-medium",
                  item.isToday && "text-blue-600",
                  !item.isCurrentMonth && "text-muted-foreground/50"
                )}>
                  {item.day}
                </span>
                {item.record?.is_locked && (
                  <Lock className="h-3 w-3 text-green-600" />
                )}
              </div>

              {item.record && (
                <div className="space-y-1">
                  <div className="flex items-center gap-1 text-xs">
                    <Fish className="h-3 w-3 text-blue-500" />
                    <span className="font-medium">{item.record.fish_count}条</span>
                  </div>
                  <div className="text-xs text-muted-foreground">
                    {fmtWeight(item.record.meat_weight_kg)}kg肉
                  </div>
                  <div className="text-xs text-blue-600 font-medium">
                    {fmtPct((item.record.meat_weight_kg / item.record.total_weight_kg) * 100)}
                  </div>
                </div>
              )}

              {item.isCurrentMonth && !item.record && (
                <div className="flex items-center justify-center h-full">
                  <Plus className="h-4 w-4 text-muted-foreground/30" />
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}

// ==================== 页面 ====================
export function DailySlaughterPage() {
  const qc = useQueryClient();
  const [search, setSearch] = useState("");
  const [typeFilter, setTypeFilter] = useState<string>("all");
  const [viewMode, setViewMode] = useState<"list" | "calendar">("list");
  const [currentMonth, setCurrentMonth] = useState(new Date());
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [form, setForm] = useState<SlaughterForm>({ ...defaultForm });
  const [deleteId, setDeleteId] = useState<number | null>(null);

  const { data, isLoading } = useQuery({
    queryKey: ["daily-slaughter", typeFilter],
    queryFn: () => slaughterApi.list({
      slaughter_type: typeFilter === "all" ? "" : typeFilter,
      limit: 500,
    }),
  });

  const records: SlaughterRecord[] = data?.items || [];

  // 统计
  const stats = useMemo(() => {
    const thisMonth = records.filter((r) => {
      const d = new Date(r.slaughter_date);
      const now = new Date();
      return d.getFullYear() === now.getFullYear() && d.getMonth() === now.getMonth();
    });
    const days = new Set(thisMonth.map((r) => r.slaughter_date)).size;
    const totalFish = thisMonth.reduce((s, r) => s + r.fish_count, 0);
    const avgMeatRate = thisMonth.length
      ? thisMonth.reduce((s, r) => s + (r.meat_weight_kg / r.total_weight_kg) * 100, 0) / thisMonth.length
      : 0;
    const avgLossRate = thisMonth.length
      ? thisMonth.reduce((s, r) => s + (r.loss_weight_kg / r.total_weight_kg) * 100, 0) / thisMonth.length
      : 0;
    return { days, totalFish, avgMeatRate, avgLossRate };
  }, [records]);

  // 创建
  const createMutation = useMutation({
    mutationFn: slaughterApi.create,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["daily-slaughter"] });
      setDialogOpen(false);
      setForm({ ...defaultForm });
      toast.success("创建成功");
    },
    onError: (err: any) => toast.error(err.response?.data?.detail || "创建失败"),
  });

  // 更新
  const updateMutation = useMutation({
    mutationFn: ({ id, body }: { id: number; body: SlaughterForm }) => slaughterApi.update(id, body),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["daily-slaughter"] });
      setDialogOpen(false);
      setEditingId(null);
      setForm({ ...defaultForm });
      toast.success("更新成功");
    },
    onError: (err: any) => toast.error(err.response?.data?.detail || "更新失败"),
  });

  // 删除
  const deleteMutation = useMutation({
    mutationFn: slaughterApi.delete,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["daily-slaughter"] });
      setDeleteId(null);
      toast.success("删除成功");
    },
    onError: (err: any) => toast.error(err.response?.data?.detail || "删除失败"),
  });

  // 锁定
  const lockMutation = useMutation({
    mutationFn: slaughterApi.lock,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["daily-slaughter"] });
      toast.success("已锁定");
    },
    onError: (err: any) => toast.error(err.response?.data?.detail || "锁定失败"),
  });

  const isWholeFish = form.slaughter_type === "whole_fish";

  // 自动计算
  const meatRate = form.total_weight_kg > 0 ? (form.meat_weight_kg / form.total_weight_kg) * 100 : 0;
  const lossRate = form.total_weight_kg > 0 ? (form.loss_weight_kg / form.total_weight_kg) * 100 : 0;
  const byproductWeight = isWholeFish
    ? form.byproduct_head_count * 0.3 + form.byproduct_tail_count * 0.1 + form.byproduct_bone_count * 0.2
    : 0;
  const totalCheck = form.meat_weight_kg + form.loss_weight_kg + form.byproduct_trim_weight_kg + byproductWeight;
  const diff = Math.abs(form.total_weight_kg - totalCheck);
  const diffWarning = diff > 0.5 && form.total_weight_kg > 0;

  function handleSave() {
    if (editingId) {
      updateMutation.mutate({ id: editingId, body: form });
    } else {
      createMutation.mutate(form);
    }
  }

  function handleEdit(r: SlaughterRecord) {
    setEditingId(r.id);
    setForm({
      slaughter_date: r.slaughter_date,
      slaughter_type: r.slaughter_type,
      fish_count: r.fish_count,
      total_weight_kg: r.total_weight_kg,
      meat_weight_kg: r.meat_weight_kg,
      byproduct_head_count: r.byproduct_head_count,
      byproduct_tail_count: r.byproduct_tail_count,
      byproduct_bone_count: r.byproduct_bone_count,
      byproduct_trim_weight_kg: r.byproduct_trim_weight_kg,
      loss_weight_kg: r.loss_weight_kg,
      cost_price_per_kg: r.cost_price_per_kg,
      notes: r.notes,
    });
    setDialogOpen(true);
  }

  function handleNew() {
    setEditingId(null);
    setForm({ ...defaultForm });
    setDialogOpen(true);
  }

  function handleDayClick(dateStr: string) {
    const existing = records.find((r) => r.slaughter_date === dateStr);
    if (existing) {
      handleEdit(existing);
    } else {
      setEditingId(null);
      setForm({ ...defaultForm, slaughter_date: dateStr });
      setDialogOpen(true);
    }
  }

  const filteredRecords = records.filter((r) => {
    if (search) {
      return r.slaughter_date.includes(search) || r.notes?.includes(search);
    }
    return true;
  });

  return (
    <div className="space-y-6">
      {/* 标题 */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">宰杀记录管理</h1>
          <p className="text-sm text-muted-foreground">每日宰杀登记与成本核算</p>
        </div>
        <div className="flex items-center gap-2">
          <div className="flex items-center border rounded-md">
            <Button
              variant={viewMode === "list" ? "default" : "ghost"}
              size="sm"
              className="rounded-none rounded-l-md"
              onClick={() => setViewMode("list")}
            >
              <List className="h-4 w-4 mr-1" />列表
            </Button>
            <Button
              variant={viewMode === "calendar" ? "default" : "ghost"}
              size="sm"
              className="rounded-none rounded-r-md"
              onClick={() => setViewMode("calendar")}
            >
              <Calendar className="h-4 w-4 mr-1" />日历
            </Button>
          </div>
        </div>
      </div>

      {/* 统计卡片 */}
      <div className="grid grid-cols-4 gap-4">
        <Card><CardContent className="p-4">
          <div className="flex items-center justify-between">
            <div className="space-y-1"><p className="text-sm text-muted-foreground">本月宰杀天数</p><p className="text-2xl font-bold">{stats.days} 天</p></div>
            <div className="p-3 bg-blue-100 rounded-full"><FileBarChart className="h-5 w-5 text-blue-600" /></div>
          </div>
        </CardContent></Card>
        <Card><CardContent className="p-4">
          <div className="flex items-center justify-between">
            <div className="space-y-1"><p className="text-sm text-muted-foreground">本月总条数</p><p className="text-2xl font-bold">{stats.totalFish} 条</p></div>
            <div className="p-3 bg-green-100 rounded-full"><Fish className="h-5 w-5 text-green-600" /></div>
          </div>
        </CardContent></Card>
        <Card><CardContent className="p-4">
          <div className="flex items-center justify-between">
            <div className="space-y-1"><p className="text-sm text-muted-foreground">平均出肉率</p><p className="text-2xl font-bold">{fmtPct(stats.avgMeatRate)}</p></div>
            <div className="p-3 bg-amber-100 rounded-full"><TrendingUp className="h-5 w-5 text-amber-600" /></div>
          </div>
        </CardContent></Card>
        <Card><CardContent className="p-4">
          <div className="flex items-center justify-between">
            <div className="space-y-1"><p className="text-sm text-muted-foreground">平均损耗率</p><p className="text-2xl font-bold">{fmtPct(stats.avgLossRate)}</p></div>
            <div className="p-3 bg-red-100 rounded-full"><Scale className="h-5 w-5 text-red-600" /></div>
          </div>
        </CardContent></Card>
      </div>

      {/* 工具栏 */}
      <div className="flex items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          {viewMode === "list" && (
            <>
              <div className="relative">
                <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
                <Input placeholder="搜索日期或备注..." className="pl-9 w-64" value={search} onChange={(e) => setSearch(e.target.value)} />
              </div>
              <Select value={typeFilter} onValueChange={(v) => setTypeFilter(v ?? "all")}>
                <SelectTrigger className="w-40"><SelectValue placeholder="类型筛选" /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">全部类型</SelectItem>
                  <SelectItem value="whole_fish">整鱼宰杀</SelectItem>
                  <SelectItem value="fillet">鱼柳加工</SelectItem>
                </SelectContent>
              </Select>
            </>
          )}
        </div>
        <Button onClick={handleNew}><Plus className="h-4 w-4 mr-1" />新建记录</Button>
      </div>

      {/* ===== 列表视图 ===== */}
      {viewMode === "list" && (
        <div className="border rounded-md">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>日期</TableHead>
                <TableHead>类型</TableHead>
                <TableHead className="text-right">条数</TableHead>
                <TableHead className="text-right">总重(kg)</TableHead>
                <TableHead className="text-right">成品肉(kg)</TableHead>
                <TableHead className="text-right">出肉率</TableHead>
                <TableHead className="text-right">损耗率</TableHead>
                <TableHead className="text-right">成本(元/kg)</TableHead>
                <TableHead className="text-right">可用肉(kg)</TableHead>
                <TableHead>状态</TableHead>
                <TableHead className="w-[120px]">操作</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {isLoading ? (
                <TableRow><TableCell colSpan={11} className="text-center py-8 text-muted-foreground">加载中...</TableCell></TableRow>
              ) : filteredRecords.length === 0 ? (
                <TableRow><TableCell colSpan={11} className="text-center py-8 text-muted-foreground">暂无记录</TableCell></TableRow>
              ) : filteredRecords.map((r) => (
                <TableRow key={r.id}>
                  <TableCell className="font-medium">{r.slaughter_date}</TableCell>
                  <TableCell>
                    <Badge variant="outline" className={cn(r.slaughter_type === "whole_fish" ? "text-blue-600 border-blue-200" : "text-amber-600 border-amber-200")}>
                      {r.slaughter_type === "whole_fish" ? "整鱼" : "鱼柳"}
                    </Badge>
                  </TableCell>
                  <TableCell className="text-right">{r.fish_count}</TableCell>
                  <TableCell className="text-right">{fmtWeight(r.total_weight_kg)}</TableCell>
                  <TableCell className="text-right">{fmtWeight(r.meat_weight_kg)}</TableCell>
                  <TableCell className="text-right">{fmtPct((r.meat_weight_kg / r.total_weight_kg) * 100)}</TableCell>
                  <TableCell className="text-right">{fmtPct((r.loss_weight_kg / r.total_weight_kg) * 100)}</TableCell>
                  <TableCell className="text-right">{fmtMoney(r.cost_price_per_kg)}</TableCell>
                  <TableCell className="text-right font-medium">{fmtWeight(r.available_meat_kg)}</TableCell>
                  <TableCell>
                    <Badge className={cn(r.is_locked ? "bg-green-100 text-green-800" : "bg-orange-100 text-orange-800")}>
                      {r.is_locked ? "已锁定" : "未锁定"}
                    </Badge>
                  </TableCell>
                  <TableCell>
                    <div className="flex items-center gap-1">
                      {!r.is_locked && (
                        <>
                          <Button variant="ghost" size="icon" className="h-8 w-8" onClick={() => handleEdit(r)}><Pencil className="h-4 w-4" /></Button>
                          <Button variant="ghost" size="icon" className="h-8 w-8" onClick={() => setDeleteId(r.id)}><Trash2 className="h-4 w-4" /></Button>
                        </>
                      )}
                      {!r.is_locked && (
                        <Button variant="ghost" size="icon" className="h-8 w-8" onClick={() => lockMutation.mutate(r.id)} title="锁定">
                          <Lock className="h-4 w-4" />
                        </Button>
                      )}
                      {r.is_locked && <Lock className="h-4 w-4 text-green-600 ml-2" />}
                    </div>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      )}

      {/* ===== 日历视图 ===== */}
      {viewMode === "calendar" && (
        <Card>
          <CardContent className="p-6">
            <SlaughterCalendar
              records={records}
              currentMonth={currentMonth}
              onMonthChange={setCurrentMonth}
              onDayClick={handleDayClick}
            />
          </CardContent>
        </Card>
      )}

      {/* 新建/编辑弹窗 */}
      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
          <DialogHeader><DialogTitle>{editingId ? "编辑宰杀记录" : "新建宰杀记录"}</DialogTitle></DialogHeader>
          <div className="space-y-4 py-4">
            {/* 类型切换 */}
            <div className="flex gap-2">
              <Button
                type="button"
                variant={isWholeFish ? "default" : "outline"}
                onClick={() => setForm((f) => ({ ...f, slaughter_type: "whole_fish", fish_count: f.fish_count || 0 }))}
                className="flex-1"
              >整鱼宰杀</Button>
              <Button
                type="button"
                variant={!isWholeFish ? "default" : "outline"}
                onClick={() => setForm((f) => ({ ...f, slaughter_type: "fillet", fish_count: 0, byproduct_head_count: 0, byproduct_tail_count: 0, byproduct_bone_count: 0 }))}
                className="flex-1"
              >鱼柳加工</Button>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label>宰杀日期</Label>
                <Input type="date" value={form.slaughter_date} onChange={(e) => setForm({ ...form, slaughter_date: e.target.value })} />
              </div>
              {isWholeFish && (
                <div className="space-y-2">
                  <Label>宰杀条数</Label>
                  <Input type="number" min={0} value={form.fish_count} onChange={(e) => setForm({ ...form, fish_count: Number(e.target.value) })} />
                </div>
              )}
            </div>

            <div className="grid grid-cols-3 gap-4">
              <div className="space-y-2">
                <Label>总重量(kg)</Label>
                <Input type="number" step="0.001" value={form.total_weight_kg} onChange={(e) => setForm({ ...form, total_weight_kg: Number(e.target.value) })} />
              </div>
              <div className="space-y-2">
                <Label>成品肉(kg)</Label>
                <Input type="number" step="0.001" value={form.meat_weight_kg} onChange={(e) => setForm({ ...form, meat_weight_kg: Number(e.target.value) })} />
              </div>
              <div className="space-y-2">
                <Label>损耗(kg)</Label>
                <Input type="number" step="0.001" value={form.loss_weight_kg} onChange={(e) => setForm({ ...form, loss_weight_kg: Number(e.target.value) })} />
              </div>
            </div>

            {/* 实时计算 */}
            <div className="grid grid-cols-2 gap-4">
              <div className="bg-muted/50 rounded-md p-3 text-center">
                <p className="text-xs text-muted-foreground">出肉率</p>
                <p className="text-lg font-bold text-blue-600">{fmtPct(meatRate)}</p>
              </div>
              <div className="bg-muted/50 rounded-md p-3 text-center">
                <p className="text-xs text-muted-foreground">损耗率</p>
                <p className="text-lg font-bold text-red-600">{fmtPct(lossRate)}</p>
              </div>
            </div>

            {isWholeFish && (
              <>
                <p className="text-sm font-medium">副产品统计</p>
                <div className="grid grid-cols-3 gap-4">
                  <div className="space-y-2"><Label>鱼头数量</Label><Input type="number" min={0} value={form.byproduct_head_count} onChange={(e) => setForm({ ...form, byproduct_head_count: Number(e.target.value) })} /></div>
                  <div className="space-y-2"><Label>鱼尾数量</Label><Input type="number" min={0} value={form.byproduct_tail_count} onChange={(e) => setForm({ ...form, byproduct_tail_count: Number(e.target.value) })} /></div>
                  <div className="space-y-2"><Label>鱼骨数量</Label><Input type="number" min={0} value={form.byproduct_bone_count} onChange={(e) => setForm({ ...form, byproduct_bone_count: Number(e.target.value) })} /></div>
                </div>
                <div className="space-y-2">
                  <Label>边角料重量(kg)</Label>
                  <Input type="number" step="0.001" value={form.byproduct_trim_weight_kg} onChange={(e) => setForm({ ...form, byproduct_trim_weight_kg: Number(e.target.value) })} />
                </div>
                <p className="text-xs text-muted-foreground">
                  副产品重量估算：鱼头 {fmtWeight(byproductWeight)} kg（{form.byproduct_head_count}×0.3 + {form.byproduct_tail_count}×0.1 + {form.byproduct_bone_count}×0.2）
                </p>
              </>
            )}

            {/* 重量平衡校验 */}
            {diffWarning && (
              <div className="flex items-center gap-2 bg-yellow-50 border border-yellow-200 rounded-md p-3 text-sm text-yellow-800">
                <AlertTriangle className="h-4 w-4 shrink-0" />
                <span>重量不平衡！总重 {fmtWeight(form.total_weight_kg)} kg vs 合计 {fmtWeight(totalCheck)} kg，差异 {fmtWeight(diff)} kg</span>
              </div>
            )}

            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label>成本单价(元/kg)</Label>
                <Input type="number" step="0.01" value={form.cost_price_per_kg} onChange={(e) => setForm({ ...form, cost_price_per_kg: Number(e.target.value) })} />
              </div>
            </div>

            <div className="space-y-2">
              <Label>备注</Label>
              <textarea
                className="flex min-h-[80px] w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
                value={form.notes}
                onChange={(e) => setForm({ ...form, notes: e.target.value })}
              />
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
          <p className="text-sm text-muted-foreground">确定要删除这条宰杀记录吗？此操作不可撤销。</p>
          <DialogFooter>
            <Button variant="outline" onClick={() => setDeleteId(null)}>取消</Button>
            <Button variant="destructive" onClick={() => deleteId && deleteMutation.mutate(deleteId)} disabled={deleteMutation.isPending}>删除</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
