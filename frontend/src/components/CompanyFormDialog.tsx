import { useState, useEffect } from "react";
import { useForm, Controller } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import * as z from "zod";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Checkbox } from "@/components/ui/checkbox";
import { api } from "@/lib/api";
import { useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { Plus, Trash2 } from "lucide-react";

const companyTypes = [
  { value: "processing_plant", label: "加工厂" },
  { value: "fish_farm", label: "渔场" },
  { value: "exporter", label: "出口商" },
  { value: "supplier", label: "供应商" },
  { value: "customer", label: "客户" },
  { value: "customs_broker", label: "报关行" },
  { value: "logistics", label: "物流" },
  { value: "internal", label: "内部" },
];

const customerCategories = [
  { value: "wholesaler", label: "批发商" },
  { value: "distributor", label: "渠道商" },
  { value: "retailer", label: "零售商" },
  { value: "platform", label: "平台" },
  { value: "group_buying", label: "团购" },
];

const formSchema = z.object({
  name: z.string().min(1, "名称不能为空").max(200),
  chinese_name: z.string().max(200).optional().or(z.literal("")),
  company_full_name: z.string().max(200).optional().or(z.literal("")),
  type: z.string().min(1, "类型不能为空"),
  code: z.string().max(50).optional().or(z.literal("")),
  contact_person: z.string().max(100).optional().or(z.literal("")),
  phone: z.string().max(50).optional().or(z.literal("")),
  email: z.string().max(100).optional().or(z.literal("")).refine((v) => !v || /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(v), { message: "邮箱格式不正确" }),
  address: z.string().optional().or(z.literal("")),
  registration_code: z.string().max(100).optional().or(z.literal("")),
  enterprise_registration_no: z.string().max(100).optional().or(z.literal("")),
  coc_cert_no: z.string().max(100).optional().or(z.literal("")),
  farming_area: z.string().max(100).optional().or(z.literal("")),
  website: z.string().max(255).optional().or(z.literal("")),
  cooperation_date: z.string().optional().or(z.literal("")),
  bank_name: z.string().max(200).optional().or(z.literal("")),
  bank_account: z.string().max(100).optional().or(z.literal("")),
  credit_limit: z.string().optional().or(z.literal("")).refine((v) => !v || !isNaN(Number(v)), { message: "信用额度必须是有效数字" }),
  logistics_info: z.string().optional().or(z.literal("")),
  salesperson_id: z.string().optional().or(z.literal("")),
  customer_category: z.string().optional().or(z.literal("")),
  notes: z.string().optional().or(z.literal("")),
});

type FormData = z.infer<typeof formSchema>;

interface CompanyFormDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  initialData?: Company | null;
  defaultType?: string;
}

interface Company {
  id: number;
  name: string;
  chinese_name: string | null;
  company_full_name: string | null;
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
  cooperation_date: string | null;
  bank_name: string | null;
  bank_account: string | null;
  credit_limit: string;
  logistics_info: string | null;
  salesperson_id: number | null;
  customer_category: string | null;
  notes: string | null;
  is_active: boolean;
  bank_accounts?: BankAccountItem[];
}

interface BankAccountItem {
  id?: number;
  account_name: string;
  bank_name: string;
  account_number: string;
  currency: string;
  is_active: boolean;
  notes: string;
}

export function CompanyFormDialog({ open, onOpenChange, initialData, defaultType }: CompanyFormDialogProps) {
  const queryClient = useQueryClient();
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [users, setUsers] = useState<{id: number; full_name: string}[]>([]);
  const [bankAccounts, setBankAccounts] = useState<BankAccountItem[]>([]);

  const emptyBankAccount = (): BankAccountItem => ({
    account_name: "",
    bank_name: "",
    account_number: "",
    currency: "CNY",
    is_active: true,
    notes: "",
  });

  const addBankAccount = () => setBankAccounts((prev) => [...prev, emptyBankAccount()]);
  const removeBankAccount = (idx: number) => setBankAccounts((prev) => prev.filter((_, i) => i !== idx));
  const updateBankAccount = (idx: number, field: keyof BankAccountItem, value: any) =>
    setBankAccounts((prev) => prev.map((item, i) => (i === idx ? { ...item, [field]: value } : item)));

  // 获取用户列表（用于业务员选择）
  useEffect(() => {
    if (open) {
      api.get("/v1/auth/users", { validateStatus: (s) => s < 500 })  // 5xx 才抛错，401/403 正常处理
        .then(res => {
          if (res.status === 401) {
            toast.error("登录已过期，请重新登录");
            return;
          }
          if (res.status >= 200 && res.status < 300) {
            setUsers(res.data || []);
          } else {
            setUsers([]);
          }
        })
        .catch(() => setUsers([]));
    }
  }, [open]);

  const form = useForm<FormData>({
    resolver: zodResolver(formSchema),
    defaultValues: {
      name: "",
      chinese_name: "",
      company_full_name: "",
      type: "",
      code: "",
      contact_person: "",
      phone: "",
      email: "",
      address: "",
      cooperation_date: "",
      bank_name: "",
      bank_account: "",
      credit_limit: "",
      logistics_info: "",
      salesperson_id: "",
      customer_category: "",
      notes: "",
    },
  });

  // 当弹窗打开且 initialData 变化时，重置表单
  useEffect(() => {
    if (open) {
      resetForm();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open, initialData?.id]);

  // 当编辑时填充数据
  const resetForm = () => {
    if (initialData) {
      form.reset({
        name: initialData.name,
        chinese_name: initialData.chinese_name ?? "",
        company_full_name: initialData.company_full_name ?? "",
        type: initialData.type,
        code: initialData.code ?? "",
        contact_person: initialData.contact_person ?? "",
        phone: initialData.phone ?? "",
        email: initialData.email ?? "",
        address: initialData.address ?? "",
        registration_code: initialData.registration_code ?? "",
        enterprise_registration_no: initialData.enterprise_registration_no ?? "",
        coc_cert_no: initialData.coc_cert_no ?? "",
        farming_area: initialData.farming_area ?? "",
        website: initialData.website ?? "",
        cooperation_date: initialData.cooperation_date ?? "",
        bank_name: initialData.bank_name ?? "",
        bank_account: initialData.bank_account ?? "",
        credit_limit: initialData.credit_limit ?? "",
        logistics_info: initialData.logistics_info ?? "",
        salesperson_id: String(initialData.salesperson_id ?? ""),
        customer_category: initialData.customer_category ?? "",
        notes: initialData.notes ?? "",
      });
      setBankAccounts((initialData.bank_accounts || []).map((acc) => ({ ...acc })));
    } else {
      form.reset({
        name: "",
        chinese_name: "",
        company_full_name: "",
        type: defaultType || "",
        code: "",
        contact_person: "",
        phone: "",
        email: "",
        address: "",
        registration_code: "",
        enterprise_registration_no: "",
        coc_cert_no: "",
        farming_area: "",
        website: "",
        cooperation_date: "",
        bank_name: "",
        bank_account: "",
        credit_limit: "",
        logistics_info: "",
        salesperson_id: "",
        customer_category: "",
        notes: "",
      });
      setBankAccounts([]);
    }
  };

  // 类型切换时自动填充/清空养殖区
  useEffect(() => {
    const currentType = form.watch("type");
    if (currentType === "fish_farm") {
      if (!form.watch("farming_area")) form.setValue("farming_area", "FAO 27");
    } else if (currentType && currentType !== "fish_farm") {
      if (form.watch("farming_area") === "FAO 27") form.setValue("farming_area", "");
    }
  }, [form.watch("type")]);

  const onSubmit = async (data: FormData) => {
    setIsSubmitting(true);
    try {
      const payload: any = {
        ...data,
        cooperation_date: data.cooperation_date || undefined,
        credit_limit: data.credit_limit ? Number(data.credit_limit) : 0,
        salesperson_id: data.salesperson_id ? Number(data.salesperson_id) : undefined,
        bank_accounts: bankAccounts
          .filter((acc) => acc.account_name.trim() || acc.bank_name.trim() || acc.account_number.trim())
          .map((acc) => ({
            ...acc,
            id: acc.id && acc.id > 0 ? acc.id : undefined,
            account_name: acc.account_name.trim(),
            bank_name: acc.bank_name.trim(),
            account_number: acc.account_number.trim(),
            notes: acc.notes.trim(),
          })),
      };
      
      // 移除空字符串字段
      if (!data.customer_category) delete payload.customer_category;
      if (!data.logistics_info) delete payload.logistics_info;
      if (!data.salesperson_id) delete payload.salesperson_id;

      if (initialData) {
        // 更新
        await api.put(`/v1/companies/${initialData.id}`, payload);
        toast.success("主体更新成功");
      } else {
        // 创建
        await api.post("/v1/companies/", payload);
        toast.success("主体创建成功");
      }

      queryClient.invalidateQueries({ queryKey: ["companies"] });
      queryClient.invalidateQueries({ queryKey: ["customers"] });
      onOpenChange(false);
      resetForm();
    } catch (error: any) {
      const msg = error.response?.data?.detail ?? "操作失败";
      toast.error(msg);
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={(v) => { if (!v) { onOpenChange(false); resetForm(); } }}>
      <DialogContent className="max-w-lg max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>{initialData ? "编辑主体" : "新增主体"}</DialogTitle>
        </DialogHeader>

        <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-4">
          {/* 名称和中文名称 */}
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="name">
                名称 <span className="text-red-500">*</span>
              </Label>
              <Input id="name" {...form.register("name")} placeholder="请输入主体名称" />
              {form.formState.errors.name && (
                <p className="text-sm text-red-500">{form.formState.errors.name.message}</p>
              )}
            </div>
            <div className="space-y-2">
              <Label htmlFor="chinese_name">中文名称</Label>
              <Input id="chinese_name" {...form.register("chinese_name")} placeholder="中文名称" />
            </div>
          </div>

          {/* 公司全称 */}
          <div className="space-y-2">
            <Label htmlFor="company_full_name">公司全称</Label>
            <Input id="company_full_name" {...form.register("company_full_name")} placeholder="公司完整注册名称" />
          </div>

          {/* 类型 */}
          <div className="space-y-2">
            <Label htmlFor="type">
              类型 <span className="text-red-500">*</span>
            </Label>
            <Select
              value={form.watch("type")}
              onValueChange={(v) => form.setValue("type", v || "")}
            >
              <SelectTrigger>
                <SelectValue placeholder="请选择类型">
                  {(() => {
                    const selected = companyTypes.find((t) => t.value === form.watch("type"));
                    return selected?.label ?? "请选择类型";
                  })()}
                </SelectValue>
              </SelectTrigger>
              <SelectContent>
                {companyTypes.map((t) => (
                  <SelectItem key={t.value} value={t.value}>
                    {t.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            {form.formState.errors.type && (
              <p className="text-sm text-red-500">{form.formState.errors.type.message}</p>
            )}
          </div>

          {/* 编码、CN海关准入、养殖GGN */}
          <div className="grid grid-cols-3 gap-4">
            <div className="space-y-2">
              <Label htmlFor="code">
                EU注册号
              </Label>
              <Input id="code" {...form.register("code")} placeholder="加工厂对外的短号" />
            </div>
            <div className="space-y-2">
              <Label htmlFor="registration_code">CN海关准入</Label>
              <Input id="registration_code" {...form.register("registration_code")} placeholder="CN海关准入号" />
            </div>
            <div className="space-y-2">
              <Label htmlFor="enterprise_registration_no">养殖GGN</Label>
              <Input id="enterprise_registration_no" {...form.register("enterprise_registration_no")} placeholder="养殖GGN编号" />
            </div>
          </div>

          {/* 监管链COC、养殖区 */}
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="coc_cert_no">监管链COC</Label>
              <Input id="coc_cert_no" {...form.register("coc_cert_no")} placeholder="监管链认证编号" />
            </div>
            <div className="space-y-2">
              <Label htmlFor="farming_area">养殖区</Label>
              <Input id="farming_area" {...form.register("farming_area")} placeholder="如 FAO 27" />
            </div>
          </div>

          {/* 网址 */}
          <div className="space-y-2">
            <Label htmlFor="website">网址</Label>
            <Input id="website" type="url" {...form.register("website")} placeholder="https://example.com" />
          </div>

          {/* 联系人和电话 */}
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="contact_person">联系人</Label>
              <Input id="contact_person" {...form.register("contact_person")} placeholder="联系人姓名" />
            </div>
            <div className="space-y-2">
              <Label htmlFor="phone">电话</Label>
              <Input id="phone" {...form.register("phone")} placeholder="联系电话" />
            </div>
          </div>

          {/* 邮箱和地址 */}
          <div className="space-y-2">
            <Label htmlFor="email">邮箱</Label>
            <Input id="email" type="email" {...form.register("email")} placeholder="邮箱地址" />
          </div>
          <div className="space-y-2">
            <Label htmlFor="address">地址</Label>
            <Input id="address" {...form.register("address")} placeholder="详细地址" />
          </div>

          {/* 开户行 */}
          <div className="space-y-2">
            <Label htmlFor="bank_name">开户行</Label>
            <Input id="bank_name" {...form.register("bank_name")} placeholder="开户银行" />
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="bank_account">银行账号</Label>
              <Input id="bank_account" {...form.register("bank_account")} placeholder="银行账号" />
            </div>
            <div className="space-y-2">
              <Label htmlFor="credit_limit">信用额度</Label>
              <Input id="credit_limit" type="number" {...form.register("credit_limit")} placeholder="0.00" />
            </div>
          </div>

          {/* 收款账户（可多个） */}
          <div className="space-y-3 border rounded-lg p-4 bg-gray-50/50">
            <div className="flex items-center justify-between">
              <Label className="text-base font-medium">收款账户</Label>
              <Button type="button" variant="outline" size="sm" onClick={addBankAccount}>
                <Plus className="h-4 w-4 mr-1" />添加账户
              </Button>
            </div>
            {bankAccounts.length === 0 && (
              <div className="text-sm text-muted-foreground">暂无收款账户，点击上方按钮添加</div>
            )}
            {bankAccounts.map((acc, idx) => (
              <div key={idx} className="border rounded-md p-3 space-y-3 bg-white">
                <div className="flex items-center justify-between">
                  <span className="text-sm font-medium text-muted-foreground">账户 {idx + 1}</span>
                  <Button type="button" variant="ghost" size="icon" className="h-7 w-7" onClick={() => removeBankAccount(idx)}>
                    <Trash2 className="h-4 w-4 text-red-500" />
                  </Button>
                </div>
                <div className="grid grid-cols-2 gap-3">
                  <div className="space-y-1">
                    <Label className="text-xs">户名</Label>
                    <Input
                      value={acc.account_name}
                      onChange={(e) => updateBankAccount(idx, "account_name", e.target.value)}
                      placeholder="收款账户名/户名"
                    />
                  </div>
                  <div className="space-y-1">
                    <Label className="text-xs">币种</Label>
                    <Select
                      value={acc.currency}
                      onValueChange={(v) => updateBankAccount(idx, "currency", v)}
                    >
                      <SelectTrigger>
                        <SelectValue>{acc.currency}</SelectValue>
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="CNY">CNY</SelectItem>
                        <SelectItem value="USD">USD</SelectItem>
                        <SelectItem value="EUR">EUR</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                </div>
                <div className="space-y-1">
                  <Label className="text-xs">开户行</Label>
                  <Input
                    value={acc.bank_name}
                    onChange={(e) => updateBankAccount(idx, "bank_name", e.target.value)}
                    placeholder="开户银行"
                  />
                </div>
                <div className="space-y-1">
                  <Label className="text-xs">银行账号</Label>
                  <Input
                    value={acc.account_number}
                    onChange={(e) => updateBankAccount(idx, "account_number", e.target.value)}
                    placeholder="银行账号"
                  />
                </div>
                <div className="space-y-1">
                  <Label className="text-xs">备注</Label>
                  <Input
                    value={acc.notes}
                    onChange={(e) => updateBankAccount(idx, "notes", e.target.value)}
                    placeholder="备注"
                  />
                </div>
                <div className="flex items-center gap-2">
                  <Checkbox
                    id={`bank_active_${idx}`}
                    checked={acc.is_active}
                    onCheckedChange={(checked) => updateBankAccount(idx, "is_active", checked === true)}
                  />
                  <Label htmlFor={`bank_active_${idx}`} className="text-xs font-normal cursor-pointer">启用</Label>
                </div>
              </div>
            ))}
          </div>

          {/* 客户专用字段：分类、业务员、物流 */}
          {form.watch("type") === "customer" && (
            <>
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="customer_category">客户分类</Label>
                  <Select
                    value={form.watch("customer_category")}
                    onValueChange={(v) => form.setValue("customer_category", v || "")}
                  >
                    <SelectTrigger>
                      <SelectValue placeholder="请选择">
                        {(() => {
                          const selected = customerCategories.find((t) => t.value === form.watch("customer_category"));
                          return selected?.label ?? "请选择";
                        })()}
                      </SelectValue>
                    </SelectTrigger>
                    <SelectContent>
                      {customerCategories.map((t) => (
                        <SelectItem key={t.value} value={t.value}>
                          {t.label}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
                <div className="space-y-2">
                  <Label htmlFor="salesperson_id">业务员</Label>
                  <Select
                    value={form.watch("salesperson_id") || undefined}
                    onValueChange={(v) => form.setValue("salesperson_id", v || "")}
                  >
                    <SelectTrigger>
                      <SelectValue placeholder="选择业务员">
                        {(() => {
                          const selected = users.find((u) => String(u.id) === form.watch("salesperson_id"));
                          return selected?.full_name ?? "选择业务员";
                        })()}
                      </SelectValue>
                    </SelectTrigger>
                    <SelectContent>
                      {users.map((u) => (
                        <SelectItem key={u.id} value={String(u.id)}>
                          {u.full_name}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
              </div>
              <div className="space-y-2">
                <Label htmlFor="logistics_info">物流信息</Label>
                <Input id="logistics_info" {...form.register("logistics_info")} placeholder="物流偏好/要求" />
              </div>
            </>
          )}

          {/* 合作日期 */}
          <div className="space-y-2">
            <Label htmlFor="cooperation_date">合作日期</Label>
            <Controller
              name="cooperation_date"
              control={form.control}
              render={({ field }) => (
                <input
                  id="cooperation_date"
                  type="date"
                  className="flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-sm shadow-sm transition-colors file:border-0 file:bg-transparent file:text-sm file:font-medium placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring disabled:cursor-not-allowed disabled:opacity-50 cursor-pointer"
                  {...field}
                  value={field.value || ""}
                  onKeyDown={(e) => e.preventDefault()}
                />
              )}
            />
          </div>

          {/* 备注 */}
          <div className="space-y-2">
            <Label htmlFor="notes">备注 / 企业介绍</Label>
            <textarea
              id="notes"
              {...form.register("notes")}
              placeholder="填写企业介绍、合作背景、特殊说明等..."
              rows={6}
              className="w-full px-3 py-2 border rounded-md text-sm bg-background resize-y focus:outline-none focus:ring-2 focus:ring-ring min-h-[120px]"
            />
          </div>

          <DialogFooter>
            <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>
              取消
            </Button>
            <Button type="submit" disabled={isSubmitting}>
              {isSubmitting ? "保存中..." : initialData ? "保存修改" : "创建主体"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
