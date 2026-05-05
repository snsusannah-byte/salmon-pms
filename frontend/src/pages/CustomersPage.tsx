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
    queryKey: ["customers", search],
    queryFn: async () => {
      const params = new URLSearchParams();
      params.set("type", "customer");
      params.set("limit", "500");
      if (search) params.set("search", search);
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
        const unpaid = Number(s.net_amount || 0) - Number(s.paid_amount || 0);
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

    const payload: any = {
      name: formName.trim(),
      company_full_name: formCompanyFullName.trim() || undefined,
      brands: formBrands.trim() || undefined,
      type: "customer",
      contact_person: formContact.trim() || undefined,
      phone: formPhone.trim() || undefined,
      address: formAddress.trim() || undefined,
      credit_limit: formCreditLimit ? Number(formCreditLimit) : undefined,
      customer_category: formCategory || undefined,
      salesperson_id: formSalespersonId ? Number(formSalespersonId) : undefined,
      bank_name: formBankName.trim() || undefined,
      bank_account: formBankAccount.trim() || undefined,
      logistics_info: formLogistics.trim() || undefined,
      notes: formNotes.trim() || undefined,
      is_active: formIsActive,
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
      <div className="flex gap-4">
        <div className="relative max-w-sm">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <Input
            placeholder="搜索客户名称..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="pl-9"
          />
        </div>
      </div>

      {/* Customer List */}
      <Card>
        <CardContent className="p-0">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead className="text-xs">客户名称</TableHead>
                <TableHead className="text-xs">公司全称</TableHead>
                <TableHead className="text-xs text-right">应收款</TableHead>
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
                  <TableCell colSpan={10} className="text-center py-8">加载中...</TableCell>
                </TableRow>
              ) : customers?.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={10} className="text-center text-muted-foreground py-8">
                    暂无客户数据
                  </TableCell>
                </TableRow>
              ) : (
                customers?.map((c) => (
                  <TableRow key={c.id}>
                    <TableCell className="text-sm font-medium">{c.name}</TableCell>
                    <TableCell className="text-xs text-muted-foreground">{c.company_full_name || "-"}</TableCell>
                    <TableCell className="text-xs text-right">
                      {receivables[c.id] ? (
                        <span className="text-red-600 font-medium">{fmt$(receivables[c.id])}</span>
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
                          onClick={() => { setDetailId(c.id); setDetailOpen(true); }}
                          title="详情"
                        >
                          <Eye className="h-3.5 w-3.5" />
                        </Button>
                        <Button
                          variant="ghost"
                          size="icon"
                          className="h-7 w-7"
                          onClick={() => handleOpenEdit(c)}
                          title="编辑"
                        >
                          <Pencil className="h-3.5 w-3.5" />
                        </Button>
                        <Button
                          variant="ghost"
                          size="icon"
                          className="h-7 w-7 text-red-500"
                          onClick={() => handleOpenDelete(c)}
                          title="删除"
                        >
                          <Trash2 className="h-3.5 w-3.5" />
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

      {/* Create/Edit Form Dialog */}
      <Dialog open={formOpen} onOpenChange={setFormOpen}>
        <DialogContent className="max-w-[520px] max-h-[85vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>{editingCustomer ? "编辑客户" : "新增客户"}</DialogTitle>
          </DialogHeader>
          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-1">
                <Label className="text-xs">客户名称 *</Label>
                <Input value={formName} onChange={(e) => setFormName(e.target.value)} placeholder="必填" />
              </div>
              <div className="space-y-1">
                <Label className="text-xs">公司全称</Label>
                <Input value={formCompanyFullName} onChange={(e) => setFormCompanyFullName(e.target.value)} placeholder="可选" />
              </div>
            </div>
            <div className="space-y-1">
              <Label className="text-xs">旗下品牌（多个用逗号分隔）</Label>
              <Input value={formBrands} onChange={(e) => setFormBrands(e.target.value)} placeholder="如：品牌A, 品牌B" />
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-1">
                <Label className="text-xs">客户分类</Label>
                <Select value={formCategory} onValueChange={(v) => setFormCategory(v ?? "")}>
                  <SelectTrigger className="h-9 text-xs">
                    <SelectValue placeholder="选择分类" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="wholesaler">批发商</SelectItem>
                    <SelectItem value="distributor">渠道商</SelectItem>
                    <SelectItem value="retailer">零售商</SelectItem>
                    <SelectItem value="platform">平台</SelectItem>
                    <SelectItem value="group_buying">团购</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-1">
                <Label className="text-xs">信用额度</Label>
                <Input type="number" value={formCreditLimit} onChange={(e) => setFormCreditLimit(e.target.value)} placeholder="可选" />
              </div>
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-1">
                <Label className="text-xs">联系人</Label>
                <Input value={formContact} onChange={(e) => setFormContact(e.target.value)} placeholder="可选" />
              </div>
              <div className="space-y-1">
                <Label className="text-xs">电话</Label>
                <Input value={formPhone} onChange={(e) => setFormPhone(e.target.value)} placeholder="可选" />
              </div>
            </div>
            <div className="space-y-1">
              <Label className="text-xs">地址</Label>
              <Input value={formAddress} onChange={(e) => setFormAddress(e.target.value)} placeholder="可选" />
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-1">
                <Label className="text-xs">业务员</Label>
                <Select value={formSalespersonId} onValueChange={(v) => setFormSalespersonId(v ?? "")}>
                  <SelectTrigger className="h-9 text-xs">
                    <SelectValue placeholder="选择业务员" />
                  </SelectTrigger>
                  <SelectContent>
                    {salespersons.map((sp) => (
                      <SelectItem key={sp.id} value={String(sp.id)} className="text-xs">{sp.name}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-1">
                <Label className="text-xs">状态</Label>
                <Select value={formIsActive ? "active" : "inactive"} onValueChange={(v) => setFormIsActive(v === "active")}>
                  <SelectTrigger className="h-9 text-xs">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="active">启用</SelectItem>
                    <SelectItem value="inactive">停用</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-1">
                <Label className="text-xs">开户行</Label>
                <Input value={formBankName} onChange={(e) => setFormBankName(e.target.value)} placeholder="可选" />
              </div>
              <div className="space-y-1">
                <Label className="text-xs">银行账号</Label>
                <Input value={formBankAccount} onChange={(e) => setFormBankAccount(e.target.value)} placeholder="可选" />
              </div>
            </div>
            <div className="space-y-1">
              <Label className="text-xs">物流信息</Label>
              <Input value={formLogistics} onChange={(e) => setFormLogistics(e.target.value)} placeholder="可选" />
            </div>
            <div className="space-y-1">
              <Label className="text-xs">备注</Label>
              <Input value={formNotes} onChange={(e) => setFormNotes(e.target.value)} placeholder="可选" />
            </div>
            <DialogFooter>
              <Button type="button" variant="outline" onClick={() => setFormOpen(false)}>取消</Button>
              <Button type="submit" disabled={createMutation.isPending || updateMutation.isPending}>
                {createMutation.isPending || updateMutation.isPending ? "保存中..." : "保存"}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>

      {/* Delete Confirm Dialog */}
      <Dialog open={deleteOpen} onOpenChange={setDeleteOpen}>
        <DialogContent className="max-w-sm">
          <DialogHeader>
            <DialogTitle>确认删除</DialogTitle>
          </DialogHeader>
          <p className="text-sm text-muted-foreground">
            确定要删除客户 <span className="font-medium">{deleteCustomer?.name}</span> 吗？<br/>
            此操作不可撤销。
          </p>
          <DialogFooter>
            <Button variant="outline" onClick={() => setDeleteOpen(false)}>取消</Button>
            <Button variant="destructive" onClick={() => deleteCustomer && deleteMutation.mutate(deleteCustomer.id)} disabled={deleteMutation.isPending}>
              {deleteMutation.isPending ? "删除中..." : "确认删除"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Detail Dialog */}
      <Dialog open={detailOpen} onOpenChange={(open) => { setDetailOpen(open); if (!open) setDetailId(null); }}>
        <DialogContent className="max-w-[800px] max-h-[85vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle className="text-base">客户详情 - {customer?.name}</DialogTitle>
          </DialogHeader>
          
          {customer ? (
            <Tabs defaultValue="info">
              <TabsList className="grid w-full grid-cols-3">
                <TabsTrigger value="info">基本信息</TabsTrigger>
                <TabsTrigger value="sales">销售记录</TabsTrigger>
                <TabsTrigger value="finance">财务信息</TabsTrigger>
              </TabsList>
              
              <TabsContent value="info" className="space-y-4 pt-4">
                <div className="grid grid-cols-2 gap-3">
                  <Card>
                    <CardHeader className="pb-2">
                      <CardTitle className="text-sm">基本信息</CardTitle>
                    </CardHeader>
                    <CardContent className="space-y-2 text-xs">
                      <div className="flex justify-between"><span className="text-muted-foreground">公司全称</span><span>{customer.company_full_name || "-"}</span></div>
                      <div className="flex justify-between"><span className="text-muted-foreground">旗下品牌</span><span>{customer.brands || "-"}</span></div>
                      <div className="flex justify-between"><span className="text-muted-foreground">分类</span><span>{customer.customer_category ? customerCategoryMap[customer.customer_category] : "-"}</span></div>
                      <div className="flex justify-between"><span className="text-muted-foreground">联系人</span><span>{customer.contact_person || "-"}</span></div>
                      <div className="flex justify-between"><span className="text-muted-foreground">电话</span><span>{customer.phone || "-"}</span></div>
                      <div className="flex justify-between"><span className="text-muted-foreground">地址</span><span>{customer.address || "-"}</span></div>
                    </CardContent>
                  </Card>
                  <Card>
                    <CardHeader className="pb-2">
                      <CardTitle className="text-sm">资质与物流</CardTitle>
                    </CardHeader>
                    <CardContent className="space-y-2 text-xs">
                      <div className="flex justify-between"><span className="text-muted-foreground">业务员</span><span>{customer.salesperson_name || "-"}</span></div>
                      <div className="flex justify-between"><span className="text-muted-foreground">物流信息</span><span>{customer.logistics_info || "-"}</span></div>
                      <div className="flex justify-between"><span className="text-muted-foreground">状态</span><span>{customer.is_active ? "启用" : "停用"}</span></div>
                      <div className="flex justify-between"><span className="text-muted-foreground">备注</span><span>{customer.notes || "-"}</span></div>
                    </CardContent>
                  </Card>
                </div>
              </TabsContent>

              <TabsContent value="sales" className="pt-4">
                {summary && (
                  <div className="space-y-4">
                    <div className="grid grid-cols-4 gap-3">
                      <Card><CardContent className="p-3">
                        <div className="text-xs text-muted-foreground">总销售额</div>
                        <div className="text-lg font-bold">{fmt$(summary.total_sales)}</div>
                      </CardContent></Card>
                      <Card><CardContent className="p-3">
                        <div className="text-xs text-muted-foreground">已收款</div>
                        <div className="text-lg font-bold text-green-600">{fmt$(summary.total_paid)}</div>
                      </CardContent></Card>
                      <Card><CardContent className="p-3">
                        <div className="text-xs text-muted-foreground">未收款</div>
                        <div className="text-lg font-bold text-red-600">{fmt$(summary.total_unpaid)}</div>
                      </CardContent></Card>
                      <Card><CardContent className="p-3">
                        <div className="text-xs text-muted-foreground">销售笔数</div>
                        <div className="text-lg font-bold">{summary.sales_count}</div>
                      </CardContent></Card>
                    </div>
                    {summary.sales && summary.sales.length > 0 && (
                      <div className="border rounded-lg overflow-hidden">
                        <p className="text-xs font-semibold px-3 py-2 bg-muted/50">销售记录</p>
                        <Table>
                          <TableHeader>
                            <TableRow className="bg-muted/50">
                              <TableHead className="text-xs">日期</TableHead>
                              <TableHead className="text-xs">单号</TableHead>
                              <TableHead className="text-xs">规格</TableHead>
                              <TableHead className="text-xs text-right">箱数</TableHead>
                              <TableHead className="text-xs text-right">重量(kg)</TableHead>
                              <TableHead className="text-xs text-right">单价</TableHead>
                              <TableHead className="text-xs text-right">净额</TableHead>
                              <TableHead className="text-xs text-right">已付</TableHead>
                              <TableHead className="text-xs">状态</TableHead>
                            </TableRow>
                          </TableHeader>
                          <TableBody>
                            {summary.sales.map((sale) => (
                              <TableRow key={sale.id}>
                                <TableCell className="text-xs">{fmtDate(sale.sale_date)}</TableCell>
                                <TableCell className="text-xs">{sale.sale_no}</TableCell>
                                <TableCell className="text-xs">{sale.spec || "-"}</TableCell>
                                <TableCell className="text-xs text-right">{sale.box_count}</TableCell>
                                <TableCell className="text-xs text-right">{Number(sale.weight_kg || 0).toLocaleString()}</TableCell>
                                <TableCell className="text-xs text-right">{fmt$(sale.unit_price)}</TableCell>
                                <TableCell className="text-xs text-right font-medium">{fmt$(sale.net_amount)}</TableCell>
                                <TableCell className="text-xs text-right">{fmt$(sale.paid_amount)}</TableCell>
                                <TableCell className="text-xs">
                                  <Badge variant="outline" className="text-[10px] h-5">
                                    {sale.status === "fully_paid" ? "已付清" : sale.status === "partial_paid" ? "部分付款" : "未付款"}
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
              </TabsContent>

              <TabsContent value="finance" className="pt-4">
                <div className="grid grid-cols-2 gap-3">
                  <Card>
                    <CardHeader className="pb-2"><CardTitle className="text-sm">银行信息</CardTitle></CardHeader>
                    <CardContent className="space-y-2 text-xs">
                      <div className="flex justify-between"><span className="text-muted-foreground">开户行</span><span>{customer.bank_name || "-"}</span></div>
                      <div className="flex justify-between"><span className="text-muted-foreground">银行账号</span><span>{customer.bank_account || "-"}</span></div>
                    </CardContent>
                  </Card>
                  <Card>
                    <CardHeader className="pb-2"><CardTitle className="text-sm">信用信息</CardTitle></CardHeader>
                    <CardContent className="space-y-2 text-xs">
                      <div className="flex justify-between"><span className="text-muted-foreground">信用额度</span><span>{customer.credit_limit ? fmt$(customer.credit_limit) : "-"}</span></div>
                      <div className="flex justify-between"><span className="text-muted-foreground">信用余额</span><span>{fmt$(customer.credit_balance)}</span></div>
                      <div className="flex justify-between"><span className="text-muted-foreground">月度限额</span><span>{fmt$(customer.monthly_purchase_limit)}</span></div>
                      <div className="flex justify-between"><span className="text-muted-foreground">本月采购</span><span>{fmt$(customer.monthly_purchase_amount)}</span></div>
                    </CardContent>
                  </Card>
                </div>
              </TabsContent>
            </Tabs>
          ) : (
            <div className="py-8 text-center">加载中...</div>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
}
