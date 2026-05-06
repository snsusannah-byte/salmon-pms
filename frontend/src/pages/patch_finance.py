import re

with open('FinancePage.tsx', 'r') as f:
    content = f.read()

# 1. Add AlertDialog import
old_import = '''import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "@/components/ui/dialog";'''
new_import = '''import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "@/components/ui/dialog";
import {
  AlertDialog,
  AlertDialogContent,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogDescription,
  AlertDialogFooter,
} from "@/components/ui/alert-dialog";'''
content = content.replace(old_import, new_import)

# 2. ImportFeesTab: add state
old = '''function ImportFeesTab() {
  const queryClient = useQueryClient();
  const [formOpen, setFormOpen] = useState(false);
  const [detailOpen, setDetailOpen] = useState(false);
  const [detailItem, setDetailItem] = useState<ImportFeeItem | null>(null);'''
new = '''function ImportFeesTab() {
  const queryClient = useQueryClient();
  const [formOpen, setFormOpen] = useState(false);
  const [detailOpen, setDetailOpen] = useState(false);
  const [detailItem, setDetailItem] = useState<ImportFeeItem | null>(null);
  const [deleteOpen, setDeleteOpen] = useState(false);
  const [deleteInvoiceId, setDeleteInvoiceId] = useState<number | null>(null);'''
content = content.replace(old, new)

# 3. ImportFeesTab: handleDelete
old = '''  const handleDelete = async (invoiceId: number) => {
    if (!confirm("确定删除此发票的进口费用？")) return;
    try {
      await api.delete(`/v1/finance/import-fees/${invoiceId}`);
      toast.success("已删除");
      queryClient.invalidateQueries({ queryKey: ["import-fees"] });
      queryClient.invalidateQueries({ queryKey: ["finance-summary"] });
    } catch (error: any) {
      toast.error(error.response?.data?.detail ?? "删除失败");
    }
  };'''
new = '''  const handleDelete = async () => {
    if (!deleteInvoiceId) return;
    try {
      await api.delete(`/v1/finance/import-fees/${deleteInvoiceId}`);
      toast.success("已删除");
      queryClient.invalidateQueries({ queryKey: ["import-fees"] });
      queryClient.invalidateQueries({ queryKey: ["finance-summary"] });
      setDeleteOpen(false);
      setDeleteInvoiceId(null);
    } catch (error: any) {
      toast.error(error.response?.data?.detail ?? "删除失败");
    }
  };'''
content = content.replace(old, new)

# 4. ImportFeesTab: button onClick
old = '''                        onClick={() => handleDelete(f.invoice_id)}'''
new = '''                        onClick={() => {
                          setDeleteInvoiceId(f.invoice_id);
                          setDeleteOpen(true);
                        }}'''
content = content.replace(old, new)

# 5. ImportFeesTab: AlertDialog before Tab 2
old = '''    </div>
  );
}

// ==================== Tab 2: 购汇登记 ===================='''
new = '''      {/* 删除确认弹窗 */}
      <AlertDialog open={deleteOpen} onOpenChange={setDeleteOpen}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>确认删除</AlertDialogTitle>
            <AlertDialogDescription>
              确定要删除此发票的进口费用吗？此操作不可撤销。
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <Button variant="outline" onClick={() => { setDeleteOpen(false); setDeleteInvoiceId(null); }}>
              取消
            </Button>
            <Button variant="destructive" onClick={handleDelete}>
              删除
            </Button>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}

// ==================== Tab 2: 购汇登记 ===================='''
content = content.replace(old, new)

# 6. ExchangeTab: add state
old = '''function ExchangeTab() {
  const queryClient = useQueryClient();
  const [formOpen, setFormOpen] = useState(false);
  const [detailOpen, setDetailOpen] = useState(false);
  const [detailRecord, setDetailRecord] = useState<ExchangeRecord | null>(null);'''
new = '''function ExchangeTab() {
  const queryClient = useQueryClient();
  const [formOpen, setFormOpen] = useState(false);
  const [detailOpen, setDetailOpen] = useState(false);
  const [detailRecord, setDetailRecord] = useState<ExchangeRecord | null>(null);
  const [deleteOpen, setDeleteOpen] = useState(false);
  const [deleteRecordId, setDeleteRecordId] = useState<number | null>(null);'''
content = content.replace(old, new)

# 7. ExchangeTab: handleDelete
old = '''  const handleDelete = async (id: number) => {
    if (!confirm("确定删除此购汇记录？")) return;
    try {
      await api.delete(`/v1/finance/exchange/${id}`);
      toast.success("已删除");
      queryClient.invalidateQueries({ queryKey: ["exchange-records"] });
      queryClient.invalidateQueries({ queryKey: ["finance-summary"] });
    } catch (error: any) {
      toast.error(error.response?.data?.detail ?? "删除失败");
    }
  };'''
new = '''  const handleDelete = async () => {
    if (!deleteRecordId) return;
    try {
      await api.delete(`/v1/finance/exchange/${deleteRecordId}`);
      toast.success("已删除");
      queryClient.invalidateQueries({ queryKey: ["exchange-records"] });
      queryClient.invalidateQueries({ queryKey: ["finance-summary"] });
      setDeleteOpen(false);
      setDeleteRecordId(null);
    } catch (error: any) {
      toast.error(error.response?.data?.detail ?? "删除失败");
    }
  };'''
content = content.replace(old, new)

# 8. ExchangeTab: button onClick
old = '''                        onClick={() => handleDelete(r.id)}'''
new = '''                        onClick={() => {
                          setDeleteRecordId(r.id);
                          setDeleteOpen(true);
                        }}'''
content = content.replace(old, new)

# 9. ExchangeTab: AlertDialog before Tab 3
old = '''    </div>
  );
}

// ==================== Tab 3: 交易流水 ===================='''
new = '''      {/* 删除确认弹窗 */}
      <AlertDialog open={deleteOpen} onOpenChange={setDeleteOpen}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>确认删除</AlertDialogTitle>
            <AlertDialogDescription>
              确定要删除此购汇记录吗？此操作不可撤销。
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <Button variant="outline" onClick={() => { setDeleteOpen(false); setDeleteRecordId(null); }}>
              取消
            </Button>
            <Button variant="destructive" onClick={handleDelete}>
              删除
            </Button>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}

// ==================== Tab 3: 交易流水 ===================='''
content = content.replace(old, new)

# 10. TransactionsTab: add state
old = '''function TransactionsTab() {
  const queryClient = useQueryClient();
  const [formOpen, setFormOpen] = useState(false);
  const [date, setDate] = useState("");
  const [type, setType] = useState("expense");
  const [category, setCategory] = useState("other");
  const [amount, setAmount] = useState("");
  const [counterparty, setCounterparty] = useState("");
  const [description, setDescription] = useState("");
  const [referenceNo, setReferenceNo] = useState("");
  const [currency, setCurrency] = useState("CNY");
  const [bankAccountId, setBankAccountId] = useState("");
  const [selectedSaleId, setSelectedSaleId] = useState("");
  const [editingTransaction, setEditingTransaction] = useState<Transaction | null>(null);'''
new = '''function TransactionsTab() {
  const queryClient = useQueryClient();
  const [formOpen, setFormOpen] = useState(false);
  const [date, setDate] = useState("");
  const [type, setType] = useState("expense");
  const [category, setCategory] = useState("other");
  const [amount, setAmount] = useState("");
  const [counterparty, setCounterparty] = useState("");
  const [description, setDescription] = useState("");
  const [referenceNo, setReferenceNo] = useState("");
  const [currency, setCurrency] = useState("CNY");
  const [bankAccountId, setBankAccountId] = useState("");
  const [selectedSaleId, setSelectedSaleId] = useState("");
  const [editingTransaction, setEditingTransaction] = useState<Transaction | null>(null);
  const [deleteOpen, setDeleteOpen] = useState(false);
  const [deleteTransactionId, setDeleteTransactionId] = useState<number | null>(null);'''
content = content.replace(old, new)

# 11. TransactionsTab: handleDelete
old = '''  const handleDelete = async (id: number) => {
    if (!confirm("确定删除？")) return;
    try {
      await api.delete(`/v1/finance/transactions/${id}`);
      toast.success("已删除");
      queryClient.invalidateQueries({ queryKey: ["transactions"] });
      queryClient.invalidateQueries({ queryKey: ["finance-summary"] });
    } catch (error: any) {
      toast.error(error.response?.data?.detail ?? "删除失败");
    }
  };'''
new = '''  const handleDelete = async () => {
    if (!deleteTransactionId) return;
    try {
      await api.delete(`/v1/finance/transactions/${deleteTransactionId}`);
      toast.success("已删除");
      queryClient.invalidateQueries({ queryKey: ["transactions"] });
      queryClient.invalidateQueries({ queryKey: ["finance-summary"] });
      setDeleteOpen(false);
      setDeleteTransactionId(null);
    } catch (error: any) {
      toast.error(error.response?.data?.detail ?? "删除失败");
    }
  };'''
content = content.replace(old, new)

# 12. TransactionsTab: button onClick
old = '''                        onClick={() => handleDelete(r.id)}'''
new = '''                        onClick={() => {
                          setDeleteTransactionId(r.id);
                          setDeleteOpen(true);
                        }}'''
content = content.replace(old, new)

# 13. TransactionsTab: AlertDialog at end (before closing div)
old = '''    </div>
  );
}'''
new = '''      {/* 删除确认弹窗 */}
      <AlertDialog open={deleteOpen} onOpenChange={setDeleteOpen}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>确认删除</AlertDialogTitle>
            <AlertDialogDescription>
              确定要删除此交易流水吗？此操作不可撤销。
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <Button variant="outline" onClick={() => { setDeleteOpen(false); setDeleteTransactionId(null); }}>
              取消
            </Button>
            <Button variant="destructive" onClick={handleDelete}>
              删除
            </Button>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}'''
content = content.replace(old, new)

with open('FinancePage.tsx', 'w') as f:
    f.write(content)

print("Done!")
