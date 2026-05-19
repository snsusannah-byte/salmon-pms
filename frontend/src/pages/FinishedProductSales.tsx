// 成品销售组件 - FinishedProductSales.tsx
// 功能：整鱼国内采购销售 + 成品定义产品销售
// 模式切换：whole_fish（整鱼销售，功能跟 SalesEntry 一致）/ finished_product（成品销售）

import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Badge } from '@/components/ui/badge';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from '@/components/ui/dialog';
import { Tabs, TabsList, TabsTrigger } from '@/components/ui/tabs';
import {
  Factory, ShoppingCart, Plus, Search, Edit2, Trash2, Save, X,
  CreditCard, Eye, Package, DollarSign
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { apiFetch, apiPost, apiDelete } from '@/lib/api';

interface FinishedSale {
  id: number;
  sale_no: string;
  sale_type: 'whole_fish' | 'finished_product';
  source_id: string;
  source_no: string;
  customer: string;
  salesperson: string;
  product_name: string;
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
  remark: string;
  created_at: string;
  products?: FinishedSaleProduct[];
}

interface FinishedSaleProduct {
  id?: number;
  product_spec: string;
  box_count: number;
  weight_kg: number;
  unit_price: number;
  total_amount: number;
  commission_rate: number;
  commission_amount: number;
  after_sales_adjustment: number;
}

interface PurchaseOrder {
  id: number;
  purchase_no: string;
  purchase_date: string;
  supplier_name: string;
  total_weight: number;
  total_boxes: number;
  total_amount: number;
}

const emptyProduct: FinishedSaleProduct = {
  product_spec: '', box_count: 0, weight_kg: 0, unit_price: 0,
  total_amount: 0, commission_rate: 0, commission_amount: 0, after_sales_adjustment: 0
};

const emptyForm = {
  sale_no: '', sale_type: 'whole_fish' as 'whole_fish' | 'finished_product',
  source_id: '', source_no: '', customer: '', salesperson: '',
  product_name: '', quantity: 0, weight: 0, unit_price: 0,
  total_amount: 0, sale_date: new Date().toISOString().split('T')[0],
  discount: 0, scan_fee: 0, rounding: 0, after_sales_adjustment: 0,
  commission: 0, actual_amount: 0, net_amount: 0, paid: false,
  remark: '', products: [emptyProduct]
};

function generateSaleNo(existing: FinishedSale[], type: string): string {
  const prefix = type === 'whole_fish' ? 'WF' : 'CP';
  const now = new Date();
  const dateStr = `${now.getFullYear()}${String(now.getMonth() + 1).padStart(2, '0')}${String(now.getDate()).padStart(2, '0')}`;
  let maxSeq = 0;
  existing.forEach(s => {
    if (s.sale_no?.startsWith(prefix)) {
      const m = s.sale_no.match(new RegExp(`${prefix}${dateStr}-(\\d{3})`));
      if (m) maxSeq = Math.max(maxSeq, parseInt(m[1]));
    }
  });
  return `${prefix}${dateStr}-${String(maxSeq + 1).padStart(3, '0')}`;
}

export function FinishedProductSales() {
  const [sales, setSales] = useState<FinishedSale[]>([]);
  const [purchaseOrders, setPurchaseOrders] = useState<PurchaseOrder[]>([]);
  const [customers, setCustomers] = useState<string[]>([]);
  const [salespeople, setSalespeople] = useState<{name: string, commission_rate: number}[]>([]);
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
  const [paymentForm, setPaymentForm] = useState({ actual_amount: 0, rounding: 0 });
  const [paymentSaleId, setPaymentSaleId] = useState<number | null>(null);

  const [showAdjustModal, setShowAdjustModal] = useState(false);
  const [adjustForm, setAdjustForm] = useState({ discount: 0, scan_fee: 0, rounding: 0, after_sales_adjustment: 0 });
  const [adjustSaleId, setAdjustSaleId] = useState<number | null>(null);

  const loadSales = async () => {
    setLoading(true);
    const res = await apiFetch('/v4/finished-product-sales');
    if (res.ok && res.data) setSales(res.data);
    setLoading(false);
  };

  const loadPurchaseOrders = async () => {
    const res = await apiFetch('/v4/purchase-orders');
    if (res.ok && res.data) setPurchaseOrders(res.data);
  };

  const loadCustomers = async () => {
    const res = await apiFetch('/v4/customers?limit=500');
    if (res.ok && res.data) {
      const items = Array.isArray(res.data) ? res.data : (res.data.data || []);
      setCustomers(items.map((c: any) => c.name));
    }
  };

  const loadSalespeople = async () => {
    const res = await apiFetch('/v1/salespersons/?limit=500');
    if (res.ok && res.data) {
      const items = Array.isArray(res.data) ? res.data : (res.data.items || []);
      setSalespeople(items.map((s: any) => ({ name: s.name || s.full_name, commission_rate: s.commission_rate || 0 })));
    }
  };

  useEffect(() => { loadSales(); loadPurchaseOrders(); loadCustomers(); loadSalespeople(); }, []);

  const handleProductChange = (idx: number, field: keyof FinishedSaleProduct, value: any) => {
    setForm(prev => {
      const products = [...prev.products];
      products[idx] = { ...products[idx], [field]: value };
      if (field === 'weight_kg' || field === 'unit_price') {
        products[idx].total_amount = round2(products[idx].weight_kg * products[idx].unit_price);
      }
      // 汇总
      const total_amount = products.reduce((s, p) => s + (p.total_amount || 0), 0);
      const weight = products.reduce((s, p) => s + (p.weight_kg || 0), 0);
      const quantity = products.reduce((s, p) => s + (p.box_count || 0), 0);
      // 自动计算佣金
      const sp = salespeople.find(s => s.name === prev.salesperson);
      const commission_rate = sp?.commission_rate || 0;
      const commission = round2(weight * commission_rate);
      // 净收入
      const net = round2(total_amount - prev.discount - prev.scan_fee - prev.rounding - prev.after_sales_adjustment - commission);
      return { ...prev, products, total_amount, weight, quantity, commission, net_amount: net };
    });
  };

  const addProduct = () => setForm(prev => ({ ...prev, products: [...prev.products, { ...emptyProduct }] }));
  const removeProduct = (idx: number) => setForm(prev => ({ ...prev, products: prev.products.filter((_, i) => i !== idx) }));

  const handleSave = async () => {
    if (!form.sale_no.trim() || !form.customer.trim()) return;
    const payload = {
      ...form,
      paid: form.paid ? 1 : 0,
      products: form.products.filter(p => p.product_spec.trim())
    };
    try {
      if (editingId) {
        await apiFetch(`/finished-product-sales/${editingId}`, {
          method: 'PUT', headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload)
        }, '更新成功');
      } else {
        await apiPost('/v4/finished-product-sales', payload, '创建成功');
      }
      setShowModal(false);
      setForm(emptyForm);
      setEditingId(null);
      loadSales();
    } catch (e) {}
  };

  const handleEdit = async (sale: FinishedSale) => {
    const res = await apiFetch(`/finished-product-sales/${sale.id}`);
    if (res.ok && res.data) {
      const s = res.data;
      setForm({
        sale_no: s.sale_no || '',
        sale_type: s.sale_type || 'whole_fish',
        source_id: s.source_id || '',
        source_no: s.source_no || '',
        customer: s.customer || '',
        salesperson: s.salesperson || '',
        product_name: s.product_name || '',
        quantity: s.quantity || 0,
        weight: s.weight || 0,
        unit_price: s.unit_price || 0,
        total_amount: s.total_amount || 0,
        sale_date: s.sale_date || new Date().toISOString().split('T')[0],
        discount: s.discount || 0,
        scan_fee: s.scan_fee || 0,
        rounding: s.rounding || 0,
        after_sales_adjustment: s.after_sales_adjustment || 0,
        commission: s.commission || 0,
        actual_amount: s.actual_amount || 0,
        net_amount: s.net_amount || 0,
        paid: !!s.paid,
        remark: s.remark || '',
        products: (s.products?.length ? s.products : [emptyProduct]).map((p: any) => ({
          product_spec: p.product_spec || '', box_count: p.box_count || 0,
          weight_kg: p.weight_kg || 0, unit_price: p.unit_price || 0,
          total_amount: p.total_amount || 0, commission_rate: p.commission_rate || 0,
          commission_amount: p.commission_amount || 0, after_sales_adjustment: p.after_sales_adjustment || 0
        }))
      });
      setEditingId(s.id);
      setShowModal(true);
    }
  };

  const handleDelete = async (id: number) => {
    if (!confirm('确定删除该销售记录？')) return;
    await apiDelete(`/finished-product-sales/${id}`, '删除成功');
    loadSales();
  };

  const handleViewDetail = async (sale: FinishedSale) => {
    const res = await apiFetch(`/finished-product-sales/${sale.id}`);
    if (res.ok && res.data) {
      setDetailSale(res.data);
      setShowDetail(true);
    }
  };

  const handleNew = (type: 'whole_fish' | 'finished_product') => {
    setForm({ ...emptyForm, sale_type: type });
    setEditingId(null);
    setShowModal(true);
  };

  const handleAdjustOpen = (sale: FinishedSale) => {
    setAdjustSaleId(sale.id);
    setAdjustForm({
      discount: sale.discount || 0,
      scan_fee: sale.scan_fee || 0,
      rounding: sale.rounding || 0,
      after_sales_adjustment: sale.after_sales_adjustment || 0,
    });
    setShowAdjustModal(true);
  };

  const handleAdjustSave = async () => {
    if (!adjustSaleId) return;
    const sale = sales.find(s => s.id === adjustSaleId);
    if (!sale) return;
    const commission = sale.commission || 0;
    const net = round2(sale.total_amount - adjustForm.discount - adjustForm.scan_fee - adjustForm.rounding - adjustForm.after_sales_adjustment - commission);
    await apiFetch(`/finished-product-sales/${adjustSaleId}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        ...sale,
        discount: adjustForm.discount,
        scan_fee: adjustForm.scan_fee,
        rounding: adjustForm.rounding,
        after_sales_adjustment: adjustForm.after_sales_adjustment,
        net_amount: net,
      })
    }, '调整成功');
    setShowAdjustModal(false);
    setAdjustSaleId(null);
    loadSales();
  };

  const handlePaymentOpen = (sale: FinishedSale) => {
    setPaymentSaleId(sale.id);
    setPaymentForm({ actual_amount: sale.net_amount || 0, rounding: 0 });
    setShowPaymentModal(true);
  };

  const handlePaymentSave = async () => {
    if (!paymentSaleId) return;
    const sale = sales.find(s => s.id === paymentSaleId);
    if (!sale) return;
    const net = round2(paymentForm.actual_amount - paymentForm.rounding - (sale.scan_fee || 0) - (sale.commission || 0) - (sale.discount || 0) - (sale.after_sales_adjustment || 0));
    await apiFetch(`/finished-product-sales/${paymentSaleId}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        ...sale,
        actual_amount: paymentForm.actual_amount,
        rounding: paymentForm.rounding,
        net_amount: net,
        paid: 1
      })
    }, '收款成功');
    setShowPaymentModal(false);
    setPaymentSaleId(null);
    loadSales();
  };

  const filteredSales = sales.filter(s => {
    if (filterType !== 'all' && s.sale_type !== filterType) return false;
    return (s.sale_no?.toLowerCase().includes(search.toLowerCase()) ||
            s.customer?.toLowerCase().includes(search.toLowerCase()) ||
            s.salesperson?.toLowerCase().includes(search.toLowerCase()));
  });

  const filteredCustomers = customers.filter(c =>
    c.toLowerCase().includes(customerSearch.toLowerCase())
  );

  const paymentStatusMap: Record<number, { label: string; color: string }> = {
    0: { label: '未收款', color: 'bg-red-100 text-red-700' },
    1: { label: '已收款', color: 'bg-green-100 text-green-700' },
  };

  return (
    <div className="space-y-4">
      <Card>
        <CardHeader className="flex flex-row items-center justify-between pb-2">
          <CardTitle className="flex items-center gap-2 text-lg">
            <Factory className="w-5 h-5" /> 成品销售
          </CardTitle>
          <div className="flex gap-2">
            <Button size="sm" variant="outline" onClick={() => handleNew('whole_fish')}>
              <ShoppingCart className="w-4 h-4 mr-1" /> 整鱼销售
            </Button>
            <Button size="sm" onClick={() => handleNew('finished_product')}>
              <Plus className="w-4 h-4 mr-1" /> 成品销售
            </Button>
          </div>
        </CardHeader>
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
          {loading ? (
            <div className="text-center py-8 text-gray-400">加载中...</div>
          ) : (
            <div className="border rounded-lg overflow-hidden">
              <table className="w-full text-sm">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="px-4 py-2 text-left">单号</th>
                    <th className="px-4 py-2 text-left">类型</th>
                    <th className="px-4 py-2 text-left">日期</th>
                    <th className="px-4 py-2 text-left">客户</th>
                    <th className="px-4 py-2 text-left">业务员</th>
                    <th className="px-4 py-2 text-right">重量(kg)</th>
                    <th className="px-4 py-2 text-right">金额</th>
                    <th className="px-4 py-2 text-center">状态</th>
                    <th className="px-4 py-2 text-center">操作</th>
                  </tr>
                </thead>
                <tbody>
                  {filteredSales.length === 0 && (
                    <tr><td colSpan={9} className="px-4 py-8 text-center text-gray-400">暂无销售记录</td></tr>
                  )}
                  {filteredSales.map(s => (
                    <tr key={s.id} className="border-t hover:bg-gray-50">
                      <td className="px-4 py-2 font-mono text-blue-600 cursor-pointer hover:underline" onClick={() => handleViewDetail(s)}>{s.sale_no}</td>
                      <td className="px-4 py-2">
                        <Badge variant={s.sale_type === 'whole_fish' ? 'secondary' : 'default'}>
                          {s.sale_type === 'whole_fish' ? '整鱼' : '成品'}
                        </Badge>
                      </td>
                      <td className="px-4 py-2">{s.sale_date}</td>
                      <td className="px-4 py-2">{s.customer}</td>
                      <td className="px-4 py-2">{s.salesperson || '-'}</td>
                      <td className="px-4 py-2 text-right">{s.weight ? s.weight.toFixed(2) : '-'}</td>
                      <td className="px-4 py-2 text-right font-medium">{s.total_amount ? s.total_amount.toLocaleString('zh-CN', { style: 'currency', currency: 'CNY' }) : '-'}</td>
                      <td className="px-4 py-2 text-center">
                        <span className={cn("px-2 py-0.5 rounded text-xs", paymentStatusMap[s.paid]?.color || paymentStatusMap[0].color)}>
                          {paymentStatusMap[s.paid]?.label || '未收款'}
                        </span>
                      </td>
                      <td className="px-4 py-2 text-center">
                        <Button size="sm" variant="ghost" onClick={() => handleAdjustOpen(s)} title="费用调整"><DollarSign className="w-4 h-4 text-orange-600" /></Button>
                        {!s.paid && <Button size="sm" variant="ghost" onClick={() => handlePaymentOpen(s)} title="收款"><CreditCard className="w-4 h-4 text-green-600" /></Button>}
                        <Button size="sm" variant="ghost" onClick={() => handleEdit(s)} title="编辑"><Edit2 className="w-4 h-4" /></Button>
                        <Button size="sm" variant="ghost" className="text-red-500" onClick={() => handleDelete(s.id)} title="删除"><Trash2 className="w-4 h-4" /></Button>
                      </td>
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
            <DialogDescription>
              {form.sale_type === 'whole_fish' ? '销售国内采购的整鱼' : '销售加工后的成品'}
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4 mt-2">
            {/* 基本信息 */}
            <div className="grid grid-cols-3 gap-3">
              <div>
                <Label>销售日期 *</Label>
                <Input type="date" value={form.sale_date} onChange={e => setForm({...form, sale_date: e.target.value})} />
              </div>
              <div>
                <Label>客户 *</Label>
                <div className="relative">
                  <Input
                    value={customerSearch || form.customer}
                    placeholder="搜索客户名称..."
                    onFocus={() => { setShowCustomerList(true); setCustomerSearch(''); }}
                    onChange={e => { setCustomerSearch(e.target.value); setShowCustomerList(true); }}
                    onBlur={() => { setTimeout(() => setShowCustomerList(false), 200); }}
                  />
                  {showCustomerList && (
                    <div className="absolute z-50 w-full bg-white border rounded shadow-lg mt-1 max-h-48 overflow-auto">
                      {filteredCustomers.length === 0 ? (
                        <div className="px-3 py-2 text-sm text-gray-400">{customers.length === 0 ? '加载中...' : '无匹配客户'}</div>
                      ) : (
                        filteredCustomers.map(c => (
                          <div key={c} className="px-3 py-2 hover:bg-gray-100 cursor-pointer text-sm" onMouseDown={() => {
                            setForm({...form, customer: c});
                            setShowCustomerList(false);
                            setCustomerSearch('');
                          }}>{c}</div>
                        ))
                      )}
                    </div>
                  )}
                </div>
              </div>
              <div>
                <Label>业务员</Label>
                <select
                  className="w-full h-9 px-3 border rounded-md text-sm"
                  value={form.salesperson}
                  onChange={e => setForm({...form, salesperson: e.target.value})}
                >
                  <option value="">请选择</option>
                  {salespeople.map(s => (
                    <option key={s.name} value={s.name}>{s.name} ({s.commission_rate}元/kg)</option>
                  ))}
                </select>
              </div>
            </div>

            {/* 整鱼模式：关联采购入库单 */}
            {form.sale_type === 'whole_fish' && (
              <div>
                <Label>关联采购入库单（整鱼来源）</Label>
                <select
                  className="w-full h-9 px-3 border rounded-md text-sm"
                  value={form.source_id}
                  onChange={async e => {
                    const orderId = e.target.value;
                    const order = purchaseOrders.find(o => String(o.id) === orderId);
                    const base = {
                      ...form,
                      source_id: orderId,
                      source_no: order?.purchase_no || ''
                    };
                    if (orderId) {
                      // 拉取采购单详情，自动带出产品明细
                      const res = await apiFetch(`v4/purchase-orders/${orderId}`);
                      if (res.ok && res.data?.products?.length) {
                        const products = res.data.products.map((p: any) => ({
                          product_spec: p.product_spec || '',
                          box_count: p.box_count || 0,
                          weight_kg: p.weight_kg || 0,
                          unit_price: 0,
                          total_amount: 0,
                          commission_rate: 0,
                          commission_amount: 0,
                          after_sales_adjustment: 0
                        }));
                        setForm({ ...base, products });
                      } else {
                        setForm(base);
                      }
                    } else {
                      setForm(base);
                    }
                  }}
                >
                  <option value="">不关联（手动填写）</option>
                  {purchaseOrders.map(o => (
                    <option key={o.id} value={String(o.id)}>
                      {o.purchase_no} | {o.supplier_name} | {o.total_weight?.toFixed(0)}kg
                    </option>
                  ))}
                </select>
              </div>
            )}

            {/* 成品模式：产品名称 */}
            {form.sale_type === 'finished_product' && (
              <div>
                <Label>成品名称</Label>
                <Input value={form.product_name} onChange={e => setForm({...form, product_name: e.target.value})} placeholder="如: 三文鱼刺身切片" />
              </div>
            )}

            {/* 产品明细 */}
            <div>
              <div className="flex items-center justify-between mb-2">
                <Label className="flex items-center gap-1"><Package className="w-4 h-4" /> 销售明细</Label>
                <Button size="sm" variant="outline" onClick={addProduct}><Plus className="w-4 h-4 mr-1" /> 添加规格</Button>
              </div>
              <div className="border rounded-lg overflow-hidden">
                <table className="w-full text-sm">
                  <thead className="bg-gray-50">
                    <tr>
                      <th className="px-3 py-2 text-left">产品名称/规格</th>
                      <th className="px-3 py-2 text-right w-24">箱数</th>
                      <th className="px-3 py-2 text-right w-28">重量(kg)</th>
                      <th className="px-3 py-2 text-right w-28">单价(元/kg)</th>
                      <th className="px-3 py-2 text-right w-28">金额</th>
                      <th className="px-3 py-2 text-center w-12"></th>
                    </tr>
                  </thead>
                  <tbody>
                    {form.products.map((p, idx) => (
                      <tr key={idx} className="border-t">
                        <td className="px-3 py-2">
                          <Input size={1} value={p.product_spec} onChange={e => handleProductChange(idx, 'product_spec', e.target.value)} placeholder={form.sale_type === 'whole_fish' ? '如: 三文鱼 6-7kg/条' : '如: 三文鱼刺身 200g/包'} />
                        </td>
                        <td className="px-3 py-2">
                          <Input type="number" className="text-right" value={p.box_count || ''} onChange={e => handleProductChange(idx, 'box_count', parseInt(e.target.value) || 0)} />
                        </td>
                        <td className="px-3 py-2">
                          <Input type="number" step="0.01" className="text-right" value={p.weight_kg || ''} onChange={e => handleProductChange(idx, 'weight_kg', parseFloat(e.target.value) || 0)} />
                        </td>
                        <td className="px-3 py-2">
                          <Input type="number" step="0.01" className="text-right" value={p.unit_price || ''} onChange={e => handleProductChange(idx, 'unit_price', parseFloat(e.target.value) || 0)} />
                        </td>
                        <td className="px-3 py-2 text-right font-medium">{p.total_amount ? p.total_amount.toFixed(2) : '-'}</td>
                        <td className="px-3 py-2 text-center">
                          <Button size="sm" variant="ghost" className="text-red-500" disabled={form.products.length <= 1} onClick={() => removeProduct(idx)}>
                            <X className="w-4 h-4" />
                          </Button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>

            {/* 汇总 */}
            <div className="grid grid-cols-3 gap-3 text-sm bg-gray-50 p-3 rounded">
              <div>总箱数: <span className="font-bold">{form.quantity}</span></div>
              <div>总重量: <span className="font-bold">{form.weight?.toFixed(2)} kg</span></div>
              <div>总金额: <span className="font-bold text-blue-600">{form.total_amount?.toLocaleString('zh-CN', { style: 'currency', currency: 'CNY' })}</span></div>
            </div>

            <div>
              <Label>备注</Label>
              <Input value={form.remark} onChange={e => setForm({...form, remark: e.target.value})} />
            </div>

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
          <DialogHeader>
            <DialogTitle>销售单详情</DialogTitle>
          </DialogHeader>
          {detailSale && (
            <div className="space-y-3 mt-2">
              <div className="grid grid-cols-3 gap-3 text-sm">
                <div><span className="text-gray-500">单号:</span> <span className="font-mono font-medium">{detailSale.sale_no}</span></div>
                <div><span className="text-gray-500">类型:</span> <Badge>{detailSale.sale_type === 'whole_fish' ? '整鱼' : '成品'}</Badge></div>
                <div><span className="text-gray-500">日期:</span> {detailSale.sale_date}</div>
                <div><span className="text-gray-500">客户:</span> {detailSale.customer}</div>
                <div><span className="text-gray-500">业务员:</span> {detailSale.salesperson || '-'}</div>
                <div><span className="text-gray-500">状态:</span> {detailSale.paid ? '已收款' : '未收款'}</div>
              </div>
              <div className="border rounded-lg overflow-hidden">
                <table className="w-full text-sm">
                  <thead className="bg-gray-50">
                    <tr>
                      <th className="px-3 py-2 text-left">规格</th>
                      <th className="px-3 py-2 text-right">箱数</th>
                      <th className="px-3 py-2 text-right">重量(kg)</th>
                      <th className="px-3 py-2 text-right">单价</th>
                      <th className="px-3 py-2 text-right">金额</th>
                    </tr>
                  </thead>
                  <tbody>
                    {detailSale.products?.map((p, i) => (
                      <tr key={i} className="border-t">
                        <td className="px-3 py-2">{p.product_spec}</td>
                        <td className="px-3 py-2 text-right">{p.box_count}</td>
                        <td className="px-3 py-2 text-right">{p.weight_kg?.toFixed(2)}</td>
                        <td className="px-3 py-2 text-right">{p.unit_price?.toFixed(2)}</td>
                        <td className="px-3 py-2 text-right font-medium">{p.total_amount?.toFixed(2)}</td>
                      </tr>
                    )) || <tr><td colSpan={5} className="px-3 py-4 text-center text-gray-400">无明细</td></tr>}
                  </tbody>
                </table>
              </div>
              <div className="grid grid-cols-2 gap-3 text-sm">
                <div>抹零: {detailSale.rounding?.toFixed(2)}</div>
                <div>手续费: {detailSale.scan_fee?.toFixed(2)}</div>
                <div>折扣: {detailSale.discount?.toFixed(2)}</div>
                <div>售后调整: {detailSale.after_sales_adjustment?.toFixed(2)}</div>
                <div>业务员提成: {detailSale.commission?.toFixed(2)}</div>
                <div className="font-bold">净收入: {detailSale.net_amount?.toFixed(2)}</div>
              </div>
              <div className="text-sm text-gray-500">备注: {detailSale.remark || '-'}</div>
            </div>
          )}
        </DialogContent>
      </Dialog>

      {/* 收款弹窗 */}
      <Dialog open={showPaymentModal} onOpenChange={setShowPaymentModal}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle>收款登记</DialogTitle>
          </DialogHeader>
          <div className="space-y-3 mt-2">
            <div>
              <Label>实收金额(元)</Label>
              <Input type="number" step="0.01" value={paymentForm.actual_amount || ''} onChange={e => setPaymentForm({...paymentForm, actual_amount: parseFloat(e.target.value) || 0})} />
            </div>
            <div>
              <Label>抹零(元)</Label>
              <Input type="number" step="0.01" value={paymentForm.rounding || ''} onChange={e => setPaymentForm({...paymentForm, rounding: parseFloat(e.target.value) || 0})} />
            </div>
            <div className="flex justify-end gap-2">
              <Button variant="outline" onClick={() => setShowPaymentModal(false)}>取消</Button>
              <Button onClick={handlePaymentSave}><DollarSign className="w-4 h-4 mr-1" /> 确认收款</Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>

      {/* 费用调整弹窗 */}
      <Dialog open={showAdjustModal} onOpenChange={setShowAdjustModal}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle>费用调整</DialogTitle>
          </DialogHeader>
          <div className="space-y-3 mt-2">
            <div>
              <Label className="text-xs text-gray-500">抹零(元)</Label>
              <Input type="number" step="0.01" value={adjustForm.rounding || ''} onChange={e => setAdjustForm({...adjustForm, rounding: parseFloat(e.target.value) || 0})} />
            </div>
            <div>
              <Label className="text-xs text-gray-500">手续费(元)</Label>
              <Input type="number" step="0.01" value={adjustForm.scan_fee || ''} onChange={e => setAdjustForm({...adjustForm, scan_fee: parseFloat(e.target.value) || 0})} />
            </div>
            <div>
              <Label className="text-xs text-gray-500">折扣(元)</Label>
              <Input type="number" step="0.01" value={adjustForm.discount || ''} onChange={e => setAdjustForm({...adjustForm, discount: parseFloat(e.target.value) || 0})} />
            </div>
            <div>
              <Label className="text-xs text-gray-500">售后调整(元)</Label>
              <Input type="number" step="0.01" value={adjustForm.after_sales_adjustment || ''} onChange={e => setAdjustForm({...adjustForm, after_sales_adjustment: parseFloat(e.target.value) || 0})} />
            </div>
            <div className="flex justify-end gap-2">
              <Button variant="outline" onClick={() => setShowAdjustModal(false)}>取消</Button>
              <Button onClick={handleAdjustSave}><Save className="w-4 h-4 mr-1" /> 保存</Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}

function round2(n: number): number {
  return Math.round((n + Number.EPSILON) * 100) / 100;
}
