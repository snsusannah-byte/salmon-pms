import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import { SupplierFormDialog } from "@/components/SupplierFormDialog";
import { DeleteConfirmDialog } from "@/components/DeleteConfirmDialog";
import { BatchImportButton } from "@/components/BatchImportButton";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  Plus, Search, Pencil, Trash2, Store, ChevronLeft, ChevronRight, Phone, User, Package,
  Eye, Globe, CreditCard, Calendar, Banknote, MapPin, Mail, Building, TrendingUp,
} from "lucide-react";

// 供应商类型
interface Supplier {
  id: number;
  name: string;
  company_full_name: string | null;
  contact_person: string | null;
  phone: string | null;
  address: string | null;
  website: string | null;
  bank_account: string | null;
  bank_name: string | null;
  currency: string;
  cooperation_date: string | null;
  logistics_info: string | null;
  notes: string | null;
  is_active: boolean;
  created_at: string;
}

interface CompanyListResponse {
  total: number;
  items: Supplier[];
  skip: number;
  limit: number;
}

interface PayableItem {
  supplier_id: number;
  supplier_name: string;
  opening_balance: string;
  current_purchase: string;
  current_expenses: string;
  current_payments: string;
  closing_balance: string;
}

interface PayableResponse {
  total: number;
  items: PayableItem[];
  total_payable: number;
}

const fmt = (v?: number | string | null, currency?: string) => {
  if (v === undefined || v === null || v === "" || Number.isNaN(Number(v))) return "-";
  const symbol = currency === "USD" ? "$" : "¥";
  return `${symbol}${Number(v).toLocaleString("zh-CN", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
};

const PAGE_SIZE = 10;

export function SuppliersPage() {
  const qc = useQueryClient();
  const [search, setSearch] = useState("");
  const [page, setPage] = useState(1);
  const [formOpen, setFormOpen] = useState(false);
  const [editingSupplier, setEditingSupplier] = useState<Supplier | null>(null);
  const [deleteOpen, setDeleteOpen] = useState(false);
  const [deleteTarget, setDeleteTarget] = useState<Supplier | null>(null);
  const [detailOpen, setDetailOpen] = useState(false);
  const [detailSupplier, setDetailSupplier] = useState<Supplier | null>(null);

  // 供应商列表
  const { data, isLoading } = useQuery<CompanyListResponse>({
    queryKey: ["suppliers", search, page],
    queryFn: async () => {
      const params = new URLSearchParams();
      if (search) params.append("search", search);
      params.append("exclude_type", "customer");
      params.append("exclude_type", "processing_plant");
      params.append("exclude_type", "fish_farm");
      params.append("exclude_type", "exporter");
      params.append("skip", String((page - 1) * PAGE_SIZE));
      params.append("limit", String(PAGE_SIZE));
      const res = await api.get(`/v1/companies/?${params.toString()}`);
      return res.data;
    },
  });

  // 应付款数据（用于列表展示）
  const { data: payableData } = useQuery<PayableResponse>({
    queryKey: ["payable-summary"],
    queryFn: async () => {
      const res = await api.get("/v1/reports/payable-statements?limit=500");
      return res.data;
    },
  });

  // 构建应付款查找表
  const payableMap: Record<number, PayableItem> = {};
  payableData?.items.forEach((item) => {
    payableMap[item.supplier_id] = item;
  });

  const deleteMutation = useMutation({
    mutationFn: (id: number) => api.delete(`/v1/companies/${id}`),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["suppliers"] });
      qc.invalidateQueries({ queryKey: ["payable-summary"] });
      setDeleteOpen(false);
      setDeleteTarget(null);
    },
  });

  const totalPages = data ? Math.ceil(data.total / PAGE_SIZE) : 0;

  const handleAdd = () => {
    setEditingSupplier(null);
    setFormOpen(true);
  };

  const handleEdit = (s: Supplier) => {
    setEditingSupplier(s);
    setFormOpen(true);
  };

  const handleDelete = (s: Supplier) => {
    setDeleteTarget(s);
    setDeleteOpen(true);
  };

  const handleViewDetail = (s: Supplier) => {
    setDetailSupplier(s);
    setDetailOpen(true);
  };

  const handlePageChange = (newPage: number) => {
    if (newPage >= 1 && newPage <= totalPages) {
      setPage(newPage);
    }
  };

  // 统计
  const allSuppliers = data?.items || [];
  const totalPayableCNY = allSuppliers.reduce((sum, s) => {
    const p = payableMap[s.id];
    return s.currency !== "USD" ? sum + (p ? Number(p.closing_balance) : 0) : sum;
  }, 0);
  const totalPayableUSD = allSuppliers.reduce((sum, s) => {
    const p = payableMap[s.id];
    return s.currency === "USD" ? sum + (p ? Number(p.closing_balance) : 0) : sum;
  }, 0);
  const withContact = allSuppliers.filter((s) => s.contact_person).length;
  const withPhone = allSuppliers.filter((s) => s.phone).length;

  return (
    <div className="space-y-6">
      <SupplierFormDialog
        open={formOpen}
        onOpenChange={setFormOpen}
        initialData={editingSupplier}
      />
      <DeleteConfirmDialog
        open={deleteOpen}
        onOpenChange={setDeleteOpen}
        companyId={deleteTarget?.id ?? null}
        companyName={deleteTarget?.name ?? ""}
      />

      {/* 详情弹窗 */}
      <Dialog open={detailOpen} onOpenChange={setDetailOpen}>
        <DialogContent className="max-w-lg">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <Store className="h-5 w-5 text-purple-600" />
              供应商详情
            </DialogTitle>
          </DialogHeader>
          {detailSupplier && (
            <div className="space-y-4 py-2">
              {/* 应付款卡片 */}
              {payableMap[detailSupplier.id] && (
                <div className="bg-red-50 border border-red-100 rounded-lg p-4">
                  <div className="text-sm text-red-700 font-medium mb-2">
                    应付账款 {detailSupplier.currency === "USD" && <span className="text-xs">(USD)</span>}
                  </div>
                  <div className="grid grid-cols-2 gap-2 text-sm">
                    <div className="flex justify-between">
                      <span className="text-muted-foreground">期初欠款</span>
                      <span>{fmt(payableMap[detailSupplier.id].opening_balance, detailSupplier.currency)}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-muted-foreground">本期采购</span>
                      <span className="text-red-600">+{fmt(payableMap[detailSupplier.id].current_purchase, detailSupplier.currency)}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-muted-foreground">本期费用</span>
                      <span className="text-red-600">+{fmt(payableMap[detailSupplier.id].current_expenses, detailSupplier.currency)}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-muted-foreground">本期付款</span>
                      <span className="text-green-600">-{fmt(payableMap[detailSupplier.id].current_payments, detailSupplier.currency)}</span>
                    </div>
                  </div>
                  <div className="border-t border-red-200 mt-2 pt-2 flex justify-between font-bold text-red-700">
                    <span>期末欠款</span>
                    <span>{fmt(payableMap[detailSupplier.id].closing_balance, detailSupplier.currency)}</span>
                  </div>
                </div>
              )}

              <div className="flex items-start gap-3">
                <Building className="h-5 w-5 text-muted-foreground mt-0.5" />
                <div>
                  <p className="font-medium text-lg">{detailSupplier.name}</p>
                  {detailSupplier.company_full_name && (
                    <p className="text-sm text-muted-foreground">{detailSupplier.company_full_name}</p>
                  )}
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3 text-sm">
                {detailSupplier.contact_person && (
                  <div className="flex items-center gap-2">
                    <User className="h-4 w-4 text-muted-foreground" />
                    <span>{detailSupplier.contact_person}</span>
                  </div>
                )}
                {detailSupplier.phone && (
                  <div className="flex items-center gap-2">
                    <Phone className="h-4 w-4 text-muted-foreground" />
                    <span>{detailSupplier.phone}</span>
                  </div>
                )}
                {detailSupplier.address && (
                  <div className="flex items-center gap-2 col-span-2">
                    <MapPin className="h-4 w-4 text-muted-foreground" />
                    <span>{detailSupplier.address}</span>
                  </div>
                )}
                {detailSupplier.website && (
                  <div className="flex items-center gap-2 col-span-2">
                    <Globe className="h-4 w-4 text-muted-foreground" />
                    <a href={detailSupplier.website} target="_blank" rel="noopener noreferrer" className="text-blue-500 hover:underline">
                      {detailSupplier.website}
                    </a>
                  </div>
                )}
                {detailSupplier.bank_name && (
                  <div className="flex items-center gap-2 col-span-2">
                    <Banknote className="h-4 w-4 text-muted-foreground" />
                    <span>{detailSupplier.bank_name} {detailSupplier.bank_account ?? ""}</span>
                  </div>
                )}
                {detailSupplier.cooperation_date && (
                  <div className="flex items-center gap-2">
                    <Calendar className="h-4 w-4 text-muted-foreground" />
                    <span>{new Date(detailSupplier.cooperation_date).toLocaleDateString("zh-CN")}</span>
                  </div>
                )}
                {detailSupplier.logistics_info && (
                  <div className="flex items-center gap-2">
                    <Package className="h-4 w-4 text-muted-foreground" />
                    <span>{detailSupplier.logistics_info}</span>
                  </div>
                )}
              </div>

              {detailSupplier.notes && (
                <div className="bg-slate-50 rounded-lg p-3">
                  <p className="text-xs text-muted-foreground mb-1">备注</p>
                  <p className="text-sm whitespace-pre-wrap">{detailSupplier.notes}</p>
                </div>
              )}

              <div className="flex gap-2 pt-2">
                <Button variant="outline" size="sm" onClick={() => { setDetailOpen(false); handleEdit(detailSupplier); }}>
                  <Pencil className="h-4 w-4 mr-2" />
                  编辑
                </Button>
              </div>
            </div>
          )}
        </DialogContent>
      </Dialog>

      {/* 标题 */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">供应商管理</h1>
          <p className="text-sm text-muted-foreground">
            共 {data?.total ?? 0} 家供应商，第 {page}/{totalPages || 1} 页
          </p>
        </div>
        <div className="flex gap-2">
          <BatchImportButton type="companies" />
          <Button onClick={handleAdd}>
            <Plus className="h-4 w-4 mr-2" />
            新增供应商
          </Button>
        </div>
      </div>

      {/* 统计卡片 */}
      <div className="grid grid-cols-4 gap-4">
        <Card>
          <CardContent className="p-4 flex items-center gap-4">
            <div className="p-3 bg-purple-100 rounded-full">
              <Store className="h-6 w-6 text-purple-600" />
            </div>
            <div>
              <p className="text-sm text-muted-foreground">供应商总数</p>
              <p className="text-2xl font-bold">{data?.total ?? 0}</p>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4 flex items-center gap-4">
            <div className="p-3 bg-red-100 rounded-full">
              <TrendingUp className="h-6 w-6 text-red-600" />
            </div>
            <div>
              <p className="text-sm text-muted-foreground">总应付款</p>
              <div className="space-y-0.5">
                {totalPayableCNY > 0 && <p className="text-lg font-bold text-red-600">{fmt(totalPayableCNY, 'CNY')}</p>}
                {totalPayableUSD > 0 && <p className="text-lg font-bold text-red-600">{fmt(totalPayableUSD, 'USD')}</p>}
                {totalPayableCNY === 0 && totalPayableUSD === 0 && <p className="text-lg font-bold text-green-600">¥0.00</p>}
              </div>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4 flex items-center gap-4">
            <div className="p-3 bg-blue-100 rounded-full">
              <User className="h-6 w-6 text-blue-600" />
            </div>
            <div>
              <p className="text-sm text-muted-foreground">有联系人</p>
              <p className="text-2xl font-bold">{withContact}</p>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4 flex items-center gap-4">
            <div className="p-3 bg-amber-100 rounded-full">
              <Phone className="h-6 w-6 text-amber-600" />
            </div>
            <div>
              <p className="text-sm text-muted-foreground">有电话</p>
              <p className="text-2xl font-bold">{withPhone}</p>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* 搜索 */}
      <div className="relative max-w-sm">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
        <Input
          placeholder="搜索供应商名称..."
          value={search}
          onChange={(e) => { setSearch(e.target.value); setPage(1); }}
          className="pl-9"
        />
      </div>

      {/* 表格 */}
      <div className="border rounded-lg">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>供应商名称</TableHead>
              <TableHead>联系人</TableHead>
              <TableHead>电话</TableHead>
              <TableHead>开户行</TableHead>
              <TableHead>合作日期</TableHead>
              <TableHead className="text-right">期末欠款</TableHead>
              <TableHead className="w-[120px]">操作</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {isLoading ? (
              <TableRow>
                <TableCell colSpan={7} className="text-center py-8 text-muted-foreground">
                  加载中...
                </TableCell>
              </TableRow>
            ) : (data?.items?.length ?? 0) === 0 ? (
              <TableRow>
                <TableCell colSpan={7} className="text-center py-8 text-muted-foreground">
                  暂无供应商，点击右上角新增
                </TableCell>
              </TableRow>
            ) : (
              data?.items.map((s) => {
                const payable = payableMap[s.id];
                const closingBalance = payable ? Number(payable.closing_balance) : 0;
                return (
                  <TableRow key={s.id} className="cursor-pointer hover:bg-slate-50/50">
                    <TableCell className="font-medium">
                      <div className="flex flex-col gap-0.5">
                        <span onClick={() => handleViewDetail(s)} className="hover:text-purple-600 hover:underline cursor-pointer">
                          {s.name}
                        </span>
                        {s.company_full_name && (
                          <span className="text-xs text-muted-foreground">{s.company_full_name}</span>
                        )}
                      </div>
                    </TableCell>
                    <TableCell className="text-sm">{s.contact_person ?? "-"}</TableCell>
                    <TableCell className="text-sm">{s.phone ?? "-"}</TableCell>
                    <TableCell className="text-sm text-muted-foreground">{s.bank_name ?? "-"}</TableCell>
                    <TableCell className="text-sm">
                      {s.cooperation_date ? new Date(s.cooperation_date).toLocaleDateString("zh-CN") : "-"}
                    </TableCell>
                    <TableCell className="text-right">
                      {closingBalance > 0 ? (
                        <span className="text-red-600 font-medium">
                          {fmt(closingBalance, s.currency)}
                          {s.currency === "USD" && <span className="text-[10px] ml-1 text-gray-400">USD</span>}
                        </span>
                      ) : (
                        <span className="text-green-600 text-sm">已结清</span>
                      )}
                    </TableCell>
                    <TableCell>
                      <div className="flex gap-1">
                        <Button variant="ghost" size="icon" className="h-8 w-8" onClick={() => handleViewDetail(s)} title="查看详情">
                          <Eye className="h-4 w-4" />
                        </Button>
                        <Button variant="ghost" size="icon" className="h-8 w-8" onClick={() => handleEdit(s)} title="编辑">
                          <Pencil className="h-4 w-4" />
                        </Button>
                        <Button variant="ghost" size="icon" className="h-8 w-8 text-red-500 hover:text-red-600" onClick={() => handleDelete(s)} title="删除">
                          <Trash2 className="h-4 w-4" />
                        </Button>
                      </div>
                    </TableCell>
                  </TableRow>
                );
              })
            )}
          </TableBody>
        </Table>
      </div>

      {/* 分页 */}
      {totalPages > 1 && (
        <div className="flex items-center justify-between">
          <div className="text-sm text-muted-foreground">
            显示 {(page - 1) * PAGE_SIZE + 1} - {Math.min(page * PAGE_SIZE, data?.total ?? 0)} / 共 {data?.total ?? 0} 条
          </div>
          <div className="flex items-center gap-2">
            <Button variant="outline" size="sm" onClick={() => handlePageChange(page - 1)} disabled={page <= 1}>
              <ChevronLeft className="h-4 w-4" />
            </Button>
            <span className="text-sm">{page} / {totalPages}</span>
            <Button variant="outline" size="sm" onClick={() => handlePageChange(page + 1)} disabled={page >= totalPages}>
              <ChevronRight className="h-4 w-4" />
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}
