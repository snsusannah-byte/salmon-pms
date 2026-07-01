// 采购售后/退货模块前端组件 — 三文鱼PMS
//
// 参考销售退货单（ReturnOrderForm），但方向相反：
// - 销售退货：退钱给客户
// - 采购售后：抵扣应付款 / 供应商退钱
//
// 核心功能：
// 1. 选择采购单（整鱼/以销定采/辅料）
// 2. 自动带出供应商、单价
// 3. 填写售后重量，自动计算金额
// 4. 备注/问题描述
// 5. 附件上传
import { useState, useEffect } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Badge } from "@/components/ui/badge";
import { api } from "@/lib/api";
import { Plus, Trash2, Upload, Image, Search, Package, X } from "lucide-react";

// ==================== 类型定义 ====================

interface PurchaseReturnItem {
  id?: number;
  weight_kg: string;
  unit_price: string;
  amount: number;
  remarks: string;
  purchase_order_product_v2_id?: number | null;
  material_purchase_item_id?: number | null;
}

interface PurchaseReturnFormData {
  id?: number;
  return_no?: string;
  purchase_order_type: "purchase_v2" | "material_purchase";
  purchase_order_v2_id?: number | null;
  material_purchase_order_id?: number | null;
  return_date: string;
  supplier_id: number | null;
  supplier_name: string;
  refund_method: "deduct_payable" | "direct_refund" | "deferred";
  bank_account_id?: number | null;
  problem_description: string;
  items: PurchaseReturnItem[];
  attachments: ReturnAttachment[];
  status?: string;
}

interface ReturnAttachment {
  id?: number;
  original_name: string;
  file_name: string;
  file_type: string;
  file_size: number;
  download_url?: string;
  file?: File;
}

interface PurchaseOrderOption {
  id: number;
  purchase_no: string;
  supplier_id: number;
  supplier_name: string;
  total_amount: number;
  order_type?: string;
}

// ==================== 退款方式选项 ====================

const refundMethodOptions = [
  { value: "deduct_payable", label: "抵扣应付款" },
  { value: "direct_refund", label: "直接退款" },
  { value: "deferred", label: "挂账/延期处理" },
];

const refundMethodLabel = (v: string) => refundMethodOptions.find(o => o.value === v)?.label || v;

// ==================== 辅助函数 ====================

function calcAmount(weight: string, price: string): number {
  const w = parseFloat(weight) || 0;
  const p = parseFloat(price) || 0;
  return parseFloat((w * p).toFixed(2));
}

const emptyItem: PurchaseReturnItem = {
  weight_kg: "",
  unit_price: "",
  amount: 0,
  remarks: "",
  purchase_order_product_v2_id: null,
  material_purchase_item_id: null,
};

const emptyForm: PurchaseReturnFormData = {
  purchase_order_type: "purchase_v2",
  purchase_order_v2_id: null,
  material_purchase_order_id: null,
  return_date: new Date().toISOString().split("T")[0],
  supplier_id: null,
  supplier_name: "",
  refund_method: "deduct_payable",
  problem_description: "",
  items: [{ ...emptyItem }],
  attachments: [],
};

// ==================== 组件 ====================

interface PurchaseReturnFormProps {
  open: boolean;
  onClose: () => void;
  editData?: any;
  initialOrder?: {
    id: number;
    order_type: "purchase_v2" | "material_purchase";
    purchase_no: string;
    supplier_id: number;
    supplier_name: string;
    total_amount: number;
  } | null;
}

export function PurchaseReturnForm({ open, onClose, editData, initialOrder }: PurchaseReturnFormProps) {
  const queryClient = useQueryClient();
  const isEdit = !!editData;
  const isFromPurchasePage = !!initialOrder;

  const [form, setForm] = useState<PurchaseReturnFormData>({ ...emptyForm });
  const [step, setStep] = useState(1);
  const [poSearch, setPoSearch] = useState("");
  const [loadingPo, setLoadingPo] = useState(false);
  const [poList, setPoList] = useState<PurchaseOrderOption[]>([]);
  const [poDetail, setPoDetail] = useState<any>(null);
  const [submitting, setSubmitting] = useState(false);

  // 编辑模式：加载数据
  useEffect(() => {
    if (open && isEdit && editData) {
      setForm({
        id: editData.id,
        return_no: editData.return_no,
        purchase_order_type: editData.purchase_order_type || "purchase_v2",
        purchase_order_v2_id: editData.purchase_order_v2_id || null,
        material_purchase_order_id: editData.material_purchase_order_id || null,
        return_date: editData.return_date || new Date().toISOString().split("T")[0],
        supplier_id: editData.supplier_id || null,
        supplier_name: editData.supplier_name || "",
        refund_method: editData.refund_method || "deduct_payable",
        bank_account_id: editData.bank_account_id || null,
        problem_description: editData.problem_description || "",
        items: (editData.items || []).map((it: any) => ({
          id: it.id,
          weight_kg: String(it.weight_kg || ""),
          unit_price: String(it.unit_price || ""),
          amount: it.amount || 0,
          remarks: it.remarks || "",
          purchase_order_product_v2_id: it.purchase_order_product_v2_id || null,
          material_purchase_item_id: it.material_purchase_item_id || null,
        })),
        attachments: (editData.attachments || []).map((att: any) => ({
          id: att.id,
          original_name: att.original_name,
          file_name: att.file_name,
          file_type: att.file_type,
          file_size: att.file_size,
          download_url: att.download_url,
        })),
        status: editData.status,
      });
      setStep(2);
    } else if (open && !isEdit && initialOrder) {
      // 从采购页面传入：自动加载采购单详情
      setLoadingPo(true);
      api.get(`/v1/purchase-returns/purchase-order-info?order_type=${initialOrder.order_type}&order_id=${initialOrder.id}`)
        .then(res => {
          const info = res.data;
          setPoDetail(info);
          const defaultUnitPrice = info.avg_unit_price ? String(info.avg_unit_price) : "";
          setForm({
            ...emptyForm,
            purchase_order_type: initialOrder.order_type,
            purchase_order_v2_id: initialOrder.order_type === "purchase_v2" ? initialOrder.id : null,
            material_purchase_order_id: initialOrder.order_type === "material_purchase" ? initialOrder.id : null,
            supplier_id: initialOrder.supplier_id,
            supplier_name: initialOrder.supplier_name,
            items: [{ ...emptyItem, unit_price: defaultUnitPrice }],
          });
          setStep(2);
        })
        .catch(() => toast.error("获取采购单详情失败"))
        .finally(() => setLoadingPo(false));
    } else if (open && !isEdit && !initialOrder) {
      setForm({ ...emptyForm });
      setStep(1);
      setPoSearch("");
      setPoList([]);
      setPoDetail(null);
    }
  }, [open, isEdit, editData, initialOrder]);

  // 查询采购单列表
  const searchPurchaseOrders = async () => {
    if (!poSearch.trim()) return;
    setLoadingPo(true);
    try {
      // 同时查询 purchase_v2 和 material_purchase
      const [v2Res, matRes] = await Promise.all([
        api.get(`/v1/purchase-inbound/import-inbound?limit=20&search=${encodeURIComponent(poSearch)}`),
        api.get(`/v1/material-purchases?limit=20&keyword=${encodeURIComponent(poSearch)}`),
      ]);

      const v2Items = (v2Res.data?.items || []).map((o: any) => ({
        id: o.id,
        purchase_no: o.purchase_no,
        supplier_id: o.supplier_id,
        supplier_name: o.supplier_name,
        total_amount: o.total_amount,
        order_type: o.order_type,
        _type: "purchase_v2" as const,
      }));

      const matItems = (matRes.data?.items || []).map((o: any) => ({
        id: o.id,
        purchase_no: o.order_no,
        supplier_id: o.supplier_id,
        supplier_name: o.supplier_name,
        total_amount: o.actual_total,
        order_type: "material_purchase",
        _type: "material_purchase" as const,
      }));

      setPoList([...v2Items, ...matItems]);
    } catch (err: any) {
      toast.error("查询采购单失败");
    } finally {
      setLoadingPo(false);
    }
  };

  // 选择采购单
  const selectPurchaseOrder = async (po: PurchaseOrderOption & { _type: string }) => {
    setLoadingPo(true);
    try {
      const orderType = po._type;
      const res = await api.get(
        `/v1/purchase-returns/purchase-order-info?order_type=${orderType}&order_id=${po.id}`
      );
      const info = res.data;
      setPoDetail(info);

      // 使用平均单价作为默认单价
      const defaultUnitPrice = info.avg_unit_price ? String(info.avg_unit_price) : "";

      setForm(prev => ({
        ...prev,
        purchase_order_type: orderType as any,
        purchase_order_v2_id: orderType === "purchase_v2" ? po.id : null,
        material_purchase_order_id: orderType === "material_purchase" ? po.id : null,
        supplier_id: po.supplier_id,
        supplier_name: po.supplier_name,
        items: [{
          ...emptyItem,
          unit_price: defaultUnitPrice,
        }],
      }));
      setStep(2);
    } catch (err: any) {
      toast.error(err.response?.data?.detail || "获取采购单详情失败");
    } finally {
      setLoadingPo(false);
    }
  };

  // 更新明细
  const updateItem = (idx: number, field: keyof PurchaseReturnItem, value: string) => {
    setForm(prev => {
      const newItems = [...prev.items];
      newItems[idx] = { ...newItems[idx], [field]: value };
      if (field === "weight_kg" || field === "unit_price") {
        newItems[idx].amount = calcAmount(newItems[idx].weight_kg, newItems[idx].unit_price);
      }
      return { ...prev, items: newItems };
    });
  };

  const addItem = () => {
    setForm(prev => ({
      ...prev,
      items: [...prev.items, { ...emptyItem, unit_price: prev.items[0]?.unit_price || "" }],
    }));
  };

  const removeItem = (idx: number) => {
    setForm(prev => ({
      ...prev,
      items: prev.items.filter((_, i) => i !== idx),
    }));
  };

  // 文件上传
  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (!files) return;
    const newAttachments: ReturnAttachment[] = [];
    for (let i = 0; i < files.length; i++) {
      const file = files[i];
      newAttachments.push({
        original_name: file.name,
        file_name: file.name,
        file_type: file.type.startsWith("image/") ? "image" : file.type.startsWith("video/") ? "video" : "document",
        file_size: file.size,
        file,
      });
    }
    setForm(prev => ({ ...prev, attachments: [...prev.attachments, ...newAttachments] }));
  };

  const removeAttachment = (idx: number) => {
    setForm(prev => ({
      ...prev,
      attachments: prev.attachments.filter((_, i) => i !== idx),
    }));
  };

  // 提交
  const handleSubmit = async () => {
    // 校验
    if (!form.supplier_id) {
      toast.error("请选择采购单");
      return;
    }
    if (form.items.length === 0 || form.items.every(it => !it.weight_kg)) {
      toast.error("请至少填写一条售后明细");
      return;
    }

    setSubmitting(true);
    try {
      const payload = {
        purchase_order_type: form.purchase_order_type,
        purchase_order_v2_id: form.purchase_order_v2_id,
        material_purchase_order_id: form.material_purchase_order_id,
        return_date: form.return_date,
        supplier_id: form.supplier_id,
        supplier_name: form.supplier_name,
        refund_method: form.refund_method,
        bank_account_id: form.bank_account_id,
        problem_description: form.problem_description,
        items: form.items
          .filter(it => parseFloat(it.weight_kg) > 0)
          .map(it => ({
            weight_kg: parseFloat(it.weight_kg),
            unit_price: parseFloat(it.unit_price) || 0,
            amount: it.amount,
            remarks: it.remarks,
            purchase_order_product_v2_id: it.purchase_order_product_v2_id,
            material_purchase_item_id: it.material_purchase_item_id,
          })),
      };

      let returnId: number;
      if (isEdit && form.id) {
        const res = await api.put(`/v1/purchase-returns/${form.id}`, payload);
        returnId = res.data.id;
        toast.success("售后单更新成功");
      } else {
        const res = await api.post("/v1/purchase-returns", payload);
        returnId = res.data.id;
        toast.success("售后单创建成功");
      }

      // 上传附件
      const filesToUpload = form.attachments.filter(att => att.file);
      for (const att of filesToUpload) {
        const fd = new FormData();
        fd.append("file", att.file!);
        if (att.description) fd.append("description", att.description);
        await api.post(`/v1/purchase-returns/${returnId}/attachments`, fd, {
          headers: { "Content-Type": "multipart/form-data" },
        });
      }

      queryClient.invalidateQueries({ queryKey: ["purchase-returns"] });
      queryClient.invalidateQueries({ queryKey: ["purchase-inbound"] });
      queryClient.invalidateQueries({ queryKey: ["material-purchases"] });
      onClose();
    } catch (err: any) {
      toast.error(err.response?.data?.detail || "提交失败");
    } finally {
      setSubmitting(false);
    }
  };

  // 汇总
  const totalWeight = form.items.reduce((s, it) => s + (parseFloat(it.weight_kg) || 0), 0);
  const totalAmount = form.items.reduce((s, it) => s + (it.amount || 0), 0);

  return (
    <Dialog open={open} onOpenChange={(v) => !v && onClose()}>
      <DialogContent className="max-w-4xl max-h-[90vh] overflow-auto">
        <DialogHeader>
          <DialogTitle>
            {isEdit ? "编辑采购售后单" : "创建采购售后单"}
            {form.return_no && <span className="text-sm text-muted-foreground ml-2">{form.return_no}</span>}
          </DialogTitle>
        </DialogHeader>

        {step === 1 && (
          <div className="space-y-4">
            <div className="text-sm text-muted-foreground">步骤 1/2：选择采购单</div>
            <div className="flex gap-2">
              <div className="relative flex-1">
                <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
                <Input
                  placeholder="搜索采购单号..."
                  className="pl-8"
                  value={poSearch}
                  onChange={(e) => setPoSearch(e.target.value)}
                  onKeyDown={(e) => e.key === "Enter" && searchPurchaseOrders()}
                />
              </div>
              <Button onClick={searchPurchaseOrders} disabled={loadingPo}>
                {loadingPo ? "搜索中..." : "搜索"}
              </Button>
            </div>

            {poList.length > 0 && (
              <div className="border rounded-md divide-y">
                {poList.map((po) => (
                  <div
                    key={`${po._type}-${po.id}`}
                    className="p-3 hover:bg-muted cursor-pointer flex items-center justify-between"
                    onClick={() => selectPurchaseOrder(po as any)}
                  >
                    <div className="flex items-center gap-3">
                      <Package className="h-4 w-4 text-muted-foreground" />
                      <div>
                        <div className="font-medium">{po.purchase_no}</div>
                        <div className="text-sm text-muted-foreground">
                          {po.supplier_name} · ¥{po.total_amount?.toFixed?.(2) || po.total_amount}
                        </div>
                      </div>
                    </div>
                    <Badge variant="outline">
                      {po._type === "purchase_v2" ? (po.order_type === "raw_material" ? "整鱼" : "以销定采") : "辅料"}
                    </Badge>
                  </div>
                ))}
              </div>
            )}

            {poList.length === 0 && poSearch && !loadingPo && (
              <div className="text-center text-muted-foreground py-8">无匹配采购单</div>
            )}
          </div>
        )}

        {step === 2 && (
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <div className="text-sm text-muted-foreground">步骤 2/2：填写售后信息</div>
            {!isFromPurchasePage && !isEdit && (
              <Button variant="ghost" size="sm" onClick={() => setStep(1)}>
                ← 重新选择采购单
              </Button>
            )}
            </div>

            {/* 基本信息 */}
            <div className="grid grid-cols-3 gap-4">
              <div>
                <Label>售后日期 *</Label>
                <Input
                  type="date"
                  value={form.return_date}
                  onChange={(e) => setForm(prev => ({ ...prev, return_date: e.target.value }))}
                />
              </div>
              <div>
                <Label>供应商</Label>
                <Input value={form.supplier_name} disabled />
              </div>
              <div>
                <Label>退款方式 *</Label>
                <Select
                  value={form.refund_method}
                  onValueChange={(v: any) => setForm(prev => ({ ...prev, refund_method: v }))}
                >
                  <SelectTrigger>
                    <SelectValue placeholder="请选择退款方式">
                      {refundMethodLabel(form.refund_method)}
                    </SelectValue>
                  </SelectTrigger>
                  <SelectContent>
                    {refundMethodOptions.map(o => (
                      <SelectItem key={o.value} value={o.value}>{o.label}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            </div>

            {/* 售后明细 */}
            <div>
              <div className="flex items-center justify-between mb-2">
                <Label>售后明细 *</Label>
                <Button variant="outline" size="sm" onClick={addItem}>
                  <Plus className="h-3.5 w-3.5 mr-1" /> 添加明细
                </Button>
              </div>

              <div className="border rounded-md">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="bg-muted/50">
                      <th className="text-left p-2 w-12">序号</th>
                      <th className="text-right p-2">重量(kg) *</th>
                      <th className="text-right p-2">单价(元) *</th>
                      <th className="text-right p-2">金额(元)</th>
                      <th className="text-left p-2">备注/问题描述</th>
                      <th className="w-12"></th>
                    </tr>
                  </thead>
                  <tbody className="divide-y">
                    {form.items.map((item, idx) => (
                      <tr key={idx}>
                        <td className="p-2 text-muted-foreground">{idx + 1}</td>
                        <td className="p-2">
                          <Input
                            type="number"
                            min={0}
                            step="0.001"
                            className="text-right h-8"
                            value={item.weight_kg}
                            onChange={(e) => updateItem(idx, "weight_kg", e.target.value)}
                          />
                        </td>
                        <td className="p-2">
                          <Input
                            type="number"
                            min={0}
                            step="0.0001"
                            className="text-right h-8"
                            value={item.unit_price}
                            onChange={(e) => updateItem(idx, "unit_price", e.target.value)}
                          />
                        </td>
                        <td className="p-2 text-right font-medium">
                          ¥{item.amount.toFixed(2)}
                        </td>
                        <td className="p-2">
                          <Input
                            placeholder="备注/问题描述"
                            className="h-8"
                            value={item.remarks}
                            onChange={(e) => updateItem(idx, "remarks", e.target.value)}
                          />
                        </td>
                        <td className="p-2">
                          {form.items.length > 1 && (
                            <Button variant="ghost" size="icon" className="h-7 w-7" onClick={() => removeItem(idx)}>
                              <Trash2 className="h-3.5 w-3.5 text-red-500" />
                            </Button>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              {/* 汇总 */}
              <div className="flex justify-end gap-4 text-sm mt-2">
                <span>共 {form.items.length} 条明细</span>
                <span>总重量: <strong>{totalWeight.toFixed(3)} kg</strong></span>
                <span className="text-red-600">售后金额: <strong>¥{totalAmount.toFixed(2)}</strong></span>
              </div>
            </div>

            {/* 附件上传 */}
            <div>
              <Label>附件上传</Label>
              <div className="border-2 border-dashed rounded-md p-4 mt-1">
                <input
                  type="file"
                  id="purchase-return-files"
                  multiple
                  accept="image/*,video/*,.pdf,.doc,.docx"
                  className="hidden"
                  onChange={handleFileChange}
                />
                <label htmlFor="purchase-return-files" className="cursor-pointer flex flex-col items-center gap-2 text-muted-foreground">
                  <Upload className="h-6 w-6" />
                  <span className="text-sm">点击上传图片/视频/文档</span>
                  <span className="text-xs">支持 JPG、PNG、GIF、MP4、PDF 等格式，单个文件不超过 20MB</span>
                </label>
              </div>

              {form.attachments.length > 0 && (
                <div className="flex flex-wrap gap-2 mt-2">
                  {form.attachments.map((att, idx) => (
                    <div key={idx} className="flex items-center gap-1 bg-muted px-2 py-1 rounded text-sm">
                      <Image className="h-3.5 w-3.5" />
                      <span className="max-w-[150px] truncate">{att.original_name}</span>
                      <button onClick={() => removeAttachment(idx)} className="text-red-500 hover:text-red-700">
                        <X className="h-3 w-3" />
                      </button>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        )}

        <DialogFooter>
          <Button variant="outline" onClick={onClose} disabled={submitting}>
            取消
          </Button>
          {step === 2 && (
            <Button onClick={handleSubmit} disabled={submitting} className="bg-orange-600 hover:bg-orange-700">
              {submitting ? "提交中..." : (isEdit ? "保存" : "提交")}
            </Button>
          )}
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
