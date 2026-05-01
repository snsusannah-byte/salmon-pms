import { useState, useEffect } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from "@/components/ui/dialog";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Plus, Search, Pencil, Trash2 } from "lucide-react";
import { toast } from "sonner";
import { PackagingConfigSection } from "@/components/PackagingConfigSection";

interface Product {
  id: number;
  category: string;
  code: string;
  name: string;
  spec: string | null;
  unit: string;
  unit_weight_kg: string | null;
  series_code: string | null;
  series_name: string | null;
  portion_weight_g: number | null;
  portion_boxes: number | null;
  is_active: boolean;
  notes: string | null;
  created_at: string;
}

export default function ProductsPage() {
  const queryClient = useQueryClient();
  const [activeTab, setActiveTab] = useState("whole_fish");
  const [search, setSearch] = useState("");
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editingProduct, setEditingProduct] = useState<Product | null>(null);
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [productToDelete, setProductToDelete] = useState<Product | null>(null);

  // 表单状态
  const [formCategory, setFormCategory] = useState("whole_fish");
  const [formCode, setFormCode] = useState("");
  const [formName, setFormName] = useState("");
  const [formSpec, setFormSpec] = useState("");
  const [formUnit, setFormUnit] = useState("kg");
  const [formWeight, setFormWeight] = useState("");
  // 成品规格专用
  const [formSeriesCode, setFormSeriesCode] = useState("");
  const [formSeriesName, setFormSeriesName] = useState("");
  const [formPortionWeight, setFormPortionWeight] = useState("");
  const [formPortionBoxes, setFormPortionBoxes] = useState("");
  // 包装物配置
  const [formPackagings, setFormPackagings] = useState<{ id?: number; level: string; material_id: number; material_name: string; quantity: number; unit: string; notes?: string }[]>([]);
  const [formNotes, setFormNotes] = useState("");

  // 成品产品名称自动生成：冰鲜三文鱼 + 规格编码
  useEffect(() => {
    if (formCategory === "finished_product" && !editingProduct) {
      const spec = formSpec.trim() || (
        formSeriesCode && formPortionWeight && formPortionBoxes
          ? `${formSeriesCode}${formPortionWeight}${formPortionBoxes}`
          : ""
      );
      if (spec) {
        setFormName(`冰鲜三文鱼${spec}`);
      }
    }
  }, [formCategory, formSeriesCode, formPortionWeight, formPortionBoxes, formSpec, editingProduct]);

  // 产品分类中文映射
  const categoryLabels: Record<string, string> = {
    whole_fish: "整鱼规格",
    finished_product: "成品定义",
    byproduct: "副产品",
    bom_material: "BOM物料",
  };

  const { data: bomMaterials } = useQuery({
    queryKey: ["bom-materials"],
    queryFn: async () => {
      const res = await api.get("/v1/products/?category=bom_material&limit=500");
      return res.data.items as { id: number; name: string; code: string; unit: string }[];
    },
    enabled: dialogOpen && formCategory === "finished_product",
  });

  const { data: seriesOptions } = useQuery({
    queryKey: ["product-series-options"],
    queryFn: async () => {
      const res = await api.get("/v1/products/series-codes");
      return res.data as { series_codes: string[]; series_names: string[] };
    },
    enabled: dialogOpen && formCategory === "finished_product",
  });

  const [isSubmitting, setIsSubmitting] = useState(false);

  const { data, isLoading } = useQuery({
    queryKey: ["products", activeTab, search],
    queryFn: async () => {
      const params = new URLSearchParams();
      params.set("category", activeTab);
      if (search) params.set("search", search);
      const res = await api.get(`/v1/products/?${params.toString()}`);
      return res.data as { total: number; items: Product[] };
    },
  });

  // 删除仍然用 mutation
  const deleteMutation = useMutation({
    mutationFn: (id: number) => api.delete(`/v1/products/${id}`),
    onSuccess: () => {
      toast.success("产品已删除");
      queryClient.invalidateQueries({ queryKey: ["products"] });
      setDeleteDialogOpen(false);
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.detail ?? "删除失败");
    },
  });

  const resetForm = () => {
    setFormCategory(activeTab);
    setFormCode("");
    setFormName(activeTab === "whole_fish" ? "挪威冰鲜三文鱼" : activeTab === "finished_product" ? "冰鲜三文鱼" : "");
    setFormSpec("");
    setFormUnit("kg");
    setFormWeight("");
    setFormSeriesCode("");
    setFormSeriesName("");
    setFormPortionWeight("");
    setFormPortionBoxes("");
    setFormPackagings([]);
    setFormNotes("");
    setEditingProduct(null);
  };

  const openCreateDialog = () => {
    resetForm();
    setDialogOpen(true);
  };

  const openEditDialog = async (product: Product) => {
    setEditingProduct(product);
    setFormCategory(product.category);
    setFormCode(product.code);
    setFormName(product.name);
    setFormSpec(product.spec ?? "");
    setFormUnit(product.unit);
    setFormWeight(product.unit_weight_kg ?? "");
    setFormSeriesCode(product.series_code ?? "");
    setFormSeriesName(product.series_name ?? "");
    setFormPortionWeight(product.portion_weight_g?.toString() ?? "");
    setFormPortionBoxes(product.portion_boxes?.toString() ?? "");
    setFormNotes(product.notes ?? "");
    // 加载包装物
    try {
      const res = await api.get(`/v1/products/${product.id}/packagings`);
      setFormPackagings(res.data.map((p: any) => ({
        id: p.id,
        level: p.level,
        material_id: p.material_id,
        material_name: p.material_name,
        quantity: p.quantity,
        unit: p.unit,
        notes: p.notes,
      })));
    } catch {
      setFormPackagings([]);
    }
    setDialogOpen(true);
  };

  const handleSubmit = async () => {
    if (!formName.trim()) {
      toast.error("产品名称不能为空");
      return;
    }

    const payload: any = {
      category: formCategory,
      code: formCode.trim() || undefined,
      name: formName,
      spec: formSpec || null,
      unit: formUnit,
      unit_weight_kg: formWeight ? parseFloat(formWeight) : null,
      is_active: true,
      notes: formNotes || null,
    };

    // 成品规格字段
    if (formCategory === "finished_product") {
      payload.series_code = formSeriesCode.trim() || null;
      payload.series_name = formSeriesName.trim() || null;
      payload.portion_weight_g = formPortionWeight ? parseInt(formPortionWeight) : null;
      payload.portion_boxes = formPortionBoxes ? parseInt(formPortionBoxes) : null;
      // 自动计算单盒重量(kg)
      if (payload.portion_weight_g && payload.portion_boxes) {
        payload.unit_weight_kg = payload.portion_weight_g / payload.portion_boxes / 1000;
      }
      // 自动生成规格编码
      if (!formSpec.trim() && payload.series_code && payload.portion_weight_g && payload.portion_boxes) {
        payload.spec = `${payload.series_code}${payload.portion_weight_g}${payload.portion_boxes}`;
      }
    }

    try {
      setIsSubmitting(true);
      let productId: number;
      if (editingProduct) {
        await api.put(`/v1/products/${editingProduct.id}`, payload);
        productId = editingProduct.id;
        toast.success("产品更新成功");
      } else {
        const res = await api.post("/v1/products/", payload);
        productId = res.data.id;
        toast.success("产品创建成功");
      }

      // 保存包装物
      if (formCategory === "finished_product" && formPackagings.length > 0) {
        // 删除旧的（编辑模式下）
        if (editingProduct) {
          try {
            const oldRes = await api.get(`/v1/products/${productId}/packagings`);
            for (const old of oldRes.data) {
              await api.delete(`/v1/products/${productId}/packagings/${old.id}`);
            }
          } catch { /* ignore */ }
        }
        // 创建新的
        for (const p of formPackagings) {
          await api.post(`/v1/products/${productId}/packagings`, {
            level: p.level,
            material_id: p.material_id,
            quantity: p.quantity,
            unit: p.unit || "个",
            notes: p.notes || null,
          });
        }
      }

      queryClient.invalidateQueries({ queryKey: ["products"] });
      setDialogOpen(false);
      resetForm();
    } catch (error: any) {
      toast.error(error.response?.data?.detail ?? "操作失败");
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleDelete = (product: Product) => {
    setProductToDelete(product);
    setDeleteDialogOpen(true);
  };

  const confirmDelete = () => {
    if (productToDelete) {
      deleteMutation.mutate(productToDelete.id);
    }
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">产品管理</h1>
        <Button onClick={openCreateDialog}>
          <Plus className="w-4 h-4 mr-1" />
          新增产品
        </Button>
      </div>

      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList className="grid w-full grid-cols-4">
          <TabsTrigger value="whole_fish">整鱼规格</TabsTrigger>
          <TabsTrigger value="finished_product">成品定义</TabsTrigger>
          <TabsTrigger value="byproduct">副产品</TabsTrigger>
          <TabsTrigger value="bom_material">BOM物料</TabsTrigger>
        </TabsList>

        {["whole_fish", "finished_product", "byproduct", "bom_material"].map((cat) => (
          <TabsContent key={cat} value={cat} className="space-y-4">
            <div className="flex items-center gap-2">
              <div className="relative flex-1 max-w-sm">
                <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
                <Input
                  placeholder="搜索编码或名称..."
                  value={search}
                  onChange={(e) => setSearch(e.target.value)}
                  className="pl-9"
                />
              </div>
            </div>

            <div className="border rounded-lg">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>编码</TableHead>
                    <TableHead>名称</TableHead>
                    <TableHead>规格</TableHead>
                    <TableHead>单位</TableHead>
                    <TableHead>重量(kg)</TableHead>
                    <TableHead>状态</TableHead>
                    <TableHead>操作</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {isLoading ? (
                    <TableRow>
                      <TableCell colSpan={7} className="text-center py-8">
                        加载中...
                      </TableCell>
                    </TableRow>
                  ) : data?.items.length === 0 ? (
                    <TableRow>
                      <TableCell colSpan={7} className="text-center py-8 text-muted-foreground">
                        暂无数据
                      </TableCell>
                    </TableRow>
                  ) : (
                    data?.items.map((product) => (
                      <TableRow key={product.id}>
                        <TableCell className="font-medium text-muted-foreground text-xs">{product.code}</TableCell>
                        <TableCell>{product.name}</TableCell>
                        <TableCell>
                          {product.category === "finished_product" && (product.series_code || product.portion_weight_g) ? (
                            <div className="text-xs space-y-0.5">
                              <div className="font-medium">{product.series_code}{product.portion_weight_g}{product.portion_boxes ?? ""}</div>
                              {product.series_name && <div className="text-muted-foreground">{product.series_name}</div>}
                              {product.portion_weight_g && product.portion_boxes && (
                                <div className="text-muted-foreground">
                                  {product.portion_weight_g}g/{product.portion_boxes}盒({Math.round(product.portion_weight_g / product.portion_boxes)}g/盒)
                                </div>
                              )}
                            </div>
                          ) : (
                            product.spec ?? "-"
                          )}
                        </TableCell>
                        <TableCell>{product.unit}</TableCell>
                        <TableCell>{product.unit_weight_kg ?? "-"}</TableCell>
                        <TableCell>
                          {product.is_active ? (
                            <Badge variant="secondary" className="bg-green-100 text-green-800">
                              启用
                            </Badge>
                          ) : (
                            <Badge variant="secondary" className="bg-gray-100 text-gray-800">
                              停用
                            </Badge>
                          )}
                        </TableCell>
                        <TableCell>
                          <div className="flex gap-2">
                            <Button
                              variant="ghost"
                              size="icon"
                              className="h-8 w-8"
                              onClick={() => openEditDialog(product)}
                            >
                              <Pencil className="h-4 w-4" />
                            </Button>
                            <Button
                              variant="ghost"
                              size="icon"
                              className="h-8 w-8 text-red-500"
                              onClick={() => handleDelete(product)}
                            >
                              <Trash2 className="h-4 w-4" />
                            </Button>
                          </div>
                        </TableCell>
                      </TableRow>
                    ))
                  )}
                </TableBody>
              </Table>
            </div>
          </TabsContent>
        ))}
      </Tabs>

      {/* 新增/编辑弹窗 */}
      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <DialogContent className="max-w-lg">
          <DialogHeader>
            <DialogTitle>{editingProduct ? "编辑产品" : "新增产品"}</DialogTitle>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label>产品分类</Label>
                <Select value={formCategory} onValueChange={(v) => setFormCategory(v || "whole_fish")}>
                  <SelectTrigger>
                    <SelectValue placeholder="选择分类">{categoryLabels[formCategory]}</SelectValue>
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="whole_fish">整鱼规格</SelectItem>
                    <SelectItem value="finished_product">成品定义</SelectItem>
                    <SelectItem value="byproduct">副产品</SelectItem>
                    <SelectItem value="bom_material">BOM物料</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-2">
                <Label>单位</Label>
                <Select value={formUnit} onValueChange={(v) => setFormUnit(v || "kg")}>
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="kg">kg</SelectItem>
                    <SelectItem value="个">个</SelectItem>
                    <SelectItem value="套">套</SelectItem>
                    <SelectItem value="份">份</SelectItem>
                    <SelectItem value="盒">盒</SelectItem>
                    <SelectItem value="箱">箱</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label>产品编码</Label>
                <Input
                  value={formCode}
                  onChange={(e) => setFormCode(e.target.value)}
                  placeholder="留空自动生成"
                  className="text-muted-foreground"
                />
              </div>
              <div className="space-y-2">
                <Label>产品名称 *</Label>
                <Input
                  value={formName}
                  onChange={(e) => setFormName(e.target.value)}
                  placeholder="如: 三文鱼"
                />
              </div>
            </div>
            {formCategory === "finished_product" ? (
              <>
                {/* 成品规格专用 */}
                <div className="grid grid-cols-4 gap-4">
                  <div className="space-y-2">
                    <Label>系列代号</Label>
                    <Input
                      list="series-code-list"
                      value={formSeriesCode}
                      onChange={(e) => setFormSeriesCode(e.target.value)}
                      placeholder="如: A"
                    />
                    <datalist id="series-code-list">
                      {seriesOptions?.series_codes.map((code: string) => (
                        <option key={code} value={code} />
                      ))}
                    </datalist>
                  </div>
                  <div className="space-y-2 col-span-3">
                    <Label>系列名称</Label>
                    <Input
                      list="series-name-list"
                      value={formSeriesName}
                      onChange={(e) => setFormSeriesName(e.target.value)}
                      placeholder="如: 三文鱼纯享"
                    />
                    <datalist id="series-name-list">
                      {seriesOptions?.series_names.map((name: string) => (
                        <option key={name} value={name} />
                      ))}
                    </datalist>
                  </div>
                </div>
                <div className="grid grid-cols-3 gap-4">
                  <div className="space-y-2">
                    <Label>单份重量(g)</Label>
                    <Input
                      type="number"
                      value={formPortionWeight}
                      onChange={(e) => setFormPortionWeight(e.target.value)}
                      placeholder="如: 400"
                    />
                  </div>
                  <div className="space-y-2">
                    <Label>份内盒数</Label>
                    <Input
                      type="number"
                      value={formPortionBoxes}
                      onChange={(e) => setFormPortionBoxes(e.target.value)}
                      placeholder="如: 2"
                    />
                  </div>
                  <div className="space-y-2">
                    <Label>规格编码</Label>
                    <Input
                      value={formSpec}
                      onChange={(e) => setFormSpec(e.target.value)}
                      placeholder="如: A4002（留空自动生成）"
                      className="text-muted-foreground"
                    />
                  </div>
                </div>
                <div className="space-y-2">
                  <Label>单盒重量(kg)</Label>
                  <Input
                    type="number"
                    step="0.001"
                    value={formWeight}
                    onChange={(e) => setFormWeight(e.target.value)}
                    placeholder={formPortionWeight && formPortionBoxes ? `自动计算: ${(parseInt(formPortionWeight) / parseInt(formPortionBoxes) / 1000).toFixed(3)}` : "自动计算或手动填写"}
                  />
                </div>
                {/* 包装物配置 */}
                <PackagingConfigSection
                  materials={bomMaterials ?? []}
                  packagings={formPackagings}
                  onChange={setFormPackagings}
                />
              </>
            ) : (
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label>规格</Label>
                  <Input
                    value={formSpec}
                    onChange={(e) => setFormSpec(e.target.value)}
                    placeholder="如: 6-7kg"
                  />
                </div>
                <div className="space-y-2">
                  <Label>单位重量(kg)</Label>
                  <Input
                    type="number"
                    step="0.001"
                    value={formWeight}
                    onChange={(e) => setFormWeight(e.target.value)}
                    placeholder="可选"
                  />
                </div>
              </div>
            )}
            <div className="space-y-2">
              <Label>备注</Label>
              <Input
                value={formNotes}
                onChange={(e) => setFormNotes(e.target.value)}
                placeholder="其他说明..."
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setDialogOpen(false)}>
              取消
            </Button>
            <Button
              onClick={handleSubmit}
              disabled={isSubmitting}
            >
              {editingProduct ? "保存修改" : "创建产品"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* 删除确认 */}
      <Dialog open={deleteDialogOpen} onOpenChange={setDeleteDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>删除产品</DialogTitle>
            <DialogDescription>
              确定要删除产品 <strong>"{productToDelete?.name}"</strong> 吗？
              <br />
              此操作不可恢复。
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setDeleteDialogOpen(false)}>
              取消
            </Button>
            <Button variant="destructive" onClick={confirmDelete}>
              确认删除
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
