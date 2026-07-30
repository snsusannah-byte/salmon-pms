import { useState, useEffect } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import * as z from "zod";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Checkbox } from "@/components/ui/checkbox";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { api } from "@/lib/api";
import { useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { CheckCircle, Building2, Plus, Trash2 } from "lucide-react";

const SUPPLIER_CATEGORIES = [
  { value: "raw_material", label: "原料供应" },
  { value: "material_supply", label: "物料供应" },
  { value: "customs_broker", label: "报关行" },
  { value: "service_provider", label: "服务商" },
  { value: "importer", label: "进口商" },
];

const formSchema = z.object({
  name: z.string().min(1, "供应商名称不能为空").max(200),
  company_full_name: z.string().max(200).optional().or(z.literal("")),
  contact_person: z.string().max(100).optional().or(z.literal("")),
  phone: z.string().max(50).optional().or(z.literal("")),
  address: z.string().optional().or(z.literal("")),
  website: z.string().max(255).optional().or(z.literal("")),
  bank_account: z.string().max(100).optional().or(z.literal("")),
  payee: z.string().max(200).optional().or(z.literal("")),
  bank_name: z.string().max(200).optional().or(z.literal("")),
  cooperation_date: z.string().optional().or(z.literal("")),
  logistics_info: z.string().optional().or(z.literal("")),
  currency: z.string().min(1),
  supplier_category: z.string().min(1, "请选择供应商分类"),
  notes: z.string().optional().or(z.literal("")),
});

type FormData = z.infer<typeof formSchema>;

interface Supplier {
  id: number;
  name: string;
  company_full_name: string | null;
  contact_person: string | null;
  phone: string | null;
  address: string | null;
  website: string | null;
  bank_account: string | null;
  payee: string | null;
  bank_name: string | null;
  cooperation_date: string | null;
  logistics_info: string | null;
  currency: string;
  supplier_category: string | null;
  notes: string | null;
  is_active?: boolean;
  created_at?: string;
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

interface SupplierFormDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  initialData?: Supplier | null;
}

export function SupplierFormDialog({ open, onOpenChange, initialData }: SupplierFormDialogProps) {
  const queryClient = useQueryClient();
  const [isSubmitting, setIsSubmitting] = useState(false);
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
  const updateBankAccount = (idx: number, field: keyof BankAccountItem, value: any) => setBankAccounts((prev) => prev.map((item, i) => (i === idx ? { ...item, [field]: value } : item)));

  const form = useForm<FormData>({
    resolver: zodResolver(formSchema),
    defaultValues: {
      name: "",
      company_full_name: "",
      contact_person: "",
      phone: "",
      address: "",
      website: "",
      bank_account: "",
      payee: "",
      bank_name: "",
      cooperation_date: "",
      logistics_info: "",
      currency: "CNY",
      supplier_category: "",
      notes: "",
    },
  });

  useEffect(() => {
    if (open) {
      if (initialData) {
        form.reset({
          name: initialData.name,
          company_full_name: initialData.company_full_name ?? "",
          contact_person: initialData.contact_person ?? "",
          phone: initialData.phone ?? "",
          address: initialData.address ?? "",
          website: initialData.website ?? "",
          bank_account: initialData.bank_account ?? "",
          payee: initialData.payee ?? "",
          bank_name: initialData.bank_name ?? "",
          cooperation_date: initialData.cooperation_date ?? "",
          logistics_info: initialData.logistics_info ?? "",
          currency: initialData.currency || "CNY",
          supplier_category: initialData.supplier_category ?? "",
          notes: initialData.notes ?? "",
        });
        const accounts = (initialData.bank_accounts || []).map((acc) => ({ ...acc }));
        if (accounts.length === 0 && (initialData.payee || initialData.bank_name || initialData.bank_account)) {
          accounts.push({
            account_name: initialData.payee || "",
            bank_name: initialData.bank_name || "",
            account_number: initialData.bank_account || "",
            currency: initialData.currency || "CNY",
            is_active: true,
            notes: "",
          });
        }
        setBankAccounts(accounts);
      } else {
        form.reset({
          name: "",
          company_full_name: "",
          contact_person: "",
          phone: "",
          address: "",
          website: "",
          bank_account: "",
          payee: "",
          bank_name: "",
          cooperation_date: "",
          logistics_info: "",
          currency: "CNY",
          supplier_category: "",
          notes: "",
        });
        setBankAccounts([]);
      }
    }
  }, [open, initialData?.id]);

  const onSubmit = async (data: FormData) => {
    setIsSubmitting(true);
    try {
      const filteredAccounts = bankAccounts
        .filter((acc) => acc.account_name.trim() || acc.bank_name.trim() || acc.account_number.trim())
        .map((acc) => ({
          ...acc,
          id: acc.id && acc.id > 0 ? acc.id : undefined,
          account_name: acc.account_name.trim(),
          bank_name: acc.bank_name.trim(),
          account_number: acc.account_number.trim(),
          notes: acc.notes.trim(),
        }));

      const payload: any = {
        ...data,
        type: "supplier",
        cooperation_date: data.cooperation_date || undefined,
        bank_accounts: filteredAccounts,
      };

      // 同步旧版单账户字段到第一个收款账户，保持兼容性
      if (filteredAccounts.length > 0) {
        payload.payee = filteredAccounts[0].account_name;
        payload.bank_name = filteredAccounts[0].bank_name;
        payload.bank_account = filteredAccounts[0].account_number;
      }

      if (initialData) {
        await api.put(`/v1/companies/${initialData.id}`, payload);
        toast.success("供应商更新成功");
      } else {
        await api.post("/v1/companies/", payload);
        toast.success("供应商创建成功");
      }
      queryClient.invalidateQueries({ queryKey: ["suppliers"] });
      queryClient.invalidateQueries({ queryKey: ["companies"] });
      onOpenChange(false);
    } catch (error: any) {
      const detail = error.response?.data?.detail;
      toast.error(typeof detail === "string" ? detail : "操作失败");
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={(v) => { if (!v) onOpenChange(false); }}>
      <DialogContent className="max-w-[520px]">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Building2 className="h-5 w-5 text-purple-600" />
            {initialData ? "编辑供应商" : "新增供应商"}
          </DialogTitle>
        </DialogHeader>

        <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-4 py-2">
          {/* 基本信息 */}
          <div className="space-y-3">
            <div className="grid gap-2">
              <Label htmlFor="name" className="text-sm">
                供应商名称 <span className="text-red-500">*</span>
              </Label>
              <Input
                id="name"
                {...form.register("name")}
                placeholder="如：ICE SEAFOOD AS"
              />
              {form.formState.errors.name && (
                <p className="text-xs text-red-500">{form.formState.errors.name.message}</p>
              )}
            </div>

            <div className="grid gap-2">
              <Label htmlFor="company_full_name" className="text-sm">公司名称（全称）</Label>
              <Input
                id="company_full_name"
                {...form.register("company_full_name")}
                placeholder="公司注册全称"
              />
            </div>

            <div className="grid gap-2">
              <Label htmlFor="supplier_category" className="text-sm">
                供应商分类 <span className="text-red-500">*</span>
              </Label>
              <select
                id="supplier_category"
                {...form.register("supplier_category")}
                className="h-9 w-full rounded-md border border-input bg-background px-3 py-1 text-sm shadow-sm transition-colors"
              >
                <option value="">请选择分类</option>
                {SUPPLIER_CATEGORIES.map((cat) => (
                  <option key={cat.value} value={cat.value}>{cat.label}</option>
                ))}
              </select>
              {form.formState.errors.supplier_category && (
                <p className="text-xs text-red-500">{form.formState.errors.supplier_category.message}</p>
              )}
            </div>
          </div>

          {/* 联系信息 */}
          <div className="border rounded-lg p-4 space-y-3">
            <div className="text-sm font-medium text-gray-700">联系信息</div>
            <div className="grid grid-cols-2 gap-3">
              <div className="grid gap-2">
                <Label htmlFor="contact_person" className="text-xs">联系人</Label>
                <Input id="contact_person" {...form.register("contact_person")} placeholder="联系人姓名" />
              </div>
              <div className="grid gap-2">
                <Label htmlFor="phone" className="text-xs">电话</Label>
                <Input id="phone" {...form.register("phone")} placeholder="联系电话" />
              </div>
            </div>
            <div className="grid gap-2">
              <Label htmlFor="address" className="text-xs">地址 / 网址</Label>
              <div className="grid grid-cols-2 gap-2">
                <Input id="address" {...form.register("address")} placeholder="公司地址" />
                <Input id="website" {...form.register("website")} placeholder="https://..." />
              </div>
            </div>
          </div>

          {/* 收款账户（可多个） */}
          <div className="border rounded-lg p-4 space-y-3 bg-gray-50/50">
            <div className="flex items-center justify-between">
              <div className="text-sm font-medium text-gray-700">收款账户</div>
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
                  <div className="grid gap-2">
                    <Label className="text-xs">户名</Label>
                    <Input
                      value={acc.account_name}
                      onChange={(e) => updateBankAccount(idx, "account_name", e.target.value)}
                      placeholder="收款账户名/户名"
                    />
                  </div>
                  <div className="grid gap-2">
                    <Label className="text-xs">币种</Label>
                    <Select
                      value={acc.currency}
                      onValueChange={(v) => updateBankAccount(idx, "currency", v)}
                    >
                      <SelectTrigger>
                        <SelectValue>{acc.currency}</SelectValue>
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="CNY">CNY 人民币</SelectItem>
                        <SelectItem value="USD">USD 美元</SelectItem>
                        <SelectItem value="EUR">EUR 欧元</SelectItem>
                        <SelectItem value="NOK">NOK 挪威克朗</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                </div>
                <div className="grid gap-2">
                  <Label className="text-xs">开户行</Label>
                  <Input
                    value={acc.bank_name}
                    onChange={(e) => updateBankAccount(idx, "bank_name", e.target.value)}
                    placeholder="开户银行"
                  />
                </div>
                <div className="grid gap-2">
                  <Label className="text-xs">银行账号</Label>
                  <Input
                    value={acc.account_number}
                    onChange={(e) => updateBankAccount(idx, "account_number", e.target.value)}
                    placeholder="银行账号"
                  />
                </div>
                <div className="grid gap-2">
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

          {/* 其他信息 */}
          <div className="grid grid-cols-2 gap-3">
            <div className="grid gap-2">
              <Label htmlFor="cooperation_date" className="text-xs">合作日期</Label>
              <Input id="cooperation_date" type="date" {...form.register("cooperation_date")} />
            </div>
            <div className="grid gap-2">
              <Label htmlFor="currency" className="text-xs">币种</Label>
              <select
                id="currency"
                {...form.register("currency")}
                className="h-9 w-full rounded-md border border-input bg-background px-3 py-1 text-sm shadow-sm transition-colors"
              >
                <option value="CNY">CNY 人民币</option>
                <option value="USD">USD 美元</option>
                <option value="EUR">EUR 欧元</option>
                <option value="NOK">NOK 挪威克朗</option>
              </select>
            </div>
          </div>

          <div className="grid gap-2">
            <Label htmlFor="logistics_info" className="text-xs">供应物流</Label>
            <Input id="logistics_info" {...form.register("logistics_info")} placeholder="物流信息" />
          </div>

          <div className="grid gap-2">
            <Label htmlFor="notes" className="text-xs">备注</Label>
            <Input id="notes" {...form.register("notes")} placeholder="备注信息" />
          </div>

          <DialogFooter>
            <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>
              取消
            </Button>
            <Button type="submit" disabled={isSubmitting}>
              <CheckCircle className="w-4 h-4 mr-1" />
              {isSubmitting ? "保存中..." : initialData ? "更新" : "保存"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
