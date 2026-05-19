/**
 * 创建/编辑退货单弹窗 - ReturnOrderForm.tsx (一屏完整显示版)
 */
import { useState, useEffect } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Badge } from "@/components/ui/badge";
import { api } from "@/lib/api";
import { cn } from "@/lib/utils";
import { Plus, Trash2, Upload, Image, Video, Search, Package, ChevronRight, X } from "lucide-react";

interface ReturnOrderFormProps {
  open: boolean;
  onClose: () => void;
  editData?: any;
  prefillSale?: {
    type: "whole_fish" | "finished_product";
    sale: any;
  };
}

export function ReturnOrderForm({ open, onClose, editData, prefillSale }: ReturnOrderFormProps) {
  const queryClient = useQueryClient();
  const isEdit = !!editData;

  const [saleType, setSaleType] = useState("whole_fish");
  const [saleId, setSaleId] = useState("");
  const [returnDate, setReturnDate] = useState(new Date().toISOString().split("T")[0]);
  const [customerId, setCustomerId] = useState("");
  const [processingPlantId, setProcessingPlantId] = useState("");
  const [processingPlantName, setProcessingPlantName] = useState("");
  const [problemDescription, setProblemDescription] = useState("");
  const [items, setItems] = useState<any[]>([{ spec: "", quantity: "", weight_kg: "", unit_price: "", return_reason: "quality_issue", reason_detail: "" }]);
  const [attachments, setAttachments] = useState<File[]>([]);
  const [step, setStep] = useState(1);
  const [saleSearch, setSaleSearch] = useState("");
  const [loadingSale, setLoadingSale] = useState(false);
  const [saleDetail, setSaleDetail] = useState<any>(null);
  const [returnOrderId, setReturnOrderId] = useState<number | null>(null);
  const [saleEuNo, setSaleEuNo] = useState<string | null>(null);
  const [refundMethod, setRefundMethod] = useState("direct_refund");
  const [bankAccountId, setBankAccountId] = useState("");

  const refundMethodOptions = [
    { value: "direct_refund", label: "直接退款" },
    { value: "balance_deduction", label: "抵扣货款" },
    { value: "prepayment", label: "转预付款" },
    { value: "deferred", label: "挂账" },
  ];

  const { data: customersData } = useQuery({
    queryKey: ["customers-for-return"],
    queryFn: async () => { const res = await api.get("/v1/companies/?type=customer&limit=500"); return res.data; },
    enabled: open,
  });
  const { data: plantsData } = useQuery({
    queryKey: ["plants-for-return"],
    queryFn: async () => { const res = await api.get("/v1/companies/?type=processing_plant&limit=500"); return res.data; },
    enabled: open,
  });
  const { data: bankAccountsData } = useQuery({
    queryKey: ["bank-accounts-for-return"],
    queryFn: async () => { const res = await api.get("/v1/finance/bank-accounts?limit=500"); return res.data; },
    enabled: open,
  });
  const { data: salesData } = useQuery({
    queryKey: ["sales-for-return", saleType],
    queryFn: async () => {
      const endpoint = saleType === "whole_fish" ? "/v1/sales/whole-fish" : "/v1/finished-product-sales";
      const res = await api.get(`${endpoint}?limit=200&status=pending,partial_paid,fully_paid,after_sales`);
      return res.data;
    },
    enabled: open && step === 1 && !isEdit,
  });

  // 编辑模式
  useEffect(() => {
    if (open && isEdit && editData) {
      setReturnOrderId(editData.id);
      setSaleType(editData.sale_type || "whole_fish");
      setSaleId(String(editData.whole_fish_sale_id || editData.finished_product_sale_id || ""));
      setReturnDate(editData.return_date || new Date().toISOString().split("T")[0]);
      setCustomerId(String(editData.customer_id || ""));
      setProcessingPlantId(String(editData.processing_plant_id || ""));
      setProcessingPlantName(editData.processing_plant_name || "");
      setProblemDescription(editData.problem_description || "");
      setRefundMethod(editData.refund_method || "direct_refund");
      setBankAccountId(editData.bank_account_id ? String(editData.bank_account_id) : "");
      setSaleEuNo(editData.processing_plant_eu_no || null);
      if (editData.items?.length > 0) {
        setItems(editData.items.map((it: any) => ({
          spec: it.spec || it.product_name || "",
          quantity: String(it.quantity || ""), weight_kg: String(it.weight_kg || ""), unit_price: String(it.unit_price || ""),
          return_reason: it.return_reason || "quality_issue", reason_detail: it.reason_detail || "",
          remarks: it.remarks || it.reason_detail || "",
          whole_fish_sale_item_id: it.whole_fish_sale_item_id, finished_product_sale_item_id: it.finished_product_sale_item_id,
          product_id: it.product_id, product_name: it.product_name,
        })));
      } else {
        setItems([{ spec: "", quantity: "", weight_kg: "", unit_price: "", return_reason: "quality_issue", reason_detail: "", remarks: "" }]);
      }
      setStep(2);
    }
  }, [open, isEdit, editData]);

  // 预填模式
  useEffect(() => {
    if (open && prefillSale && !isEdit) {
      const { type, sale } = prefillSale;
      setSaleType(type);
      setSaleId(String(sale.id));
      setSaleDetail(sale);
      setCustomerId(String(sale.customer_id || ""));
      setSaleEuNo(sale.processing_plant_eu_no || null);
      setStep(2);
      // 默认只创建1条退货明细
      const firstItem = sale.items?.[0];
      setItems([{
        spec: firstItem?.spec || firstItem?.product_name || sale.spec || sale.product_name || "",
        quantity: "", weight_kg: "",
        unit_price: String(firstItem?.unit_price || sale.unit_price || ""),
        return_reason: "quality_issue", reason_detail: "", remarks: "",
        whole_fish_sale_item_id: firstItem?.id,
        finished_product_sale_item_id: firstItem?.id,
        product_id: firstItem?.product_id,
        product_name: firstItem?.product_name,
      }]);
    }
  }, [open, prefillSale]);

  // 自动匹配加工厂
  useEffect(() => {
    if (saleEuNo && plantsData?.items?.length > 0 && !processingPlantId) {
      const matched = plantsData.items.find((p: any) => p.code === saleEuNo || p.eu_registration_no === saleEuNo);
      if (matched) { setProcessingPlantId(String(matched.id)); setProcessingPlantName(matched.name); }
    }
  }, [saleEuNo, plantsData]);

  const createMutation = useMutation({
    mutationFn: async (payload: any) => { const res = await api.post("/v1/returns", payload); return res.data; },
    onSuccess: (data) => { toast.success("退货单创建成功"); if (attachments.length > 0) uploadAttachments(data.id); else finish(); },
    onError: (err: any) => toast.error(err.response?.data?.detail || "创建失败"),
  });
  const updateMutation = useMutation({
    mutationFn: async ({ id, payload }: { id: number; payload: any }) => { const res = await api.put(`/v1/returns/${id}`, payload); return res.data; },
    onSuccess: (data) => { toast.success("退货单更新成功"); if (attachments.length > 0 && returnOrderId) uploadAttachments(returnOrderId); else finish(); },
    onError: (err: any) => toast.error(err.response?.data?.detail || "更新失败"),
  });

  const uploadAttachments = async (returnId: number) => {
    for (const file of attachments) {
      const formData = new FormData(); formData.append("file", file);
      try { await api.post(`/v1/returns/${returnId}/attachments`, formData, { headers: { "Content-Type": "multipart/form-data" } }); }
      catch (e) { toast.error(`附件 ${file.name} 上传失败`); }
    }
    finish();
  };

  const finish = () => {
    queryClient.invalidateQueries({ queryKey: ["returns"] });
    queryClient.invalidateQueries({ queryKey: ["return-stats"] });
    queryClient.invalidateQueries({ queryKey: ["sales"] });
    queryClient.invalidateQueries({ queryKey: ["finished-product-sales"] });
    onClose(); resetForm();
  };

  const resetForm = () => {
    setSaleType("whole_fish"); setSaleId(""); setReturnDate(new Date().toISOString().split("T")[0]);
    setCustomerId(""); setProcessingPlantId(""); setProcessingPlantName("");
    setProblemDescription(""); setRefundMethod("direct_refund"); setBankAccountId(""); setItems([{ spec: "", quantity: "", weight_kg: "", unit_price: "", return_reason: "quality_issue", reason_detail: "", remarks: "" }]);
    setAttachments([]); setStep(1); setSaleDetail(null); setReturnOrderId(null); setSaleSearch(""); setSaleEuNo(null);
  };

  const handleSelectSale = async (id: string) => {
    setSaleId(id); setLoadingSale(true);
    try {
      const endpoint = saleType === "whole_fish" ? `/v1/sales/whole-fish/${id}` : `/v1/finished-product-sales/${id}`;
      const res = await api.get(endpoint);
      const sale = res.data;
      setSaleDetail(sale); setCustomerId(String(sale.customer_id));
      // 默认只创建1条退货明细，使用第一条销售子项的单价作为默认值
      const firstItem = sale.items?.[0];
      setItems([{
        spec: firstItem?.spec || firstItem?.product_name || sale.spec || sale.product_name || "",
        quantity: "", weight_kg: "",
        unit_price: String(firstItem?.unit_price || sale.unit_price || ""),
        return_reason: "quality_issue", reason_detail: "", remarks: "",
        whole_fish_sale_item_id: firstItem?.id,
        finished_product_sale_item_id: firstItem?.id,
        product_id: firstItem?.product_id,
        product_name: firstItem?.product_name,
      }]);
      setStep(2);
    } catch { toast.error("加载销售单详情失败"); }
    finally { setLoadingSale(false); }
  };

  const addItem = () => setItems([...items, { spec: "", quantity: "", weight_kg: "", unit_price: "", return_reason: "quality_issue", reason_detail: "", remarks: "" }]);
  const removeItem = (idx: number) => { if (items.length <= 1) return; setItems(items.filter((_, i) => i !== idx)); };
  const updateItem = (idx: number, field: string, value: string) => { const newItems = [...items]; newItems[idx] = { ...newItems[idx], [field]: value }; setItems(newItems); };

  const totalAmount = items.reduce((sum, it) => { const w = parseFloat(it.weight_kg || "0"); const p = parseFloat(it.unit_price || "0"); return sum + w * p; }, 0);
  const totalWeight = items.reduce((sum, it) => sum + parseFloat(it.weight_kg || "0"), 0);

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files; if (!files) return;
    const newFiles = Array.from(files).filter((f) => f.size <= 20 * 1024 * 1024);
    if (newFiles.length < Array.from(files).length) toast.warning("部分文件超过20MB限制，已过滤");
    setAttachments((prev) => [...prev, ...newFiles]);
  };

  const handleSubmit = () => {
    if (!returnDate || !customerId) { toast.error("请填写退货日期和客户"); return; }
    const validItems = items.filter((it) => parseFloat(it.weight_kg || "0") > 0).map((it) => ({ weight_kg: parseFloat(it.weight_kg || "0"), unit_price: parseFloat(it.unit_price || "0"), remarks: it.remarks || null }));
    if (validItems.length === 0) { toast.error("请至少填写一条退货明细"); return; }
    const payload: any = { return_date: returnDate, customer_id: parseInt(customerId), problem_description: problemDescription || null, processing_plant_id: processingPlantId ? parseInt(processingPlantId) : null, processing_plant_name: processingPlantName || null, refund_method: refundMethod, items: validItems };
    if (refundMethod === "direct_refund" && bankAccountId) payload.bank_account_id = parseInt(bankAccountId);
    if (isEdit && returnOrderId) { updateMutation.mutate({ id: returnOrderId, payload }); }
    else { if (!saleId) { toast.error("请选择销售单"); return; } payload.sale_type = saleType; if (saleType === "whole_fish") payload.whole_fish_sale_id = parseInt(saleId); else payload.finished_product_sale_id = parseInt(saleId); createMutation.mutate(payload); }
  };

  const filteredSales = (salesData?.items || []).filter((sale: any) => {
    if (!saleSearch.trim()) return true;
    const search = saleSearch.trim().toLowerCase();
    return (sale.sale_no || "").toLowerCase().includes(search) || (sale.customer_name || "").toLowerCase().includes(search);
  });

  const getCustomerName = (id: string) => customersData?.items?.find((c: any) => String(c.id) === id)?.name || "-";

  return (
    <Dialog open={open} onOpenChange={(v) => { if (!v) { onClose(); if (!isEdit) resetForm(); } }}>
      <DialogContent className="sm:max-w-[1440px] max-h-[92vh] overflow-y-auto overflow-x-hidden p-0">
        {/* Header */}
        <DialogHeader className="px-6 pt-4 pb-2 border-b shrink-0">
          <DialogTitle className="flex items-center gap-2 text-base">
            <Package className="h-5 w-5 text-orange-600" />
            {isEdit ? "编辑退货单" : "创建退货单"}
          </DialogTitle>
          <DialogDescription className="text-xs">
            {isEdit ? `单号: ${editData?.return_no || ""}` : step === 1 ? "选择原销售单" : `关联销售单: ${saleDetail?.sale_no || `#${saleId}`}${saleDetail?.customer_name ? ` · ${saleDetail?.customer_name}` : ""}`}
          </DialogDescription>
        </DialogHeader>

        {/* ====== Step 1: 选择销售单 ====== */}
        {!isEdit && step === 1 && (
          <div className="px-6 py-3 space-y-3">
            <div className="flex gap-3">
              <div className="flex-1 space-y-1">
                <Label className="text-xs">销售类型</Label>
                <Select value={saleType} onValueChange={setSaleType}>
                  <SelectTrigger className="h-8 text-xs"><SelectValue /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="whole_fish">整鱼销售</SelectItem>
                    <SelectItem value="finished_product">成品销售</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div className="flex-[2] space-y-1">
                <Label className="text-xs">搜索销售单</Label>
                <div className="relative">
                  <Search className="absolute left-2.5 top-2 h-4 w-4 text-muted-foreground" />
                  <Input placeholder="单号或客户名称..." value={saleSearch} onChange={(e) => setSaleSearch(e.target.value)} className="pl-9 h-8 text-xs" />
                </div>
              </div>
            </div>
            <div className="border rounded-lg overflow-hidden">
              <div className="bg-muted/50 px-3 py-1.5 text-xs font-medium text-muted-foreground grid grid-cols-[1fr_100px_120px_100px_80px] gap-2">
                <span>单号 / 客户</span><span className="text-center">日期</span><span className="text-right">金额</span><span className="text-right">状态</span><span></span>
              </div>
              <div className="max-h-[300px] overflow-y-auto">
                {filteredSales.length > 0 ? filteredSales.map((sale: any) => (
                  <div key={sale.id} className={cn("px-3 py-2 grid grid-cols-[1fr_100px_120px_100px_80px] gap-2 items-center border-t cursor-pointer", saleId === String(sale.id) ? "bg-orange-50" : "hover:bg-muted/30")} onClick={() => handleSelectSale(String(sale.id))}>
                    <div className="min-w-0"><div className="font-mono text-xs font-medium truncate">{sale.sale_no || `#${sale.id}`}</div><div className="text-[10px] text-muted-foreground truncate">{sale.customer_name || "-"}</div></div>
                    <div className="text-center text-xs text-muted-foreground">{sale.sale_date}</div>
                    <div className="text-right text-xs font-medium">¥{Number(sale.gross_amount || sale.net_amount).toLocaleString("en-US", { minimumFractionDigits: 2 })}</div>
                    <div className="text-right"><Badge variant="outline" className="text-[10px]">{sale.status === "pending" ? "待收款" : sale.status === "partial_paid" ? "部分收款" : sale.status === "fully_paid" ? "全部收款" : sale.status}</Badge></div>
                    <div className="text-right"><Button size="sm" variant={saleId === String(sale.id) ? "default" : "ghost"} className="h-6 text-[10px] px-2" onClick={(e) => { e.stopPropagation(); handleSelectSale(String(sale.id)); }}>{saleId === String(sale.id) ? "已选" : "选择"}</Button></div>
                  </div>
                )) : (
                  <div className="text-center py-8 text-muted-foreground text-xs">暂无符合条件的销售单</div>
                )}
              </div>
            </div>
          </div>
        )}

        {/* ====== Step 2: 填写退货信息 ====== */}
        {(step === 2 || isEdit) && (
          <div className="px-6 py-4 space-y-4">

            {/* 基本信息行：2列（退货日期、加工厂） */}
            <div className="grid grid-cols-2 gap-3">
              <div>
                <Label className="text-xs text-muted-foreground mb-1 block">退货日期 *</Label>
                <Input type="date" value={returnDate} onChange={(e) => setReturnDate(e.target.value)} className="h-9 text-sm" />
              </div>
              <div>
                <Label className="text-xs text-muted-foreground mb-1 block">加工厂</Label>
                {(processingPlantName || saleEuNo) ? (
                  <div className="h-9 flex items-center px-3 rounded-md border bg-muted/30 text-sm">
                    <span className="truncate">{processingPlantName || "-"}</span>
                    {saleEuNo && <span className="ml-2 text-muted-foreground font-mono text-xs shrink-0">{saleEuNo}</span>}
                  </div>
                ) : (
                  <Select value={processingPlantId} onValueChange={(v) => { setProcessingPlantId(v); const p = plantsData?.items?.find((pl: any) => String(pl.id) === v); setProcessingPlantName(p?.name || ""); }}>
                    <SelectTrigger className="h-9 text-sm"><SelectValue placeholder="选择加工厂" /></SelectTrigger>
                    <SelectContent>{plantsData?.items?.map((pl: any) => <SelectItem key={pl.id} value={String(pl.id)}>{pl.name}</SelectItem>)}</SelectContent>
                  </Select>
                )}
              </div>
            </div>

            {/* 退款方式 + 银行账户 */}
            <div className="grid grid-cols-2 gap-3">
              <div>
                <Label className="text-xs text-muted-foreground mb-1 block">退款方式 *</Label>
                <Select value={refundMethod} onValueChange={setRefundMethod}>
                  <SelectTrigger className="h-9 text-sm">
                    <SelectValue>
                      {refundMethodOptions.find((opt) => opt.value === refundMethod)?.label || "选择退款方式"}
                    </SelectValue>
                  </SelectTrigger>
                  <SelectContent>
                    {refundMethodOptions.map((opt) => (
                      <SelectItem key={opt.value} value={opt.value}>{opt.label}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              {refundMethod === "direct_refund" && (
                <div>
                  <Label className="text-xs text-muted-foreground mb-1 block">付款账户 *</Label>
                  <Select value={bankAccountId} onValueChange={setBankAccountId}>
                    <SelectTrigger className="h-9 text-sm">
                      <SelectValue placeholder="选择银行账户" />
                    </SelectTrigger>
                    <SelectContent>
                      {bankAccountsData?.map((acc: any) => (
                        <SelectItem key={acc.id} value={String(acc.id)}>{acc.bank_name} {acc.account_number ? `(${acc.account_number})` : ""}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
              )}
            </div>

            {/* 退货明细 */}
            <div>
              <div className="flex items-center justify-between mb-1">
                <Label className="text-xs text-muted-foreground">退货明细</Label>
                <Button type="button" size="sm" variant="outline" className="h-7 text-xs" onClick={addItem}>
                  <Plus className="h-3.5 w-3.5 mr-1" />添加明细
                </Button>
              </div>
              <div className="grid grid-cols-[40px_140px_140px_120px_1fr_44px] gap-2 px-3 py-2 bg-muted/50 rounded-t-md text-xs font-medium text-muted-foreground">
                <span className="text-center">序号</span>
                <span className="text-right">重量(kg)</span>
                <span className="text-right">单价</span>
                <span className="text-right">金额</span>
                <span>备注</span>
                <span></span>
              </div>
              <div className="border-x border-b rounded-b-md overflow-hidden">
                {items.map((item, idx) => (
                  <div key={idx} className={cn("grid grid-cols-[40px_140px_140px_120px_1fr_44px] gap-2 px-3 py-2 items-center", idx > 0 && "border-t")}>
                    <div className="text-xs text-muted-foreground text-center">{idx + 1}</div>
                    <Input className="h-8 text-sm text-right" inputMode="decimal" value={item.weight_kg} onChange={(e) => updateItem(idx, "weight_kg", e.target.value)} placeholder="0.00" />
                    <Input className="h-8 text-sm text-right" inputMode="decimal" value={item.unit_price} onChange={(e) => updateItem(idx, "unit_price", e.target.value)} placeholder="0.00" />
                    <div className="h-8 flex items-center justify-end px-2 rounded-md border bg-muted/30 text-sm font-semibold">
                      ¥{(parseFloat(item.weight_kg || "0") * parseFloat(item.unit_price || "0")).toLocaleString("en-US", { minimumFractionDigits: 2 })}
                    </div>
                    <Input className="h-8 text-sm" value={item.remarks || ""} onChange={(e) => updateItem(idx, "remarks", e.target.value)} placeholder="备注/问题描述" />
                    <Button variant="ghost" size="icon" className="h-7 w-7 text-red-500" onClick={() => removeItem(idx)} disabled={items.length <= 1}>
                      <Trash2 className="h-4 w-4" />
                    </Button>
                  </div>
                ))}
              </div>
              <div className="flex items-center justify-between mt-2 px-1">
                <div className="flex gap-4 text-sm text-muted-foreground">
                  <span>共 <span className="font-medium text-foreground">{items.length}</span> 条明细</span>
                  <span>总重量: <span className="font-medium text-foreground">{totalWeight.toLocaleString("en-US", { minimumFractionDigits: 2 })} kg</span></span>
                </div>
                <div className="text-lg font-bold text-red-600">
                  ¥{totalAmount.toLocaleString("en-US", { minimumFractionDigits: 2 })}
                </div>
              </div>
            </div>

            {/* 附件上传放到最下面 */}
            <div>
              <Label className="text-xs text-muted-foreground mb-1 block">附件上传 {attachments.length > 0 && <span className="text-orange-600">({attachments.length})</span>}</Label>
              <div className="flex flex-wrap gap-2 items-center">
                {attachments.map((file, idx) => (
                  <div key={idx} className="flex items-center gap-2 bg-muted rounded-md px-2 py-1 text-sm border">
                    {file.type.startsWith("image/") ? <Image className="h-3.5 w-3.5 text-blue-500" /> : <Video className="h-3.5 w-3.5 text-purple-500" />}
                    <span className="max-w-[120px] truncate">{file.name}</span>
                    <span className="text-xs text-muted-foreground">({(file.size / 1024 / 1024).toFixed(1)}MB)</span>
                    <button className="text-red-500 hover:text-red-700" onClick={() => setAttachments(attachments.filter((_, i) => i !== idx))}>
                      <X className="h-3.5 w-3.5" />
                    </button>
                  </div>
                ))}
                <label className="cursor-pointer flex items-center gap-2 border-2 border-dashed border-muted-foreground/30 rounded-md px-3 py-1.5 text-sm text-muted-foreground hover:border-orange-400 hover:text-orange-600 transition-colors">
                  <Upload className="h-4 w-4" />
                  <span>上传图片/视频</span>
                  <input type="file" multiple accept="image/*,video/*" className="hidden" onChange={handleFileSelect} />
                </label>
              </div>
              <p className="text-xs text-muted-foreground mt-1">支持 JPG、PNG、GIF、MP4 等格式，单个文件不超过 20MB</p>
            </div>
          </div>
        )}

        {/* Footer */}
        <DialogFooter className="px-6 py-2 border-t gap-2 bg-white shrink-0">
          {!isEdit && step === 2 && (
            <Button variant="outline" onClick={() => setStep(1)} className="mr-auto h-7 text-xs"><ChevronRight className="h-3 w-3 rotate-180 mr-1" />上一步</Button>
          )}
          <Button variant="ghost" className="h-7 text-xs" onClick={() => { onClose(); if (!isEdit) resetForm(); }}>取消</Button>
          {(step === 2 || isEdit) && (
            <Button onClick={handleSubmit} disabled={createMutation.isPending || updateMutation.isPending} className="bg-orange-600 hover:bg-orange-700 h-7 text-xs">
              {createMutation.isPending || updateMutation.isPending ? "保存中..." : isEdit ? "更新" : "提交"}
            </Button>
          )}
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
