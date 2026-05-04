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
import { CompanyFormDialog } from "@/components/CompanyFormDialog";
import { DeleteConfirmDialog } from "@/components/DeleteConfirmDialog";
import {
  Plus, Search, Pencil, Trash2, Store, ChevronLeft, ChevronRight, Phone, User, Package,
} from "lucide-react";

// 复用 CompaniesPage 的类型
type Company = {
  id: number;
  name: string;
  chinese_name: string | null;
  type: string;
  code: string | null;
  contact_person: string | null;
  phone: string | null;
  email: string | null;
  address: string | null;
  registration_code: string | null;
  enterprise_registration_no: string | null;
  coc_cert_no: string | null;
  farming_area: string | null;
  website: string | null;
  bank_name: string | null;
  bank_account: string | null;
  cooperation_date: string | null;
  credit_limit: string;
  logistics_info: string | null;
  salesperson_id: number | null;
  customer_category: string | null;
  notes: string | null;
  is_active: boolean;
  created_at: string;
};

type CompanyListResponse = {
  total: number;
  items: Company[];
  skip: number;
  limit: number;
};

interface Material {
  id: number;
  supplier_id: number | null;
  name: string;
  unit: string;
}

const PAGE_SIZE = 10;

export function SuppliersPage() {
  const qc = useQueryClient();
  const [search, setSearch] = useState("");
  const [page, setPage] = useState(1);
  const [formOpen, setFormOpen] = useState(false);
  const [editingSupplier, setEditingSupplier] = useState<Company | null>(null);
  const [deleteOpen, setDeleteOpen] = useState(false);
  const [deleteTarget, setDeleteTarget] = useState<Company | null>(null);

  const { data, isLoading } = useQuery<CompanyListResponse>({
    queryKey: ["suppliers", search, page],
    queryFn: async () => {
      const params = new URLSearchParams();
      if (search) params.append("search", search);
      params.append("type", "supplier");
      params.append("skip", String((page - 1) * PAGE_SIZE));
      params.append("limit", String(PAGE_SIZE));
      const res = await api.get(`/v1/companies/?${params.toString()}`);
      return res.data;
    },
  });

  const { data: materialsData } = useQuery({
    queryKey: ["supplier-materials-count"],
    queryFn: async () => {
      const res = await api.get("/v1/products/?category=bom_material&limit=500");
      return res.data.items as Material[];
    },
  });

  const materials = materialsData || [];

  const deleteMutation = useMutation({
    mutationFn: (id: number) => api.delete(`/v1/companies/${id}`),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["suppliers"] });
      setDeleteOpen(false);
      setDeleteTarget(null);
    },
  });

  const totalPages = data ? Math.ceil(data.total / PAGE_SIZE) : 0;

  const handleAdd = () => {
    setEditingSupplier(null);
    setFormOpen(true);
  };

  const handleEdit = (s: Company) => {
    setEditingSupplier(s);
    setFormOpen(true);
  };

  const handleDelete = (s: Company) => {
    setDeleteTarget(s);
    setDeleteOpen(true);
  };

  const handlePageChange = (newPage: number) => {
    if (newPage >= 1 && newPage <= totalPages) {
      setPage(newPage);
    }
  };

  const supplierMaterialCount = (supplierId: number) => {
    return materials.filter((m) => m.supplier_id === supplierId).length;
  };

  return (
    <div className="space-y-6">
      <CompanyFormDialog
        open={formOpen}
        onOpenChange={setFormOpen}
        initialData={editingSupplier}
        defaultType="supplier"
      />
      <DeleteConfirmDialog
        open={deleteOpen}
        onOpenChange={setDeleteOpen}
        companyId={deleteTarget?.id ?? null}
        companyName={deleteTarget?.name ?? ""}
      />

      {/* 标题 */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">供应商管理</h1>
          <p className="text-sm text-muted-foreground">
            共 {data?.total ?? 0} 家供应商，第 {page}/{totalPages || 1} 页
          </p>
        </div>
        <Button onClick={handleAdd}>
          <Plus className="h-4 w-4 mr-2" />
          新增供应商
        </Button>
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
            <div className="p-3 bg-green-100 rounded-full">
              <Package className="h-6 w-6 text-green-600" />
            </div>
            <div>
              <p className="text-sm text-muted-foreground">物料种类</p>
              <p className="text-2xl font-bold">{materials.length}</p>
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
              <p className="text-2xl font-bold">{data?.items?.filter((s) => s.contact_person).length ?? 0}</p>
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
              <p className="text-2xl font-bold">{data?.items?.filter((s) => s.phone).length ?? 0}</p>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* 搜索 */}
      <div className="relative max-w-sm">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
        <Input
          placeholder="搜索供应商名称、编码、联系人..."
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
              <TableHead>名称</TableHead>
              <TableHead>中文名称</TableHead>
              <TableHead>编码</TableHead>
              <TableHead>联系人</TableHead>
              <TableHead>电话</TableHead>
              <TableHead>邮箱</TableHead>
              <TableHead>地址</TableHead>
              <TableHead>银行账户</TableHead>
              <TableHead>供应物料</TableHead>
              <TableHead className="w-[120px]">操作</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {isLoading ? (
              <TableRow>
                <TableCell colSpan={10} className="text-center py-8 text-muted-foreground">
                  加载中...
                </TableCell>
              </TableRow>
            ) : (data?.items?.length ?? 0) === 0 ? (
              <TableRow>
                <TableCell colSpan={10} className="text-center py-8 text-muted-foreground">
                  暂无供应商，点击右上角新增
                </TableCell>
              </TableRow>
            ) : (
              data?.items.map((s) => {
                const matCount = supplierMaterialCount(s.id);
                return (
                  <TableRow key={s.id}>
                    <TableCell className="font-medium">{s.name}</TableCell>
                    <TableCell className="text-sm">{s.chinese_name ?? "-"}</TableCell>
                    <TableCell className="font-mono text-xs text-muted-foreground">{s.code ?? "-"}</TableCell>
                    <TableCell className="text-sm">{s.contact_person ?? "-"}</TableCell>
                    <TableCell className="text-sm">{s.phone ?? "-"}</TableCell>
                    <TableCell className="text-sm">{s.email ?? "-"}</TableCell>
                    <TableCell className="text-sm text-muted-foreground">{s.address ?? "-"}</TableCell>
                    <TableCell className="text-sm text-muted-foreground">
                      {s.bank_name ? `${s.bank_name} ${s.bank_account ?? ""}` : "-"}
                    </TableCell>
                    <TableCell>
                      {matCount > 0 ? (
                        <Badge variant="outline" className="text-xs text-purple-600 border-purple-200">
                          {matCount} 种物料
                        </Badge>
                      ) : (
                        <span className="text-sm text-muted-foreground">-</span>
                      )}
                    </TableCell>
                    <TableCell>
                      <div className="flex gap-1">
                        <Button variant="ghost" size="icon" className="h-8 w-8" onClick={() => handleEdit(s)}>
                          <Pencil className="h-4 w-4" />
                        </Button>
                        <Button variant="ghost" size="icon" className="h-8 w-8 text-red-500 hover:text-red-600" onClick={() => handleDelete(s)}>
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
