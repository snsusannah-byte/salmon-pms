import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
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
import { CompanyFormDialog } from "@/components/CompanyFormDialog";
import { DeleteConfirmDialog } from "@/components/DeleteConfirmDialog";
import { Plus, Search, User, Pencil, Trash2, ChevronLeft, ChevronRight } from "lucide-react";

interface Company {
  id: number;
  name: string;
  chinese_name: string | null;
  contact_person: string | null;
  phone: string | null;
  address: string | null;
  logistics_info: string | null;
  credit_limit: string;
  salesperson_id: number | null;
  salesperson_name: string | null;
  customer_category: string | null;
  cooperation_date: string | null;
  notes: string | null;
  is_active: boolean;
  created_at: string;
}

interface CompanyListResponse {
  total: number;
  items: Company[];
  skip: number;
  limit: number;
}

const PAGE_SIZE = 10;

const categoryMap: Record<string, string> = {
  wholesaler: "批发商",
  distributor: "渠道商",
  retailer: "零售商",
  platform: "平台",
  group_buying: "团购",
};

export function CustomersPage() {
  const [search, setSearch] = useState("");
  const [page, setPage] = useState(1);
  const [formOpen, setFormOpen] = useState(false);
  const [editingCompany, setEditingCompany] = useState<Company | null>(null);
  const [deleteOpen, setDeleteOpen] = useState(false);
  const [deleteTarget, setDeleteTarget] = useState<Company | null>(null);

  const { data, isLoading } = useQuery<CompanyListResponse>({
    queryKey: ["customers", search, page],
    queryFn: async () => {
      const params = new URLSearchParams();
      if (search) params.append("search", search);
      params.append("type", "customer");
      params.append("skip", String((page - 1) * PAGE_SIZE));
      params.append("limit", String(PAGE_SIZE));
      const res = await api.get(`/v1/companies/?${params.toString()}`);
      return res.data;
    },
  });

  const totalPages = data ? Math.ceil(data.total / PAGE_SIZE) : 0;

  const handleAdd = () => {
    setEditingCompany(null);
    setFormOpen(true);
  };

  const handleEdit = (company: Company) => {
    setEditingCompany(company);
    setFormOpen(true);
  };

  const handleDelete = (company: Company) => {
    setDeleteTarget(company);
    setDeleteOpen(true);
  };

  const handlePageChange = (newPage: number) => {
    if (newPage >= 1 && newPage <= totalPages) {
      setPage(newPage);
    }
  };

  return (
    <div className="space-y-6">
      <CompanyFormDialog
        open={formOpen}
        onOpenChange={setFormOpen}
        initialData={editingCompany}
        defaultType="customer"
      />
      <DeleteConfirmDialog
        open={deleteOpen}
        onOpenChange={setDeleteOpen}
        companyId={deleteTarget?.id ?? null}
        companyName={deleteTarget?.name ?? ""}
      />

      {/* 标题栏 */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">客户管理</h1>
          <p className="text-sm text-muted-foreground">
            共 {data?.total ?? 0} 个客户，第 {page}/{totalPages} 页
          </p>
        </div>
        <Button onClick={handleAdd}>
          <Plus className="h-4 w-4 mr-2" />
          新增客户
        </Button>
      </div>

      {/* 筛选栏 */}
      <div className="flex gap-4">
        <div className="relative flex-1 max-w-sm">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <Input
            placeholder="搜索名称、编码、联系人..."
            value={search}
            onChange={(e) => { setSearch(e.target.value); setPage(1); }}
            className="pl-9"
          />
        </div>
      </div>

      {/* 数据表格 */}
      <div className="border rounded-lg">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>名称</TableHead>
              <TableHead>分类</TableHead>
              <TableHead>联系人</TableHead>
              <TableHead>电话</TableHead>
              <TableHead>地址</TableHead>
              <TableHead>物流</TableHead>
              <TableHead>应收款</TableHead>
              <TableHead>业务员</TableHead>
              <TableHead className="w-[200px]">备注</TableHead>
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
            ) : data?.items.length === 0 ? (
              <TableRow>
                <TableCell colSpan={10} className="text-center py-8 text-muted-foreground">
                  暂无客户，点击右上角新增客户
                </TableCell>
              </TableRow>
            ) : (
              data?.items.map((company) => (
                <TableRow key={company.id}>
                  <TableCell className="font-medium">
                    <div className="flex items-center gap-2">
                      <User className="h-4 w-4 text-orange-500" />
                      {company.name}
                    </div>
                  </TableCell>
                  <TableCell>
                    {company.customer_category ? (
                      <Badge variant="secondary" className="text-xs">
                        {categoryMap[company.customer_category] ?? company.customer_category}
                      </Badge>
                    ) : (
                      "-"
                    )}
                  </TableCell>
                  <TableCell className="text-sm">{company.contact_person ?? "-"}</TableCell>
                  <TableCell className="text-sm">{company.phone ?? "-"}</TableCell>
                  <TableCell className="text-sm">{company.address ?? "-"}</TableCell>
                  <TableCell className="text-sm">{company.logistics_info ?? "-"}</TableCell>
                  <TableCell className="text-sm">
                    ¥{Number(company.credit_limit).toLocaleString()}
                  </TableCell>
                  <TableCell className="text-sm">
                    {company.salesperson_name ?? "-"}
                  </TableCell>
                  <TableCell className="max-w-[200px]">
                    <div className="text-sm text-muted-foreground whitespace-pre-wrap line-clamp-3">
                      {company.notes ?? "-"}
                    </div>
                  </TableCell>
                  <TableCell>
                    <div className="flex gap-1">
                      <Button variant="ghost" size="icon" className="h-8 w-8" onClick={() => handleEdit(company)}>
                        <Pencil className="h-4 w-4" />
                      </Button>
                      <Button variant="ghost" size="icon" className="h-8 w-8 text-red-500 hover:text-red-600" onClick={() => handleDelete(company)}>
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

      {/* 分页 */}
      {totalPages > 1 && (
        <div className="flex items-center justify-between">
          <div className="text-sm text-muted-foreground">
            显示 {(page - 1) * PAGE_SIZE + 1} - {Math.min(page * PAGE_SIZE, data?.total ?? 0)} / 共 {data?.total ?? 0} 条
          </div>
          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() => handlePageChange(page - 1)}
              disabled={page <= 1}
            >
              <ChevronLeft className="h-4 w-4" />
            </Button>
            <span className="text-sm">
              {page} / {totalPages}
            </span>
            <Button
              variant="outline"
              size="sm"
              onClick={() => handlePageChange(page + 1)}
              disabled={page >= totalPages}
            >
              <ChevronRight className="h-4 w-4" />
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}
