import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
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
import { Search, Plus, Pencil, Trash2 } from "lucide-react";
import { toast } from "sonner";

interface BankAccount {
  id: number;
  code: string;
  bank_name: string;
  account_name: string;
  account_number: string;
  type: string;
  current_balance: string;
  company_id: number | null;
  company_name: string | null;
  currency: string;
  is_active: boolean;
}

const typeMap: Record<string, string> = {
  public: "公账",
  private: "私账",
  scan: "扫码",
};

function fmt$(v: number | string | null | undefined) {
  const n = Number(v ?? 0);
  if (Number.isNaN(n)) return "¥0.00";
  return `¥${n.toLocaleString("zh-CN", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

export function BankAccountsPage() {
  const qc = useQueryClient();
  const [search, setSearch] = useState("");
  const [formOpen, setFormOpen] = useState(false);
  const [editingAccount, setEditingAccount] = useState<BankAccount | null>(null);
  const [deleteAccount, setDeleteAccount] = useState<BankAccount | null>(null);
  const [deleteOpen, setDeleteOpen] = useState(false);

  // Form fields
  const [formCode, setFormCode] = useState("");
  const [formBankName, setFormBankName] = useState("");
  const [formAccountName, setFormAccountName] = useState("");
  const [formAccountNumber, setFormAccountNumber] = useState("");
  const [formType, setFormType] = useState("public");
  const [formBalance, setFormBalance] = useState("");
  const [formCompanyId, setFormCompanyId] = useState("");
  const [formCurrency, setFormCurrency] = useState("CNY");
  const [formNotes, setFormNotes] = useState("");

  const resetForm = () => {
    setFormCode("");
    setFormBankName("");
    setFormAccountName("");
    setFormAccountNumber("");
    setFormType("public");
    setFormBalance("");
    setFormCompanyId("");
    setFormCurrency("CNY");
    setFormNotes("");
    setEditingAccount(null);
  };

  const loadForm = (a: BankAccount) => {
    setFormCode(a.code || "");
    setFormBankName(a.bank_name || "");
    setFormAccountName(a.account_name || "");
    setFormAccountNumber(a.account_number || "");
    setFormType(a.type || "public");
    setFormBalance(a.current_balance || "");
    setFormCompanyId(a.company_id ? String(a.company_id) : "");
    setFormCurrency(a.currency || "CNY");
    setFormNotes("");
  };

  const { data: accounts, isLoading } = useQuery({
    queryKey: ["bank-accounts", search],
    queryFn: async () => {
      const res = await api.get("/v1/finance/bank-accounts");
      let data = res.data as BankAccount[];
      if (search) {
        const s = search.toLowerCase();
        data = data.filter(
          (a) =>
            a.code?.toLowerCase().includes(s) ||
            a.bank_name?.toLowerCase().includes(s) ||
            a.account_name?.toLowerCase().includes(s) ||
            a.account_number?.includes(s) ||
            a.company_name?.toLowerCase().includes(s)
        );
      }
      return data;
    },
  });

  // Fetch companies for dropdown
  const { data: companiesData } = useQuery({
    queryKey: ["companies-dropdown"],
    queryFn: async () => {
      const res = await api.get("/v1/companies/?limit=500");
      return res.data?.items || [];
    },
  });
  const companies = companiesData || [];

  const createMutation = useMutation({
    mutationFn: async (payload: any) => {
      const res = await api.post("/v1/finance/bank-accounts", payload);
      return res.data;
    },
    onSuccess: () => {
      toast.success("银行账户创建成功");
      qc.invalidateQueries({ queryKey: ["bank-accounts"] });
      setFormOpen(false);
      resetForm();
    },
    onError: (err: any) => toast.error(err.response?.data?.detail || "创建失败"),
  });

  const updateMutation = useMutation({
    mutationFn: async ({ id, payload }: { id: number; payload: any }) => {
      const res = await api.put(`/v1/finance/bank-accounts/${id}`, payload);
      return res.data;
    },
    onSuccess: () => {
      toast.success("银行账户更新成功");
      qc.invalidateQueries({ queryKey: ["bank-accounts"] });
      setFormOpen(false);
      resetForm();
    },
    onError: (err: any) => toast.error(err.response?.data?.detail || "更新失败"),
  });

  const deleteMutation = useMutation({
    mutationFn: async (id: number) => {
      await api.delete(`/v1/finance/bank-accounts/${id}`);
    },
    onSuccess: () => {
      toast.success("银行账户已删除");
      qc.invalidateQueries({ queryKey: ["bank-accounts"] });
      setDeleteOpen(false);
      setDeleteAccount(null);
    },
    onError: (err: any) => toast.error(err.response?.data?.detail || "删除失败"),
  });

  const handleOpenCreate = () => {
    resetForm();
    setFormOpen(true);
  };

  const handleOpenEdit = (a: BankAccount) => {
    setEditingAccount(a);
    loadForm(a);
    setFormOpen(true);
  };

  const handleOpenDelete = (a: BankAccount) => {
    setDeleteAccount(a);
    setDeleteOpen(true);
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!formBankName.trim()) {
      toast.error("银行名称必填");
      return;
    }

    const payload: any = {
      bank_name: formBankName.trim(),
      account_name: formAccountName.trim() || undefined,
      account_number: formAccountNumber.trim() || undefined,
      type: formType,
      opening_balance: formBalance ? Number(formBalance) : 0,
      current_balance: formBalance ? Number(formBalance) : 0,
      company_id: formCompanyId ? Number(formCompanyId) : undefined,
      currency: formCurrency,
      notes: formNotes.trim() || undefined,
    };

    if (editingAccount) {
      updateMutation.mutate({ id: editingAccount.id, payload });
    } else {
      createMutation.mutate(payload);
    }
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">银行账户管理</h1>
          <p className="text-sm text-muted-foreground">银行账户、余额、关联公司</p>
        </div>
        <Button onClick={handleOpenCreate}>
          <Plus className="h-4 w-4 mr-2" />
          新增账户
        </Button>
      </div>

      <div className="flex gap-4">
        <div className="relative max-w-sm">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <Input
            placeholder="搜索编号、银行、公司..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="pl-9"
          />
        </div>
      </div>

      <div className="border rounded-lg">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead className="text-xs">编号</TableHead>
              <TableHead className="text-xs">银行名称</TableHead>
              <TableHead className="text-xs">类型</TableHead>
              <TableHead className="text-xs">账号</TableHead>
              <TableHead className="text-xs">公司名称</TableHead>
              <TableHead className="text-xs text-right">余额</TableHead>
              <TableHead className="text-xs text-center">操作</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {isLoading ? (
              <TableRow>
                <TableCell colSpan={7} className="text-center py-8">加载中...</TableCell>
              </TableRow>
            ) : accounts?.length === 0 ? (
              <TableRow>
                <TableCell colSpan={7} className="text-center text-muted-foreground py-8">
                  暂无银行账户
                </TableCell>
              </TableRow>
            ) : (
              accounts?.map((a) => (
                <TableRow key={a.id}>
                  <TableCell className="text-sm font-medium">{a.code}</TableCell>
                  <TableCell className="text-xs">{a.bank_name}</TableCell>
                  <TableCell className="text-xs">
                    <span className="px-2 py-0.5 rounded text-xs font-medium bg-muted">{typeMap[a.type] || a.type}</span>
                  </TableCell>
                  <TableCell className="text-xs font-mono">{a.account_number}</TableCell>
                  <TableCell className="text-xs">{a.company_name || "-"}</TableCell>
                  <TableCell className="text-xs text-right font-medium">{fmt$(a.current_balance)}</TableCell>
                  <TableCell className="text-center">
                    <div className="flex justify-center gap-1">
                      <Button variant="ghost" size="icon" className="h-7 w-7" onClick={() => handleOpenEdit(a)} title="编辑">
                        <Pencil className="h-3.5 w-3.5" />
                      </Button>
                      <Button variant="ghost" size="icon" className="h-7 w-7 text-red-500" onClick={() => handleOpenDelete(a)} title="删除">
                        <Trash2 className="h-3.5 w-3.5" />
                      </Button>
                    </div>
                  </TableCell>
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </div>

      {/* Form Dialog */}
      <Dialog open={formOpen} onOpenChange={setFormOpen}>
        <DialogContent className="max-w-[480px]">
          <DialogHeader>
            <DialogTitle>{editingAccount ? "编辑银行账户" : "新增银行账户"}</DialogTitle>
          </DialogHeader>
          <form onSubmit={handleSubmit} className="space-y-3">
            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-1">
                <Label className="text-xs">银行名称 *</Label>
                <Input value={formBankName} onChange={(e) => setFormBankName(e.target.value)} placeholder="必填" />
              </div>
              <div className="space-y-1">
                <Label className="text-xs">类型</Label>
                <Select value={formType} onValueChange={(v) => setFormType(v ?? "public")}>
                  <SelectTrigger className="h-9 text-xs"><SelectValue /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="public">公账</SelectItem>
                    <SelectItem value="private">私账</SelectItem>
                    <SelectItem value="scan">扫码</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-1">
                <Label className="text-xs">账户名称</Label>
                <Input value={formAccountName} onChange={(e) => setFormAccountName(e.target.value)} placeholder="可选" />
              </div>
              <div className="space-y-1">
                <Label className="text-xs">银行账号</Label>
                <Input value={formAccountNumber} onChange={(e) => setFormAccountNumber(e.target.value)} placeholder="可选" />
              </div>
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-1">
                <Label className="text-xs">余额</Label>
                <Input type="number" value={formBalance} onChange={(e) => setFormBalance(e.target.value)} placeholder="0" />
              </div>
              <div className="space-y-1">
                <Label className="text-xs">币种</Label>
                <Select value={formCurrency} onValueChange={(v) => setFormCurrency(v ?? "CNY")}>
                  <SelectTrigger className="h-9 text-xs"><SelectValue /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="CNY">CNY</SelectItem>
                    <SelectItem value="USD">USD</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>
            <div className="space-y-1">
              <Label className="text-xs">关联公司</Label>
              <Select value={formCompanyId} onValueChange={(v) => setFormCompanyId(v ?? "")}>
                <SelectTrigger className="h-9 text-xs"><SelectValue placeholder="选择公司（可选）" /></SelectTrigger>
                <SelectContent>
                  {companies.map((c: any) => (
                    <SelectItem key={c.id} value={String(c.id)} className="text-xs">{c.name}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
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

      {/* Delete Dialog */}
      <Dialog open={deleteOpen} onOpenChange={setDeleteOpen}>
        <DialogContent className="max-w-sm">
          <DialogHeader><DialogTitle>确认删除</DialogTitle></DialogHeader>
          <p className="text-sm text-muted-foreground">
            确定要删除银行账户 <span className="font-medium">{deleteAccount?.bank_name} {deleteAccount?.account_number?.slice(-4)}</span> 吗？
          </p>
          <DialogFooter>
            <Button variant="outline" onClick={() => setDeleteOpen(false)}>取消</Button>
            <Button variant="destructive" onClick={() => deleteAccount && deleteMutation.mutate(deleteAccount.id)} disabled={deleteMutation.isPending}>
              {deleteMutation.isPending ? "删除中..." : "确认删除"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
