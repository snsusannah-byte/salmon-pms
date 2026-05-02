import React, { useState, useEffect } from "react";
import { useForm, useFieldArray } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import * as z from "zod";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { api } from "@/lib/api";
import { useQueryClient, useQuery } from "@tanstack/react-query";
import { toast } from "sonner";
import { Plus, Trash2 } from "lucide-react";

const productSchema = z.object({
  product_name: z.string().min(1, "产品名称不能为空"),
  product_spec: z.string().min(1, "规格不能为空"),
  box_count: z.coerce.number().min(1, "箱数至少为1"),
  net_weight_kg: z.coerce.number().min(0.001, "重量必须大于0"),
  unit_price: z.coerce.number().min(0.0001, "单价必须大于0"),
  total_amount: z.coerce.number().min(0, "金额不能为负数"),
  notes: z.string().optional().or(z.literal("")),
});

const formSchema = z.object({
  invoice_no: z.string().min(1, "发票编号不能为空").max(50),
  invoice_date: z.string().min(1, "发票日期不能为空"),
  kill_date: z.string().min(1, "宰杀日期不能为空"),
  arrival_date: z.string().optional().or(z.literal("")),
  processing_plant_id: z.coerce.number().min(1, "请选择加工厂"),
  fish_farm_id: z.coerce.number().min(0, "渔场ID不能为负数").optional(),
  exporter_id: z.coerce.number().min(1, "请选择出口商"),
  total_amount_usd: z.coerce.number().min(0, "金额不能为负数"),
  total_boxes: z.coerce.number().min(0, "箱数不能为负数"),
  total_weight_kg: z.coerce.number().min(0, "重量不能为负数"),
  awb_no: z.string().max(50).optional().or(z.literal("")),
  gross_weight_kg: z.coerce.number().min(0, "重量不能为负数").optional().or(z.literal(0)),
  eta: z.string().optional().or(z.literal("")),
  departure_date: z.string().optional().or(z.literal("")),
  flight_info: z.string().max(100).optional().or(z.literal("")),
  origin_certificate: z.string().max(100).optional().or(z.literal("")),
  inspection_certificate: z.string().max(100).optional().or(z.literal("")),
  customs_status: z.string().default("PENDING_CUSTOMS"),
  exchange_status: z.string().default("NOT_EXCHANGED"),
  notes: z.string().optional().or(z.literal("")),
  products: z.array(productSchema).min(1, "至少需要一条产品明细"),
});

type FormData = z.infer<typeof formSchema>;

interface InvoiceFormDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  initialData?: Invoice | null;
}

interface Invoice {
  id: number;
  invoice_no: string;
  invoice_date: string;
  kill_date: string | null;
  arrival_date: string | null;
  processing_plant_id: number;
  fish_farm_id: number;
  exporter_id: number;
  total_amount_usd: string;
  total_boxes: number;
  total_weight_kg: string;
  awb_no: string | null;
  gross_weight_kg: string | null;
  eta: string | null;
  departure_date: string | null;
  flight_info: string | null;
  origin_certificate: string | null;
  inspection_certificate: string | null;
  customs_status: string;
  exchange_status: string;
  notes: string | null;
  products: InvoiceProduct[];
}

interface InvoiceProduct {
  id?: number;
  product_name: string;
  product_spec: string;
  box_count: number;
  net_weight_kg: number | string;
  unit_price: number | string;
  total_amount: number | string;
  notes: string | null;
}

export function InvoiceFormDialog({ open, onOpenChange, initialData }: InvoiceFormDialogProps) {
  const queryClient = useQueryClient();
  const [isSubmitting, setIsSubmitting] = useState(false);

  const form = useForm<FormData>({
    resolver: zodResolver(formSchema) as any,
    defaultValues: {
      invoice_no: "",
      invoice_date: "",
      kill_date: "",
      arrival_date: "",
      processing_plant_id: 0,
      fish_farm_id: 0,
      exporter_id: 0,
      total_amount_usd: 0,
      total_boxes: 0,
      total_weight_kg: 0,
      awb_no: "",
      gross_weight_kg: 0,
      eta: "",
      departure_date: "",
      flight_info: "",
      origin_certificate: "",
      inspection_certificate: "",
      customs_status: "PENDING_CUSTOMS",
      exchange_status: "NOT_EXCHANGED",
      notes: "",
      products: [],
    },
  });

  // 查询公司列表
  const { data: companiesData } = useQuery({
    queryKey: ["companies"],
    queryFn: async () => {
      const res = await api.get("/v1/companies/");
      return res.data as { items: { id: number; name: string; type: string }[] };
    },
    enabled: open,
  });

  // 查询产品列表（整鱼规格）
  const { data: productsData } = useQuery({
    queryKey: ["products", "whole_fish"],
    queryFn: async () => {
      const res = await api.get("/v1/products/?category=whole_fish&limit=500");
      return res.data.items as { id: number; name: string; spec: string | null }[];
    },
    enabled: open,
  });

  const processingPlants = companiesData?.items.filter(c => c.type === "processing_plant") || [];
  const fishFarms = companiesData?.items.filter(c => c.type === "fish_farm") || [];
  const exporters = companiesData?.items.filter(c => c.type === "exporter") || [];

  // 从真实产品数据构建选项
  const productNameOptions = [...new Set(productsData?.map(p => p.name).filter(Boolean) || [])] as string[];
  const specOptions = [...new Set(productsData?.map(p => p.spec).filter(Boolean) || [])] as string[];
  
  // 规格→产品名称映射
  const specToProductMap: Record<string, string> = {};
  productsData?.forEach(p => {
    if (p.spec && p.name) {
      specToProductMap[p.spec] = p.name;
    }
  });

  const { fields, append, remove } = useFieldArray({
    control: form.control,
    name: "products",
  });

  // 当弹窗打开且 initialData 变化时，重置表单
  React.useEffect(() => {
    if (open) {
      resetForm();
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open, initialData?.id]);

  const resetForm = () => {
    if (initialData) {
      form.reset({
        invoice_no: initialData.invoice_no,
        invoice_date: initialData.invoice_date,
        kill_date: initialData.kill_date ?? "",
        arrival_date: initialData.arrival_date ?? "",
        processing_plant_id: initialData.processing_plant_id,
        fish_farm_id: initialData.fish_farm_id,
        exporter_id: initialData.exporter_id,
        total_amount_usd: Number(initialData.total_amount_usd),
        total_boxes: initialData.total_boxes,
        total_weight_kg: Number(initialData.total_weight_kg),
        awb_no: initialData.awb_no ?? "",
        gross_weight_kg: initialData.gross_weight_kg ? Number(initialData.gross_weight_kg) : 0,
        eta: initialData.eta ? initialData.eta.slice(0, 16) : "",
        departure_date: initialData.departure_date ?? "",
        flight_info: initialData.flight_info ?? "",
        origin_certificate: initialData.origin_certificate ?? "",
        inspection_certificate: initialData.inspection_certificate ?? "",
        customs_status: initialData.customs_status,
        exchange_status: initialData.exchange_status,
        notes: initialData.notes ?? "",
        products: initialData.products.map((p) => ({
          product_name: p.product_name,
          product_spec: p.product_spec,
          box_count: p.box_count,
          net_weight_kg: Number(p.net_weight_kg),
          unit_price: Number(p.unit_price),
          total_amount: Number(p.total_amount),
          notes: p.notes ?? "",
        })),
      });
    } else {
      form.reset({
        invoice_no: "",
        invoice_date: "",
        kill_date: "",
        arrival_date: "",
        processing_plant_id: 0,
        fish_farm_id: 0,
        exporter_id: 0,
        total_amount_usd: 0,
        total_boxes: 0,
        total_weight_kg: 0,
        awb_no: "",
        gross_weight_kg: 0,
        eta: "",
        departure_date: "",
        flight_info: "",
        origin_certificate: "",
        inspection_certificate: "",
        customs_status: "PENDING_CUSTOMS",
        exchange_status: "NOT_EXCHANGED",
        notes: "",
        products: [],
      });
    }
  };

  const onSubmit = async (data: any) => {
    setIsSubmitting(true);
    try {
      // 计算汇总数据
      const currentProducts = data.products || [];
      let tBoxes = 0;
      let tWeight = 0;
      let tAmount = 0;
      
      const productsWithAmount = currentProducts.map((p: any) => {
        const netWeight = Number(p?.net_weight_kg || 0);
        const unitPrice = Number(p?.unit_price || 0);
        const boxCount = Number(p?.box_count || 0);
        const lineAmount = netWeight * unitPrice;
        
        tBoxes += boxCount;
        tWeight += netWeight;
        tAmount += lineAmount;
        
        return {
          ...p,
          total_amount: Number(lineAmount.toFixed(2)),
        };
      });

      const payload = {
        ...data,
        products: productsWithAmount,
        total_boxes: tBoxes,
        total_weight_kg: Number(tWeight.toFixed(3)),
        total_amount_usd: Number(tAmount.toFixed(2)),
        kill_date: data.kill_date || undefined,
        arrival_date: data.arrival_date || undefined,
      };

      if (initialData) {
        await api.put(`/v1/invoices/${initialData.id}`, payload);
        toast.success("发票更新成功");
      } else {
        await api.post("/v1/invoices/", payload);
        toast.success("发票创建成功");
      }

      queryClient.invalidateQueries({ queryKey: ["invoices"] });
      onOpenChange(false);
      resetForm();
    } catch (error: any) {
      const detail = error.response?.data?.detail;
      let msg: string;
      if (Array.isArray(detail)) {
        msg = detail.map((d: any) => d.msg).join("; ");
      } else if (typeof detail === "string") {
        msg = detail;
      } else {
        msg = "操作失败";
      }
      toast.error(msg);
    } finally {
      setIsSubmitting(false);
    }
  };

  const addProduct = () => {
    append({
      product_name: "三文鱼",
      product_spec: "",
      box_count: 1,
      net_weight_kg: 0,
      unit_price: 0,
      total_amount: 0,
      notes: "",
    });
  };

  // 实时计算汇总（直接在渲染时计算，不触发 setValue 避免无限循环）
  const products = form.watch("products") || [];
  let totalBoxes = 0;
  let totalWeight = 0;
  let totalAmount = 0;

  products.forEach((p: any) => {
    const netWeight = Number(p?.net_weight_kg || 0);
    const unitPrice = Number(p?.unit_price || 0);
    const boxCount = Number(p?.box_count || 0);
    totalBoxes += boxCount;
    totalWeight += netWeight;
    totalAmount += netWeight * unitPrice;
  });

  return (
    <Dialog open={open} onOpenChange={(v) => { if (!v) { onOpenChange(false); resetForm(); } }}>
      <DialogContent className="!w-[500px] !max-w-[500px] max-h-[90vh] overflow-y-auto p-6">
        <DialogHeader>
          <DialogTitle>{initialData ? "编辑发票" : "新增发票"}</DialogTitle>
        </DialogHeader>

        <form onSubmit={form.handleSubmit(onSubmit, (errors) => {
          console.error("表单验证错误:", errors);
          toast.error("请检查表单必填项");
        })} className="space-y-8">
          {/* 基本信息 */}
          <div className="space-y-6">
            <h3 className="text-sm font-semibold text-foreground">基本信息</h3>
            <div className="grid grid-cols-3 gap-6">
              <div className="space-y-2">
                <Label htmlFor="invoice_no">发票号（供应商原始编号） *</Label>
                <Input id="invoice_no" {...form.register("invoice_no")} placeholder="如: 8690" />
                {form.formState.errors.invoice_no && <p className="text-xs text-red-500">{form.formState.errors.invoice_no.message}</p>}
              </div>
              <div className="space-y-2">
                <Label htmlFor="invoice_date">发票日期 *</Label>
                <Input id="invoice_date" type="date" {...form.register("invoice_date")} />
                {form.formState.errors.invoice_date && <p className="text-xs text-red-500">{form.formState.errors.invoice_date.message}</p>}
              </div>
              <div className="space-y-2">
                <Label htmlFor="kill_date">宰杀日期 *</Label>
                <Input id="kill_date" type="date" {...form.register("kill_date")} />
              </div>
              <div className="space-y-2">
                <Label htmlFor="processing_plant_id">加工厂 *</Label>
                <Select
                  value={form.watch("processing_plant_id") ? String(form.watch("processing_plant_id")) : undefined}
                  onValueChange={(v) => form.setValue("processing_plant_id", parseInt(v || "0"))}
                >
                  <SelectTrigger className="w-full">
                    <SelectValue placeholder="选择加工厂" />
                  </SelectTrigger>
                  <SelectContent>
                    {processingPlants.map((c) => (
                      <SelectItem key={c.id} value={String(c.id)}>{c.name}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
                {form.formState.errors.processing_plant_id && <p className="text-xs text-red-500">{form.formState.errors.processing_plant_id.message}</p>}
              </div>
              <div className="space-y-2">
                <Label htmlFor="fish_farm_id">渔场</Label>
                <Select
                  value={form.watch("fish_farm_id") ? String(form.watch("fish_farm_id")) : undefined}
                  onValueChange={(v) => form.setValue("fish_farm_id", parseInt(v || "0"))}
                >
                  <SelectTrigger className="w-full">
                    <SelectValue placeholder="选择渔场" />
                  </SelectTrigger>
                  <SelectContent>
                    {fishFarms.map((c) => (
                      <SelectItem key={c.id} value={String(c.id)}>{c.name}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
                {form.formState.errors.fish_farm_id && <p className="text-xs text-red-500">{form.formState.errors.fish_farm_id.message}</p>}
              </div>
              <div className="space-y-2">
                <Label htmlFor="exporter_id">出口商 *</Label>
                <Select
                  value={form.watch("exporter_id") ? String(form.watch("exporter_id")) : undefined}
                  onValueChange={(v) => form.setValue("exporter_id", parseInt(v || "0"))}
                >
                  <SelectTrigger className="w-full">
                    <SelectValue placeholder="选择出口商" />
                  </SelectTrigger>
                  <SelectContent>
                    {exporters.map((c) => (
                      <SelectItem key={c.id} value={String(c.id)}>{c.name}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
                {form.formState.errors.exporter_id && <p className="text-xs text-red-500">{form.formState.errors.exporter_id.message}</p>}
              </div>
            </div>
          </div>

          {/* 物流与证书信息 */}
          <div className="space-y-6">
            <h3 className="text-sm font-semibold text-foreground">物流与证书信息</h3>
            <div className="grid grid-cols-3 gap-6">
              <div className="space-y-2">
                <Label htmlFor="awb_no">AWB航空运单号 *</Label>
                <Input id="awb_no" {...form.register("awb_no")} placeholder="如: 176-12345678" />
              </div>
              <div className="space-y-2">
                <Label htmlFor="gross_weight_kg">毛重(kg)</Label>
                <Input id="gross_weight_kg" {...form.register("gross_weight_kg")} placeholder="毛重" />
              </div>
              <div className="space-y-2">
                <Label htmlFor="eta">ETA预计到达 *</Label>
                <Input id="eta" type="datetime-local" {...form.register("eta")} />
              </div>
              <div className="space-y-2">
                <Label htmlFor="departure_date">发运时间</Label>
                <Input id="departure_date" type="date" {...form.register("departure_date")} />
              </div>
              <div className="space-y-2">
                <Label htmlFor="flight_info">航班信息</Label>
                <Input id="flight_info" {...form.register("flight_info")} placeholder="如: CA1234" />
              </div>
              <div className="space-y-2">
                <Label htmlFor="origin_certificate">原产地证书</Label>
                <Input id="origin_certificate" {...form.register("origin_certificate")} placeholder="证书编号" />
              </div>
              <div className="space-y-2">
                <Label htmlFor="inspection_certificate">检验检疫证书</Label>
                <Input id="inspection_certificate" {...form.register("inspection_certificate")} placeholder="证书编号" />
              </div>
            </div>
          </div>

          {/* 产品明细 */}
          <div className="space-y-6">
            <div className="flex items-center justify-between">
              <h3 className="text-sm font-semibold text-foreground">产品明细</h3>
              <Button type="button" variant="outline" size="sm" onClick={addProduct}>
                <Plus className="w-3 h-3 mr-1" />
                添加产品
              </Button>
            </div>

            {fields.length > 0 && (
              <div className="grid grid-cols-12 gap-2 px-2 py-2 text-xs text-muted-foreground font-medium bg-muted/50 rounded-t-md">
                <div className="col-span-2">产品</div>
                <div className="col-span-2">规格</div>
                <div className="col-span-1 text-center">箱数</div>
                <div className="col-span-2 text-center">重量(kg)</div>
                <div className="col-span-2 text-center">单价(USD)</div>
                <div className="col-span-2 text-center">金额(USD)</div>
                <div className="col-span-1"></div>
              </div>
            )}

            {fields.map((field, index) => {
              const netWeight = Number(form.watch(`products.${index}.net_weight_kg`) || 0);
              const unitPrice = Number(form.watch(`products.${index}.unit_price`) || 0);
              const lineAmount = netWeight * unitPrice;
              
              return (
                <div key={field.id} className="grid grid-cols-12 gap-2 items-center px-2 py-2 border rounded-md">
                  <div className="col-span-2">
                    <div className="text-xs font-medium text-foreground truncate px-2 py-1.5 h-8 bg-muted/30 rounded border flex items-center" title={form.watch(`products.${index}.product_name`) || "-"}>
                      {form.watch(`products.${index}.product_name`) || "选择规格后自动显示"}
                    </div>
                  </div>
                  <div className="col-span-2">
                    <Select
                      value={form.watch(`products.${index}.product_spec`) || undefined}
                      onValueChange={(v) => {
                        const spec = v || "";
                        form.setValue(`products.${index}.product_spec`, spec);
                        // 自动对应产品名称
                        const productName = specToProductMap[spec];
                        if (productName) {
                          form.setValue(`products.${index}.product_name`, productName);
                        }
                      }}
                    >
                      <SelectTrigger className="text-xs w-full h-8">
                        <SelectValue placeholder="规格" />
                      </SelectTrigger>
                      <SelectContent>
                        {specOptions.map((spec) => (
                          <SelectItem key={spec} value={spec}>{spec}</SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                  <div className="col-span-1">
                    <Input type="number" inputMode="numeric" className="text-center text-xs h-8 px-1 appearance-none [-moz-appearance:textfield] [&::-webkit-outer-spin-button]:appearance-none [&::-webkit-inner-spin-button]:appearance-none" {...form.register(`products.${index}.box_count`)} />
                  </div>
                  <div className="col-span-2">
                    <Input type="number" step="0.001" inputMode="decimal" className="text-center text-xs h-8 px-1 appearance-none [-moz-appearance:textfield] [&::-webkit-outer-spin-button]:appearance-none [&::-webkit-inner-spin-button]:appearance-none" {...form.register(`products.${index}.net_weight_kg`)} />
                  </div>
                  <div className="col-span-2">
                    <Input type="number" step="0.0001" inputMode="decimal" className="text-center text-xs h-8 px-1 appearance-none [-moz-appearance:textfield] [&::-webkit-outer-spin-button]:appearance-none [&::-webkit-inner-spin-button]:appearance-none" {...form.register(`products.${index}.unit_price`)} />
                  </div>
                  <div className="col-span-2 text-center text-xs font-medium truncate" title={lineAmount.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}>
                    {lineAmount.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                  </div>
                  <div className="col-span-1 flex justify-end">
                    <Button type="button" variant="ghost" size="icon" className="h-7 w-7 text-red-500" onClick={() => remove(index)}>
                      <Trash2 className="h-3 w-3" />
                    </Button>
                  </div>
                </div>
              );
            })}

            {/* 汇总行 - 移到产品列表下方 */}
            {fields.length > 0 && (
              <div className="flex gap-4 text-sm bg-muted/50 px-4 py-3 rounded-md justify-end">
                <span className="text-muted-foreground">总箱数: <strong className="text-foreground">{totalBoxes}</strong></span>
                <span className="text-muted-foreground">总重量: <strong className="text-foreground">{totalWeight.toFixed(2)} kg</strong></span>
                <span className="text-muted-foreground">总金额: <strong className="text-primary">${totalAmount.toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2})}</strong></span>
              </div>
            )}
          </div>

          {/* 备注 */}
          <div className="space-y-2">
            <Label htmlFor="notes">备注</Label>
            <textarea
              id="notes"
              {...form.register("notes")}
              placeholder="其他备注信息..."
              rows={3}
              className="w-full px-3 py-2 border rounded-md text-sm bg-background resize-y focus:outline-none focus:ring-2 focus:ring-ring"
            />
          </div>

          <DialogFooter>
            <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>
              取消
            </Button>
            <Button type="submit" disabled={isSubmitting}>
              {isSubmitting ? "保存中..." : initialData ? "保存修改" : "创建发票"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
