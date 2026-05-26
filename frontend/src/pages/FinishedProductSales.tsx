// 成品销售组件 - FinishedProductSales.tsx
// 功能：整鱼国内采购销售 + 成品定义产品销售
// 模式切换：whole_fish（整鱼销售）/ finished_product（成品销售）

import { useState, useEffect } from 'react';
import { createPortal } from 'react-dom';
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
}

interface FinishedSaleProduct {
  id?: number;
  product_name?: string;
  product_spec: string;
  factory?: string;
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
  product_spec: '', box_count: 0, weight_kg: 0, unit_price: 0,
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

function round2(n: number): number {
  return Math.round((n + Number.EPSILON) * 100) / 100;
}

export function FinishedProductSales() {
  const [sales, setSales] = useState<FinishedSale[]>([]);
  const [customers, setCustomers] = useState<any[]>([]);
  const [salespeople, setSalespeople] = useState<{name: string, commission_rate: number}[]>([]);
  const [productGroups, setProductGroups] = useState<ProductGroup[]>([]);
  const [loading, setLoading] = useState(false);
  const [search, setSearch] = useState('');
  const [filterType, setFilterType] = useState<'all' | 'whole_fish' | 'finished_product'>('all');
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
  const [showAdjustModal, setShowAdjustModal] = useState(false);
  const [adjustForm, setAdjustForm] = useState({ discount: 0, scan_fee: 0, rounding: 0, after_sales_adjustment: 0 });
  const [adjustSaleId, setAdjustSaleId] = useState<number | null>(null);
  const [deleteSale, setDeleteSale] = useState<FinishedSale | null>(null);
  const [deleteLoading, setDeleteLoading] = useState(false);
  const [selectedIds, setSelectedIds] = useState<Set<number>>(new Set());
  const [exportLoading, setExportLoading] = useState(false);

  // 产品名称下拉
  const [activeProductNameIdx, setActiveProductNameIdx] = useState<number | null>(null);
  const [productNameSearch, setProductNameSearch] = useState('');
  const [productDropdownPos, setProductDropdownPos] = useState<{top:number,left:number,width:number}|null>(null);
  // 规格下拉
  const [activeSpecIdx, setActiveSpecIdx] = useState<number | null>(null);
  const [specSearch, setSpecSearch] = useState('');
  const [specDropdownPos, setSpecDropdownPos] = useState<{top:number,left:number,width:number}|null>(null);

  const loadSales = async () => {
    setLoading(true);
    const res = await apiFetch('v4/finished-product-sales');
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
      products: form.products.filter(p => p.product_spec.trim())
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
        product_name: p.product_name || '', product_spec: p.product_spec || '', factory: p.factory || '',
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
    if (!confirm(`确定删除选中的 ${selectedIds.size} 条销售记录吗？`)) return;
    try {
      const ids = Array.from(selectedIds);
      await apiPost('/v4/finished-product-sales/batch-delete', { ids }, '批量删除成功');
      setSelectedIds(new Set()); loadSales();
    } catch (e) {}
  };

  const filteredCustomers = customers.filter(c => c.toLowerCase().includes(customerSearch.toLowerCase()));
  const filteredProductNames = productNameSearch.trim()
    ? productGroups.filter(g => (g.name || '').toLowerCase().includes(productNameSearch.toLowerCase()))
    : productGroups;

  const paymentStatusMap: Record<number, { label: string; color: string }> = {
    0: { label: '未收款', color: 'bg-red-100 text-red-700' },
    1: { label: '已收款', color: 'bg-green-100 text-green-700' },
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
    <div className="space-y-4">
      <Card>
        <CardHeader className="flex flex-row items-center justify-between pb-2"><CardTitle className="flex items-center gap-2 text-lg"><Factory className="w-5 h-5" /> 成品销售</CardTitle></CardHeader>
        <CardContent>
          <div className="flex gap-2 mb-4">
            <div className="relative flex-1">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
              <Input className="pl-9" placeholder="搜索销售单号/客户/业务员..." value={search} onChange={e => setSearch(e.target.value)} />
            </div>
            <Tabs value={filterType} onValueChange={(v: any) => setFilterType(v)} className="w-auto">
              <TabsList>
                <TabsTrigger value="all">全部</TabsTrigger>
                <TabsTrigger value="whole_fish">整鱼</TabsTrigger>
                <TabsTrigger value="finished_product">成品</TabsTrigger>
              </TabsList>
            </Tabs>
          </div>

          {/* 操作栏 */}
          <div className="flex items-center gap-2 flex-wrap mb-4">
            <Button size="sm" variant="outline" onClick={() => handleNew('whole_fish')}><ShoppingCart className="h-4 w-4 mr-1" />整鱼销售</Button>
            <Button size="sm" onClick={() => handleNew('finished_product')}><Plus className="h-4 w-4 mr-1" />成品销售</Button>
            <Button size="sm" variant="outline" onClick={handleExport} disabled={exportLoading}><Download className="h-4 w-4 mr-1" />{exportLoading ? '导出中...' : '导出'}</Button>
            {hasSelection && <div className="h-6 w-px bg-border" />}
            <Button size="sm" variant="ghost" disabled={!single} onClick={() => singleSale && handleViewDetail(singleSale)} title="查看"><Eye className="h-4 w-4 mr-1" />查看</Button>
            <Button size="sm" variant="ghost" disabled={!single} onClick={() => singleSale && handleEdit(singleSale)} title="编辑"><Pencil className="h-4 w-4 mr-1" />编辑</Button>
            <Button size="sm" variant="ghost" className="text-green-600" disabled={!single || (singleSale?.payment_status === 'fully_paid')} onClick={() => singleSale && handlePaymentOpen(singleSale)} title="收款"><Banknote className="h-4 w-4 mr-1" />收款</Button>
            <Button size="sm" variant="ghost" className="text-orange-600" disabled={!single} onClick={() => singleSale && handleAdjustOpen(singleSale)} title="调整"><SlidersHorizontal className="h-4 w-4 mr-1" />调整</Button>
            <Button size="sm" variant="ghost" className="text-red-500" disabled={!hasSelection} onClick={multi ? handleBatchDelete : () => singleSale && handleDelete(singleSale)} title="删除"><Trash2 className="h-4 w-4 mr-1" />{multi ? '批量删除' : '删除'}</Button>
          </div>

          {loading ? (
            <div className="text-center py-8 text-gray-400">加载中...</div>
          ) : (
            <div className="border rounded-lg overflow-hidden">
              <table className="w-full text-sm">
                <thead className="bg-gray-50">
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
                  {filteredSales.length === 0 && <tr><td colSpan={20} className="px-4 py-8 text-center text-gray-400">暂无销售记录</td></tr>}
                  {filteredSales.map(s => (
                    <tr key={s.id} className="border-t hover:bg-gray-50">
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
                      <td className="px-3 py-2 text-right text-green-600 whitespace-nowrap">{s.paid_amount ? s.paid_amount.toLocaleString('zh-CN', { style: 'currency', currency: 'CNY' }) : '-'}</td>
                      <td className="px-3 py-2 text-right text-red-500 whitespace-nowrap">{s.after_sales_adjustment ? s.after_sales_adjustment.toLocaleString('zh-CN', { style: 'currency', currency: 'CNY' }) : '-'}</td>
                      <td className="px-3 py-2 text-right whitespace-nowrap">{s.rounding || '-'}</td>
                      <td className="px-3 py-2 text-right whitespace-nowrap">{s.discount || '-'}</td>
                      <td className="px-3 py-2 text-center whitespace-nowrap"><span className={cn("px-2 py-0.5 rounded text-xs", paymentStatusMap[s.paid]?.color || paymentStatusMap[0].color)}>{paymentStatusMap[s.paid]?.label || '未收款'}</span></td>
                      <td className="px-3 py-2 text-center whitespace-nowrap">{s.sale_type === 'whole_fish' ? <span className={cn("px-2 py-0.5 rounded text-xs", procurementStatusMap[s.procurement_status || s.status || 'pending']?.color || 'bg-gray-100 text-gray-700')}>{procurementStatusMap[s.procurement_status || s.status || 'pending']?.label || '待采购'}</span> : '-'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
      </Card>

      {/* 销售弹窗 */}
      <Dialog open={showModal} onOpenChange={setShowModal}>
        <DialogContent className="sm:max-w-[1024px] max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>{editingId ? '编辑销售单' : (form.sale_type === 'whole_fish' ? '新建整鱼销售' : '新建成品销售')}</DialogTitle>
            <DialogDescription>{form.sale_type === 'whole_fish' ? '销售国内采购的整鱼' : '销售加工后的成品'}</DialogDescription>
          </DialogHeader>
          <div className="space-y-4 mt-2">
            <div className="grid grid-cols-3 gap-3">
              <div><Label>销售日期 *</Label><Input type="date" value={form.sale_date} onChange={e => setForm({...form, sale_date: e.target.value})} /></div>
              <div>
                <Label>客户 *</Label>
                <div className="relative">
                  <Input value={customerSearch || form.customer} placeholder="搜索客户名称..." onFocus={() => { setShowCustomerList(true); setCustomerSearch(''); }} onChange={e => { setCustomerSearch(e.target.value); setShowCustomerList(true); }} onBlur={() => { setTimeout(() => setShowCustomerList(false), 200); }} />
                  {showCustomerList && (
                    <div className="absolute z-50 w-full bg-white border rounded shadow-lg mt-1 max-h-48 overflow-auto">
                      {filteredCustomers.length === 0 ? <div className="px-3 py-2 text-sm text-gray-400">{customers.length === 0 ? '加载中...' : '无匹配客户'}</div> : filteredCustomers.map(c => (
                        <div key={c} className="px-3 py-2 hover:bg-gray-100 cursor-pointer text-sm" onMouseDown={() => { setForm({...form, customer: c}); setShowCustomerList(false); setCustomerSearch(''); }}>{c}</div>
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

            <div className="grid grid-cols-3 gap-3">
              <div>
                <Label>产品名称 *</Label>
                <div className="relative">
                  <Input className="h-9 text-sm" value={activeProductNameIdx === -1 ? String(productNameSearch) : String(form.product_name)} placeholder="输入产品名称搜索..."
                    onFocus={(e) => { const rect = (e.target as HTMLInputElement).getBoundingClientRect(); setProductDropdownPos({ top: rect.bottom + 4, left: rect.left, width: rect.width }); setActiveProductNameIdx(-1); setProductNameSearch(form.product_name); }}
                    onChange={e => { setProductNameSearch(e.target.value); setActiveProductNameIdx(-1); setForm({...form, product_name: e.target.value}); }}
                    onBlur={() => { setActiveProductNameIdx(null); setProductNameSearch(''); setProductDropdownPos(null); }}
                  />
                  {activeProductNameIdx === -1 && productDropdownPos && createPortal(
                    <div className="fixed bg-white border rounded shadow-lg max-h-40 overflow-auto z-[9999]" style={{ top: productDropdownPos.top, left: productDropdownPos.left, width: productDropdownPos.width }}>
                      {filteredProductNames.length === 0 ? <div className="px-3 py-2 text-sm text-gray-400">无匹配产品</div> : filteredProductNames.map(g => (
                        <div key={g.id} className="px-3 py-2 hover:bg-gray-100 cursor-pointer text-sm" onMouseDown={() => { setForm(prev => ({ ...prev, product_name: g.name })); setActiveProductNameIdx(null); setProductNameSearch(''); setProductDropdownPos(null); }}>{g.name}</div>
                      ))}
                    </div>, document.body
                  )}
                </div>
              </div>
              <div><Label>宰杀日期</Label><Input type="date" value={form.slaughter_date} onChange={e => setForm({...form, slaughter_date: e.target.value})} /></div>
              <div><Label>加工厂</Label><Input value={form.factory} onChange={e => setForm({...form, factory: e.target.value})} placeholder="加工厂名称" /></div>
            </div>

            <div className="grid grid-cols-3 gap-3">
              <div><Label>收货地址</Label><Input value={form.delivery_address} onChange={e => setForm({...form, delivery_address: e.target.value})} placeholder="客户收货地址" /></div>
              <div><Label>物流信息</Label><Input value={form.logistics_info} onChange={e => setForm({...form, logistics_info: e.target.value})} placeholder="物流单号/承运商" /></div>
              <div><Label>批次号</Label><Input value={form.sale_no} onChange={e => setForm({...form, sale_no: e.target.value})} placeholder="自动生成（可选）" /></div>
            </div>

            <div>
              <div className="flex items-center justify-between mb-2"><Label className="flex items-center gap-1"><Package className="w-4 h-4" /> 规格明细</Label><Button size="sm" variant="outline" onClick={addProduct}><Plus className="w-4 h-4 mr-1" /> 添加规格</Button></div>
              <div className="border rounded-lg overflow-hidden">
                <table className="w-full text-sm">
                  <thead className="bg-gray-50">
                    <tr>
                      <th className="px-3 py-2 text-left w-[25%]">规格</th>
                      <th className="px-3 py-2 text-right w-[14%]">箱数</th>
                      <th className="px-3 py-2 text-right w-[16%]">重量(kg)</th>
                      <th className="px-3 py-2 text-right w-[16%]">单价(元/kg)</th>
                      <th className="px-3 py-2 text-right w-[16%]">金额</th>
                      <th className="px-3 py-2 text-center w-[8%]"></th>
                    </tr>
                  </thead>
                  <tbody>
                    {form.products.map((p, idx) => {
                      const isSpecOpen = activeSpecIdx === idx;
                      const filteredSpecs = specSearch.trim() && selectedProductGroup ? selectedProductGroup.specs.filter(s => (s.spec || '').toLowerCase().includes(specSearch.toLowerCase())) : (selectedProductGroup?.specs || []);
                      return (
                        <tr key={idx} className="border-t">
                          <td className="px-3 py-2 relative">
                            <Input className="h-8 text-sm" value={isSpecOpen ? String(specSearch) : String(p.product_spec || '')} placeholder={selectedProductGroup ? "选择规格..." : "请先选择产品名称"} disabled={!form.product_name}
                              onFocus={(e) => { if (form.product_name) { const rect = (e.target as HTMLInputElement).getBoundingClientRect(); setSpecDropdownPos({ top: rect.bottom + 4, left: rect.left, width: rect.width }); setActiveSpecIdx(idx); setSpecSearch(p.product_spec || ''); }}}
                              onChange={e => { setSpecSearch(e.target.value); setActiveSpecIdx(idx); }}
                              onBlur={() => { setTimeout(() => { setActiveSpecIdx(null); setSpecSearch(''); setSpecDropdownPos(null); }, 200); }}
                            />
                            {isSpecOpen && specDropdownPos && createPortal(
                              <div className="fixed bg-white border rounded shadow-lg max-h-32 overflow-auto z-[9999]" style={{ top: specDropdownPos.top, left: specDropdownPos.left, width: specDropdownPos.width }}>
                                {!selectedProductGroup ? <div className="px-3 py-2 text-sm text-gray-400">请先选择产品名称</div> : filteredSpecs.length === 0 ? <div className="px-3 py-2 text-sm text-gray-400">无匹配规格</div> : filteredSpecs.map(s => (
                                  <div key={s.id} className="px-3 py-2 hover:bg-gray-100 cursor-pointer text-sm" onMouseDown={() => { handleProductChange(idx, 'product_spec', s.spec || ''); setActiveSpecIdx(null); setSpecSearch(''); setSpecDropdownPos(null); }}>{s.spec || '(无规格)'} {s.code ? `· ${s.code}` : ''}</div>
                                ))}
                              </div>, document.body
                            )}
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
        <DialogContent className="max-w-2xl">
          <DialogHeader><DialogTitle>销售单详情</DialogTitle></DialogHeader>
          {detailSale && (
            <div className="space-y-3 mt-2">
              <div className="grid grid-cols-3 gap-3 text-sm">
                <div><span className="text-gray-500">单号:</span> <span className="font-mono font-medium">{detailSale.sale_no}</span></div>
                <div><span className="text-gray-500">类型:</span> <Badge>{detailSale.sale_type === 'whole_fish' ? '整鱼' : '成品'}</Badge></div>
                <div><span className="text-gray-500">日期:</span> {detailSale.sale_date}</div>
                <div><span className="text-gray-500">客户:</span> {detailSale.customer}</div>
                <div><span className="text-gray-500">业务员:</span> {detailSale.salesperson || '-'}</div>
                <div><span className="text-gray-500">状态:</span> {detailSale.paid ? '已收款' : '未收款'}</div>
                {detailSale.product_name && <div><span className="text-gray-500">产品:</span> {detailSale.product_name}</div>}
                {detailSale.factory && <div><span className="text-gray-500">加工厂:</span> {detailSale.factory}</div>}
                {detailSale.slaughter_date && <div><span className="text-gray-500">宰杀日期:</span> {detailSale.slaughter_date}</div>}
                {detailSale.delivery_address && <div><span className="text-gray-500">收货地址:</span> {detailSale.delivery_address}</div>}
                {detailSale.logistics_info && <div><span className="text-gray-500">物流:</span> {detailSale.logistics_info}</div>}
              </div>
              <div className="border rounded-lg overflow-hidden">
                <table className="w-full text-sm">
                  <thead className="bg-gray-50">
                    <tr><th className="px-3 py-2 text-left">规格</th><th className="px-3 py-2 text-right">箱数</th><th className="px-3 py-2 text-right">重量(kg)</th><th className="px-3 py-2 text-right">单价</th><th className="px-3 py-2 text-right">金额</th></tr>
                  </thead>
                  <tbody>
                    {detailSale.products?.map((p, i) => (
                      <tr key={i} className="border-t"><td className="px-3 py-2">{p.product_spec}</td><td className="px-3 py-2 text-right">{p.box_count}</td><td className="px-3 py-2 text-right">{p.weight_kg?.toFixed(2)}</td><td className="px-3 py-2 text-right">{p.unit_price?.toFixed(2)}</td><td className="px-3 py-2 text-right font-medium">{p.total_amount?.toFixed(2)}</td></tr>
                    )) || <tr><td colSpan={5} className="px-3 py-4 text-center text-gray-400">无明细</td></tr>}
                  </tbody>
                </table>
              </div>
              <div className="grid grid-cols-2 gap-3 text-sm">
                <div>抹零: {detailSale.rounding?.toFixed(2)}</div><div>手续费: {detailSale.scan_fee?.toFixed(2)}</div>
                <div>折扣: {detailSale.discount?.toFixed(2)}</div><div>售后调整: {detailSale.after_sales_adjustment?.toFixed(2)}</div>
                <div>业务员提成: {detailSale.commission?.toFixed(2)}</div><div className="font-bold">净收入: {detailSale.net_amount?.toFixed(2)}</div>
              </div>
              <div className="text-sm text-gray-500">备注: {detailSale.remark || '-'}</div>
            </div>
          )}
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
                    <SelectValue />
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

      {/* 删除确认弹窗 */}
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
