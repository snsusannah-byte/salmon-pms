import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
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
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Search, Eye, Plus, Pencil, Trash2 } from "lucide-react";
import { toast } from "sonner";

interface Customer {
  id: number;
  name: string;
  company_full_name: string | null;
  brands: string | null;
  code: string | null;
  type: string;
  contact_person: string | null;
  phone: string | null;
  email: string | null;
  address: string | null;
  credit_limit: number | null;
  credit_balance: number | null;
  is_credit_enabled: boolean;
  monthly_purchase_limit: number | null;
  monthly_purchase_amount: number | null;
  prepaid_balance: number | null;
  customer_category: string | null;
  salesperson_id: number | null;
  salesperson_name: string | null;
  bank_name: string | null;
  bank_account: string | null;
  logistics_info: string | null;
  notes: string | null;
  is_active: boolean;
  created_at: string;
}

interface CustomerSale {
  id: number;
  sale_no: string;
  sale_date: string;
  spec: string | null;
  box_count: number;
  weight_kg: number;
  unit_price: number;
  gross_amount: number;
  net_amount: number;
  paid_amount: number;
  status: string;
}

interface CustomerSummary {
  total_sales: number;
  total_paid: number;
  total_unpaid: number;
  sales_count: number;
  last_sale_date: string | null;
}

interface Salesperson {
  id: number;
  name: string;
}

const customerCategoryMap: Record<string, string> = {
  wholesaler: "批发商",
  distributor: "渠道商",
  retailer: "零售商",
  platform: "平台",
  group_buying: "团购",
};

function fmt$(v: number | string | null | undefined) {
  const n = Number(v ?? 0);
  if (Number.isNaN(n)) return "¥0.00";
  return `¥${n.toLocaleString("zh-CN", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

function fmtDate(d: string | null | undefined) {
  if (!d) return "-";
  return new Date(d).toLocaleDateString("zh-CN");
}

export function CustomersPage() {
  const qc = useQueryClient();
  const [search, setSearch] = useState("");
  const [categoryFilter, setCategoryFilter] = useState("all");
  const [detailId, setDetailId] = useState<number | null>(null);
  const [detailOpen, setDetailOpen] = useState(false);

  // Form state for create/edit
  const [formOpen, setFormOpen] = useState(false);
  const [editingCustomer, setEditingCustomer] = useState<Customer | null>(null);
  const [deleteCustomer, setDeleteCustomer] = useState<Customer | null>(null);
  const [deleteOpen, setDeleteOpen] = useState(false);

  // Form fields
  const [formName, setFormName] = useState("");
  const [formCompanyFullName, setFormCompanyFullName] = useState("");
  const [formBrands, setFormBrands] = useState("");
  const [formContact, setFormContact] = useState("");
  const [formPhone, setFormPhone] = useState("");
  const [formAddress, setFormAddress] = useState("");
  const [formCreditLimit, setFormCreditLimit] = useState("");
  const [formCategory, setFormCategory] = useState("");
  const [formSalespersonId, setFormSalespersonId] = useState("");
  const [formBankName, setFormBankName] = useState("");
  const [formBankAccount, setFormBankAccount] = useState("");
  const [formLogistics, setFormLogistics] = useState("");
  const [formNotes, setFormNotes] = useState("");
  const [formIsActive, setFormIsActive] = useState(true);

  const resetForm = () => {
    setFormName("");
    setFormCompanyFullName("");
    setFormBrands("");
    setFormContact("");
    setFormPhone("");
    setFormAddress("");
    setFormCreditLimit("");
    setFormCategory("");
    setFormSalespersonId("");
    setFormBankName("");
    setFormBankAccount("");
    setFormLogistics("");
    setFormNotes("");
    setFormIsActive(true);
    setEditingCustomer(null);
  };

  const loadCustomerIntoForm = (c: Customer) => {
    setFormName(c.name || "");
    setFormCompanyFullName(c.company_full_name || "");
    setFormBrands(c.brands || "");
    setFormContact(c.contact_person || "");
    setFormPhone(c.phone || "");
    setFormAddress(c.address || "");
    setFormCreditLimit(c.credit_limit ? String(c.credit_limit) : "");
    setFormCategory(c.customer_category || "");
    setFormSalespersonId(c.salesperson_id ? String(c.salesperson_id) : "");
    setFormBankName(c.bank_name || "");
    setFormBankAccount(c.bank_account || "");
    setFormLogistics(c.logistics_info || "");
    setFormNotes(c.notes || "");
    setFormIsActive(c.is_active ?? true);
  };

  const { data: customers, isLoading } = useQuery({
    queryKey: ["customers", search, categoryFilter],
    queryFn: async () => {
      const params = new URLSearchParams();
      params.set("type", "customer");
      params.set("limit", "500");
      if (search) params.set("search", search);
      if (categoryFilter && categoryFilter !== "all") params.set("customer_category", categoryFilter);
      const res = await api.get(`/v1/companies/?${params.toString()}`);
      return res.data.items as Customer[];
    },
  });

  // Fetch salespersons for dropdown
  const { data: salespersonsData } = useQuery({
    queryKey: ["salespersons-dropdown"],
    queryFn: async () => {
      const res = await api.get("/v1/salespersons?limit=500");
      return res.data?.items || [];
    },
  });
  const salespersons: Salesperson[] = salespersonsData || [];

  // Fetch customer receivables (total_unpaid per customer)
  const { data: receivablesData } = useQuery({
    queryKey: ["customer-receivables"],
    queryFn: async () => {
      const res = await api.get("/v1/sales/whole-fish?limit=500");
      const sales = res.data?.items || [];

      const map: Record<number, number> = {};
      for (const s of sales) {
        const net = Number(s.net_amount || 0);
        const paid = Number(s.paid_amount || 0);
        const unpaid = Math.max(0, net - paid);
        if (unpaid > 0) {
          map[s.customer_id] = (map[s.customer_id] || 0) + unpaid;
        }
      }
      return map;
    },
    enabled: !!customers?.length,
  });
  const receivables = receivablesData || {};

  const createMutation = useMutation({
    mutationFn: async (payload: any) => {
      const res = await api.post("/v1/companies/", payload);
      return res.data;
    },
    onSuccess: () => {
      toast.success("客户创建成功");
      qc.invalidateQueries({ queryKey: ["customers"] });
      setFormOpen(false);
      resetForm();
    },
    onError: (err: any) => toast.error(err.response?.data?.detail || "创建失败"),
  });

  const updateMutation = useMutation({
    mutationFn: async ({ id, payload }: { id: number; payload: any }) => {
      const res = await api.put(`/v1/companies/${id}`, payload);
      return res.data;
    },
    onSuccess: () => {
      toast.success("客户更新成功");
      qc.invalidateQueries({ queryKey: ["customers"] });
      setFormOpen(false);
      resetForm();
    },
    onError: (err: any) => toast.error(err.response?.data?.detail || "更新失败"),
  });

  const deleteMutation = useMutation({
    mutationFn: async (id: number) => {
      await api.delete(`/v1/companies/${id}`);
    },
    onSuccess: () => {
      toast.success("客户已删除");
      qc.invalidateQueries({ queryKey: ["customers"] });
      setDeleteOpen(false);
      setDeleteCustomer(null);
    },
    onError: (err: any) => toast.error(err.response?.data?.detail || "删除失败"),
  });

  const { data: summary } = useQuery({
    queryKey: ["customer-summary", detailId],
    queryFn: async () => {
      if (!detailId) return null;
      const res = await api.get(`/v1/sales/whole-fish?customer_id=${detailId}&limit=500`);
      const sales = res.data.items as CustomerSale[];
      const total_sales = sales.reduce((sum, s) => sum + Number(s.net_amount || 0), 0);
      const total_paid = sales.reduce((sum, s) => sum + Number(s.paid_amount || 0), 0);
      return {
        total_sales,
        total_paid,
        total_unpaid: total_sales - total_paid,
        sales_count: sales.length,
        last_sale_date: sales.length > 0 ? sales[0].sale_date : null,
        sales,
      } as CustomerSummary & { sales: CustomerSale[] };
    },
    enabled: !!detailId,
  });

  const customer = customers?.find((c) => c.id === detailId);

  const handleOpenCreate = () => {
    resetForm();
    setFormOpen(true);
  };

  const handleOpenEdit = (c: Customer) => {
    setEditingCustomer(c);
    loadCustomerIntoForm(c);
    setFormOpen(true);
  };

  const handleOpenDelete = (c: Customer) => {
    setDeleteCustomer(c);
    setDeleteOpen(true);
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!formName.trim()) {
      toast.error("客户名称必填");
      return;
    }

    const payload = {
      name: formName.trim(),
      company_full_name: formCompanyFullName.trim() || null,
      brands: formBrands.trim() || null,
      contact_person: formContact.trim() || null,
      phone: formPhone.trim() || null,
      address: formAddress.trim() || null,
      credit_limit: formCreditLimit ? Number(formCreditLimit) : null,
      customer_category: formCategory || null,
      salesperson_id: formSalespersonId ? Number(formSalespersonId) : null,
      bank_name: formBankName.trim() || null,
      bank_account: formBankAccount.trim() || null,
      logistics_info: formLogistics.trim() || null,
      notes: formNotes.trim() || null,
      is_active: formIsActive,
      type: "customer",
    };

    if (editingCustomer) {
      updateMutation.mutate({ id: editingCustomer.id, payload });
    } else {
      createMutation.mutate(payload);
    }
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">客户管理</h1>
          <p className="text-sm text-muted-foreground">客户信息、信用额度、应收款</p>
        </div>
        <Button onClick={handleOpenCreate}>
          <Plus className="h-4 w-4 mr-2" />
          新增客户
        </Button>
      </div>

      {/* Search */}
      <div className="flex gap-4 items-center flex-wrap">
        <div className="relative max-w-sm">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <Input
            placeholder="搜索客户名称..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="pl-9"
          />
        </div>
        <Select value={categoryFilter} onValueChange={setCategoryFilter}>
          <SelectTrigger className="w-[160px]">
            <SelectValue placeholder="全部分类" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">全部分类</SelectItem>
            {Object.entries(customerCategoryMap).map(([key, label]) => (
              <SelectItem key={key} value={key}>{label}</SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      {/* Customer List */}
      <Card>
        <CardContent className="p-0">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead className="text-xs">客户名称</TableHead>
                <TableHead className="text-xs">公司全称</TableHead>
                <TableHead className="text-xs text-right cursor-pointer hover:bg-muted" onClick={() => { /* 点击表头也可排序 */ }}>应收款</TableHead>
                <TableHead className="text-xs text-right">预付款余额</TableHead>
                <TableHead className="text-xs">分类</TableHead>
                <TableHead className="text-xs">联系人</TableHead>
                <TableHead className="text-xs">电话</TableHead>
                <TableHead className="text-xs text-right">信用额度</TableHead>
                <TableHead className="text-xs text-center">状态</TableHead>
                <TableHead className="text-xs text-center">操作</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {isLoading ? (
                <TableRow>
                  <TableCell colSpan={11} className="text-center py-8">加载中...</TableCell>
                </TableRow>
              ) : customers?.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={11} className="text-center text-muted-foreground py-8">
                    暂无客户数据
                  </TableCell>
                </TableRow>
              ) : (
                // 按应收款降序排列
                [...(customers || [])]
                  .sort((a, b) => (receivables[b.id] || 0) - (receivables[a.id] || 0))
                  .map((c) => (
                  <TableRow key={c.id}>
                    <TableCell className="text-sm font-medium">{c.name}</TableCell>
                    <TableCell className="text-xs text-muted-foreground">{c.company_full_name || "-"}</TableCell>
                    <TableCell className="text-xs text-right">
                      {receivables[c.id] ? (
                        <span className="text-red-600 font-medium">{fmt$(receivables[c.id])}</span>
                      ) : "-"}
                    </TableCell>
                    <TableCell className="text-xs text-right">
                      {c.prepaid_balance && Number(c.prepaid_balance) > 0 ? (
                        <span className="text-green-600 font-medium">{fmt$(c.prepaid_balance)}</span>
                      ) : "-"}
                    </TableCell>
                    <TableCell className="text-xs">
                      {c.customer_category ? (
                        <Badge variant="outline" className="text-[10px]">
                          {customerCategoryMap[c.customer_category] || c.customer_category}
                        </Badge>
                      ) : "-"}
                    </TableCell>
                    <TableCell className="text-xs">{c.contact_person || "-"}</TableCell>
                    <TableCell className="text-xs">{c.phone || "-"}</TableCell>
                    <TableCell className="text-xs text-right">
                      {c.credit_limit ? fmt$(c.credit_limit) : "-"}
                    </TableCell>
                    <TableCell className="text-xs text-center">
                      {c.is_active ? (
                        <span className="text-green-600">启用</span>
                      ) : (
                        <span className="text-muted-foreground">停用</span>
                      )}
                    </TableCell>
                    <TableCell className="text-center">
                      <div className="flex justify-center gap-1">
                        <Button
                          variant="ghost"
                          size="icon"
                          className="h-7 w-7"
                          onClick={() => {
                            setDetailId(c.id);
                            setDetailOpen(true);
                          }}
                        >
                          <Eye className="h-4 w-4" />
                        </Button>
                        <Button
                          variant="ghost"
                          size="icon"
                          className="h-7 w-7"
                          onClick={() => handleOpenEdit(c)}
                        >
                          <Pencil className="h-4 w-4" />
                        </Button>
                        <Button
                          variant="ghost"
                          size="icon"
                          className="h-7 w-7 text-red-500"
                          onClick={() => handleOpenDelete(c)}
                        >
                          <Trash2 className="h-4 w-4" />
                        </Button>
                      </div>
                    </TableCell>
                  </TableRow>
                ))
              )}
            </TableBody>
          </Table>
        </CardContent>
      </Card>

      {/* Detail Dialog */}
      <Dialog open={detailOpen} onOpenChange={setDetailOpen}>
        <DialogContent className="max-w-3xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>客户详情</DialogTitle>
          </DialogHeader>
          {customer && (
            <div className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <Label className="text-xs text-muted-foreground">客户名称</Label>
                  <div className="font-medium">{customer.name}</div>
                </div>
                <div>
                  <Label className="text-xs text-muted-foreground">公司全称</Label>
                  <div>{customer.company_full_name || "-"}</div>
                </div>
                <div>
                  <Label className="text-xs text-muted-foreground">分类</Label>
                  <div>
                    {customer.customer_category ? (
                      <Badge variant="outline">
                        {customerCategoryMap[customer.customer_category] || customer.customer_category}
                      </Badge>
                    ) : "-"}
                  </div>
                </div>
                <div>
                  <Label className="text-xs text-muted-foreground">业务员</Label>
                  <div>{customer.salesperson_name || "-"}</div>
                </div>
                <div>
                  <Label className="text-xs text-muted-foreground">联系人</Label>
                  <div>{customer.contact_person || "-"}</div>
                </div>
                <div>
                  <Label className="text-xs text-muted-foreground">电话</Label>
                  <div>{customer.phone || "-"}</div>
                </div>
                <div>
                  <Label className="text-xs text-muted-foreground">信用额度</Label>
                  <div>{customer.credit_limit ? fmt$(customer.credit_limit) : "-"}</div>
                </div>
                <div>
                  <Label className="text-xs text-muted-foreground">预付款余额</Label>
                  <div>{customer.prepaid_balance ? fmt$(customer.prepaid_balance) : "-"}</div>
                </div>
              </div>

              {summary && (
                <div className="border rounded-lg p-4 space-y-2">
                  <h3 className="font-medium">销售统计</h3>
                  <div className="grid grid-cols-3 gap-4">
                    <div>
                      <div className="text-xs text-muted-foreground">总销售额</div>
                      <div className="font-medium">{fmt$(summary.total_sales)}</div>
                    </div>
                    <div>
                      <div className="text-xs text-muted-foreground">已付款</div>
                      <div className="font-medium text-green-600">{fmt$(summary.total_paid)}</div>
                    </div>
                    <div>
                      <div className="text-xs text-muted-foreground">未付款</div>
                      <div className="font-medium text-red-600">{fmt$(summary.total_unpaid)}</div>
                    </div>
                  </div>
                  <div className="text-xs text-muted-foreground">
                    共 {summary.sales_count} 笔销售
                    {summary.last_sale_date ? `，最近销售 ${fmtDate(summary.last_sale_date)}` : ""}
                  </div>
                </div>
              )}

              {summary?.sales && summary.sales.length > 0 && (
                <div className="border rounded-lg overflow-hidden">
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead className="text-xs">销售单号</TableHead>
                        <TableHead className="text-xs">日期</TableHead>
                        <TableHead className="text-xs">规格</TableHead>
                        <TableHead className="text-xs text-right">数量</TableHead>
                        <TableHead className="text-xs text-right">重量</TableHead>
                        <TableHead className="text-xs text-right">金额</TableHead>
                        <TableHead className="text-xs text-right">已付</TableHead>
                        <TableHead className="text-xs text-center">状态</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {summary.sales.map((sale) => (
                        <TableRow key={sale.id}>
                          <TableCell className="text-xs font-medium">{sale.sale_no}</TableCell>
                          <TableCell className="text-xs">{fmtDate(sale.sale_date)}</TableCell>
                          <TableCell className="text-xs">{sale.spec || "-"}</TableCell>
                          <TableCell className="text-xs text-right">{sale.box_count}</TableCell>
                          <TableCell className="text-xs text-right">{sale.weight_kg} kg</TableCell>
                          <TableCell className="text-xs text-right">{fmt$(sale.net_amount)}</TableCell>
                          <TableCell className="text-xs text-right">{fmt$(sale.paid_amount)}</TableCell>
                          <TableCell className="text-xs text-center">
                            <Badge variant="outline" className="text-[10px]">
                              {sale.status === "fully_paid" ? "已付清"
                                : sale.status === "partial_paid" ? "部分付款"
                                : sale.status === "pending" ? "待付款"
                                : sale.status}
                            </Badge>
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </div>
              )}
            </div>
          )}
        </DialogContent>
      </Dialog>

      {/* Create/Edit Dialog */}
      <Dialog open={formOpen} onOpenChange={setFormOpen}>
        <DialogContent className="max-w-lg max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>{editingCustomer ? "编辑客户" : "新增客户"}</DialogTitle>
          </DialogHeader>
          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label>客户名称 <span className="text-red-500">*</span></Label>
                <Input value={formName} onChange={(e) => setFormName(e.target.value)} />
              </div>
              <div className="space-y-2">
                <Label>公司全称</Label>
                <Input value={formCompanyFullName} onChange={(e) => setFormCompanyFullName(e.target.value)} />
              </div>
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label>分类</Label>
                <Select value={formCategory} onValueChange={setFormCategory}>
                  <SelectTrigger>
                    <SelectValue placeholder="选择分类" />
                  </SelectTrigger>
                  <SelectContent>
                    {Object.entries(customerCategoryMap).map(([key, label]) => (
                      <SelectItem key={key} value={key}>{label}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-2">
                <Label>业务员</Label>
                <Select value={formSalespersonId} onValueChange={setFormSalespersonId}>
                  <SelectTrigger>
                    <SelectValue placeholder="选择业务员" />
                  </SelectTrigger>
                  <SelectContent>
                    {salespersons.map((sp) => (
                      <SelectItem key={sp.id} value={String(sp.id)}>{sp.name}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label>联系人</Label>
                <Input value={formContact} onChange={(e) => setFormContact(e.target.value)} />
              </div>
              <div className="space-y-2">
                <Label>电话</Label>
                <Input value={formPhone} onChange={(e) => setFormPhone(e.target.value)} />
              </div>
            </div>
            <div className="space-y-2">
              <Label>地址</Label>
              <Input value={formAddress} onChange={(e) => setFormAddress(e.target.value)} />
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label>信用额度</Label>
                <Input
                  type="number"
                  value={formCreditLimit}
                  onChange={(e) => setFormCreditLimit(e.target.value)}
                  placeholder="0"
                />
              </div>
              <div className="space-y-2">
                <Label>品牌</Label>
                <Input value={formBrands} onChange={(e) => setFormBrands(e.target.value)} />
              </div>
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label>银行名称</Label>
                <Input value={formBankName} onChange={(e) => setFormBankName(e.target.value)} />
              </div>
              <div className="space-y-2">
                <Label>银行账号</Label>
                <Input value={formBankAccount} onChange={(e) => setFormBankAccount(e.target.value)} />
              </div>
            </div>
            <div className="space-y-2">
              <Label>物流信息</Label>
              <Input value={formLogistics} onChange={(e) => setFormLogistics(e.target.value)} />
            </div>
            <div className="space-y-2">
              <Label>备注</Label>
              <Input value={formNotes} onChange={(e) => setFormNotes(e.target.value)} />
            </div>
            <div className="flex items-center gap-2">
              <input
                type="checkbox"
                checked={formIsActive}
                onChange={(e) => setFormIsActive(e.target.checked)}
                id="is-active"
              />
              <Label htmlFor="is-active">启用</Label>
            </div>
            <DialogFooter>
              <Button type="button" variant="outline" onClick={() => { setFormOpen(false); resetForm(); }}>
                取消
              </Button>
              <Button type="submit" disabled={createMutation.isPending || updateMutation.isPending}>
                {editingCustomer ? "更新" : "创建"}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>

      {/* Delete Dialog */}
      <Dialog open={deleteOpen} onOpenChange={setDeleteOpen}>
        <DialogContent className="max-w-sm">
          <DialogHeader>
            <DialogTitle>确认删除</DialogTitle>
          </DialogHeader>
          <p className="text-sm text-muted-foreground">
            确定要删除客户「{deleteCustomer?.name}」吗？此操作不可撤销。
          </p>
          <DialogFooter>
            <Button variant="outline" onClick={() => setDeleteOpen(false)}>取消</Button>
            <Button
              variant="destructive"
              onClick={() => deleteCustomer && deleteMutation.mutate(deleteCustomer.id)}
              disabled={deleteMutation.isPending}
            >
              删除
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
