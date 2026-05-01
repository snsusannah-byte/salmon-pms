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
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { CompanyFormDialog } from "@/components/CompanyFormDialog";
import { DeleteConfirmDialog } from "@/components/DeleteConfirmDialog";
import { Plus, Search, Building2, Fish, Ship, Store, User, Truck, HardHat, Home, Pencil, Trash2, ChevronLeft, ChevronRight } from "lucide-react";
import { BatchImportButton } from "@/components/BatchImportButton";

const typeMap: Record<string, { label: string; icon: React.ElementType; color: string }> = {
  processing_plant: { label: "加工厂", icon: Building2, color: "bg-blue-100 text-blue-800" },
  fish_farm: { label: "渔场", icon: Fish, color: "bg-cyan-100 text-cyan-800" },
  exporter: { label: "出口商", icon: Ship, color: "bg-green-100 text-green-800" },
  supplier: { label: "供应商", icon: Store, color: "bg-purple-100 text-purple-800" },
  customs_broker: { label: "报关行", icon: HardHat, color: "bg-gray-100 text-gray-800" },
  logistics: { label: "物流", icon: Truck, color: "bg-yellow-100 text-yellow-800" },
  internal: { label: "内部", icon: Home, color: "bg-red-100 text-red-800" },
};

interface Company {
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

export function CompaniesPage() {
  const [search, setSearch] = useState("");
  const [type, setType] = useState<string>("all");
  const [page, setPage] = useState(1);
  const [formOpen, setFormOpen] = useState(false);
  const [editingCompany, setEditingCompany] = useState<Company | null>(null);
  const [deleteOpen, setDeleteOpen] = useState(false);
  const [deleteTarget, setDeleteTarget] = useState<Company | null>(null);

  const { data, isLoading } = useQuery<CompanyListResponse>({
    queryKey: ["companies", search, type, page, "exclude_customer"],
    queryFn: async () => {
      const params = new URLSearchParams();
      if (search) params.append("search", search);
      if (type && type !== "all") params.append("type", type);
      params.append("exclude_type", "customer");
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
          <h1 className="text-2xl font-bold">主体管理</h1>
          <p className="text-sm text-muted-foreground">
            共 {data?.total ?? 0} 个主体，第 {page}/{totalPages} 页
          </p>
        </div>
        <div className="flex gap-2">
          <BatchImportButton type="companies" />
          <Button onClick={handleAdd}>
            <Plus className="h-4 w-4 mr-2" />
            新增主体
          </Button>
        </div>
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
        <Select value={type} onValueChange={(v) => { setType(v ?? "all"); setPage(1); }}>
          <SelectTrigger className="w-[180px]">
            <SelectValue placeholder="全部类型">
              {type === "all" ? "全部类型" : typeMap[type]?.label ?? type}
            </SelectValue>
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">全部类型</SelectItem>
            {Object.entries(typeMap).map(([key, { label, icon: Icon }]) => (
              <SelectItem key={key} value={key}>
                <div className="flex items-center gap-2">
                  <Icon className="h-4 w-4" />
                  {label}
                </div>
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      {/* 数据表格 */}
      <div className="border rounded-lg">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>名称</TableHead>
              <TableHead>中文名称</TableHead>
              <TableHead>类型</TableHead>
              <TableHead>EU注册号</TableHead>
              <TableHead>CN海关准入</TableHead>
              <TableHead>养殖GGN</TableHead>
              <TableHead>监管链COC</TableHead>
              <TableHead>养殖区</TableHead>
              <TableHead>网址</TableHead>
              <TableHead>合作日期</TableHead>
              <TableHead>信用额度</TableHead>
              <TableHead className="w-[200px]">备注</TableHead>
              <TableHead className="w-[120px]">操作</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {isLoading ? (
              <TableRow>
                <TableCell colSpan={13} className="text-center py-8 text-muted-foreground">
                  加载中...
                </TableCell>
              </TableRow>
            ) : data?.items.length === 0 ? (
              <TableRow>
                <TableCell colSpan={13} className="text-center py-8 text-muted-foreground">
                  暂无数据，点击右上角新增主体
                </TableCell>
              </TableRow>
            ) : (
              data?.items.map((company) => {
                const typeInfo = typeMap[company.type];
                const Icon = typeInfo?.icon ?? Building2;
                return (
                  <TableRow key={company.id}>
                    <TableCell className="font-medium">{company.name}</TableCell>
                    <TableCell className="text-sm">{company.chinese_name ?? "-"}</TableCell>
                    <TableCell>
                      <Badge variant="secondary" className={typeInfo?.color ?? ""}>
                        <Icon className="h-3 w-3 mr-1" />
                        {typeInfo?.label ?? company.type}
                      </Badge>
                    </TableCell>
                    <TableCell className="text-muted-foreground text-sm">
                      {company.code ?? "-"}
                    </TableCell>
                    <TableCell className="text-muted-foreground text-sm">
                      {company.registration_code ?? "-"}
                    </TableCell>
                    <TableCell className="text-muted-foreground text-sm">
                      {company.enterprise_registration_no ?? "-"}
                    </TableCell>
                    <TableCell className="text-muted-foreground text-sm">
                      {company.coc_cert_no ?? "-"}
                    </TableCell>
                    <TableCell className="text-muted-foreground text-sm">
                      {company.farming_area ?? "-"}
                    </TableCell>
                    <TableCell className="text-sm">
                      {company.website ? (
                        (company.website.startsWith('http://') || company.website.startsWith('https://')) ? (
                          <a href={company.website} target="_blank" rel="noopener noreferrer" className="text-blue-500 hover:underline truncate max-w-[150px] inline-block">
                            {company.website.replace(/^https?:\/\//, '').substring(0, 20)}...
                          </a>
                        ) : (
                          <span className="text-muted-foreground" title={company.website}>
                            {company.website.substring(0, 20)}...
                          </span>
                        )
                      ) : "-"}
                    </TableCell>
                    <TableCell className="text-sm">
                      {company.cooperation_date
                        ? new Date(company.cooperation_date).toLocaleDateString("zh-CN")
                        : "-"}
                    </TableCell>
                    <TableCell>¥{Number(company.credit_limit).toLocaleString()}</TableCell>
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
