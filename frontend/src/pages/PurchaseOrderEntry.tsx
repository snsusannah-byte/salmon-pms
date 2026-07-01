// 采购入库组件 - PurchaseOrderEntry.tsx
// 参考进口单证(InvoicesPage)布局：功能区、列表区、详情区

import { useState, useEffect } from 'react';
import { createPortal } from 'react-dom';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Badge } from '@/components/ui/badge';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from '@/components/ui/dialog';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { cn } from '@/lib/utils';
import { apiFetch, apiPost, apiDelete } from '@/lib/api';
import {
  Truck,
  Plus,
  Search,
  Edit2,
  Trash2,
  Save,
  X,
  Eye,
  Package,
  Lock,
  Unlock,
  MinusCircle,
} from 'lucide-react';
import { PurchaseReturnForm } from "@/components/purchase-returns/PurchaseReturnForm";

interface PurchaseOrder {
  id: number;
  purchase_no: string;
  purchase_date: string;
  supplier_id: number;
  supplier_name: string;
  order_type?: string;
  total_amount: number;
  after_sales_adjustment?: number;
  net_amount?: number;
  total_weight: number;
  total_boxes: number;
  factories?: string[];
  slaughter_date?: string;
  factory?: string;
  remark: string;
  status: string;
  created_at: string;
  products?: PurchaseProduct[];
  sale_id?: number | null;
  sale_no?: string | null;
  inbounds?: {
    inbound_no: string;
    batch_no: string;
    inbound_date: string;
    remaining_weight_kg: number;
    remaining_box_count: number;
  }[];
}

interface PurchaseProduct {
  id?: number;
  product_name: string;
  product_spec: string;
  factory: string;
  batch?: string;     // 批次号：加工厂-月日，如 N430-0130
  box_count: number;
  weight_kg: number;
  unit?: string;
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
  factory: '',
  batch: '',
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
  sale_id: null as number | null,
  slaughter_date: '' as string,
  factory: '' as string,
  products: [emptyProduct]
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

export function PurchaseOrderEntry() {
  const [orders, setOrders] = useState<PurchaseOrder[]>([]);
  const [suppliers, setSuppliers] = useState<Supplier[]>([]);
  const [productGroups, setProductGroups] = useState<ProductGroup[]>([]);
  const [sales, setSales] = useState<any[]>([]);
  const [materials, setMaterials] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [search, setSearch] = useState('');
  const [orderTypeFilter, setOrderTypeFilter] = useState<'all' | 'whole_fish' | 'made_to_order'>('all');
  const [showModal, setShowModal] = useState(false);
  const [deleteOrder, setDeleteOrder] = useState<PurchaseOrder | null>(null);
  const [deleteLoading, setDeleteLoading] = useState(false);

  // 采购售后（完整明细）
  const [returnFormOpen, setReturnFormOpen] = useState(false);
  const [returnFormOrder, setReturnFormOrder] = useState<PurchaseOrder | null>(null);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [form, setForm] = useState(emptyForm);
  const [supplierSearch, setSupplierSearch] = useState('');
  const [showSupplierList, setShowSupplierList] = useState(false);
  const [selectedOrder, setSelectedOrder] = useState<PurchaseOrder | null>(null);
  const [detailOrder, setDetailOrder] = useState<PurchaseOrder | null>(null);
  const [showDetailModal, setShowDetailModal] = useState(false);

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

  const loadSales = async () => {
    const res = await apiFetch('/v4/finished-product-sales');
    if (res.ok && res.data) {
      const arr = Array.isArray(res.data) ? res.data : (res.data.data || []);
      setSales(arr.filter((s: any) =>
        s.sale_type === 'whole_fish' &&
        (s.procurement_status || s.status) === 'pending' &&
        (s.purchase_count || 0) === 0
      ));
    }
  };

  const loadMaterials = async () => {
    const res = await apiFetch('/v4/materials?limit=500');
    if (res.ok && res.data) {
      const arr = Array.isArray(res.data) ? res.data : (res.data.items || res.data.data || []);
      setMaterials(arr);
    }
  };

  // 加载单个销售单（用于编辑时显示已关联但不在销售列表中的销售单）
  const [linkedSale, setLinkedSale] = useState<any>(null);
  useEffect(() => {
    if (form.sale_id && !sales.find((s: any) => s.id === form.sale_id)) {
      apiFetch(`/v4/finished-product-sales/${form.sale_id}`).then(res => {
        if (res.ok && res.data) {
          setLinkedSale(res.data.data || res.data);
        }
      });
    } else {
      setLinkedSale(null);
    }
  }, [form.sale_id, sales]);

  useEffect(() => { loadOrders(); loadSuppliers(); loadProducts(); loadSales(); loadMaterials(); }, []);
  useEffect(() => { if (showModal && productGroups.length === 0) loadProducts(); }, [showModal]);

  const filteredOrders = orders.filter(o => {
    // 搜索匹配
    const matchesSearch = !search ||
      (o.purchase_no?.toLowerCase().includes(search.toLowerCase()) ||
       o.supplier_name?.toLowerCase().includes(search.toLowerCase()));
    // 类型筛选
    const matchesType = orderTypeFilter === 'all'
      ? o.order_type !== 'accessories'
      : orderTypeFilter === 'made_to_order'
        ? !!o.sale_id
        : !o.sale_id;
    return matchesSearch && matchesType;
  });

  // 汇总数据
  const totalOrders = filteredOrders.length;
  const totalBoxes = filteredOrders.reduce((s, o) => s + (o.total_boxes || 0), 0);
  const totalWeight = filteredOrders.reduce((s, o) => s + (o.total_weight || 0), 0);
  const totalAmount = filteredOrders.reduce((s, o) => s + (o.total_amount || 0), 0);

  const parseWeight = (v: any): number => {
    if (typeof v === 'string' && v.includes('+')) {
      return v.split('+').reduce((a, b) => a + (parseFloat(b.trim()) || 0), 0);
    }
    return parseFloat(v) || 0;
  };

  const handleProductChange = (idx: number, field: keyof PurchaseProduct, value: any) => {
    setForm(prev => {
      const products = [...prev.products];
      products[idx] = { ...products[idx], [field]: value };
      if (field === 'weight_kg' || field === 'unit_price') {
        const w = parseWeight(products[idx].weight_kg);
        const p = parseFloat(products[idx].unit_price as any) || 0;
        products[idx].total_amount = round2(w * p);
      }
      const total_amount = products.reduce((s, p) => s + (p.total_amount || 0), 0);
      const total_weight = products.reduce((s, p) => s + parseWeight(p.weight_kg), 0);
      const total_boxes = products.reduce((s, p) => s + (p.box_count || 0), 0);
      return { ...prev, products, total_amount, total_weight, total_boxes };
    });
  };

  const handleProductChanges = (idx: number, updates: Partial<PurchaseProduct>) => {
    setForm(prev => {
      const products = [...prev.products];
      products[idx] = { ...products[idx], ...updates };
      if (updates.weight_kg !== undefined || updates.unit_price !== undefined) {
        const w = parseWeight(products[idx].weight_kg);
        const p = parseFloat(products[idx].unit_price as any) || 0;
        products[idx].total_amount = round2(w * p);
      }
      const total_amount = products.reduce((s, p) => s + (p.total_amount || 0), 0);
      const total_weight = products.reduce((s, p) => s + parseWeight(p.weight_kg), 0);
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
    const year = form.purchase_date.slice(0, 4);
    const payload = {
      ...form,
      sale_id: form.sale_id,
      slaughter_date: form.slaughter_date || undefined,
      factory: form.factory || undefined,
      products: form.products.filter(p => p.product_name.trim() || p.product_spec.trim()).map(p => {
        const parsed = p.batch ? parseBatch(p.batch, year) : null;
        return {
          ...p,
          factory: p.factory || parsed?.factory || '',
        };
      })
    };
    try {
      if (editingId) {
        await apiFetch(`/v4/purchase-orders/${editingId}`, {
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
      loadSales();
    } catch (e) {}
  };

  const handleEdit = async (order: PurchaseOrder) => {
    const res = await apiFetch(`/v4/purchase-orders/${order.id}`);
    if (res.ok && res.data) {
      const o = res.data.data || res.data;
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
        sale_id: o.sale_id || null,
        slaughter_date: o.slaughter_date || '',
        factory: o.factory || '',
        products: (o.products?.length ? o.products : [emptyProduct]).map((p: any) => ({
          product_name: p.product_name || '',
          product_spec: p.product_spec || '',
          factory: p.factory || '',
          batch: p.batch || formatBatch(p.factory, o.slaughter_date) || '',
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

  const handleDeleteOpen = (order: PurchaseOrder) => {
    setDeleteOrder(order);
  };

  const confirmDelete = async () => {
    if (!deleteOrder) return;
    setDeleteLoading(true);
    try {
      await apiDelete(`/v4/purchase-orders/${deleteOrder.id}`, '删除成功');
      setDeleteOrder(null);
      if (selectedOrder?.id === deleteOrder.id) setSelectedOrder(null);
      loadOrders();
      loadSales();
    } catch (e) {} finally { setDeleteLoading(false); }
  };

  const handleViewDetail = async (order: PurchaseOrder) => {
    const res = await apiFetch(`/v4/purchase-orders/${order.id}`);
    if (res.ok && res.data) {
      const d = res.data.data || res.data;
      setDetailOrder(d);
      setShowDetailModal(true);
    }
  };

  const handleReturnOpen = (order: PurchaseOrder) => {
    setReturnFormOrder(order);
    setReturnFormOpen(true);
  };

  const handleNew = (type: 'raw_material' | 'accessories') => {
    setForm({ ...emptyForm, order_type: type });
    setEditingId(null);
    setShowModal(true);
  };

  const filteredSuppliers = suppliers.filter(s =>
    s.name.toLowerCase().includes(supplierSearch.toLowerCase())
  );

  return (
    <div className="h-full flex flex-col gap-4">
      {/* ==================== 功能区 ==================== */}
      <div className="flex-none space-y-3">
        {/* 搜索行：标题 + 搜索 + 按钮 */}
        <div className="flex items-center justify-between gap-4">
          <div className="flex items-center gap-4">
            <div>
              <h1 className="text-2xl font-bold flex items-center gap-2">
                <Truck className="h-6 w-6" />
                采购入库
              </h1>
              <p className="text-sm text-muted-foreground">
                共 {orders.length} 单
              </p>
            </div>
            <div className="relative w-[260px]">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
              <Input
                placeholder="搜索采购单号/供应商..."
                value={search}
                onChange={e => setSearch(e.target.value)}
                className="pl-9"
              />
            </div>
            <Select value={orderTypeFilter} onValueChange={(v: 'all' | 'whole_fish' | 'made_to_order') => setOrderTypeFilter(v)}>
              <SelectTrigger className="w-[120px] h-9 text-sm">
                <SelectValue placeholder="全部类型">
                  {orderTypeFilter === 'all' ? '全部类型' : orderTypeFilter === 'whole_fish' ? '整鱼' : '以销定采'}
                </SelectValue>
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">全部类型</SelectItem>
                <SelectItem value="whole_fish">整鱼</SelectItem>
                <SelectItem value="made_to_order">以销定采</SelectItem>
              </SelectContent>
            </Select>
          </div>
          <div className="flex gap-2">
            <Button variant="outline" onClick={() => handleNew('raw_material')}>
              <Plus className="h-4 w-4 mr-1" />
              整鱼采购
            </Button>
          </div>
        </div>

        {/* 汇总行 */}
        <div className="grid grid-cols-4 gap-4">
          <div className="bg-muted/50 rounded-lg p-3 text-center">
            <div className="text-xs text-muted-foreground">采购单数</div>
            <div className="text-lg font-bold">{totalOrders}</div>
          </div>
          <div className="bg-muted/50 rounded-lg p-3 text-center">
            <div className="text-xs text-muted-foreground">总箱数</div>
            <div className="text-lg font-bold text-primary">{totalBoxes}</div>
          </div>
          <div className="bg-muted/50 rounded-lg p-3 text-center">
            <div className="text-xs text-muted-foreground">总重量(kg)</div>
            <div className="text-lg font-bold text-primary">
              {totalWeight.toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
            </div>
          </div>
          <div className="bg-muted/50 rounded-lg p-3 text-center">
            <div className="text-xs text-muted-foreground">总金额(元)</div>
            <div className="text-lg font-bold text-primary">
              ¥{totalAmount.toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
            </div>
          </div>
        </div>
      </div>

      {/* ==================== 列表区 + 详情区 ==================== */}
      <div className="flex-1 flex flex-col min-h-0 gap-4">
        {/* 列表区 */}
        <div className="flex-none flex flex-col min-h-0 border rounded-lg overflow-hidden">
          <div className="overflow-auto" style={{ maxHeight: 'calc(100vh - 320px)' }}>
            <Table>
              <TableHeader>
                <TableRow className="bg-muted/50">
                  <TableHead className="sticky top-0 bg-background z-10 w-[150px]">采购单号</TableHead>
                  <TableHead className="sticky top-0 bg-background z-10">日期</TableHead>
                  <TableHead className="sticky top-0 bg-background z-10">供应商</TableHead>
                  <TableHead className="sticky top-0 bg-background z-10">产品名称</TableHead>
                  <TableHead className="sticky top-0 bg-background z-10">批次</TableHead>
                  <TableHead className="sticky top-0 bg-background z-10 text-right">箱数</TableHead>
                  <TableHead className="sticky top-0 bg-background z-10 text-right">数量/重量</TableHead>
                  <TableHead className="sticky top-0 bg-background z-10 text-center">单位</TableHead>
                  <TableHead className="sticky top-0 bg-background z-10 text-right">金额(元)</TableHead>
                  <TableHead className="sticky top-0 bg-background z-10 text-right">售后扣款</TableHead>
                  <TableHead className="sticky top-0 bg-background z-10 text-right">净金额</TableHead>
                  <TableHead className="sticky top-0 bg-background z-10 w-[100px]">操作</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {loading ? (
                  <TableRow>
                    <TableCell colSpan={10} className="text-center py-8 text-muted-foreground">加载中...</TableCell>
                  </TableRow>
                ) : filteredOrders.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={10} className="text-center py-8 text-muted-foreground">
                      {search ? '无匹配数据' : '暂无采购入库单'}
                    </TableCell>
                  </TableRow>
                ) : (
                  filteredOrders.map((o) => {
                    const productNames = [...new Set(o.products?.map((p: any) => p.product_name).filter(Boolean) || [])];
                    const sd = o.slaughter_date ? o.slaughter_date.slice(5, 10).replace('-', '') : '';
                    const isSelected = selectedOrder?.id === o.id;
                    return (
                      <TableRow
                        key={o.id}
                        className={cn(
                          "cursor-pointer transition-colors",
                          isSelected && "bg-primary/10 hover:bg-primary/15"
                        )}
                        onClick={() => {
                          setSelectedOrder(o);
                          // 获取完整详情，确保 sale_no、products 等字段完整
                          apiFetch(`/v4/purchase-orders/${o.id}`).then(res => {
                            if (res.ok && res.data) {
                              setSelectedOrder(res.data.data || res.data);
                            }
                          });
                        }}
                      >
                        <TableCell className="font-medium font-mono text-blue-600">
                          <div className="flex items-center gap-1.5">
                            {o.purchase_no}
                            {o.sale_id ? (
                              <Badge variant="outline" className="text-blue-600 border-blue-200 text-[10px] px-1 py-0 h-4">以销定采</Badge>
                            ) : (
                              <Badge variant="outline" className="text-green-600 border-green-200 text-[10px] px-1 py-0 h-4">整鱼</Badge>
                            )}
                          </div>
                        </TableCell>
                        <TableCell>{o.purchase_date}</TableCell>
                        <TableCell>{o.supplier_name}</TableCell>
                        <TableCell className="text-sm text-muted-foreground">
                          {productNames.length ? productNames.join('、') : '-'}
                        </TableCell>
                        <TableCell className="font-mono text-xs">
                          {(() => {
                            // 手写批次优先，其次入库自动生成的批次，最后 fallback
                            const productBatch = o.products?.[0]?.batch;
                            if (productBatch) return productBatch;
                            const inboundBatch = o.inbounds?.[0]?.batch_no;
                            if (inboundBatch) return inboundBatch;
                            const derived = formatBatch(o.factory, o.slaughter_date);
                            return derived || '-';
                          })()}
                        </TableCell>
                        <TableCell className="text-right">{o.total_boxes || '-'}</TableCell>
                        <TableCell className="text-right">
                          {o.total_weight ? o.total_weight.toFixed(2) : '-'}
                        </TableCell>
                        <TableCell className="text-center">kg</TableCell>
                        <TableCell className="text-right font-medium">
                          {o.total_amount ? o.total_amount.toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) : '-'}
                        </TableCell>
                        <TableCell className="text-right">
                          {o.after_sales_adjustment ? (
                            <span className="text-red-500">-¥{o.after_sales_adjustment.toFixed(2)}</span>
                          ) : '-'}
                        </TableCell>
                        <TableCell className="text-right font-medium">
                          {o.net_amount !== undefined ? (
                            <span>¥{o.net_amount.toFixed(2)}</span>
                          ) : (
                            o.total_amount ? `¥${o.total_amount.toFixed(2)}` : '-'
                          )}
                        </TableCell>
                        <TableCell>
                          <div className="flex gap-1">
                            <Button variant="ghost" size="icon" className="h-8 w-8" onClick={(e) => { e.stopPropagation(); handleViewDetail(o); }} title="查看">
                              <Eye className="h-4 w-4" />
                            </Button>
                            <Button variant="ghost" size="icon" className="h-8 w-8" onClick={(e) => { e.stopPropagation(); handleEdit(o); }} title="编辑">
                              <Edit2 className="h-4 w-4" />
                            </Button>
                            <Button variant="ghost" size="icon" className="h-8 w-8 text-orange-600" onClick={(e) => { e.stopPropagation(); handleReturnOpen(o); }} title="采购售后">
                              <MinusCircle className="h-4 w-4" />
                            </Button>
                            <Button variant="ghost" size="icon" className="h-8 w-8 text-red-500" onClick={(e) => { e.stopPropagation(); handleDeleteOpen(o); }} title="删除">
                              <Trash2 className="h-4 w-4" />
                            </Button>
                          </div>
                        </TableCell>
                      </TableRow>
                    );
                  })
                )}
              </TableBody>
            </Table>
          </div>

          {/* 汇总行 */}
          {!loading && filteredOrders.length > 0 && (
            <div className="flex-none border-t bg-muted/30">
              <div className="flex items-center justify-between px-4 py-2 text-sm">
                <div className="flex items-center gap-4">
                  <span className="text-muted-foreground">
                    显示 {filteredOrders.length} 条
                  </span>
                  <span className="text-muted-foreground">|</span>
                  <span>
                    合计：箱数 {totalBoxes} · 净重 {totalWeight.toLocaleString('zh-CN', {minimumFractionDigits: 2, maximumFractionDigits: 2})} kg · 金额 ¥{totalAmount.toLocaleString('zh-CN', {minimumFractionDigits: 2, maximumFractionDigits: 2})}
                    {(() => {
                      const adj = filteredOrders.reduce((s, o) => s + (o.after_sales_adjustment || 0), 0);
                      const net = filteredOrders.reduce((s, o) => s + (o.net_amount || o.total_amount || 0), 0);
                      return adj > 0 ? ` · 售后扣款 -¥${adj.toLocaleString('zh-CN', {minimumFractionDigits: 2, maximumFractionDigits: 2})} · 净金额 ¥${net.toLocaleString('zh-CN', {minimumFractionDigits: 2, maximumFractionDigits: 2})}` : '';
                    })()}
                  </span>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* ==================== 详情区 ==================== */}
        {selectedOrder && (
          <div className="flex-none border rounded-lg overflow-auto bg-background">
            <div className="p-4 space-y-3">
              {/* 详情头部 */}
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <h3 className="font-semibold text-base">采购单详情</h3>
                  <Badge variant="outline" className="text-blue-600 border-blue-200">
                    {selectedOrder.purchase_no}
                  </Badge>
                </div>
                <div className="flex gap-2">
                  <Button variant="ghost" size="sm" onClick={() => handleViewDetail(selectedOrder)}>
                    <Eye className="h-4 w-4 mr-1" />完整详情
                  </Button>
                  <Button variant="ghost" size="icon" className="h-8 w-8" onClick={() => setSelectedOrder(null)}>
                    <X className="h-4 w-4" />
                  </Button>
                </div>
              </div>

              {/* 基本信息 */}
              <div className="grid grid-cols-4 gap-3 text-sm">
                <div><span className="text-muted-foreground">供应商:</span> <span className="font-medium">{selectedOrder.supplier_name}</span></div>
                <div><span className="text-muted-foreground">日期:</span> {selectedOrder.purchase_date}</div>
                <div><span className="text-muted-foreground">宰杀日期:</span> {selectedOrder.slaughter_date || '-'}</div>
                <div><span className="text-muted-foreground">批次:</span> {
                  (() => {
                    const batches = [...new Set(selectedOrder.products?.map((p: any) => p.batch || formatBatch(p.factory, selectedOrder.slaughter_date)).filter(Boolean) || [])];
                    return batches.length ? batches.join('、') : (formatBatch(selectedOrder.factory, selectedOrder.slaughter_date) || '-');
                  })()
                }</div>
                <div><span className="text-muted-foreground">总金额:</span> <span className="font-medium">¥{selectedOrder.total_amount?.toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</span></div>
                <div><span className="text-muted-foreground">售后扣款:</span> <span className="text-red-500">{selectedOrder.after_sales_adjustment ? `-¥${selectedOrder.after_sales_adjustment.toFixed(2)}` : '-'}</span></div>
                <div><span className="text-muted-foreground">净金额:</span> <span className="font-medium">{selectedOrder.net_amount !== undefined ? `¥${selectedOrder.net_amount.toFixed(2)}` : `¥${selectedOrder.total_amount?.toFixed(2) || '0.00'}`}</span></div>
              </div>

              {/* 产品明细 */}
              {(selectedOrder.products?.length || 0) > 0 && (
                <div>
                  <div className="text-muted-foreground text-xs mb-1">产品明细 ({selectedOrder.products!.length} 项)</div>
                  <div className="border rounded-md overflow-hidden">
                    <Table>
                      <TableHeader>
                        <TableRow className="bg-muted/30">
                          <TableHead className="text-xs h-7">产品</TableHead>
                          <TableHead className="text-xs h-7">规格</TableHead>
                          <TableHead className="text-xs h-7">批次</TableHead>
                          <TableHead className="text-xs h-7 text-right">箱数</TableHead>
                          <TableHead className="text-xs h-7 text-right">重量(kg)</TableHead>
                          <TableHead className="text-xs h-7 text-right">单价</TableHead>
                          <TableHead className="text-xs h-7 text-right">金额</TableHead>
                        </TableRow>
                      </TableHeader>
                      <TableBody>
                        {selectedOrder.products!.map((p, i) => (
                          <TableRow key={i} className="h-7">
                            <TableCell className="text-sm py-0.5">{p.product_name || '-'}</TableCell>
                            <TableCell className="text-sm py-0.5">{p.product_spec || '-'}</TableCell>
                            <TableCell className="text-sm py-0.5">{p.batch || formatBatch(p.factory, selectedOrder.slaughter_date) || '-'}</TableCell>
                            <TableCell className="text-sm py-0.5 text-right">{p.box_count}</TableCell>
                            <TableCell className="text-sm py-0.5 text-right">{p.weight_kg?.toFixed?.(2) ?? p.weight_kg}</TableCell>
                            <TableCell className="text-sm py-0.5 text-right">{p.unit_price?.toFixed?.(2) ?? p.unit_price}</TableCell>
                            <TableCell className="text-sm py-0.5 text-right font-medium">
                              {p.total_amount?.toLocaleString?.('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) ?? p.total_amount}
                            </TableCell>
                          </TableRow>
                        ))}
                        {/* 汇总行 */}
                        <TableRow className="bg-muted/20 font-medium h-7">
                          <TableCell className="text-sm py-0.5" colSpan={3}>合计</TableCell>
                          <TableCell className="text-sm py-0.5 text-right">{selectedOrder.total_boxes}</TableCell>
                          <TableCell className="text-sm py-0.5 text-right">{selectedOrder.total_weight?.toFixed?.(2) ?? selectedOrder.total_weight} kg</TableCell>
                          <TableCell className="text-sm py-0.5 text-right">-</TableCell>
                          <TableCell className="text-sm py-0.5 text-right font-bold text-blue-600">
                            ¥{selectedOrder.total_amount?.toLocaleString?.('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) ?? selectedOrder.total_amount?.toFixed?.(2)}
                          </TableCell>
                        </TableRow>
                      </TableBody>
                    </Table>
                  </div>
                </div>
              )}

              {selectedOrder.remark && (
                <div className="text-sm text-muted-foreground">备注: {selectedOrder.remark}</div>
              )}
              {selectedOrder.sale_id && (
                <div className="bg-blue-50 p-2 rounded text-sm">
                  <span className="text-blue-600 font-medium">以销定采：</span>
                  关联销售单 {selectedOrder.sale_no || `#${selectedOrder.sale_id}`}
                </div>
              )}
            </div>
          </div>
        )}
      </div>

      {/* ==================== 编辑/新建弹窗 ==================== */}
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
              {form.order_type === 'raw_material' && (
                <div>
                  <Label>关联销售单（以销定采）</Label>
                  <select
                    className="w-full h-9 px-3 rounded-md border border-input bg-background text-sm"
                    value={form.sale_id || ''}
                    onChange={async e => {
                      const saleId = e.target.value ? Number(e.target.value) : null;
                      if (!saleId) {
                        setForm({...form, sale_id: null, products: [emptyProduct]});
                        return;
                      }
                      const res = await apiFetch(`/v4/finished-product-sales/${saleId}`);
                      if (res.ok && res.data) {
                        const s = res.data.data || res.data;
                        const autoProducts = (s.products || []).map((sp: any) => ({
                          product_name: s.product_name || sp.product_name || '',
                          product_spec: sp.product_spec || '',
                          factory: sp.factory || s.factory || '',
                          batch: sp.batch || formatBatch(sp.factory, sp.slaughter_date) || formatBatch(s.factory, s.slaughter_date) || '',
                          box_count: sp.box_count || 0,
                          weight_kg: 0,
                          unit_price: sp.unit_price || 0,
                          total_amount: 0,
                        }));
                        setForm(prev => {
                          const firstBatch = autoProducts[0]?.batch || '';
                          const year = prev.purchase_date.slice(0, 4);
                          const parsed = firstBatch ? parseBatch(firstBatch, year) : null;
                          return {
                            ...prev,
                            sale_id: saleId,
                            slaughter_date: parsed?.slaughter_date || s.slaughter_date || prev.purchase_date,
                            factory: parsed?.factory || s.factory || '',
                            products: autoProducts.length ? autoProducts : [emptyProduct],
                            total_boxes: autoProducts.reduce((sum: number, p: any) => sum + (p.box_count || 0), 0),
                            total_weight: 0,
                            total_amount: 0,
                          };
                        });
                      } else {
                        setForm({...form, sale_id: saleId});
                      }
                    }}
                  >
                    <option value="">不关联（常规采购）</option>
                    {/* 已关联但不在可选列表中的销售单 */}
                    {linkedSale && (
                      <option value={linkedSale.id}>
                        {linkedSale.sale_no} · {linkedSale.customer || '-'}（已关联）
                      </option>
                    )}
                    {sales.map((s: any) => {
                      const totalBoxes = (s.products || []).reduce((sum: number, p: any) => sum + (p.box_count || 0), 0) || s.quantity || 0;
                      const batchLabel = s.products?.[0]?.batch || formatBatch(s.factory, s.slaughter_date) || '-';
                      return (
                        <option key={s.id} value={s.id}>
                          {s.sale_no} · {s.customer || '-'}·{batchLabel}·{totalBoxes}箱
                        </option>
                      );
                    })}
                  </select>
                </div>
              )}
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
              {form.order_type === 'raw_material' && !form.sale_id && (
                <div>
                  <Label>宰杀日期</Label>
                  <Input
                    type="date"
                    value={form.slaughter_date || ''}
                    onChange={e => setForm({...form, slaughter_date: e.target.value})}
                  />
                </div>
              )}
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
                      <th className="px-3 py-2 text-left w-[20%]">产品名称</th>
                      <th className="px-3 py-2 text-left w-[14%]">规格</th>
                      <th className="px-3 py-2 text-left w-[14%]">批次</th>
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
                            {form.order_type === 'accessories' ? (
                              <select
                                className="w-full h-8 text-sm px-2 rounded border border-input bg-background"
                                value={p.product_name || ''}
                                onChange={e => {
                                  const material = materials.find((m: any) => m.name === e.target.value);
                                  if (material) {
                                    handleProductChanges(idx, {
                                      product_name: material.name,
                                      product_spec: material.spec || '',
                                      unit_price: material.cost_price || material.last_purchase_price || 0,
                                      unit: material.unit,
                                    });
                                  } else {
                                    handleProductChange(idx, 'product_name', e.target.value);
                                  }
                                }}
                              >
                                <option value="">选择物料...</option>
                                {materials.map((m: any) => (
                                  <option key={m.id} value={m.name}>
                                    {m.name} {m.spec ? `(${m.spec})` : ''} ¥{m.cost_price || m.last_purchase_price || '-'}/{m.unit}
                                  </option>
                                ))}
                              </select>
                            ) : (
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
                            )}
                          </td>
                          <td className="px-3 py-2 relative">
                            {form.order_type === 'accessories' ? (
                              <Input
                                className="h-8 text-sm bg-muted/30"
                                value={p.product_spec || ''}
                                readOnly
                                placeholder="自动带出"
                              />
                            ) : (
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
                            )}
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
                            <Input
                              className="h-8 text-sm"
                              value={p.batch || ''}
                              onChange={e => {
                                const batchStr = e.target.value;
                                const year = form.purchase_date ? form.purchase_date.slice(0, 4) : new Date().getFullYear();
                                const parsed = parseBatch(batchStr, year);
                                if (parsed) {
                                  handleProductChanges(idx, {
                                    batch: batchStr,
                                    factory: parsed.factory,
                                  });
                                  // 同步更新表单级别的宰杀日期和加工厂（以销定采时从批次解析）
                                  if (form.sale_id) {
                                    setForm(prev => ({
                                      ...prev,
                                      slaughter_date: parsed.slaughter_date,
                                      factory: parsed.factory,
                                    }));
                                  }
                                } else {
                                  handleProductChange(idx, 'batch', batchStr);
                                  if (!batchStr.includes('-')) {
                                    handleProductChange(idx, 'factory', '');
                                  }
                                }
                              }}
                              placeholder="如 N430-0130"
                            />
                          </td>
                          <td className="px-3 py-2">
                            <Input type="number" className="h-8 text-sm text-right" value={String(p.box_count || '')} onChange={e => handleProductChange(idx, 'box_count', parseInt(e.target.value) || 0)} placeholder="箱" />
                          </td>
                          <td className="px-3 py-2">
                            <Input type="text" className="h-8 text-sm text-right" value={String(p.weight_kg ?? '')} onChange={e => {
                                handleProductChange(idx, 'weight_kg', e.target.value);
                              }} onBlur={e => {
                                const val = e.target.value.trim();
                                if (val.includes('+')) {
                                  const sum = val.split('+').reduce((a, b) => a + (parseFloat(b.trim()) || 0), 0);
                                  handleProductChange(idx, 'weight_kg', round2(sum));
                                } else {
                                  const num = parseFloat(val);
                                  if (!isNaN(num)) {
                                    handleProductChange(idx, 'weight_kg', round2(num));
                                  }
                                }
                              }} onKeyDown={e => {
                                if (e.key === 'Enter') {
                                  const val = (e.target as HTMLInputElement).value.trim();
                                  if (val.includes('+')) {
                                    const sum = val.split('+').reduce((a, b) => a + (parseFloat(b.trim()) || 0), 0);
                                    handleProductChange(idx, 'weight_kg', round2(sum));
                                  } else {
                                    const num = parseFloat(val);
                                    if (!isNaN(num)) {
                                      handleProductChange(idx, 'weight_kg', round2(num));
                                    }
                                  }
                                }
                              }} placeholder="22.16 或 10+17.9" />
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

      {/* ==================== 详情弹窗 ==================== */}
      <Dialog open={showDetailModal} onOpenChange={setShowDetailModal}>
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
                      <th className="px-3 py-2 text-left">批次</th>
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
                        <td className="px-3 py-2">{p.batch || formatBatch(p.factory, detailOrder.slaughter_date) || '-'}</td>
                        <td className="px-3 py-2 text-right">{p.box_count}</td>
                        <td className="px-3 py-2 text-right">{p.weight_kg?.toFixed(2)}</td>
                        <td className="px-3 py-2 text-right">{p.unit_price?.toFixed(2)}</td>
                        <td className="px-3 py-2 text-right font-medium">{p.total_amount?.toFixed(2)}</td>
                      </tr>
                    )) || <tr><td colSpan={6} className="px-3 py-4 text-center text-gray-400">无明细</td></tr>}
                  </tbody>
                  {(detailOrder.products?.length || 0) > 0 && (
                    <tfoot className="bg-gray-50 border-t-2">
                      <tr>
                        <td className="px-3 py-2 font-bold">合计</td>
                        <td className="px-3 py-2"></td>
                        <td className="px-3 py-2 text-right font-bold">{detailOrder.total_boxes}</td>
                        <td className="px-3 py-2 text-right font-bold">{detailOrder.total_weight?.toFixed?.(2) ?? detailOrder.total_weight} kg</td>
                        <td className="px-3 py-2"></td>
                        <td className="px-3 py-2 text-right font-bold text-blue-600">
                          {detailOrder.total_amount?.toLocaleString?.('zh-CN', { style: 'currency', currency: 'CNY' }) ?? detailOrder.total_amount?.toFixed?.(2)}
                        </td>
                      </tr>
                    </tfoot>
                  )}
                </table>
              </div>
              <div className="text-sm text-gray-500">备注: {detailOrder.remark || '-'}</div>
              {detailOrder.sale_id && (
                <div className="bg-blue-50 p-2 rounded text-sm">
                  <span className="text-blue-600 font-medium">以销定采：</span>
                  关联销售单 {detailOrder.sale_no || `#${detailOrder.sale_id}`}
                </div>
              )}
            </div>
          )}
        </DialogContent>
      </Dialog>

      {/* ==================== 删除确认弹窗 ==================== */}
      <Dialog open={!!deleteOrder} onOpenChange={() => setDeleteOrder(null)}>
        <DialogContent className="max-w-sm">
          <DialogHeader>
            <DialogTitle>确认删除</DialogTitle>
            <DialogDescription>
              确定要删除采购入库单 {deleteOrder?.purchase_no ?? `#${deleteOrder?.id}`} 吗？
              <br />供应商: {deleteOrder?.supplier_name ?? "-"}
              <br />此操作不可恢复。
            </DialogDescription>
          </DialogHeader>
          <div className="flex justify-end gap-2 mt-4">
            <Button variant="outline" onClick={() => setDeleteOrder(null)} disabled={deleteLoading}>取消</Button>
            <Button variant="destructive" onClick={confirmDelete} disabled={deleteLoading}>
              {deleteLoading ? '删除中...' : '删除'}
            </Button>
          </div>
        </DialogContent>
      </Dialog>

      {/* ==================== 采购售后（完整明细） ==================== */}
      <PurchaseReturnForm
        open={returnFormOpen}
        onClose={() => {
          setReturnFormOpen(false);
          setReturnFormOrder(null);
          loadOrders();
        }}
        initialOrder={
          returnFormOrder
            ? {
                id: returnFormOrder.id,
                order_type: "purchase_v2" as const,
                purchase_no: returnFormOrder.purchase_no,
                supplier_id: returnFormOrder.supplier_id,
                supplier_name: returnFormOrder.supplier_name,
                total_amount: returnFormOrder.total_amount,
              }
            : null
        }
      />
    </div>
  );
}

export default PurchaseOrderEntry;
