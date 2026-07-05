// 成品销售组件 - FinishedProductSales.tsx
// 功能：整鱼国内采购销售 + 成品定义产品销售
// 模式切换：whole_fish（整鱼销售）/ finished_product（成品销售）

import { useState, useEffect } from 'react';
import { createPortal } from 'react-dom';
import { useLocation } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Badge } from '@/components/ui/badge';
import { Checkbox } from '@/components/ui/checkbox';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter } from '@/components/ui/dialog';
import { Tabs, TabsList, TabsTrigger } from '@/components/ui/tabs';
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from '@/components/ui/table';
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from '@/components/ui/select';
import {
  Factory, ShoppingCart, Plus, Search, Edit2, Trash2, Save, X,
  CreditCard, Eye, Package, DollarSign, Download, Pencil, Banknote,
  ArrowLeftRight, SlidersHorizontal, Lock, Unlock
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { api, apiFetch, apiPost, apiDelete } from '@/lib/api';
import { toast } from 'sonner';
import { ReturnOrderForm } from '@/components/returns/ReturnOrderForm';
import { ProductSelectorV2 } from '@/components/ProductSelectorV2';

interface FinishedSaleReceipt {
  id: number;
  sale_id: number;
  receipt_date: string;
  amount: number;
  payment_method: string;
  bank_account_id?: number | null;
  reference_no?: string | null;
  notes?: string | null;
}

interface FinishedSale {
  id: number;
  sale_no: string;
  sale_type: 'whole_fish' | 'finished_product';
  customer: string;
  salesperson: string;
  product_name: string;
  factory: string;
  slaughter_date: string;
  delivery_address: string;
  logistics_info: string;
  quantity: number;
  weight: number;
  unit_price: number;
  total_amount: number;
  sale_date: string;
  discount: number;
  scan_fee: number;
  rounding: number;
  after_sales_adjustment: number;
  commission: number;
  actual_amount: number;
  net_amount: number;
  paid: number;
  paid_amount?: number;
  remark: string;
  created_at: string;
  status?: string;
  batch_no?: string;
  procurement_status?: string;
  payment_status?: string;
  products?: FinishedSaleProduct[];
  receipts?: FinishedSaleReceipt[];
  aftersales?: any[];
  return_orders?: any[];
}

interface FinishedSaleProduct {
  id?: number;
  variant_id?: number | null;
  product_name?: string;
  product_spec: string;
  factory?: string;
  slaughter_date?: string;
  batch?: string;          // 批次号：加工厂-月日，如 N430-0130
  box_count: number;
  weight_kg: number;
  unit_price: number;
  total_amount: number;
  commission_rate?: number;
  commission_amount?: number;
  after_sales_adjustment?: number;
}

interface ProductGroup {
  id: number;
  name: string;
  unit: string;
  specs: { id: number; spec: string; code: string; unit: string }[];
}

const emptyProduct: FinishedSaleProduct = {
  variant_id: null, product_name: '', product_spec: '', factory: '', slaughter_date: '', batch: '',
  box_count: 0, weight_kg: 0, unit_price: 0,
  total_amount: 0, commission_rate: 0, commission_amount: 0, after_sales_adjustment: 0
};

const emptyForm = {
  sale_no: '', sale_type: 'whole_fish' as 'whole_fish' | 'finished_product',
  customer: '', salesperson: '', product_name: '', factory: '',
  slaughter_date: '', delivery_address: '', logistics_info: '',
  quantity: 0, weight: 0, unit_price: 0, total_amount: 0,
  sale_date: new Date().toISOString().split('T')[0],
  discount: 0, scan_fee: 0, rounding: 0, after_sales_adjustment: 0,
  commission: 0, actual_amount: 0, net_amount: 0, paid: false, remark: '',
  products: [emptyProduct]
};

const paymentMethodMap: Record<string, string> = {
  bank_transfer: "银行转账",
  cash: "现金",
  check: "支票",
  scan: "扫码",
  balance: "余额抵扣",
};

function round2(n: number): number {
  return Math.round((n + Number.EPSILON) * 100) / 100;
}

// 解析批次号：N430-0130 -> { factory: 'N430', slaughter_date: '2026-01-30' }
function parseBatch(batchStr: string, year: string | number): { factory: string; slaughter_date: string } | null {
  if (!batchStr || !batchStr.includes('-')) return null;
  const [factory, mmdd] = batchStr.split('-');
  if (!factory || !mmdd || mmdd.length !== 4) return null;
  const month = mmdd.slice(0, 2);
  const day = mmdd.slice(2, 4);
  if (!/\d{4}/.test(mmdd)) return null;
  const y = String(year);
  return {
    factory: factory.trim(),
    slaughter_date: `${y}-${month}-${day}`,
  };
}

// 反向生成批次号：factory='N430', slaughter_date='2026-01-30' -> 'N430-0130'
function formatBatch(factory?: string, slaughter_date?: string): string {
  if (!factory || !slaughter_date) return '';
  const d = slaughter_date.slice(5, 10).replace('-', ''); // '01-30' -> '0130'
  return `${factory}-${d}`;
}

export function FinishedProductSales() {
  const location = useLocation();
  const isMadeToOrder = location.pathname === '/made-to-order';
  const pageTitle = isMadeToOrder ? '以销定采' : '预包装销售';
  const allowedSaleType = isMadeToOrder ? 'whole_fish' : 'finished_product';

  const [sales, setSales] = useState<FinishedSale[]>([]);
  const [customers, setCustomers] = useState<any[]>([]);
  const [salespeople, setSalespeople] = useState<{name: string, commission_rate: number}[]>([]);
  const [productGroups, setProductGroups] = useState<ProductGroup[]>([]);
  const [loading, setLoading] = useState(false);
  const [search, setSearch] = useState('');
  const [filterType, setFilterType] = useState<'all' | 'whole_fish' | 'finished_product'>(allowedSaleType);
  const [showModal, setShowModal] = useState(false);
  const [showDetail, setShowDetail] = useState(false);
  const [detailSale, setDetailSale] = useState<FinishedSale | null>(null);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [form, setForm] = useState(emptyForm);
  const [customerSearch, setCustomerSearch] = useState('');
  const [showCustomerList, setShowCustomerList] = useState(false);
  const [showPaymentModal, setShowPaymentModal] = useState(false);
  const [receiptSale, setReceiptSale] = useState<FinishedSale | null>(null);
  const [receiptAmount, setReceiptAmount] = useState("");
  const [receiptRounding, setReceiptRounding] = useState("0");
  const [receiptMethod, setReceiptMethod] = useState("bank_transfer");
  const [receiptBankAccountId, setReceiptBankAccountId] = useState("");
  const [receiptDate, setReceiptDate] = useState(new Date().toISOString().split('T')[0]);
  const [receiptDescription, setReceiptDescription] = useState("");
  const [paymentLoading, setPaymentLoading] = useState(false);
  // 合并收款
  const [showBatchPaymentModal, setShowBatchPaymentModal] = useState(false);
  const [batchReceiptAmount, setBatchReceiptAmount] = useState("");
  const [batchReceiptMethod, setBatchReceiptMethod] = useState("bank_transfer");
  const [batchReceiptBankAccountId, setBatchReceiptBankAccountId] = useState("");
  const [batchReceiptDate, setBatchReceiptDate] = useState(new Date().toISOString().split('T')[0]);
  const [batchReceiptDescription, setBatchReceiptDescription] = useState("");
  const [batchReceiptRounding, setBatchReceiptRounding] = useState("");
  const [batchPaymentLoading, setBatchPaymentLoading] = useState(false);
  const [showAdjustModal, setShowAdjustModal] = useState(false);
  const [adjustForm, setAdjustForm] = useState({ discount: 0, scan_fee: 0, rounding: 0, after_sales_adjustment: 0 });
  const [adjustSaleId, setAdjustSaleId] = useState<number | null>(null);
  const [deleteSale, setDeleteSale] = useState<FinishedSale | null>(null);
  const [deleteLoading, setDeleteLoading] = useState(false);
  const [batchDeleteDialogOpen, setBatchDeleteDialogOpen] = useState(false);
  const [selectedIds, setSelectedIds] = useState<Set<number>>(new Set());
  const [selectedSale, setSelectedSale] = useState<FinishedSale | null>(null);
  const [exportLoading, setExportLoading] = useState(false);
  const [page, setPage] = useState(1);
  const PAGE_SIZE = 50; // 增加每页显示条数，避免屏幕留白
  // 退货表单
  const [returnFormOpen, setReturnFormOpen] = useState(false);
  const [returnPrefillSale, setReturnPrefillSale] = useState<{ type: "whole_fish" | "finished_product"; sale: any } | null>(null);

  // 规格行级别：产品名称下拉（每行独立）
  const [activeProductNameIdx, setActiveProductNameIdx] = useState<number | null>(null);
  const [productNameSearch, setProductNameSearch] = useState('');
  const [productDropdownPos, setProductDropdownPos] = useState<{top:number,left:number,width:number}|null>(null);
  // 规格下拉
  const [activeSpecIdx, setActiveSpecIdx] = useState<number | null>(null);
  const [specSearch, setSpecSearch] = useState('');
  const [specDropdownPos, setSpecDropdownPos] = useState<{top:number,left:number,width:number}|null>(null);

  const loadSales = async () => {
    setLoading(true);
    const res = await apiFetch(`v4/finished-product-sales?sale_type=${allowedSaleType}`);
    if (res.ok && res.data) {
      const arr = Array.isArray(res.data) ? res.data : (res.data.data || []);
      setSales(arr);
    }
    setLoading(false);
  };

  const loadCustomers = async () => {
    const res = await apiFetch('v4/customers?limit=500');
    if (res.ok && res.data) {
      const items = Array.isArray(res.data) ? res.data : (res.data.data || []);
      setCustomers(items);
    }
  };

  const loadSalespeople = async () => {
    try {
      const res = await api.get('v1/salespersons/?limit=500');
      const items = Array.isArray(res.data) ? res.data : (res.data.items || []);
      setSalespeople(items.map((s: any) => ({ name: s.name || s.full_name, commission_rate: s.commission_rate || 0 })));
    } catch (e) {}
  };

  const loadProducts = async () => {
    const res = await apiFetch('/v4/products-by-name');
    if (res.ok && res.data) {
      const arr = Array.isArray(res.data) ? res.data : (res.data.data || []);
      setProductGroups(arr);
    }
  };

  const handleCustomerSelect = (customerName: string) => {
    const customer = customers.find((c: any) => c.name === customerName);
    setForm(prev => ({
      ...prev,
      customer: customerName,
      delivery_address: customer?.address || prev.delivery_address,
      logistics_info: customer?.logistics_info || prev.logistics_info,
    }));
  };

  useEffect(() => { loadSales(); loadCustomers(); loadSalespeople(); loadProducts(); }, []);

  const selectedProductGroup = productGroups.find(g => g.name === form.product_name);

  const handleProductChange = (idx: number, field: keyof FinishedSaleProduct, value: any) => {
    setForm(prev => {
      const products = [...prev.products];
      products[idx] = { ...products[idx], [field]: value };
      if (field === 'weight_kg' || field === 'unit_price') {
        const w = parseFloat(products[idx].weight_kg as any) || 0;
        const p = parseFloat(products[idx].unit_price as any) || 0;
        products[idx].total_amount = round2(w * p);
      }
      const total_amount = products.reduce((s, p) => s + (p.total_amount || 0), 0);
      const weight = products.reduce((s, p) => s + (parseFloat(p.weight_kg as any) || 0), 0);
      const quantity = products.reduce((s, p) => s + (parseInt(p.box_count as any) || 0), 0);
      const sp = salespeople.find(s => s.name === prev.salesperson);
      const commission_rate = sp?.commission_rate || 0;
      const commission = round2(weight * commission_rate);
      const net = round2(total_amount - prev.discount - prev.scan_fee - prev.rounding - prev.after_sales_adjustment - commission);
      return { ...prev, products, total_amount, weight, quantity, commission, net_amount: net };
    });
  };

  const addProduct = () => setForm(prev => ({ ...prev, products: [...prev.products, { ...emptyProduct }] }));
  const removeProduct = (idx: number) => setForm(prev => ({ ...prev, products: prev.products.filter((_, i) => i !== idx) }));

  const handleSave = async () => {
    if (!form.customer.trim()) { toast.error('客户名称不能为空'); return; }
    const payload = {
      ...form,
      sale_no: form.sale_no.trim() || undefined,
      paid: form.paid ? 1 : 0,
      products: form.products.filter(p => p.product_spec.trim()).map(p => ({
        ...p,
        factory: p.factory || (p.batch ? parseBatch(p.batch, form.sale_date.slice(0, 4))?.factory : '') || '',
        slaughter_date: p.slaughter_date || (p.batch ? parseBatch(p.batch, form.sale_date.slice(0, 4))?.slaughter_date : '') || '',
      })),
    };
    try {
      if (editingId) {
        await apiFetch('v4/finished-product-sales/' + editingId, {
          method: 'PUT', headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload)
        }, '更新成功');
      } else {
        await apiPost('v4/finished-product-sales', payload, '创建成功');
      }
      setShowModal(false);
      setForm(emptyForm);
      setEditingId(null);
      loadSales();
    } catch (e) {}
  };

  const handleEdit = async (sale: FinishedSale) => {
    const res = await apiFetch(`/v4/finished-product-sales/${sale.id}`);
    if (res.ok && res.data) {
      const s = res.data.data || res.data;
      const products = (s.products?.length ? s.products : [emptyProduct]).map((p: any) => ({
        product_name: p.product_name || '', product_spec: p.product_spec || '', factory: p.factory || '', slaughter_date: p.slaughter_date || '',
        batch: p.batch || formatBatch(p.factory, p.slaughter_date), // 兼容旧数据：反向生成批次号
        box_count: p.box_count || 0, weight_kg: p.weight_kg || 0, unit_price: p.unit_price || 0,
        total_amount: p.total_amount || 0, commission_rate: p.commission_rate || 0,
        commission_amount: p.commission_amount || 0, after_sales_adjustment: p.after_sales_adjustment || 0
      }));
      const totalWeight = s.weight || 0;
      const totalBoxes = products.reduce((sum: number, p: any) => sum + (p.box_count || 0), 0);
      if (totalWeight > 0 && totalBoxes > 0 && products.every((p: any) => !p.weight_kg)) {
        products.forEach((p: any) => {
          p.weight_kg = round2(totalWeight * (p.box_count / totalBoxes));
          p.total_amount = round2(p.weight_kg * p.unit_price);
        });
      }
      setForm({
        sale_no: s.sale_no || '', sale_type: s.sale_type || 'whole_fish',
        customer: s.customer || '', salesperson: s.salesperson || '',
        product_name: s.product_name || '', factory: s.factory || '',
        slaughter_date: s.slaughter_date || '', delivery_address: s.delivery_address || '',
        logistics_info: s.logistics_info || '', quantity: s.quantity || 0,
        weight: s.weight || 0, unit_price: s.unit_price || 0, total_amount: s.total_amount || 0,
        sale_date: s.sale_date || new Date().toISOString().split('T')[0],
        discount: s.discount || 0, scan_fee: s.scan_fee || 0, rounding: s.rounding || 0,
        after_sales_adjustment: s.after_sales_adjustment || 0, commission: s.commission || 0,
        actual_amount: s.actual_amount || 0, net_amount: s.net_amount || 0,
        paid: !!s.paid, remark: s.remark || '', products,
      });
      setEditingId(s.id);
      setShowModal(true);
    }
  };

  const handleDelete = async (sale: FinishedSale) => { setDeleteSale(sale); };
  const confirmDelete = async () => {
    if (!deleteSale) return;
    setDeleteLoading(true);
    try { await apiDelete(`/v4/finished-product-sales/${deleteSale.id}`, '删除成功'); setDeleteSale(null); loadSales(); } catch (e) {} finally { setDeleteLoading(false); }
  };

  const handleViewDetail = async (sale: FinishedSale) => {
    const res = await apiFetch(`/v4/finished-product-sales/${sale.id}`);
    if (res.ok && res.data) { setDetailSale(res.data.data || res.data); setShowDetail(true); }
  };

  const handleNew = (type: 'whole_fish' | 'finished_product') => {
    setForm({ ...emptyForm, sale_type: type });
    setEditingId(null);
    setShowModal(true);
  };

  const handleAdjustOpen = (sale: FinishedSale) => {
    setAdjustSaleId(sale.id);
    setAdjustForm({ discount: sale.discount || 0, scan_fee: sale.scan_fee || 0, rounding: sale.rounding || 0, after_sales_adjustment: sale.after_sales_adjustment || 0 });
    setShowAdjustModal(true);
  };
  const handleAdjustSave = async () => {
    if (!adjustSaleId) return;
    const sale = sales.find(s => s.id === adjustSaleId);
    if (!sale) return;
    const commission = sale.commission || 0;
    const net = round2(sale.total_amount - adjustForm.discount - adjustForm.scan_fee - adjustForm.rounding - adjustForm.after_sales_adjustment - commission);
    await apiFetch(`/v4/finished-product-sales/${adjustSaleId}`, {
      method: 'PUT', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ ...sale, discount: adjustForm.discount, scan_fee: adjustForm.scan_fee, rounding: adjustForm.rounding, after_sales_adjustment: adjustForm.after_sales_adjustment, net_amount: net })
    }, '调整成功');
    setShowAdjustModal(false); setAdjustSaleId(null); loadSales();
  };

  // 银行账户列表
  const { data: bankAccountsData } = useQuery({
    queryKey: ['bank-accounts'],
    queryFn: async () => {
      const res = await api.get('/v1/finance/bank-accounts');
      return Array.isArray(res.data) ? res.data : (res.data?.items || []);
    },
  });
  const bankAccounts = bankAccountsData || [];

  // 客户列表（用于余额抵扣显示客户余额）
  const { data: customersDataV4 } = useQuery({
    queryKey: ['customers-list-v4'],
    queryFn: async () => {
      const res = await apiFetch('v4/customers?limit=500');
      return res.ok ? (res.data?.data || res.data || []) : [];
    },
  });
  const customersListV4 = customersDataV4 || [];

  const handlePaymentOpen = (sale: FinishedSale) => {
    setReceiptSale(sale);
    const receivable = Math.max(0, (sale.net_amount || 0) - (sale.paid_amount || 0));
    setReceiptAmount(receivable > 0 ? receivable.toFixed(2) : '');
    setReceiptRounding('0');
    setReceiptMethod('bank_transfer');
    setReceiptBankAccountId('');
    setReceiptDate(new Date().toISOString().split('T')[0]);
    setReceiptDescription('');
    setShowPaymentModal(true);
  };

  // 当实收金额变化时，实时计算抹零 = 应收 - 实收
  const handleReceiptAmountChange = (value: string) => {
    setReceiptAmount(value);
    if (!receiptSale) return;
    const receivable = Math.max(0, (receiptSale.net_amount || 0) - (receiptSale.paid_amount || 0));
    const actual = Number(value) || 0;
    const rounding = Math.max(0, receivable - actual);
    setReceiptRounding(rounding > 0 ? rounding.toFixed(2) : '0');
  };

  const handlePaymentSave = async () => {
    if (!receiptSale) return;
    const amount = Number(receiptAmount);
    if (amount <= 0) {
      toast.error('收款金额必须大于0');
      return;
    }
    setPaymentLoading(true);
    try {
      const res = await apiPost(`/v4/finished-product-sales/${receiptSale.id}/receipts`, {
        receipt_date: receiptDate,
        amount: amount,
        payment_method: receiptMethod,
        bank_account_id: receiptBankAccountId ? Number(receiptBankAccountId) : null,
        rounding_adjustment: Number(receiptRounding || 0),
        notes: receiptDescription.trim() || undefined,
      }, '收款成功');
      if (res.ok) {
        setShowPaymentModal(false);
        setReceiptSale(null);
        loadSales();
      }
    } catch (e: any) {
      toast.error(e?.response?.data?.detail || '收款失败');
    } finally {
      setPaymentLoading(false);
    }
  };

  // 合并收款
  const handleBatchPaymentOpen = () => {
    if (selectedSales.length < 2) {
      toast.error('请至少选择2个销售单进行合并收款');
      return;
    }
    const totalReceivable = selectedSales.reduce((sum, s) => sum + Math.max(0, (s.net_amount || 0) - (s.paid_amount || 0)), 0);
    setBatchReceiptAmount(totalReceivable > 0 ? totalReceivable.toFixed(2) : '');
    setBatchReceiptRounding('0');
    setBatchReceiptMethod('bank_transfer');
    setBatchReceiptBankAccountId('');
    setBatchReceiptDate(new Date().toISOString().split('T')[0]);
    setBatchReceiptDescription('');
    setShowBatchPaymentModal(true);
  };

  const handleBatchPaymentSave = async () => {
    const totalAmount = Number(batchReceiptAmount);
    if (totalAmount < 0) {
      toast.error('收款金额不能为负数');
      return;
    }
    setBatchPaymentLoading(true);
    try {
      // 按销售日期排序（旧的在前），优先满足旧单
      const sortedSales = [...selectedSales].sort((a, b) => new Date(a.sale_date).getTime() - new Date(b.sale_date).getTime());
      
      let remainingPayment = totalAmount;
      const saleReceipts: { sale_id: number; amount: number; rounding_adjustment: number }[] = [];
      
      for (let i = 0; i < sortedSales.length; i++) {
        const s = sortedSales[i];
        const receivable = Math.max(0, (s.net_amount || 0) - (s.paid_amount || 0));
        
        if (remainingPayment >= receivable) {
          // 足够付清这一单
          saleReceipts.push({ sale_id: s.id, amount: receivable, rounding_adjustment: 0 });
          remainingPayment = round2(remainingPayment - receivable);
        } else if (remainingPayment > 0) {
          // 部分付款，剩下的作为抹零
          const rounding = round2(receivable - remainingPayment);
          saleReceipts.push({ sale_id: s.id, amount: remainingPayment, rounding_adjustment: rounding });
          remainingPayment = 0;
        } else {
          // 没钱了，全部抹零
          saleReceipts.push({ sale_id: s.id, amount: 0, rounding_adjustment: receivable });
        }
      }
      
      // 过滤掉 amount=0 且 rounding=0 的（理论上不会有）
      const validReceipts = saleReceipts.filter(r => r.amount > 0 || r.rounding_adjustment > 0);

      const res = await apiPost('/v4/finished-product-sales/batch-receipts', {
        sale_receipts: validReceipts,
        receipt_date: batchReceiptDate,
        payment_method: batchReceiptMethod,
        bank_account_id: batchReceiptMethod !== 'balance' ? (batchReceiptBankAccountId ? Number(batchReceiptBankAccountId) : null) : null,
        notes: batchReceiptDescription.trim() || undefined,
      }, '合并收款成功');
      if (res.ok) {
        setShowBatchPaymentModal(false);
        setSelectedIds(new Set());
        loadSales();
      }
    } catch (e: any) {
      toast.error(e?.response?.data?.detail || '合并收款失败');
    } finally {
      setBatchPaymentLoading(false);
    }
  };

  const handleExport = async () => {
    setExportLoading(true);
    try {
      const params = new URLSearchParams();
      if (filterType !== 'all') params.append('sale_type', filterType);
      if (search.trim()) params.append('search', search.trim());
      const res = await api.get(`/v4/finished-product-sales/export?${params.toString()}`, { responseType: 'blob' });
      const blob = new Blob([res.data], { type: 'text/csv;charset=utf-8;' });
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = `finished_product_sales_${new Date().toISOString().split('T')[0].replace(/-/g, '')}.csv`;
      document.body.appendChild(link); link.click(); document.body.removeChild(link);
      window.URL.revokeObjectURL(url); toast.success('导出成功');
    } catch (err: any) { toast.error('导出失败'); } finally { setExportLoading(false); }
  };

  const filteredSales = sales.filter(s => {
    if (filterType !== 'all' && s.sale_type !== filterType) return false;
    return (s.sale_no?.toLowerCase().includes(search.toLowerCase()) || s.customer?.toLowerCase().includes(search.toLowerCase()) || s.salesperson?.toLowerCase().includes(search.toLowerCase()));
  });

  const totalPages = Math.ceil(filteredSales.length / PAGE_SIZE) || 1;
  const pageData = filteredSales.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE);

  // 勾选相关
  const toggleSelectAll = () => {
    if (selectedIds.size === filteredSales.length) setSelectedIds(new Set());
    else setSelectedIds(new Set(filteredSales.map(s => s.id)));
  };
  const toggleSelect = (id: number, checked: boolean | 'indeterminate') => {
    if (checked === 'indeterminate') return;
    const newSet = new Set(selectedIds);
    if (checked) newSet.add(id); else newSet.delete(id);
    setSelectedIds(newSet);
  };
  const selectedSales = selectedIds.size > 0 ? filteredSales.filter(s => selectedIds.has(s.id)) : [];
  const hasSelection = selectedIds.size > 0;
  const single = selectedIds.size === 1;
  const multi = selectedIds.size > 1;
  const singleSale = single ? selectedSales[0] : null;

  const handleBatchDelete = async () => {
    if (selectedIds.size === 0) { toast.error('请先选择要删除的记录'); return; }
    setBatchDeleteDialogOpen(true);
  };
  const confirmBatchDelete = async () => {
    try {
      const ids = Array.from(selectedIds);
      await apiPost('/v4/finished-product-sales/batch-delete', { ids }, '批量删除成功');
      setSelectedIds(new Set()); loadSales();
    } catch (e) {} finally { setBatchDeleteDialogOpen(false); }
  };

  const filteredCustomers = customers.filter((c: any) => c.name?.toLowerCase().includes(customerSearch.toLowerCase()));
  const filteredProductNames = productNameSearch.trim()
    ? productGroups.filter(g => (g.name || '').toLowerCase().includes(productNameSearch.toLowerCase()))
    : productGroups;

  const paymentStatusMap: Record<number, { label: string; color: string }> = {
    0: { label: '未收款', color: 'bg-red-100 text-red-700' },
    1: { label: '已收款', color: 'bg-green-100 text-green-700' },
  };

  const paymentStatusMapV4: Record<string, { label: string; color: string }> = {
    pending: { label: '未收款', color: 'bg-red-100 text-red-700' },
    partial_paid: { label: '部分收款', color: 'bg-yellow-100 text-yellow-700' },
    fully_paid: { label: '已收款', color: 'bg-green-100 text-green-700' },
  };

  const procurementStatusMap: Record<string, { label: string; color: string }> = {
    pending: { label: '待采购', color: 'bg-gray-100 text-gray-700' },
    ordered: { label: '已下单', color: 'bg-blue-100 text-blue-800' },
    purchased: { label: '采购中', color: 'bg-yellow-100 text-yellow-800' },
    arrived: { label: '已到货', color: 'bg-indigo-100 text-indigo-800' },
    shipped: { label: '已发货', color: 'bg-cyan-100 text-cyan-800' },
    paid: { label: '已收款', color: 'bg-green-100 text-green-800' },
  };

  return (
    <div className="h-full flex flex-col gap-4">
      <div className="flex-none space-y-3">
        <div className="flex flex-row items-center justify-between pb-2"><h1 className="text-lg font-bold flex items-center gap-2"><Factory className="w-5 h-5" /> {pageTitle}</h1></div>
          <div className="flex gap-2 mb-4">
            <div className="relative flex-1">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
              <Input className="pl-9" placeholder="搜索销售单号/客户/业务员..." value={search} onChange={e => { setSearch(e.target.value); setPage(1); }} />
            </div>
            {!isMadeToOrder && (
              <Tabs value={filterType} onValueChange={(v: any) => setFilterType(v)} className="w-auto">
                <TabsList>
                  <TabsTrigger value="all">全部</TabsTrigger>
                  <TabsTrigger value="whole_fish">整鱼</TabsTrigger>
                  <TabsTrigger value="finished_product">成品</TabsTrigger>
                </TabsList>
              </Tabs>
            )}
          </div>

          {/* 操作栏 */}
          <div className="flex items-center gap-2 flex-wrap mb-4">
            {isMadeToOrder && <Button size="sm" variant="outline" onClick={() => handleNew('whole_fish')}><ShoppingCart className="h-4 w-4 mr-1" />新建销售单</Button>}
            {!isMadeToOrder && <Button size="sm" onClick={() => handleNew('finished_product')}><Plus className="h-4 w-4 mr-1" />成品销售</Button>}
            <Button size="sm" variant="outline" onClick={handleExport} disabled={exportLoading}><Download className="h-4 w-4 mr-1" />{exportLoading ? '导出中...' : '导出'}</Button>
            {hasSelection && <div className="h-6 w-px bg-border" />}
            <Button size="sm" variant="ghost" disabled={!single} onClick={() => singleSale && handleViewDetail(singleSale)} title="查看"><Eye className="h-4 w-4 mr-1" />查看</Button>
            <Button size="sm" variant="ghost" disabled={!single} onClick={() => singleSale && handleEdit(singleSale)} title="编辑"><Pencil className="h-4 w-4 mr-1" />编辑</Button>
            <Button size="sm" variant="ghost" className="text-green-600" disabled={!single || (singleSale?.payment_status === 'fully_paid')} onClick={() => singleSale && handlePaymentOpen(singleSale)} title="收款"><Banknote className="h-4 w-4 mr-1" />收款</Button>
            {multi && <Button size="sm" variant="ghost" className="text-green-700" onClick={handleBatchPaymentOpen} title="合并收款"><Banknote className="h-4 w-4 mr-1" />合并收款</Button>}
            <Button size="sm" variant="ghost" className="text-orange-600" disabled={!single} onClick={() => singleSale && handleAdjustOpen(singleSale)} title="调整"><SlidersHorizontal className="h-4 w-4 mr-1" />调整</Button>
            <Button size="sm" variant="ghost" className="text-purple-600" disabled={!single} onClick={() => { if (singleSale) { setReturnPrefillSale({ type: "finished_product", sale: singleSale }); setReturnFormOpen(true); } }} title="售后"><ArrowLeftRight className="h-4 w-4 mr-1" />售后</Button>
            <Button size="sm" variant="ghost" className="text-red-500" disabled={!hasSelection} onClick={multi ? handleBatchDelete : () => singleSale && handleDelete(singleSale)} title="删除"><Trash2 className="h-4 w-4 mr-1" />{multi ? '批量删除' : '删除'}</Button>
          </div>

      </div>

      {/* 列表区 */}
      <div className="flex-1 flex flex-col min-h-0 border rounded-lg overflow-hidden">
        {loading ? (
          <div className="flex-1 flex items-center justify-center text-gray-400">加载中...</div>
        ) : (
          <div className="flex-1 overflow-auto">
              <table className="w-full text-sm">
                <thead className="bg-gray-50 sticky top-0 z-10">
                  <tr>
                    <th className="px-3 py-2 w-[40px]"><Checkbox checked={filteredSales.length > 0 && selectedIds.size === filteredSales.length} onCheckedChange={toggleSelectAll} /></th>
                    <th className="px-3 py-2 text-left whitespace-nowrap">销售单号</th>
                    <th className="px-3 py-2 text-left whitespace-nowrap">类型</th>
                    <th className="px-3 py-2 text-left whitespace-nowrap">日期</th>
                    <th className="px-3 py-2 text-left whitespace-nowrap">客户</th>
                    <th className="px-3 py-2 text-left whitespace-nowrap">业务员</th>
                    <th className="px-3 py-2 text-left whitespace-nowrap">产品</th>
                    <th className="px-3 py-2 text-left whitespace-nowrap">批次</th>
                    <th className="px-3 py-2 text-left whitespace-nowrap">规格</th>
                    <th className="px-3 py-2 text-right whitespace-nowrap">箱数</th>
                    <th className="px-3 py-2 text-right whitespace-nowrap">重量</th>
                    <th className="px-3 py-2 text-right whitespace-nowrap">金额</th>
                    <th className="px-3 py-2 text-right whitespace-nowrap">净金额</th>
                    <th className="px-3 py-2 text-right whitespace-nowrap">已收</th>
                    <th className="px-3 py-2 text-right whitespace-nowrap">售后</th>
                    <th className="px-3 py-2 text-right whitespace-nowrap">抹零</th>
                    <th className="px-3 py-2 text-right whitespace-nowrap">折扣</th>
                    <th className="px-3 py-2 text-center whitespace-nowrap">收款状态</th>
                    <th className="px-3 py-2 text-center whitespace-nowrap">采购状态</th>
                  </tr>
                </thead>
                <tbody>
                  {pageData.length === 0 && <tr><td colSpan={20} className="px-4 py-8 text-center text-gray-400">暂无销售记录</td></tr>}
                  {pageData.map(s => (
                    <tr key={s.id} className={cn("border-t hover:bg-gray-50 cursor-pointer", selectedSale?.id === s.id && "bg-primary/10")} onClick={() => setSelectedSale(s)}>
                      <td className="px-3 py-2"><Checkbox checked={selectedIds.has(s.id)} onCheckedChange={(checked) => toggleSelect(s.id, checked)} /></td>
                      <td className="px-3 py-2 font-mono text-blue-600 cursor-pointer hover:underline whitespace-nowrap" onClick={() => handleViewDetail(s)}>{s.sale_no}</td>
                      <td className="px-3 py-2 whitespace-nowrap"><Badge variant={s.sale_type === 'whole_fish' ? 'secondary' : 'default'}>{s.sale_type === 'whole_fish' ? '整鱼' : '成品'}</Badge></td>
                      <td className="px-3 py-2 whitespace-nowrap">{s.sale_date}</td>
                      <td className="px-3 py-2 whitespace-nowrap">{s.customer}</td>
                      <td className="px-3 py-2 whitespace-nowrap">{s.salesperson || '-'}</td>
                      <td className="px-3 py-2 text-xs text-gray-600 whitespace-nowrap">{s.product_name || '-'}</td>
                      <td className="px-3 py-2 text-xs text-gray-500 whitespace-nowrap">{s.sale_type === 'whole_fish' ? '-' : (s.batch_no || s.factory || '-')}</td>
                      <td className="px-3 py-2 text-xs text-gray-500 whitespace-nowrap">{s.products && s.products.length > 0 ? s.products.map((p: any) => `${p.product_spec || '-'}(${p.box_count || 0})`).join(', ') : (s.products?.[0]?.product_spec || '-')}</td>
                      <td className="px-3 py-2 text-right whitespace-nowrap">{s.quantity || '-'}</td>
                      <td className="px-3 py-2 text-right whitespace-nowrap">{s.weight ? `${s.weight.toFixed(2)} kg` : '-'}</td>
                      <td className="px-3 py-2 text-right font-medium whitespace-nowrap">{s.total_amount ? s.total_amount.toLocaleString('zh-CN', { style: 'currency', currency: 'CNY' }) : '-'}</td>
                      <td className="px-3 py-2 text-right whitespace-nowrap">{s.net_amount ? s.net_amount.toLocaleString('zh-CN', { style: 'currency', currency: 'CNY' }) : '-'}</td>
                      <td className="px-3 py-2 text-right text-green-600 whitespace-nowrap">{s.paid_amount != null ? s.paid_amount.toLocaleString('zh-CN', { style: 'currency', currency: 'CNY' }) : '-'}</td>
                      <td className="px-3 py-2 text-right text-red-500 whitespace-nowrap">{s.after_sales_adjustment ? s.after_sales_adjustment.toLocaleString('zh-CN', { style: 'currency', currency: 'CNY' }) : '-'}</td>
                      <td className="px-3 py-2 text-right whitespace-nowrap">{s.rounding || '-'}</td>
                      <td className="px-3 py-2 text-right whitespace-nowrap">{s.discount || '-'}</td>
                      <td className="px-3 py-2 text-center whitespace-nowrap"><span className={cn("px-2 py-0.5 rounded text-xs", (s.payment_status ? paymentStatusMapV4[s.payment_status] : paymentStatusMap[s.paid])?.color || paymentStatusMap[0].color)}>{(s.payment_status ? paymentStatusMapV4[s.payment_status] : paymentStatusMap[s.paid])?.label || '未收款'}</span></td>
                      <td className="px-3 py-2 text-center whitespace-nowrap">{s.sale_type === 'whole_fish' ? <span className={cn("px-2 py-0.5 rounded text-xs", procurementStatusMap[s.procurement_status || s.status || 'pending']?.color || 'bg-gray-100 text-gray-700')}>{procurementStatusMap[s.procurement_status || s.status || 'pending']?.label || '待采购'}</span> : '-'}</td>
                    </tr>
                  ))}
                  {/* 本页合计 */}
                  {pageData.length > 0 && (
                    <tr className="bg-gray-50 font-medium border-t-2">
                      <td colSpan={9} className="px-3 py-2 text-right text-xs">本页合计:</td>
                      <td className="px-3 py-2 text-right text-xs">{pageData.reduce((s, it) => s + (it.quantity || 0), 0)}</td>
                      <td className="px-3 py-2 text-right text-xs">{pageData.reduce((s, it) => s + (it.weight || 0), 0).toFixed(2)} kg</td>
                      <td className="px-3 py-2 text-right text-xs">¥{pageData.reduce((s, it) => s + (it.total_amount || 0), 0).toLocaleString('zh-CN', {minimumFractionDigits: 2, maximumFractionDigits: 2})}</td>
                      <td className="px-3 py-2 text-right text-xs">¥{pageData.reduce((s, it) => s + (it.net_amount || 0), 0).toLocaleString('zh-CN', {minimumFractionDigits: 2, maximumFractionDigits: 2})}</td>
                      <td className="px-3 py-2 text-right text-xs text-green-600">¥{pageData.reduce((s, it) => s + (it.paid_amount || 0), 0).toLocaleString('zh-CN', {minimumFractionDigits: 2, maximumFractionDigits: 2})}</td>
                      <td className="px-3 py-2 text-right text-xs text-red-500">{(() => { const t = pageData.reduce((s, it) => s + (it.after_sales_adjustment || 0), 0); return t > 0 ? `¥${t.toLocaleString('zh-CN', {minimumFractionDigits: 2, maximumFractionDigits: 2})}` : "-"; })()}</td>
                      <td className="px-3 py-2 text-right text-xs">{(() => { const t = pageData.reduce((s, it) => s + (it.rounding || 0), 0); return t > 0 ? `¥${t.toLocaleString('zh-CN', {minimumFractionDigits: 2, maximumFractionDigits: 2})}` : "-"; })()}</td>
                      <td className="px-3 py-2 text-right text-xs">{(() => { const t = pageData.reduce((s, it) => s + (it.discount || 0), 0); return t > 0 ? `¥${t.toLocaleString('zh-CN', {minimumFractionDigits: 2, maximumFractionDigits: 2})}` : "-"; })()}</td>
                      <td colSpan={2} />
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          )}

          {/* 汇总行 */}
          {!loading && filteredSales.length > 0 && (
            <div className="border-t bg-gray-50 px-4 py-2 text-sm">
              <div className="flex items-center justify-between">
                <span className="text-gray-500">显示 {(page - 1) * PAGE_SIZE + 1} - {Math.min(page * PAGE_SIZE, filteredSales.length)} / 共 {filteredSales.length} 条</span>
                {totalPages > 1 && (
                  <div className="flex items-center gap-2">
                    <button className="px-2 py-1 border rounded text-xs hover:bg-gray-100 disabled:opacity-50" onClick={() => setPage(page - 1)} disabled={page <= 1}>上一页</button>
                    <span className="text-xs">{page} / {totalPages}</span>
                    <button className="px-2 py-1 border rounded text-xs hover:bg-gray-100 disabled:opacity-50" onClick={() => setPage(page + 1)} disabled={page >= totalPages}>下一页</button>
                  </div>
                )}
              </div>
            </div>
          )}
        </div>

      {/* 详情区 */}
      {selectedSale && (
        <div className="flex-none border rounded-lg overflow-auto bg-background">
          <div className="p-3 space-y-2">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <h3 className="font-semibold text-base">销售详情</h3>
                <span className="text-xs bg-gray-100 px-2 py-0.5 rounded">{selectedSale.sale_type === 'whole_fish' ? '整鱼' : '成品'}</span>
              </div>
              <div className="flex gap-2">
                <Button variant="ghost" size="sm" onClick={() => { setDetailSale(selectedSale); setShowDetail(true); }}>
                  <Eye className="h-4 w-4 mr-1" />完整详情
                </Button>
                <Button variant="ghost" size="icon" className="h-8 w-8" onClick={() => setSelectedSale(null)}>
                  <X className="h-4 w-4" />
                </Button>
              </div>
            </div>
            <div className="text-muted-foreground text-xs mb-1">规格明细</div>
            <div className="border rounded-md overflow-hidden">
              <table className="w-full text-sm">
                <thead className="bg-gray-50 sticky top-0 z-10">
                  <tr><th className="px-3 py-1 text-xs">产品名称</th><th className="px-3 py-1 text-xs">规格</th><th className="px-3 py-1 text-xs">批次</th><th className="px-3 py-1 text-xs">箱数</th><th className="px-3 py-1 text-xs">重量(kg)</th><th className="px-3 py-1 text-xs">单价</th><th className="px-3 py-1 text-xs">金额</th></tr>
                </thead>
                <tbody>
                  {(selectedSale.products && selectedSale.products.length > 0) ? selectedSale.products.map((p: any, i: number) => (
                    <tr key={i} className="border-t">
                      <td className="px-3 py-1">{p.product_name || selectedSale.product_name || '-'}</td>
                      <td className="px-3 py-1">{p.product_spec || '-'}</td>
                      <td className="px-3 py-1">{p.batch || formatBatch(p.factory, p.slaughter_date) || '-'}</td>
                      <td className="px-3 py-1">{p.box_count || '-'}</td>
                      <td className="px-3 py-1">{p.weight_kg || '-'}</td>
                      <td className="px-3 py-1">{p.unit_price || '-'}</td>
                      <td className="px-3 py-1">{p.total_amount || '-'}</td>
                    </tr>
                  )) : (
                    <tr className="border-t">
                      <td className="px-3 py-1">{selectedSale.product_name || '-'}</td>
                      <td className="px-3 py-1">-</td>
                      <td className="px-3 py-1">{formatBatch(selectedSale.factory, selectedSale.slaughter_date) || '-'}</td>
                      <td className="px-3 py-1">{selectedSale.quantity || '-'}</td>
                      <td className="px-3 py-1">{selectedSale.weight || '-'}</td>
                      <td className="px-3 py-1">{selectedSale.unit_price || '-'}</td>
                      <td className="px-3 py-1">{selectedSale.total_amount || '-'}</td>
                    </tr>
                  )}
                  <tr className="bg-gray-50 font-medium">
                    <td className="px-3 py-1" colSpan={3}>合计</td>
                    <td className="px-3 py-1">{(selectedSale.products && selectedSale.products.length > 0) ? selectedSale.products.reduce((s: number, p: any) => s + (p.box_count || 0), 0) : (selectedSale.quantity || 0)}</td>
                    <td className="px-3 py-1">{(selectedSale.products && selectedSale.products.length > 0) ? selectedSale.products.reduce((s: number, p: any) => s + (p.weight_kg || 0), 0) : (selectedSale.weight || 0)}</td>
                    <td className="px-3 py-1">-</td>
                    <td className="px-3 py-1">{(selectedSale.products && selectedSale.products.length > 0) ? selectedSale.products.reduce((s: number, p: any) => s + (p.total_amount || 0), 0) : (selectedSale.total_amount || 0)}</td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {/* 销售弹窗 */}
      <Dialog open={showModal} onOpenChange={setShowModal}>
        <DialogContent className="sm:max-w-[1024px] max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>{editingId ? '编辑销售单' : (isMadeToOrder ? '新建销售单' : (form.sale_type === 'whole_fish' ? '新建整鱼销售' : '新建成品销售'))}</DialogTitle>
            <DialogDescription>{form.sale_type === 'whole_fish' ? '销售国内采购的整鱼' : '销售加工后的成品'}</DialogDescription>
          </DialogHeader>
          <div className="space-y-4 mt-2">
            <div className="grid grid-cols-3 gap-3">
              <div><Label>销售日期 *</Label><Input type="date" value={form.sale_date} onChange={e => setForm({...form, sale_date: e.target.value})} /></div>
              <div>
                <Label>客户 *</Label>
                <div className="relative">
                  <Input value={customerSearch || form.customer} placeholder="搜索客户名称..." onFocus={() => { setShowCustomerList(true); setCustomerSearch(''); }} onChange={e => { setCustomerSearch(e.target.value); setShowCustomerList(true); }} onBlur={(e) => { if (!e.relatedTarget?.closest('[data-customer-list]')) setTimeout(() => setShowCustomerList(false), 200); }} />
                  {showCustomerList && (
                    <div className="absolute z-50 w-full bg-white border rounded shadow-lg mt-1 max-h-48 overflow-auto" data-customer-list tabIndex={-1}>
                      {filteredCustomers.length === 0 ? <div className="px-3 py-2 text-sm text-gray-400">{customers.length === 0 ? '加载中...' : '无匹配客户'}</div> : filteredCustomers.map((c: any) => (
                        <div key={c.name} className="px-3 py-2 hover:bg-gray-100 cursor-pointer text-sm" onMouseDown={() => { handleCustomerSelect(c.name); setShowCustomerList(false); setCustomerSearch(''); }}>{c.name}</div>
                      ))}
                    </div>
                  )}
                </div>
              </div>
              <div>
                <Label>业务员</Label>
                <select className="w-full h-9 px-3 border rounded-md text-sm" value={form.salesperson} onChange={e => setForm({...form, salesperson: e.target.value})}>
                  <option value="">请选择</option>
                  {salespeople.map(s => <option key={s.name} value={s.name}>{s.name} ({s.commission_rate}元/kg)</option>)}
                </select>
              </div>
            </div>

            {/* 成品定义V2：级联产品选择器（仅成品销售模式） */}
            {form.sale_type === 'finished_product' && (
              <div className="col-span-3">
                <ProductSelectorV2
                  customerLevel={customers.find((c: any) => c.name === form.customer)?.customer_level || "normal"}
                  quantity={form.products.reduce((sum, p) => sum + (p.box_count || 0), 0)}
                  onSelect={(product) => {
                    if (product) {
                      setForm(prev => ({
                        ...prev,
                        product_name: product.template.name,
                      }));
                      // 更新第一个产品明细
                      setForm(prev => {
                        const newProducts = [...prev.products];
                        if (newProducts.length > 0) {
                          newProducts[0] = {
                            ...newProducts[0],
                            variant_id: product.variant.id,
                            product_name: product.template.name,
                            product_spec: product.spec.name,
                            unit_price: product.priceTier?.price || product.variant.cost_price || 0,
                            total_amount: round2((newProducts[0].weight_kg || 0) * (product.priceTier?.price || product.variant.cost_price || 0)),
                          };
                        }
                        return { ...prev, products: newProducts };
                      });
                    }
                  }}
                />
              </div>
            )}

            <div className="grid grid-cols-3 gap-3">
              <div><Label>收货地址</Label><Input value={form.delivery_address} onChange={e => setForm({...form, delivery_address: e.target.value})} placeholder="客户收货地址" /></div>
              <div><Label>物流信息</Label><Input value={form.logistics_info} onChange={e => setForm({...form, logistics_info: e.target.value})} placeholder="物流单号/承运商" /></div>
              <div><Label>批次号</Label><Input value={form.sale_no} onChange={e => setForm({...form, sale_no: e.target.value})} placeholder="自动生成（可选）" /></div>
            </div>

            <div>
              <div className="flex items-center justify-between mb-2"><Label className="flex items-center gap-1"><Package className="w-4 h-4" /> 规格明细</Label><Button size="sm" variant="outline" onClick={addProduct}><Plus className="w-4 h-4 mr-1" /> 添加规格</Button></div>
              <div className="border rounded-lg overflow-hidden">
                <table className="w-full text-sm">
                  <thead className="bg-gray-50 sticky top-0 z-10">
                    <tr>
                      <th className="px-3 py-2 text-left w-[18%]">产品名称</th>
                      <th className="px-3 py-2 text-left w-[18%]">规格</th>
                      <th className="px-3 py-2 text-left w-[14%]">批次</th>
                      <th className="px-3 py-2 text-right w-[10%]">箱数</th>
                      <th className="px-3 py-2 text-right w-[10%]">重量(kg)</th>
                      <th className="px-3 py-2 text-right w-[10%]">单价(元/kg)</th>
                      <th className="px-3 py-2 text-right w-[10%]">金额</th>
                      <th className="px-3 py-2 text-center w-[2%]"></th>
                    </tr>
                  </thead>
                  <tbody>
                    {form.products.map((p, idx) => {
                      const allSpecOptions = productGroups.flatMap((g: any) => g.specs.map((s: any) => ({
                        key: `${g.name}###${s.spec || ''}`,
                        productName: g.name,
                        spec: s.spec || '',
                        label: `${g.name} · ${s.spec || '(无规格)'}`,
                      })));
                      const currentKey = p.product_name && p.product_spec !== undefined
                        ? `${p.product_name}###${p.product_spec}`
                        : '';
                      return (
                        <tr key={idx} className="border-t">
                          <td className="px-3 py-2">
                            <div className="text-xs font-medium truncate min-w-0" title={p.product_name}>
                              {p.product_name || <span className="text-muted-foreground">产品</span>}
                            </div>
                          </td>
                          <td className="px-3 py-2">
                            <Select value={currentKey} onValueChange={(v) => {
                              const option = allSpecOptions.find((o: any) => o.key === v);
                              if (option) {
                                handleProductChange(idx, 'product_name', option.productName);
                                handleProductChange(idx, 'product_spec', option.spec);
                              }
                            }}>
                              <SelectTrigger className="h-8 text-xs px-2">
                                <SelectValue placeholder="选择规格">
                                  {currentKey && (() => {
                                    const option = allSpecOptions.find((o: any) => o.key === currentKey);
                                    return option ? option.spec || '选择规格' : '选择规格';
                                  })()}
                                </SelectValue>
                              </SelectTrigger>
                              <SelectContent>
                                {allSpecOptions.map((o: any) => (
                                  <SelectItem key={o.key} value={o.key} className="text-xs">
                                    {o.label}
                                  </SelectItem>
                                ))}
                              </SelectContent>
                            </Select>
                          </td>
                          <td className="px-3 py-2">
                            <Input
                              type="text"
                              className="h-8 text-sm"
                              value={String(p.batch || '')}
                              onChange={e => {
                                const batchStr = e.target.value;
                                const year = form.sale_date ? form.sale_date.slice(0, 4) : new Date().getFullYear();
                                const parsed = parseBatch(batchStr, year);
                                if (parsed) {
                                  handleProductChange(idx, 'batch', batchStr);
                                  handleProductChange(idx, 'factory', parsed.factory);
                                  handleProductChange(idx, 'slaughter_date', parsed.slaughter_date);
                                } else {
                                  handleProductChange(idx, 'batch', batchStr);
                                  // 若格式不对，清空派生字段
                                  if (!batchStr.includes('-')) {
                                    handleProductChange(idx, 'factory', '');
                                    handleProductChange(idx, 'slaughter_date', '');
                                  }
                                }
                              }}
                              placeholder="如 N430-0130"
                            />
                          </td>
                          <td className="px-3 py-2"><Input type="text" className="h-8 text-sm text-right" value={String(p.box_count || '')} onChange={e => handleProductChange(idx, 'box_count', parseInt(e.target.value) || 0)} placeholder="待填写" /></td>
                          <td className="px-3 py-2"><Input type="text" className="h-8 text-sm text-right" value={String(p.weight_kg || '')} onChange={e => handleProductChange(idx, 'weight_kg', e.target.value)} onBlur={e => { const val = e.target.value.trim(); if (val.includes('+')) { const sum = val.split('+').reduce((a, b) => a + (parseFloat(b.trim()) || 0), 0); handleProductChange(idx, 'weight_kg', round2(sum)); } else { const num = parseFloat(val); if (!isNaN(num)) handleProductChange(idx, 'weight_kg', round2(num)); } }} placeholder="待填写" /></td>
                          <td className="px-3 py-2"><Input type="number" step="0.01" className="h-8 text-sm text-right" value={String(p.unit_price || '')} onChange={e => handleProductChange(idx, 'unit_price', parseFloat(e.target.value) || 0)} placeholder="元/kg" /></td>
                          <td className="px-3 py-2 text-right font-medium">{p.total_amount ? p.total_amount.toFixed(2) : '-'}</td>
                          <td className="px-3 py-2 text-center"><Button size="sm" variant="ghost" className="text-red-500 h-7 w-7 p-0" disabled={form.products.length <= 1} onClick={() => removeProduct(idx)}><X className="w-4 h-4" /></Button></td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
              <p className="text-xs text-gray-400 mt-1">箱数、重量在供应商理货后确定，下单时可先留空或填写预估数量。</p>
            </div>

            <div className="grid grid-cols-3 gap-3 text-sm bg-gray-50 p-3 rounded">
              <div>总箱数: <span className="font-bold">{form.quantity}</span></div>
              <div>总重量: <span className="font-bold">{form.weight?.toFixed(2)} kg</span></div>
              <div>总金额: <span className="font-bold text-blue-600">{form.total_amount?.toLocaleString('zh-CN', { style: 'currency', currency: 'CNY' })}</span></div>
            </div>

            <div><Label>备注</Label><Input value={form.remark} onChange={e => setForm({...form, remark: e.target.value})} /></div>
            <div className="flex justify-end gap-2">
              <Button variant="outline" onClick={() => setShowModal(false)}>取消</Button>
              <Button onClick={handleSave}><Save className="w-4 h-4 mr-1" /> 保存</Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>

      {/* 详情弹窗 */}
      <Dialog open={showDetail} onOpenChange={setShowDetail}>
        <DialogContent className="max-w-2xl max-h-[80vh] overflow-auto">
          <DialogHeader>
            <DialogTitle>销售单详情</DialogTitle>
            <DialogDescription>{detailSale ? `${detailSale.sale_no ?? `#${detailSale.id}`} · ${detailSale.customer ?? '-'}` : ''}</DialogDescription>
          </DialogHeader>
          {detailSale && <FinishedSaleDetailDialog sale={detailSale} onClose={() => setShowDetail(false)} />}
        </DialogContent>
      </Dialog>

      {/* 收款弹窗 */}
      <Dialog open={showPaymentModal} onOpenChange={setShowPaymentModal}>
        <DialogContent className="max-w-[450px]">
          <DialogHeader>
            <DialogTitle>💰 销售收款</DialogTitle>
            <DialogDescription>
              {receiptSale ? `销售单: ${receiptSale.sale_no ?? `#${receiptSale.id}`} · 客户: ${receiptSale.customer ?? '-'}` : ''}
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-2">
            {/* 金额明细 */}
            <div className="bg-muted/50 rounded-md p-3 text-sm space-y-1">
              <div className="flex justify-between">
                <span className="text-muted-foreground">销售金额</span>
                <span className="font-medium tabular-nums">¥{receiptSale ? Number(receiptSale.total_amount).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) : '0'}</span>
              </div>
              {receiptSale && Number(receiptSale.rounding) !== 0 && (
                <div className="flex justify-between text-orange-600">
                  <span>抹零调整</span>
                  <span className="tabular-nums">-¥{Number(receiptSale.rounding).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</span>
                </div>
              )}
              {receiptSale && Number(receiptSale.after_sales_adjustment) !== 0 && (
                <div className="flex justify-between text-orange-600">
                  <span>售后调整</span>
                  <span className="tabular-nums">-¥{Number(receiptSale.after_sales_adjustment).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</span>
                </div>
              )}
              {receiptSale && Number(receiptSale.discount) !== 0 && (
                <div className="flex justify-between text-orange-600">
                  <span>折扣</span>
                  <span className="tabular-nums">-¥{Number(receiptSale.discount).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</span>
                </div>
              )}
              {receiptSale && Number(receiptSale.commission) !== 0 && (
                <div className="flex justify-between text-orange-600">
                  <span>提成</span>
                  <span className="tabular-nums">-¥{Number(receiptSale.commission).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</span>
                </div>
              )}
              {receiptSale && Number(receiptSale.scan_fee) !== 0 && (
                <div className="flex justify-between text-orange-600">
                  <span>扫码手续费</span>
                  <span className="tabular-nums">-¥{Number(receiptSale.scan_fee).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</span>
                </div>
              )}
              <div className="flex justify-between">
                <span className="text-muted-foreground">已收金额</span>
                <span className="font-medium tabular-nums">¥{receiptSale ? Number(receiptSale.paid_amount || 0).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) : '0'}</span>
              </div>
              <div className="flex justify-between font-semibold border-t border-dashed pt-2 mt-1">
                <span>应收金额</span>
                <span className="text-blue-600 text-base tabular-nums">
                  ¥{receiptSale ? Math.max(0, Number(receiptSale.net_amount || 0) - Number(receiptSale.paid_amount || 0)).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) : '0'}
                </span>
              </div>
            </div>

            <div className="space-y-2">
              <Label>本次实收金额</Label>
              <Input
                inputMode="decimal"
                value={receiptAmount}
                onChange={(e) => handleReceiptAmountChange(e.target.value)}
                placeholder="输入实际收款金额"
                className="text-lg"
              />
            </div>

            <div className="space-y-2">
              <Label className="text-xs">抹零调整</Label>
              <Input
                inputMode="decimal"
                value={receiptRounding}
                onChange={(e) => setReceiptRounding(e.target.value)}
                placeholder="0"
                className="text-sm"
              />
              <p className="text-xs text-muted-foreground">本次收款时减免的尾差金额，默认0</p>
            </div>

            {/* 动态抹零/多收标签 */}
            {(() => {
              if (!receiptSale || !receiptAmount) return null;
              const receivable = Math.max(0, Number(receiptSale.net_amount || 0) - Number(receiptSale.paid_amount || 0));
              const actual = Number(receiptAmount) || 0;
              const rounding = Number(receiptRounding) || 0;
              const diff = receivable - actual - rounding;
              if (diff === 0) {
                return (
                  <div className="flex justify-end items-center mt-1.5 animate-in fade-in slide-in-from-top-1 duration-300">
                    <span className="text-xs text-green-600 font-medium">已付清 ✓</span>
                  </div>
                );
              }
              if (diff > 0) {
                return (
                  <div className="flex justify-end items-center gap-2 mt-1.5 animate-in fade-in slide-in-from-top-1 duration-300">
                    <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-medium bg-orange-50 text-orange-600 border border-orange-200">
                      未付余额
                    </span>
                    <span className="text-sm font-semibold text-orange-600 tabular-nums">¥{diff.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</span>
                  </div>
                );
              }
              return (
                <div className="flex justify-end items-center gap-2 mt-1.5 animate-in fade-in slide-in-from-top-1 duration-300">
                  <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-medium bg-green-50 text-green-600 border border-green-200">
                    ↑ 多收
                  </span>
                  <span className="text-sm font-semibold text-green-600 tabular-nums">¥{Math.abs(diff).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</span>
                </div>
              );
            })()}
            {/* 计算公式提示 */}
            {(() => {
              if (!receiptSale || !receiptAmount) return null;
              const receivable = Math.max(0, Number(receiptSale.net_amount || 0) - Number(receiptSale.paid_amount || 0));
              const actual = Number(receiptAmount) || 0;
              const rounding = Number(receiptRounding) || 0;
              const diff = receivable - actual - rounding;
              if (diff === 0) return null;
              return (
                <div className="flex justify-end mt-0.5">
                  <span className="text-xs text-muted-foreground">
                    应收 ¥{receivable.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })} - 实收 ¥{actual.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })} {rounding > 0 ? `- 抹零 ¥${rounding.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}` : ''} = {diff > 0 ? `未付 ¥${diff.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}` : `多收 ¥${Math.abs(diff).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`}
                  </span>
                </div>
              );
            })()}

            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-1">
                <Label className="text-xs">收款方式</Label>
                <Select value={receiptMethod} onValueChange={(v) => { setReceiptMethod(v ?? ''); if (v === 'balance') setReceiptBankAccountId(''); }}>
                  <SelectTrigger className="h-8 text-xs">
                    <SelectValue placeholder="选择收款方式">
                      {paymentMethodMap[receiptMethod] || receiptMethod}
                    </SelectValue>
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="bank_transfer">银行转账</SelectItem>
                    <SelectItem value="cash">现金</SelectItem>
                    <SelectItem value="check">支票</SelectItem>
                    <SelectItem value="scan">扫码</SelectItem>
                    <SelectItem value="balance">余额抵扣</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              {receiptMethod !== 'balance' ? (
                <div className="space-y-1">
                  <Label className="text-xs">收款银行</Label>
                  <Select value={receiptBankAccountId} onValueChange={(v) => setReceiptBankAccountId(v ?? '')}>
                    <SelectTrigger className="h-8 text-xs">
                      <SelectValue placeholder="选择银行">
                        {(() => {
                          const b = bankAccounts.find((ba: any) => String(ba.id) === receiptBankAccountId);
                          return b ? `${b.bank_name} ···${b.account_number?.slice(-4)}` : '选择银行';
                        })()}
                      </SelectValue>
                    </SelectTrigger>
                    <SelectContent>
                      {bankAccounts.map((b: any) => (
                        <SelectItem key={b.id} value={String(b.id)} className="text-xs">{b.bank_name} ···{b.account_number?.slice(-4)}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
              ) : (
                <div className="space-y-1">
                  <Label className="text-xs">客户余额</Label>
                  <div className="h-8 flex items-center px-3 rounded-md border bg-muted/30 text-xs">
                    {(() => {
                      const c = customersListV4.find((c: any) => c.name === receiptSale?.customer);
                      const bal = Number(c?.prepaid_balance || 0);
                      return (
                        <span className={bal > 0 ? 'text-green-600 font-medium' : 'text-muted-foreground'}>
                          {c ? `¥${bal.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}` : '—'}
                        </span>
                      );
                    })()}
                  </div>
                </div>
              )}
            </div>
            <div className="space-y-1">
              <Label className="text-xs">收款日期</Label>
              <Input type="date" value={receiptDate} onChange={(e) => setReceiptDate(e.target.value)} className="h-8 text-xs" />
            </div>
            <div className="space-y-1">
              <Label className="text-xs">收款描述</Label>
              <Input
                value={receiptDescription}
                onChange={(e) => setReceiptDescription(e.target.value)}
                placeholder="如：张三转账/微信收款/尾款等"
                className="h-8 text-xs"
              />
              <p className="text-xs text-muted-foreground">描述会同步显示在交易流水中</p>
            </div>

            {/* 本次收款后未付 */}
            <div className="border-t pt-3">
              <div className="flex justify-between items-center">
                <span className="text-sm font-medium">本次收款后未付</span>
                <span className={`text-lg font-bold tabular-nums ${(() => {
                  if (!receiptSale) return 'text-gray-400';
                  const remaining = Math.max(0, Number(receiptSale.net_amount || 0) - Number(receiptSale.paid_amount || 0));
                  if (!receiptAmount) {
                    return remaining <= 0 ? 'text-green-600' : 'text-orange-600';
                  }
                  const actual = Number(receiptAmount) || 0;
                  const rounding = Number(receiptRounding) || 0;
                  const afterPay = Math.max(0, remaining - actual - rounding);
                  return afterPay <= 0 ? 'text-green-600' : 'text-orange-600';
                })()}`}>
                  ¥{(() => {
                    if (!receiptSale) return '0.00';
                    const remaining = Math.max(0, Number(receiptSale.net_amount || 0) - Number(receiptSale.paid_amount || 0));
                    if (!receiptAmount) {
                      return remaining.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
                    }
                    const actual = Number(receiptAmount) || 0;
                    const rounding = Number(receiptRounding) || 0;
                    const afterPay = Math.max(0, remaining - actual - rounding);
                    return afterPay.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
                  })()}
                </span>
              </div>
              {receiptAmount && Number(receiptAmount) > 0 && (() => {
                const receivable = Math.max(0, Number(receiptSale?.net_amount || 0) - Number(receiptSale?.paid_amount || 0));
                const actual = Number(receiptAmount) || 0;
                const rounding = Number(receiptRounding) || 0;
                const afterPay = receivable - actual - rounding;
                if (afterPay > 0) {
                  return (
                    <div className="flex justify-end mt-1">
                      <span className="text-xs text-muted-foreground">应收 ¥{receivable.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })} - 实收 ¥{actual.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })} - 抹零 ¥{rounding.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })} = 未付 ¥{afterPay.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</span>
                    </div>
                  );
                }
                if (afterPay <= 0) {
                  return (
                    <div className="flex justify-end mt-1">
                      <span className="text-xs text-muted-foreground">应收 ¥{receivable.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })} - 实收 ¥{actual.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })} {rounding > 0 ? `- 抹零 ¥${rounding.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}` : ''} = 已结清</span>
                    </div>
                  );
                }
                return null;
              })()}
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowPaymentModal(false)}>取消</Button>
            <Button onClick={handlePaymentSave} disabled={paymentLoading} className="bg-green-600 hover:bg-green-700">{paymentLoading ? '收款中...' : '确认收款'}</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* 合并收款弹窗 */}
      <Dialog open={showBatchPaymentModal} onOpenChange={setShowBatchPaymentModal}>
        <DialogContent className="max-w-[550px] max-h-[85vh] overflow-auto">
          <DialogHeader>
            <DialogTitle>💰 合并收款</DialogTitle>
            <DialogDescription>
              共选中 {selectedSales.length} 个销售单
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-2">
            {/* 选中销售单列表 */}
            <div className="border rounded-md overflow-hidden">
              <table className="w-full text-sm">
                <thead className="bg-muted/50">
                  <tr>
                    <th className="px-3 py-2 text-left text-xs">销售单号</th>
                    <th className="px-3 py-2 text-left text-xs">日期</th>
                    <th className="px-3 py-2 text-right text-xs">待收</th>
                    <th className="px-3 py-2 text-right text-xs">本次分配</th>
                  </tr>
                </thead>
                <tbody>
                  {(() => {
                    const totalReceivable = selectedSales.reduce((sum, s) => sum + Math.max(0, (s.net_amount || 0) - (s.paid_amount || 0)), 0);
                    const inputAmount = Number(batchReceiptAmount || 0);
                    const sortedSales = [...selectedSales].sort((a, b) => new Date(a.sale_date).getTime() - new Date(b.sale_date).getTime());
                    let remaining = inputAmount;
                    return sortedSales.map(s => {
                      const receivable = Math.max(0, (s.net_amount || 0) - (s.paid_amount || 0));
                      let amount = 0;
                      let rounding = 0;
                      if (remaining >= receivable) {
                        amount = receivable;
                        remaining = round2(remaining - receivable);
                      } else if (remaining > 0) {
                        amount = remaining;
                        rounding = round2(receivable - remaining);
                        remaining = 0;
                      } else {
                        rounding = receivable;
                      }
                      return { s, amount, rounding };
                    }).map(({ s, amount, rounding }) => (
                      <tr key={s.id} className="border-t">
                        <td className="px-3 py-1.5 font-mono text-xs">{s.sale_no}</td>
                        <td className="px-3 py-1.5 text-xs">{s.sale_date}</td>
                        <td className="px-3 py-1.5 text-right text-xs">¥{Math.max(0, Number(s.net_amount || 0) - Number(s.paid_amount || 0)).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</td>
                        <td className="px-3 py-1.5 text-right text-xs">
                          {amount > 0 && <span className="text-green-600">+¥{amount.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</span>}
                          {rounding > 0 && <span className="text-orange-500 ml-1">抹零¥{rounding.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</span>}
                          {amount === 0 && rounding === 0 && <span className="text-muted-foreground">—</span>}
                        </td>
                      </tr>
                    ));
                  })()}
                  <tr className="bg-muted/30 font-medium">
                    <td className="px-3 py-2 text-xs" colSpan={2}>合计</td>
                    <td className="px-3 py-2 text-right text-xs">¥{selectedSales.reduce((sum, s) => sum + Math.max(0, Number(s.net_amount || 0) - Number(s.paid_amount || 0)), 0).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</td>
                    <td className="px-3 py-2 text-right text-xs">
                      {(() => {
                        const totalReceivable = selectedSales.reduce((sum, s) => sum + Math.max(0, (s.net_amount || 0) - (s.paid_amount || 0)), 0);
                        const inputAmount = Number(batchReceiptAmount || 0);
                        const rounding = Math.max(0, round2(totalReceivable - inputAmount));
                        return (
                          <>
                            <span className="text-green-600">+¥{Math.min(inputAmount, totalReceivable).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</span>
                            {rounding > 0 && <span className="text-orange-500 ml-1">抹零¥{rounding.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</span>}
                          </>
                        );
                      })()}
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>

            <div className="space-y-2">
              <Label>本次总收款金额</Label>
              <Input
                inputMode="decimal"
                value={batchReceiptAmount}
                onChange={(e) => setBatchReceiptAmount(e.target.value)}
                placeholder="输入总收款金额"
                className="text-lg"
              />
              <div className="flex justify-between text-xs text-muted-foreground">
                <span>待收合计：¥{selectedSales.reduce((sum, s) => sum + Math.max(0, (s.net_amount || 0) - (s.paid_amount || 0)), 0).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</span>
                <span>
                  {(() => {
                    const totalReceivable = selectedSales.reduce((sum, s) => sum + Math.max(0, (s.net_amount || 0) - (s.paid_amount || 0)), 0);
                    const inputAmount = Number(batchReceiptAmount || 0);
                    const rounding = Math.max(0, round2(totalReceivable - inputAmount));
                    return rounding > 0 ? `抹零 ¥${rounding.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}` : '';
                  })()}
                </span>
              </div>
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-1">
                <Label className="text-xs">收款方式</Label>
                <Select value={batchReceiptMethod} onValueChange={(v) => { setBatchReceiptMethod(v ?? ''); if (v === 'balance') setBatchReceiptBankAccountId(''); }}>
                  <SelectTrigger className="h-8 text-xs">
                    <SelectValue placeholder="选择收款方式">
                      {paymentMethodMap[batchReceiptMethod] || batchReceiptMethod}
                    </SelectValue>
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="bank_transfer">银行转账</SelectItem>
                    <SelectItem value="cash">现金</SelectItem>
                    <SelectItem value="check">支票</SelectItem>
                    <SelectItem value="scan">扫码</SelectItem>
                    <SelectItem value="balance">余额抵扣</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              {batchReceiptMethod !== 'balance' ? (
                <div className="space-y-1">
                  <Label className="text-xs">收款银行</Label>
                  <Select value={batchReceiptBankAccountId} onValueChange={(v) => setBatchReceiptBankAccountId(v ?? '')}>
                    <SelectTrigger className="h-8 text-xs">
                      <SelectValue placeholder="选择银行">
                        {(() => {
                          const b = bankAccounts.find((ba: any) => String(ba.id) === batchReceiptBankAccountId);
                          return b ? `${b.bank_name} ···${b.account_number?.slice(-4)}` : '选择银行';
                        })()}
                      </SelectValue>
                    </SelectTrigger>
                    <SelectContent>
                      {bankAccounts.map((b: any) => (
                        <SelectItem key={b.id} value={String(b.id)} className="text-xs">{b.bank_name} ···{b.account_number?.slice(-4)}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
              ) : (
                <div className="space-y-1">
                  <Label className="text-xs">客户余额</Label>
                  <div className="h-8 flex items-center px-3 rounded-md border bg-muted/30 text-xs">
                    {(() => {
                      const firstCustomer = selectedSales[0]?.customer;
                      const c = customersListV4.find((c: any) => c.name === firstCustomer);
                      const bal = Number(c?.prepaid_balance || 0);
                      return (
                        <span className={bal > 0 ? 'text-green-600 font-medium' : 'text-muted-foreground'}>
                          {c ? `¥${bal.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}` : '—'}
                        </span>
                      );
                    })()}
                  </div>
                </div>
              )}
            </div>
            <div className="space-y-1">
              <Label className="text-xs">收款日期</Label>
              <Input type="date" value={batchReceiptDate} onChange={(e) => setBatchReceiptDate(e.target.value)} className="h-8 text-xs" />
            </div>
            <div className="space-y-1">
              <Label className="text-xs">收款描述</Label>
              <Input
                value={batchReceiptDescription}
                onChange={(e) => setBatchReceiptDescription(e.target.value)}
                placeholder="如：张三转账/合并收款等"
                className="h-8 text-xs"
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowBatchPaymentModal(false)}>取消</Button>
            <Button onClick={handleBatchPaymentSave} disabled={batchPaymentLoading} className="bg-green-600 hover:bg-green-700">
              {batchPaymentLoading ? '收款中...' : (() => {
                const totalReceivable = selectedSales.reduce((sum, s) => sum + Math.max(0, (s.net_amount || 0) - (s.paid_amount || 0)), 0);
                const inputAmount = Number(batchReceiptAmount || 0);
                const rounding = Math.max(0, round2(totalReceivable - inputAmount));
                if (rounding > 0) {
                  return `确认合并收款 ¥${inputAmount.toLocaleString('en-US', { minimumFractionDigits: 2 })}（抹零 ¥${rounding.toLocaleString('en-US', { minimumFractionDigits: 2 })}）`;
                }
                return `确认合并收款 ¥${Number(batchReceiptAmount || 0).toLocaleString('en-US', { minimumFractionDigits: 2 })}`;
              })()}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* 费用调整弹窗 */}
      <Dialog open={showAdjustModal} onOpenChange={setShowAdjustModal}>
        <DialogContent className="max-w-md">
          <DialogHeader><DialogTitle>费用调整</DialogTitle></DialogHeader>
          <div className="space-y-3 mt-2">
            <div><Label className="text-xs text-gray-500">抹零(元)</Label><Input type="number" step="0.01" value={adjustForm.rounding || ''} onChange={e => setAdjustForm({...adjustForm, rounding: parseFloat(e.target.value) || 0})} /></div>
            <div><Label className="text-xs text-gray-500">手续费(元)</Label><Input type="number" step="0.01" value={adjustForm.scan_fee || ''} onChange={e => setAdjustForm({...adjustForm, scan_fee: parseFloat(e.target.value) || 0})} /></div>
            <div><Label className="text-xs text-gray-500">折扣(元)</Label><Input type="number" step="0.01" value={adjustForm.discount || ''} onChange={e => setAdjustForm({...adjustForm, discount: parseFloat(e.target.value) || 0})} /></div>
            <div><Label className="text-xs text-gray-500">售后调整(元)</Label><Input type="number" step="0.01" value={adjustForm.after_sales_adjustment || ''} onChange={e => setAdjustForm({...adjustForm, after_sales_adjustment: parseFloat(e.target.value) || 0})} /></div>
            <div className="flex justify-end gap-2"><Button variant="outline" onClick={() => setShowAdjustModal(false)}>取消</Button><Button onClick={handleAdjustSave}><Save className="w-4 h-4 mr-1" /> 保存</Button></div>
          </div>
        </DialogContent>
      </Dialog>

      {/* 批量删除确认弹窗 */}
      <Dialog open={batchDeleteDialogOpen} onOpenChange={setBatchDeleteDialogOpen}>
        <DialogContent className="max-w-sm">
          <DialogHeader>
            <DialogTitle>确认批量删除</DialogTitle>
          </DialogHeader>
          <p className="text-sm text-muted-foreground">
            确定删除选中的 {selectedIds.size} 条销售记录吗？此操作不可撤销。
          </p>
          <DialogFooter>
            <Button variant="outline" onClick={() => setBatchDeleteDialogOpen(false)}>取消</Button>
            <Button variant="destructive" onClick={confirmBatchDelete} disabled={deleteLoading}>
              {deleteLoading ? '删除中...' : '确认删除'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* 退货表单弹窗 */}
      <ReturnOrderForm
        open={returnFormOpen}
        onClose={() => { setReturnFormOpen(false); setReturnPrefillSale(null); }}
        prefillSale={returnPrefillSale ?? undefined}
      />

      {/* 删除确认弹窗 */}
      <Dialog open={!!deleteSale} onOpenChange={() => setDeleteSale(null)}>
        <DialogContent className="max-w-sm">
          <DialogHeader><DialogTitle>确认删除</DialogTitle></DialogHeader>
          <p className="text-sm text-muted-foreground">
            确定要删除销售记录 <span className="font-mono font-medium">{deleteSale?.sale_no ?? `#${deleteSale?.id}`}</span> 吗？<br/>客户: {deleteSale?.customer ?? "-"}<br/>此操作不可恢复。
          </p>
          <DialogFooter>
            <Button variant="outline" onClick={() => setDeleteSale(null)} disabled={deleteLoading}>取消</Button>
            <Button variant="destructive" onClick={confirmDelete} disabled={deleteLoading}>{deleteLoading ? '删除中...' : '删除'}</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}

// ==================== 成品销售详情弹窗组件 ====================
function FinishedSaleDetailDialog({ sale, onClose }: { sale: FinishedSale; onClose: () => void }) {
  const [activeTab, setActiveTab] = useState("info");
  const { data: bankAccountsData } = useQuery({
    queryKey: ['bank-accounts'],
    queryFn: async () => {
      const res = await api.get('/v1/finance/bank-accounts');
      return Array.isArray(res.data) ? res.data : (res.data?.items || []);
    },
  });
  const bankAccounts = bankAccountsData || [];

  const paymentMethodMap: Record<string, string> = {
    bank_transfer: "银行转账",
    cash: "现金",
    check: "支票",
    scan: "扫码",
    balance: "余额抵扣",
  };

  const receipts = sale.receipts || [];
  const aftersalesCount = 0; // TODO: 后端支持后接入
  const returnOrders = sale.return_orders || []; // TODO: 后端支持后接入

  const unpaid = Number(sale.net_amount || 0) - Number(sale.paid_amount || 0);

  return (
    <div className="py-2">
      <div className="flex gap-2 mb-4">
        <Button variant={activeTab === "info" ? "default" : "outline"} size="sm" onClick={() => setActiveTab("info")}>基本信息</Button>
        <Button variant={activeTab === "receipts" ? "default" : "outline"} size="sm" onClick={() => setActiveTab("receipts")}>收款记录 ({receipts.length})</Button>
        <Button variant={activeTab === "aftersales" ? "default" : "outline"} size="sm" onClick={() => setActiveTab("aftersales")}>售后/退货 ({aftersalesCount + returnOrders.length})</Button>
      </div>

      {/* 基本信息 */}
      {activeTab === "info" && (
        <div className="space-y-4">
          <div className="grid grid-cols-2 gap-3 text-sm">
            <div><span className="text-muted-foreground">销售单号:</span> <span className="ml-1 font-mono">{sale.sale_no ?? "-"}</span></div>
            <div><span className="text-muted-foreground">类型:</span> <span className="ml-1"><Badge>{sale.sale_type === 'whole_fish' ? '整鱼' : '成品'}</Badge></span></div>
            <div><span className="text-muted-foreground">日期:</span> <span className="ml-1">{sale.sale_date}</span></div>
            <div><span className="text-muted-foreground">客户:</span> <span className="ml-1">{sale.customer ?? "-"}</span></div>
            <div><span className="text-muted-foreground">业务员:</span> <span className="ml-1">{sale.salesperson ?? "-"}</span></div>
            <div><span className="text-muted-foreground">状态:</span> <span className="ml-1">{sale.payment_status === 'fully_paid' ? '已收款' : sale.payment_status === 'partial_paid' ? '部分收款' : '未收款'}</span></div>
            {sale.product_name && <div><span className="text-muted-foreground">产品:</span> <span className="ml-1">{sale.product_name}</span></div>}
            {sale.factory && <div><span className="text-muted-foreground">加工厂:</span> <span className="ml-1">{sale.factory}</span></div>}
            {sale.slaughter_date && <div><span className="text-muted-foreground">宰杀日期:</span> <span className="ml-1">{sale.slaughter_date}</span></div>}
            {sale.delivery_address && <div><span className="text-muted-foreground">收货地址:</span> <span className="ml-1">{sale.delivery_address}</span></div>}
            {sale.logistics_info && <div><span className="text-muted-foreground">物流:</span> <span className="ml-1">{sale.logistics_info}</span></div>}
          </div>

          {/* 规格明细 */}
          {sale.products && sale.products.length > 0 && (
            <div className="border rounded-md overflow-hidden">
              <div className="bg-muted/50 px-3 py-2 text-xs font-medium">规格明细</div>
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead className="text-xs">规格</TableHead>
                    <TableHead className="text-xs">批次</TableHead>
                    <TableHead className="text-xs text-right">箱数</TableHead>
                    <TableHead className="text-xs text-right">重量(kg)</TableHead>
                    <TableHead className="text-xs text-right">单价</TableHead>
                    <TableHead className="text-xs text-right">金额</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {sale.products.map((p) => (
                    <TableRow key={p.id ?? p.product_spec}>
                      <TableCell className="text-sm">{p.product_spec ?? "-"}</TableCell>
                      <TableCell className="text-sm">{p.batch || formatBatch(p.factory, p.slaughter_date) || "-"}</TableCell>
                      <TableCell className="text-sm text-right">{p.box_count ?? "-"}</TableCell>
                      <TableCell className="text-sm text-right">{Number(p.weight_kg).toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</TableCell>
                      <TableCell className="text-sm text-right">{Number(p.unit_price).toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</TableCell>
                      <TableCell className="text-sm text-right">¥{Number(p.total_amount).toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</TableCell>
                    </TableRow>
                  ))}
                  <TableRow className="bg-muted/50 font-medium text-sm">
                    <TableCell colSpan={2} className="text-right">合计:</TableCell>
                    <TableCell className="text-right">{sale.products.reduce((s, it) => s + Number(it.box_count || 0), 0)}</TableCell>
                    <TableCell className="text-right">{sale.products.reduce((s, it) => s + Number(it.weight_kg || 0), 0).toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })} kg</TableCell>
                    <TableCell />
                    <TableCell className="text-right">¥{sale.products.reduce((s, it) => s + Number(it.total_amount || 0), 0).toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</TableCell>
                  </TableRow>
                </TableBody>
              </Table>
            </div>
          )}

          {/* 汇总金额 */}
          <div className="bg-muted p-3 rounded-md space-y-2 text-sm">
            <div className="flex justify-between"><span>毛金额</span><span>¥{Number(sale.total_amount).toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</span></div>
            {Number(sale.rounding) > 0 && <div className="flex justify-between text-red-500"><span>抹零调整</span><span>-¥{Number(sale.rounding).toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</span></div>}
            {Number(sale.after_sales_adjustment) > 0 && <div className="flex justify-between text-red-500"><span>售后调整</span><span>-¥{Number(sale.after_sales_adjustment).toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</span></div>}
            {Number(sale.discount) > 0 && <div className="flex justify-between text-red-500"><span>折扣</span><span>-¥{Number(sale.discount).toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</span></div>}
            {Number(sale.scan_fee) > 0 && <div className="flex justify-between text-red-500"><span>手续费</span><span>-¥{Number(sale.scan_fee).toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</span></div>}
            {Number(sale.commission) > 0 && <div className="flex justify-between text-red-500"><span>业务员提成</span><span>-¥{Number(sale.commission).toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</span></div>}
            <div className="flex justify-between font-semibold border-t pt-1"><span>净金额</span><span>¥{Number(sale.net_amount).toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</span></div>
            <div className="flex justify-between text-green-600"><span>已付</span><span>¥{Number(sale.paid_amount || 0).toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</span></div>
            {unpaid > 0 ? (
              <div className="flex justify-between text-orange-600 font-medium"><span>未付</span><span>¥{unpaid.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</span></div>
            ) : unpaid < 0 ? (
              <div className="flex justify-between text-blue-600 font-medium"><span>应退</span><span>¥{Math.abs(unpaid).toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</span></div>
            ) : (
              <div className="flex justify-between text-green-600 font-medium"><span>已结清</span><span>¥0.00</span></div>
            )}
          </div>

          {sale.remark && <div className="text-sm text-muted-foreground">备注: {sale.remark}</div>}
        </div>
      )}

      {/* 收款记录 */}
      {activeTab === "receipts" && (
        <div className="space-y-4">
          {receipts.length > 0 ? (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead className="text-xs">日期</TableHead>
                  <TableHead className="text-xs">方式</TableHead>
                  <TableHead className="text-xs">银行</TableHead>
                  <TableHead className="text-xs text-right">金额</TableHead>
                  <TableHead className="text-xs">备注</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {receipts.map((r) => (
                  <TableRow key={r.id}>
                    <TableCell className="text-sm">{r.receipt_date}</TableCell>
                    <TableCell className="text-sm">{paymentMethodMap[r.payment_method] || r.payment_method}</TableCell>
                    <TableCell className="text-sm">{(() => {
                      const b = bankAccounts.find((ba: any) => ba.id === r.bank_account_id);
                      return b ? `${b.bank_name} ${b.account_number?.slice(-4)}` : "-";
                    })()}</TableCell>
                    <TableCell className="text-sm text-right">¥{Number(r.amount).toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</TableCell>
                    <TableCell className="text-sm">{r.notes ?? "-"}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          ) : (
            <div className="text-sm text-muted-foreground text-center py-8">暂无收款记录</div>
          )}
        </div>
      )}

      {/* 售后/退货 */}
      {activeTab === "aftersales" && (
        <div className="space-y-4">
          {/* 发起退货按钮 */}
          <div className="flex justify-end">
            <Button size="sm" variant="outline" className="text-orange-600" onClick={() => { toast.info("退货功能开发中"); }}>
              <ArrowLeftRight className="h-4 w-4 mr-1" />发起退货
            </Button>
          </div>

          {/* 售后记录 */}
          {sale.aftersales && sale.aftersales.length > 0 && (
            <div>
              <h4 className="text-sm font-medium mb-2 text-muted-foreground">历史售后记录</h4>
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead className="text-xs">日期</TableHead>
                    <TableHead className="text-xs">类型</TableHead>
                    <TableHead className="text-xs text-right">金额</TableHead>
                    <TableHead className="text-xs">状态</TableHead>
                    <TableHead className="text-xs">原因</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {sale.aftersales.map((a: any) => (
                    <TableRow key={a.id}>
                      <TableCell className="text-sm">{a.record_date}</TableCell>
                      <TableCell className="text-sm">{a.type}</TableCell>
                      <TableCell className="text-sm text-right">¥{Number(a.amount).toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</TableCell>
                      <TableCell className="text-sm">{a.status}</TableCell>
                      <TableCell className="text-sm">{a.reason ?? "-"}</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          )}

          {/* 退货单 */}
          {sale.return_orders && sale.return_orders.length > 0 && (
            <div>
              <h4 className="text-sm font-medium mb-2 text-muted-foreground">退货记录</h4>
              {sale.return_orders.map((ro: any) => (
                <div key={ro.id} className="border rounded-md p-3 mb-2">
                  <div className="flex justify-between items-center">
                    <span className="font-medium text-sm">{ro.return_no}</span>
                    <Badge className={ro.status === "completed" ? "bg-green-100 text-green-800" : ro.status === "approved" ? "bg-blue-100 text-blue-800" : ro.status === "pending_approval" ? "bg-yellow-100 text-yellow-800" : "bg-gray-100 text-gray-800"}>
                      {ro.status === "draft" ? "草稿" : ro.status === "pending_approval" ? "待审批" : ro.status === "approved" ? "已批准" : ro.status === "refunding" ? "退款中" : ro.status === "completed" ? "已完成" : ro.status === "rejected" ? "已拒绝" : ro.status === "cancelled" ? "已取消" : ro.status}
                    </Badge>
                  </div>
                  <div className="text-sm text-muted-foreground mt-1">
                    退货日期: {ro.return_date}
                  </div>
                  <div className="text-sm mt-1">
                    重量: {Number(ro.total_weight_kg).toLocaleString("en-US", { minimumFractionDigits: 2 })} kg · 金额: ¥{Number(ro.total_amount).toLocaleString("en-US", { minimumFractionDigits: 2 })}
                  </div>
                  {ro.problem_description && (
                    <div className="text-sm text-red-500 mt-1">原因: {ro.problem_description}</div>
                  )}
                </div>
              ))}
            </div>
          )}

          {/* 售后调整合计 */}
          {Number(sale.after_sales_adjustment) > 0 && (
            <div className="flex justify-between text-red-500 font-medium border-t pt-2">
              <span>售后调整合计</span>
              <span>-¥{Number(sale.after_sales_adjustment).toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</span>
            </div>
          )}

          {/* 空状态 */}
          {(!sale.aftersales || sale.aftersales.length === 0) && (!sale.return_orders || sale.return_orders.length === 0) && Number(sale.after_sales_adjustment) === 0 && (
            <div className="text-sm text-muted-foreground text-center py-8">暂无售后记录</div>
          )}
        </div>
      )}
    </div>
  );
}

// ==================== 接口类型扩展 ====================
interface FinishedSaleWithReturns extends FinishedSale {
  return_orders?: any[];
}

export default FinishedProductSales;
