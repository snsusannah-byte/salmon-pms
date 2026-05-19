// 采购入库组件 - PurchaseOrderEntry.tsx
// 功能：国内供应商采购入库单录入、编辑、删除、查看

import { useState, useEffect } from 'react';
import { createPortal } from 'react-dom';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Badge } from '@/components/ui/badge';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from '@/components/ui/dialog';
import {
  Truck,
  Plus,
  Search,
  Edit2,
  Trash2,
  Save,
  X,
  Eye,
  Package
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { apiFetch, apiPost, apiDelete } from '@/lib/api';

interface PurchaseOrder {
  id: number;
  purchase_no: string;
  purchase_date: string;
  supplier_id: number;
  supplier_name: string;
  order_type?: string;
  total_amount: number;
  total_weight: number;
  total_boxes: number;
  remark: string;
  status: string;
  created_at: string;
  products?: PurchaseProduct[];
}

interface PurchaseProduct {
  id?: number;
  product_name: string;    // 产品名称
  product_spec: string;    // 规格
  box_count: number;
  weight_kg: number;
  unit_price: number;
  total_amount: number;
}

interface ProductGroup {
  id: number;
  name: string;
  unit: string;
  specs: { id: number; spec: string; code: string; unit: string }[];
}

interface Supplier {
  id: number;
  name: string;
  code?: string;
}

const emptyProduct: PurchaseProduct = {
  product_name: '',
  product_spec: '',
  box_count: 0,
  weight_kg: 0,
  unit_price: 0,
  total_amount: 0
};

const emptyForm = {
  purchase_no: '',
  purchase_date: new Date().toISOString().split('T')[0],
  supplier_id: 0,
  supplier_name: '',
  order_type: 'raw_material' as 'raw_material' | 'accessories',
  total_amount: 0,
  total_weight: 0,
  total_boxes: 0,
  remark: '',
  products: [emptyProduct]
};

function generatePurchaseNo(existing: PurchaseOrder[]): string {
  const now = new Date();
  const dateStr = `${now.getFullYear()}${String(now.getMonth() + 1).padStart(2, '0')}${String(now.getDate()).padStart(2, '0')}`;
  let maxSeq = 0;
  existing.forEach(o => {
    const m = o.purchase_no?.match(new RegExp(`CG${dateStr}\\-(\\d{3})`));
    if (m) maxSeq = Math.max(maxSeq, parseInt(m[1]));
  });
  return `CG${dateStr}-${String(maxSeq + 1).padStart(3, '0')}`;
}

export function PurchaseOrderEntry() {
  const [orders, setOrders] = useState<PurchaseOrder[]>([]);
  const [suppliers, setSuppliers] = useState<Supplier[]>([]);
  const [productGroups, setProductGroups] = useState<ProductGroup[]>([]);
  const [loading, setLoading] = useState(false);
  const [search, setSearch] = useState('');
  const [showModal, setShowModal] = useState(false);
  const [showDetail, setShowDetail] = useState(false);
  const [detailOrder, setDetailOrder] = useState<PurchaseOrder | null>(null);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [form, setForm] = useState(emptyForm);
  const [supplierSearch, setSupplierSearch] = useState('');
  const [showSupplierList, setShowSupplierList] = useState(false);

  const loadOrders = async () => {
    setLoading(true);
    const res = await apiFetch('/v4/purchase-orders');
    if (res.ok && res.data) {
      const arr = Array.isArray(res.data) ? res.data : (res.data.data || []);
      setOrders(arr);
    }
    setLoading(false);
  };

  const loadSuppliers = async () => {
    const res = await apiFetch('/v4/suppliers?limit=500');
    if (res.ok && res.data) {
      const arr = Array.isArray(res.data) ? res.data : (res.data.data || []);
      setSuppliers(arr);
    }
  };

  const loadProducts = async () => {
    const res = await apiFetch('/v4/products-by-name');
    if (res.ok && res.data) {
      const arr = Array.isArray(res.data) ? res.data : (res.data.data || []);
      setProductGroups(arr);
    }
  };

  useEffect(() => { loadOrders(); loadSuppliers(); loadProducts(); }, []);
  useEffect(() => { if (showModal && productGroups.length === 0) loadProducts(); }, [showModal]);

  const handleProductChange = (idx: number, field: keyof PurchaseProduct, value: any) => {
    setForm(prev => {
      const products = [...prev.products];
      products[idx] = { ...products[idx], [field]: value };
      // 自动计算金额
      if (field === 'weight_kg' || field === 'unit_price') {
        products[idx].total_amount = round2(products[idx].weight_kg * products[idx].unit_price);
      }
      // 汇总
      const total_amount = products.reduce((s, p) => s + (p.total_amount || 0), 0);
      const total_weight = products.reduce((s, p) => s + (p.weight_kg || 0), 0);
      const total_boxes = products.reduce((s, p) => s + (p.box_count || 0), 0);
      return { ...prev, products, total_amount, total_weight, total_boxes };
    });
  };

  // 批量更新产品字段（避免多次 setState 导致中间状态不一致）
  const handleProductChanges = (idx: number, updates: Partial<PurchaseProduct>) => {
    setForm(prev => {
      const products = [...prev.products];
      products[idx] = { ...products[idx], ...updates };
      // 自动计算金额
      if (updates.weight_kg !== undefined || updates.unit_price !== undefined) {
        products[idx].total_amount = round2(products[idx].weight_kg * products[idx].unit_price);
      }
      // 汇总
      const total_amount = products.reduce((s, p) => s + (p.total_amount || 0), 0);
      const total_weight = products.reduce((s, p) => s + (p.weight_kg || 0), 0);
      const total_boxes = products.reduce((s, p) => s + (p.box_count || 0), 0);
      return { ...prev, products, total_amount, total_weight, total_boxes };
    });
  };

  const addProduct = () => setForm(prev => ({ ...prev, products: [...prev.products, { ...emptyProduct }] }));
  const removeProduct = (idx: number) => setForm(prev => ({ ...prev, products: prev.products.filter((_, i) => i !== idx) }));

  const [activeProductNameIdx, setActiveProductNameIdx] = useState<number | null>(null);
  const [productNameSearch, setProductNameSearch] = useState('');
  const [activeSpecIdx, setActiveSpecIdx] = useState<number | null>(null);
  const [specSearch, setSpecSearch] = useState('');
  const [productDropdownPos, setProductDropdownPos] = useState<{top:number,left:number,width:number}|null>(null);
  const [specDropdownPos, setSpecDropdownPos] = useState<{top:number,left:number,width:number}|null>(null);

  const handleSave = async () => {
    if (!form.supplier_id) return;
    const payload = {
      ...form,
      products: form.products.filter(p => p.product_name.trim() || p.product_spec.trim())
    };
    try {
      if (editingId) {
        await apiFetch(`/purchase-orders/${editingId}`, {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload)
        }, '更新成功');
      } else {
        await apiPost('/v4/purchase-orders', payload, '创建成功');
      }
      setShowModal(false);
      setForm(emptyForm);
      setEditingId(null);
      loadOrders();
    } catch (e) {}
  };

  const handleEdit = async (order: PurchaseOrder) => {
    const res = await apiFetch(`/purchase-orders/${order.id}`);
    if (res.ok && res.data) {
      const o = res.data;
      setForm({
        purchase_no: o.purchase_no || '',
        purchase_date: o.purchase_date || new Date().toISOString().split('T')[0],
        supplier_id: o.supplier_id || 0,
        supplier_name: o.supplier_name || '',
        order_type: o.order_type || 'raw_material',
        total_amount: o.total_amount || 0,
        total_weight: o.total_weight || 0,
        total_boxes: o.total_boxes || 0,
        remark: o.remark || '',
        products: (o.products?.length ? o.products : [emptyProduct]).map((p: any) => ({
          product_name: p.product_name || '',
          product_spec: p.product_spec || '',
          box_count: p.box_count || 0,
          weight_kg: p.weight_kg || 0,
          unit_price: p.unit_price || 0,
          total_amount: p.total_amount || 0
        }))
      });
      setEditingId(o.id);
      setShowModal(true);
    }
  };

  const handleDelete = async (id: number) => {
    if (!confirm('确定删除该采购入库单？')) return;
    await apiDelete(`/purchase-orders/${id}`, '删除成功');
    loadOrders();
  };

  const handleViewDetail = async (order: PurchaseOrder) => {
    const res = await apiFetch(`/purchase-orders/${order.id}`);
    if (res.ok && res.data) {
      setDetailOrder(res.data);
      setShowDetail(true);
    }
  };

  const handleNew = (type: 'raw_material' | 'accessories') => {
    setForm({ ...emptyForm, order_type: type });
    setEditingId(null);
    setShowModal(true);
  };

  const filteredSuppliers = suppliers.filter(s =>
    s.name.toLowerCase().includes(supplierSearch.toLowerCase())
  );

  const filteredOrders = orders.filter(o =>
    o.purchase_no?.toLowerCase().includes(search.toLowerCase()) ||
    o.supplier_name?.toLowerCase().includes(search.toLowerCase())
  );

  return (
    <div className="space-y-4">
      <Card>
        <CardHeader className="flex flex-row items-center justify-between pb-2">
          <CardTitle className="flex items-center gap-2 text-lg">
            <Truck className="w-5 h-5" /> 采购入库
          </CardTitle>
          <div className="flex gap-2">
            <Button size="sm" variant="outline" onClick={() => handleNew('raw_material')}>
              <Plus className="w-4 h-4 mr-1" /> 整鱼采购
            </Button>
            <Button size="sm" variant="outline" onClick={() => handleNew('accessories')}>
              <Plus className="w-4 h-4 mr-1" /> 辅料采购
            </Button>
          </div>
        </CardHeader>
        <CardContent>
          <div className="flex gap-2 mb-4">
            <div className="relative flex-1">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
              <Input className="pl-9" placeholder="搜索采购单号/供应商..." value={search} onChange={e => setSearch(e.target.value)} />
            </div>
          </div>
          {loading ? (
            <div className="text-center py-8 text-gray-400">加载中...</div>
          ) : (
            <div className="border rounded-lg overflow-hidden">
              <table className="w-full text-sm">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="px-4 py-2 text-left">采购单号</th>
                    <th className="px-4 py-2 text-left">日期</th>
                    <th className="px-4 py-2 text-left">供应商</th>
                    <th className="px-4 py-2 text-right">箱数</th>
                    <th className="px-4 py-2 text-right">重量(kg)</th>
                    <th className="px-4 py-2 text-right">金额(元)</th>
                    <th className="px-4 py-2 text-center">操作</th>
                  </tr>
                </thead>
                <tbody>
                  {filteredOrders.length === 0 && (
                    <tr><td colSpan={7} className="px-4 py-8 text-center text-gray-400">暂无采购入库单</td></tr>
                  )}
                  {filteredOrders.map(o => (
                    <tr key={o.id} className="border-t hover:bg-gray-50">
                      <td className="px-4 py-2 font-mono text-blue-600 cursor-pointer hover:underline" onClick={() => handleViewDetail(o)}>{o.purchase_no}</td>
                      <td className="px-4 py-2">{o.purchase_date}</td>
                      <td className="px-4 py-2">{o.supplier_name}</td>
                      <td className="px-4 py-2 text-right">{o.total_boxes || '-'}</td>
                      <td className="px-4 py-2 text-right">{o.total_weight ? o.total_weight.toFixed(2) : '-'}</td>
                      <td className="px-4 py-2 text-right font-medium">{o.total_amount ? o.total_amount.toLocaleString('zh-CN', { style: 'currency', currency: 'CNY' }) : '-'}</td>
                      <td className="px-4 py-2 text-center">
                        <Button size="sm" variant="ghost" onClick={() => handleEdit(o)}><Edit2 className="w-4 h-4" /></Button>
                        <Button size="sm" variant="ghost" className="text-red-500" onClick={() => handleDelete(o.id)}><Trash2 className="w-4 h-4" /></Button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
      </Card>

      {/* 编辑/新建弹窗 */}
      <Dialog open={showModal} onOpenChange={setShowModal}>
        <DialogContent className="sm:max-w-[900px] max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>
              {editingId ? '编辑采购入库单' : (form.order_type === 'raw_material' ? '整鱼采购入库' : '辅料采购入库')}
            </DialogTitle>
            <DialogDescription>
              {form.order_type === 'raw_material' ? '从国内供应商采购进口规格整鱼，入整包仓库' : '采购包材、配料、消耗品等辅料，入辅料仓库'}
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4 mt-2">
            <div className="grid grid-cols-2 gap-3">
              <div>
                <Label>采购日期 *</Label>
                <Input type="date" value={form.purchase_date} onChange={e => setForm({...form, purchase_date: e.target.value})} />
              </div>
              <div>
                <Label>供应商 *</Label>
                <div className="relative">
                  <Input
                    value={supplierSearch || (form.supplier_id ? suppliers.find(s => s.id === form.supplier_id)?.name || form.supplier_name : '')}
                    placeholder="搜索供应商名称..."
                    onFocus={() => { setShowSupplierList(true); setSupplierSearch(''); }}
                    onChange={e => { setSupplierSearch(e.target.value); setShowSupplierList(true); }}
                    onBlur={() => { setTimeout(() => setShowSupplierList(false), 200); }}
                  />
                  {showSupplierList && (
                    <div className="absolute z-50 w-full bg-white border rounded shadow-lg mt-1 max-h-48 overflow-auto">
                      {filteredSuppliers.length === 0 ? (
                        <div className="px-3 py-2 text-sm text-gray-400">{suppliers.length === 0 ? '加载中...' : '无匹配供应商'}</div>
                      ) : (
                        filteredSuppliers.map(s => (
                          <div
                            key={s.id}
                            className="px-3 py-2 hover:bg-gray-100 cursor-pointer text-sm"
                            onMouseDown={() => {
                              setForm({...form, supplier_id: s.id, supplier_name: s.name});
                              setShowSupplierList(false);
                              setSupplierSearch('');
                            }}
                          >
                            {s.name} {s.code ? `(${s.code})` : ''}
                          </div>
                        ))
                      )}
                    </div>
                  )}
                </div>
              </div>
            </div>

            {/* 产品明细 */}
            <div>
              <div className="flex items-center justify-between mb-2">
                <Label className="flex items-center gap-1"><Package className="w-4 h-4" /> 采购明细</Label>
                <Button size="sm" variant="outline" onClick={addProduct}><Plus className="w-4 h-4 mr-1" /> 添加规格</Button>
              </div>
              <div className="border rounded-lg">
                <table className="w-full text-sm">
                  <thead className="bg-gray-50">
                    <tr>
                      <th className="px-3 py-2 text-left w-[25%]">产品名称</th>
                      <th className="px-3 py-2 text-left w-[15%]">规格</th>
                      <th className="px-3 py-2 text-right w-[10%]">箱数</th>
                      <th className="px-3 py-2 text-right w-[12%]">重量(kg)</th>
                      <th className="px-3 py-2 text-right w-[12%]">单价(元/kg)</th>
                      <th className="px-3 py-2 text-right w-[12%]">金额</th>
                      <th className="px-3 py-2 text-center w-[4%]"></th>
                    </tr>
                  </thead>
                  <tbody>
                    {form.products.map((p, idx) => {
                      const selectedGroup = productGroups.find(g => g.name === p.product_name);
                      const isProductNameOpen = activeProductNameIdx === idx;
                      const isSpecOpen = activeSpecIdx === idx;
                      const filteredProductNames = productNameSearch.trim()
                        ? productGroups.filter(g => {
                            const matchSearch = (g.name || '').toLowerCase().includes(productNameSearch.toLowerCase());
                            if (!matchSearch) return false;
                            if (form.order_type === 'raw_material') return g.unit === 'kg';
                            return g.unit !== 'kg';
                          })
                        : productGroups.filter(g => {
                            if (form.order_type === 'raw_material') return g.unit === 'kg';
                            return g.unit !== 'kg';
                          });
                      const filteredSpecs = specSearch.trim() && selectedGroup
                        ? selectedGroup.specs.filter(s => (s.spec || '').toLowerCase().includes(specSearch.toLowerCase()))
                        : (selectedGroup?.specs || []);
                      return (
                        <tr key={idx} className="border-t">
                          <td className="px-3 py-2 relative">
                            <Input
                              className="h-8 text-sm"
                              value={isProductNameOpen ? String(productNameSearch) : String(p.product_name)}
                              placeholder="输入产品名称搜索..."
                              onFocus={(e) => {
                                const rect = (e.target as HTMLInputElement).getBoundingClientRect();
                                setProductDropdownPos({ top: rect.bottom + 4, left: rect.left, width: rect.width });
                                setActiveProductNameIdx(idx);
                                setProductNameSearch(p.product_name);
                              }}
                              onChange={e => {
                                setProductNameSearch(e.target.value);
                                setActiveProductNameIdx(idx);
                                handleProductChange(idx, 'product_name', e.target.value);
                              }}
                              onBlur={() => {
                                const search = productNameSearch.trim().toLowerCase();
                                let newName = p.product_name;
                                if (search) {
                                  const exact = productGroups.find(g => g.name.toLowerCase() === search);
                                  const filtered = productGroups.filter(g => g.name.toLowerCase().includes(search));
                                  if (exact) newName = exact.name;
                                  else if (filtered.length === 1) newName = filtered[0].name;
                                }
                                if (newName !== p.product_name) {
                                  handleProductChanges(idx, { product_name: newName, product_spec: '' });
                                }
                                setActiveProductNameIdx(null);
                                setProductNameSearch('');
                                setProductDropdownPos(null);
                              }}
                            />
                          </td>
                          <td className="px-3 py-2 relative">
                            <Input
                              className="h-8 text-sm"
                              value={isSpecOpen ? String(specSearch) : String(p.product_spec || '')}
                              placeholder={selectedGroup ? "选择规格..." : "输入规格..."}
                              disabled={!p.product_name}
                              onFocus={(e) => {
                                if (p.product_name) {
                                  const rect = (e.target as HTMLInputElement).getBoundingClientRect();
                                  setSpecDropdownPos({ top: rect.bottom + 4, left: rect.left, width: rect.width });
                                  setActiveSpecIdx(idx);
                                  setSpecSearch(p.product_spec || '');
                                }
                              }}
                              onChange={e => { setSpecSearch(e.target.value); setActiveSpecIdx(idx); }}
                              onBlur={() => {
                                setTimeout(() => {
                                  setActiveSpecIdx(null);
                                  setSpecSearch('');
                                  setSpecDropdownPos(null);
                                }, 200);
                              }}
                            />
                          </td>
                          {/* 浮动下拉层 — 产品名称 */}
                          {isProductNameOpen && productDropdownPos && createPortal(
                            <div
                              className="fixed bg-white border rounded shadow-lg max-h-40 overflow-auto z-[9999]"
                              style={{ top: productDropdownPos.top, left: productDropdownPos.left, width: productDropdownPos.width }}
                            >
                              {filteredProductNames.length === 0 ? (
                                <div className="px-3 py-2 text-sm text-gray-400">无匹配产品</div>
                              ) : (
                                filteredProductNames.map(g => (
                                  <div
                                    key={g.id}
                                    className="px-3 py-2 hover:bg-gray-100 cursor-pointer text-sm"
                                    onMouseDown={() => {
                                      handleProductChanges(idx, { product_name: g.name, product_spec: '' });
                                      setActiveProductNameIdx(null);
                                      setProductNameSearch('');
                                      setProductDropdownPos(null);
                                    }}
                                  >
                                    {g.name}
                                  </div>
                                ))
                              )}
                            </div>,
                            document.body
                          )}
                          {/* 浮动下拉层 — 规格 */}
                          {isSpecOpen && specDropdownPos && createPortal(
                            <div
                              className="fixed bg-white border rounded shadow-lg max-h-32 overflow-auto z-[9999]"
                              style={{ top: specDropdownPos.top, left: specDropdownPos.left, width: specDropdownPos.width }}
                            >
                              {!selectedGroup ? (
                                <div className="px-3 py-2 text-sm text-gray-400">请先选择产品名称</div>
                              ) : filteredSpecs.length === 0 ? (
                                <div className="px-3 py-2 text-sm text-gray-400">无匹配规格</div>
                              ) : (
                                filteredSpecs.map(s => (
                                  <div
                                    key={s.id}
                                    className="px-3 py-2 hover:bg-gray-100 cursor-pointer text-sm"
                                    onMouseDown={() => {
                                      handleProductChanges(idx, { product_spec: s.spec || '' });
                                      setActiveSpecIdx(null);
                                      setSpecSearch('');
                                      setSpecDropdownPos(null);
                                    }}
                                  >
                                    {s.spec || '(无规格)'}
                                  </div>
                                ))
                              )}
                            </div>,
                            document.body
                          )}
                          <td className="px-3 py-2">
                            <Input type="number" className="h-8 text-sm text-right" value={String(p.box_count || '')} onChange={e => handleProductChange(idx, 'box_count', parseInt(e.target.value) || 0)} placeholder="箱" />
                          </td>
                          <td className="px-3 py-2">
                            <Input type="number" step="0.01" className="h-8 text-sm text-right" value={String(p.weight_kg || '')} onChange={e => handleProductChange(idx, 'weight_kg', parseFloat(e.target.value) || 0)} placeholder="kg" />
                          </td>
                          <td className="px-3 py-2">
                            <Input type="number" step="0.01" className="h-8 text-sm text-right" value={String(p.unit_price || '')} onChange={e => handleProductChange(idx, 'unit_price', parseFloat(e.target.value) || 0)} placeholder="元/kg" />
                          </td>
                          <td className="px-3 py-2 text-right font-medium">{p.total_amount ? p.total_amount.toFixed(2) : '-'}</td>
                          <td className="px-3 py-2 text-center">
                            <Button size="sm" variant="ghost" className="text-red-500 h-7 w-7 p-0" disabled={form.products.length <= 1} onClick={() => removeProduct(idx)}>
                              <X className="w-4 h-4" />
                            </Button>
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            </div>

            <div className="grid grid-cols-4 gap-3 text-sm bg-gray-50 p-3 rounded">
              <div>总箱数: <span className="font-bold">{form.total_boxes}</span></div>
              <div>总重量: <span className="font-bold">{form.total_weight?.toFixed(2)} kg</span></div>
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
            <DialogTitle>采购入库单详情</DialogTitle>
          </DialogHeader>
          {detailOrder && (
            <div className="space-y-3 mt-2">
              <div className="grid grid-cols-3 gap-3 text-sm">
                <div><span className="text-gray-500">采购单号:</span> <span className="font-mono font-medium">{detailOrder.purchase_no}</span></div>
                <div><span className="text-gray-500">日期:</span> {detailOrder.purchase_date}</div>
                <div><span className="text-gray-500">供应商:</span> {detailOrder.supplier_name}</div>
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
                    {detailOrder.products?.map((p, i) => (
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
              <div className="text-sm text-gray-500">备注: {detailOrder.remark || '-'}</div>
            </div>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
}

function round2(n: number): number {
  return Math.round((n + Number.EPSILON) * 100) / 100;
}
