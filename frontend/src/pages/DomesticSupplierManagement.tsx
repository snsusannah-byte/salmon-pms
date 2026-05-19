// 国内供应商管理组件
import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { Plus, Search, Edit2, Trash2, Building2 } from 'lucide-react';
import { apiFetch, apiPost, apiDelete } from '@/lib/api';

interface DomesticSupplier {
  id: number;
  name: string;
  contact_name?: string;
  phone?: string;
  address?: string;
  remark?: string;
  status: string;
  created_at: string;
}

const emptyForm = {
  name: '',
  contact_name: '',
  phone: '',
  address: '',
  remark: ''
};

export function DomesticSupplierManagement() {
  const [suppliers, setSuppliers] = useState<DomesticSupplier[]>([]);
  const [loading, setLoading] = useState(false);
  const [search, setSearch] = useState('');
  const [showModal, setShowModal] = useState(false);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [form, setForm] = useState(emptyForm);

  const loadSuppliers = async () => {
    setLoading(true);
    const res = await apiFetch('/v4/domestic-suppliers');
    if (res.ok && res.data) {
      setSuppliers(res.data);
    }
    setLoading(false);
  };

  useEffect(() => { loadSuppliers(); }, []);

  const handleSave = async () => {
    if (!form.name.trim()) return;
    if (editingId) {
      await apiFetch(`/domestic-suppliers/${editingId}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(form)
      }, '更新成功');
    } else {
      await apiPost('/v4/domestic-suppliers', form, '创建成功');
    }
    setShowModal(false);
    setForm(emptyForm);
    setEditingId(null);
    loadSuppliers();
  };

  const handleEdit = (s: DomesticSupplier) => {
    setForm({
      name: s.name || '',
      contact_name: s.contact_name || '',
      phone: s.phone || '',
      address: s.address || '',
      remark: s.remark || ''
    });
    setEditingId(s.id);
    setShowModal(true);
  };

  const handleDelete = async (id: number) => {
    if (!confirm('确定删除该供应商？')) return;
    await apiDelete(`/domestic-suppliers/${id}`, '删除成功');
    loadSuppliers();
  };

  const filtered = suppliers.filter(s =>
    s.name.toLowerCase().includes(search.toLowerCase()) ||
    (s.contact_name || '').toLowerCase().includes(search.toLowerCase()) ||
    (s.phone || '').includes(search)
  );

  return (
    <div className="space-y-4">
      <Card>
        <CardHeader className="flex flex-row items-center justify-between pb-2">
          <CardTitle className="flex items-center gap-2 text-lg">
            <Building2 className="w-5 h-5" /> 国内供应商管理
          </CardTitle>
          <Button size="sm" onClick={() => { setForm(emptyForm); setEditingId(null); setShowModal(true); }}>
            <Plus className="w-4 h-4 mr-1" /> 新增供应商
          </Button>
        </CardHeader>
        <CardContent>
          <div className="flex gap-2 mb-4">
            <div className="relative flex-1">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
              <Input className="pl-9" placeholder="搜索供应商名称/联系人/电话..." value={search} onChange={e => setSearch(e.target.value)} />
            </div>
          </div>
          {loading ? (
            <div className="text-center py-8 text-gray-400">加载中...</div>
          ) : (
            <div className="border rounded-lg overflow-hidden">
              <table className="w-full text-sm">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="px-4 py-2 text-left">供应商名称</th>
                    <th className="px-4 py-2 text-left">联系人</th>
                    <th className="px-4 py-2 text-left">电话</th>
                    <th className="px-4 py-2 text-left">地址</th>
                    <th className="px-4 py-2 text-center">操作</th>
                  </tr>
                </thead>
                <tbody>
                  {filtered.length === 0 && (
                    <tr><td colSpan={5} className="px-4 py-8 text-center text-gray-400">暂无供应商</td></tr>
                  )}
                  {filtered.map(s => (
                    <tr key={s.id} className="border-t hover:bg-gray-50">
                      <td className="px-4 py-2 font-medium">{s.name}</td>
                      <td className="px-4 py-2">{s.contact_name || '-'}</td>
                      <td className="px-4 py-2">{s.phone || '-'}</td>
                      <td className="px-4 py-2">{s.address || '-'}</td>
                      <td className="px-4 py-2 text-center">
                        <Button size="sm" variant="ghost" onClick={() => handleEdit(s)}>
                          <Edit2 className="w-4 h-4" />
                        </Button>
                        <Button size="sm" variant="ghost" className="text-red-500" onClick={() => handleDelete(s.id)}>
                          <Trash2 className="w-4 h-4" />
                        </Button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
      </Card>

      <Dialog open={showModal} onOpenChange={setShowModal}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{editingId ? '编辑供应商' : '新增供应商'}</DialogTitle>
          </DialogHeader>
          <div className="space-y-3 mt-2">
            <div><Label>供应商名称 *</Label><Input value={form.name} onChange={e => setForm({...form, name: e.target.value})} /></div>
            <div><Label>联系人</Label><Input value={form.contact_name} onChange={e => setForm({...form, contact_name: e.target.value})} /></div>
            <div><Label>电话</Label><Input value={form.phone} onChange={e => setForm({...form, phone: e.target.value})} /></div>
            <div><Label>地址</Label><Input value={form.address} onChange={e => setForm({...form, address: e.target.value})} /></div>
            <div><Label>备注</Label><Input value={form.remark} onChange={e => setForm({...form, remark: e.target.value})} /></div>
          </div>
          <div className="flex justify-end gap-2 mt-4">
            <Button variant="outline" onClick={() => setShowModal(false)}>取消</Button>
            <Button onClick={handleSave}>保存</Button>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}
