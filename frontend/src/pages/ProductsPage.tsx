import { useState, useEffect } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { cn } from "@/lib/utils";
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
import {
  Plus,
  Search,
  Pencil,
  Trash2,
  Eye,
  X,
  AlertTriangle,
  Package,
  Layers,
} from "lucide-react";
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
  cost_price: string | null;
  suggested_retail_price: string | null;
  wholesale_price: string | null;
  min_price: string | null;
  stock_quantity: number;
  safety_stock: number;
  brand_id: number | null;  // V3: 品牌ID
  brand_name: string | null; // V3: 品牌名称
}

interface BOMItem {
  id: number;
  material_id: number;
  material_name: string | null;
  quantity: string;
  unit: string;
  notes: string | null;
}

interface PackagingDetailItem {
  id: number;
  level: string;
  material_id: number;
  material_name: string | null;
  brand_id: number | null;
  brand_name: string | null;
  quantity: string;
  unit: string;
  notes: string | null;
}

interface ProductCostResponse {
  product_id: number;
  cost_price: string;
}

interface LowStockItem {
  id: number;
  code: string;
  name: string;
  stock_quantity: number;
  safety_stock: number;
}

const categoryLabels: Record<string, string> = {
  whole_fish: "进口规格",
  finished_product: "成品定义",
  byproduct: "副产品",
  bom_material: "BOM物料",
};

export default function ProductsPage() {
  const queryClient = useQueryClient();
  const [activeTab, setActiveTab] = useState("whole_fish");
  const [statsSearch, setStatsSearch] = useState("");
  const [search, setSearch] = useState("");
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editingProduct, setEditingProduct] = useState<Product | null>(null);
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [productToDelete, setProductToDelete] = useState<Product | null>(null);

  // 新增状态
  const [selectedIds, setSelectedIds] = useState<Set<number>>(new Set());
  const [detailDialogOpen, setDetailDialogOpen] = useState(false);
  const [detailProduct, setDetailProduct] = useState<Product | null>(null);
  const [detailTab, setDetailTab] = useState("info");
  const [filterLowStock, setFilterLowStock] = useState(false);

  // 表单状态
  const [formCategory, setFormCategory] = useState("whole_fish");
  const [formCode, setFormCode] = useState("");
  const [formName, setFormName] = useState("");
  const [formSpec, setFormSpec] = useState("");
  const [formUnit, setFormUnit] = useState("kg");
  const [formWeight, setFormWeight] = useState("");
  const [formSeriesCode, setFormSeriesCode] = useState("");
  const [formSeriesName, setFormSeriesName] = useState("");
  const [formPortionWeight, setFormPortionWeight] = useState("");
  const [formPortionBoxes, setFormPortionBoxes] = useState("");
  const [formPackagings, setFormPackagings] = useState<
    {
      id?: number;
      level: string;
      material_id: number;
      material_name?: string;
      quantity: number;
      unit: string;
      notes?: string;
    }[]
  >([]);
  // V3: 配套产品配置
  const [formAccessories, setFormAccessories] = useState<
    {
      id?: number;
      accessory_id: number;
      accessory_name?: string;
      quantity: number;
      unit: string;
    }[]
  >([]);
  const [formNotes, setFormNotes] = useState("");
  const [formIsActive, setFormIsActive] = useState(true);

  // V3: 鱼的部位配置
  interface FishPart {
    part_name: string; // 鱼腩 / 中段 / 鱼尾 / 鱼骨 等
    weight_g: number;   // 每份该部位的重量(g)
  }
  const [formFishParts, setFormFishParts] = useState<FishPart[]>([
    { part_name: "鱼腩", weight_g: 200 },
    { part_name: "中段", weight_g: 200 },
  ]);

  // V3: 品牌
  const [formBrandId, setFormBrandId] = useState("");

  const [isSubmitting, setIsSubmitting] = useState(false);

  // V3: 成品产品名称自动生成——根据鱼的部位
  useEffect(() => {
    if (formCategory === "finished_product" && !editingProduct) {
      // 计算总重量 = 各部位重量之和
      const totalWeightG = formFishParts.reduce((sum, p) => sum + (p.weight_g || 0), 0);
      // 部位描述：鱼腩200g+中段200g
      const partsDesc = formFishParts
        .filter((p) => p.part_name && p.weight_g > 0)
        .map((p) => `${p.part_name}${p.weight_g}g`)
        .join("+");
      // 规格编码
      const specCode =
        formSpec.trim() ||
        (formSeriesCode && formPortionWeight && formPortionBoxes
          ? `${formSeriesCode}${formPortionWeight}${formPortionBoxes}`
          : "");
      if (partsDesc && specCode) {
        setFormName(`${partsDesc} ${specCode}`);
      }
      // 自动计算单份重量
      if (totalWeightG > 0) {
        setFormPortionWeight(String(totalWeightG));
      }
    }
  }, [
    formCategory,
    formFishParts,
    formSeriesCode,
    formPortionWeight,
    formPortionBoxes,
    formSpec,
    editingProduct,
  ]);

  // V3: 获取品牌列表
  const { data: brandsData } = useQuery({
    queryKey: ["brands"],
    queryFn: async () => {
      const res = await api.get("/v1/brands/?limit=500");
      return res.data.items as { id: number; name: string; code: string | null; is_oem: boolean }[];
    },
  });
  const brands = brandsData || [];

  // 获取物料管理中的物料（用于成品包装物/BOM选择）
  const { data: bomMaterials } = useQuery({
    queryKey: ["bom-materials"],
    queryFn: async () => {
      const res = await api.get("/v1/materials/?limit=500");
      return res.data.items as {
        id: number;
        name: string;
        code: string;
        unit: string;
        spec: string | null;
        suppliers: { supplier_name: string | null; unit_price: number | null }[];
      }[];
    },
    enabled: dialogOpen && formCategory === "finished_product",
  });

  // V3: 获取所有产品（用于配套产品下拉选择）
  const { data: allProductsData } = useQuery({
    queryKey: ["all-products"],
    queryFn: async () => {
      const res = await api.get("/v1/products/?limit=500");
      return res.data.items as Product[];
    },
    enabled: dialogOpen && formCategory === "finished_product",
  });
  const allProducts = allProductsData || [];

  const { data: seriesOptions } = useQuery({
    queryKey: ["product-series-options"],
    queryFn: async () => {
      const res = await api.get("/v1/products/series-codes");
      return res.data as { series_codes: string[]; series_names: string[] };
    },
    enabled: dialogOpen && formCategory === "finished_product",
  });

  const { data, isLoading } = useQuery({
    queryKey: ["products", activeTab, search],
    queryFn: async () => {
      const params = new URLSearchParams();
      if (activeTab === "whole_fish") {
        params.set("categories", "whole_fish,fillet");
      } else {
        params.set("category", activeTab);
      }
      if (search) params.set("search", search);
      const res = await api.get(`/v1/products/?${params.toString()}`);
      return res.data as { total: number; items: Product[] };
    },
  });

  // 跨品牌统计查询
  const { data: statsData, isLoading: statsLoading } = useQuery({
    queryKey: ["product-stats-by-name", statsSearch],
    queryFn: async () => {
      const params = new URLSearchParams();
      params.set("category", "finished_product");
      if (statsSearch) params.set("search", statsSearch);
      const res = await api.get(`/v1/products/stats/by-name?${params.toString()}`);
      return res.data as {
        product_name: string;
        spec: string | null;
        category: string;
        unit: string;
        total_stock: number;
        total_safety_stock: number;
        brand_variants: number;
        items: {
          product_id: number;
          brand_id: number | null;
          brand_name: string | null;
          code: string;
          is_oem: boolean;
          stock_quantity: number;
          safety_stock: number;
          cost_price: number | null;
          suggested_retail_price: number | null;
        }[];
      }[];
    },
    enabled: activeTab === "stats",
  });

  const { data: lowStockData } = useQuery({
    queryKey: ["products-low-stock"],
    queryFn: async () => {
      const res = await api.get("/v1/products/low-stock");
      return res.data as LowStockItem[];
    },
    enabled: activeTab === "finished_product",
  });

  const { data: productCost } = useQuery({
    queryKey: ["product-cost", detailProduct?.id],
    queryFn: async () => {
      const res = await api.get(`/v1/products/${detailProduct!.id}/cost`);
      return res.data as ProductCostResponse;
    },
    enabled: detailDialogOpen && !!detailProduct,
  });

  const { data: productBOMs } = useQuery({
    queryKey: ["product-boms", detailProduct?.id],
    queryFn: async () => {
      const res = await api.get(`/v1/products/${detailProduct!.id}/boms`);
      return res.data as BOMItem[];
    },
    enabled: detailDialogOpen && !!detailProduct,
  });

  const { data: productPackagings } = useQuery({
    queryKey: ["product-packagings", detailProduct?.id],
    queryFn: async () => {
      const res = await api.get(
        `/v1/products/${detailProduct!.id}/packagings`
      );
      return res.data as PackagingDetailItem[];
    },
    enabled: detailDialogOpen && !!detailProduct,
  });

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

  const batchToggleMutation = useMutation({
    mutationFn: async ({
      ids,
      isActive,
    }: {
      ids: number[];
      isActive: boolean;
    }) => {
      await Promise.all(
        ids.map((id) =>
          api.put(`/v1/products/${id}`, { is_active: isActive })
        )
      );
    },
    onSuccess: () => {
      toast.success("批量操作成功");
      queryClient.invalidateQueries({ queryKey: ["products"] });
      setSelectedIds(new Set());
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.detail ?? "批量操作失败");
    },
  });

  const resetForm = () => {
    setFormCategory(activeTab);
    setFormCode("");
    setFormName(
      activeTab === "whole_fish"
        ? "挪威冰鲜三文鱼"
        : activeTab === "finished_product"
        ? ""
        : ""
    );
    setFormSpec("");
    setFormUnit("kg");
    setFormWeight("");
    setFormSeriesCode("");
    setFormSeriesName("");
    setFormPortionWeight("");
    setFormPortionBoxes("");
    setFormPackagings([]);
    setFormAccessories([]);
    setFormNotes("");
    setFormBrandId("");
    setFormIsActive(true);
    setFormFishParts([
      { part_name: "鱼腩", weight_g: 200 },
      { part_name: "中段", weight_g: 200 },
    ]);
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
    setFormBrandId(product.brand_id ? String(product.brand_id) : "");
    setFormIsActive(product.is_active);
    // V3: 加载部位数据（从名称中解析，或从 product.notes 或扩展字段）
    // 目前简单处理：默认重置
    setFormFishParts([
      { part_name: "鱼腩", weight_g: 200 },
      { part_name: "中段", weight_g: 200 },
    ]);
    // 加载包装物
    try {
      const res = await api.get(`/v1/products/${product.id}/packagings`);
      setFormPackagings(
        res.data.map((p: any) => ({
          id: p.id,
          level: p.level,
          material_id: p.material_id,
          material_name: p.material_name,
          brand_id: p.brand_id,
          brand_name: p.brand_name,
          quantity: p.quantity,
          unit: p.unit,
          notes: p.notes,
        }))
      );
    } catch {
      setFormPackagings([]);
    }
    // 加载配套产品
    try {
      const res = await api.get(`/v1/products/${product.id}/accessories`);
      setFormAccessories(
        res.data.map((a: any) => ({
          id: a.id,
          accessory_id: a.accessory_id,
          accessory_name: a.accessory_name,
          quantity: a.quantity,
          unit: a.unit,
        }))
      );
    } catch {
      setFormAccessories([]);
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
      is_active: formIsActive,
      notes: formNotes || null,
    };

    // 成品规格字段
    if (formCategory === "finished_product") {
      payload.series_code = formSeriesCode.trim() || null;
      payload.series_name = formSeriesName.trim() || null;
      payload.portion_weight_g = formPortionWeight
        ? parseInt(formPortionWeight)
        : null;
      payload.portion_boxes = formPortionBoxes
        ? parseInt(formPortionBoxes)
        : null;
      // V3: 价格/库存已删除，不提交
      payload.suggested_retail_price = null;
      payload.wholesale_price = null;
      payload.min_price = null;
      payload.stock_quantity = 0;
      payload.safety_stock = 0;
      payload.brand_id = formBrandId ? Number(formBrandId) : null;
      // 自动计算单盒重量(kg)
      if (payload.portion_weight_g && payload.portion_boxes) {
        payload.unit_weight_kg =
          payload.portion_weight_g / payload.portion_boxes / 1000;
      }
      // 自动生成规格编码
      if (
        !formSpec.trim() &&
        payload.series_code &&
        payload.portion_weight_g &&
        payload.portion_boxes
      ) {
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
      if (
        formCategory === "finished_product" &&
        formPackagings.length > 0
      ) {
        // 删除旧的（编辑模式下）
        if (editingProduct) {
          try {
            const oldRes = await api.get(
              `/v1/products/${productId}/packagings`
            );
            for (const old of oldRes.data) {
              await api.delete(
                `/v1/products/${productId}/packagings/${old.id}`
              );
            }
          } catch {
            /* ignore */
          }
        }
        // 创建新的
        for (const p of formPackagings) {
          await api.post(`/v1/products/${productId}/packagings`, {
            level: p.level,
            material_id: p.material_id,
            brand_id: p.brand_id || null,
            quantity: p.quantity,
            unit: p.unit || "个",
            notes: p.notes || null,
          });
        }
      }

      // 保存配套产品
      if (
        formCategory === "finished_product" &&
        formAccessories.length > 0
      ) {
        // 删除旧的（编辑模式下）
        if (editingProduct) {
          try {
            const oldRes = await api.get(
              `/v1/products/${productId}/accessories`
            );
            for (const old of oldRes.data) {
              await api.delete(
                `/v1/products/${productId}/accessories/${old.id}`
              );
            }
          } catch {
            /* ignore */
          }
        }
        // 创建新的
        for (const a of formAccessories) {
          await api.post(`/v1/products/${productId}/accessories`, {
            accessory_id: a.accessory_id,
            quantity: a.quantity,
            unit: a.unit || "个",
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

  const handleView = (product: Product) => {
    setDetailProduct(product);
    setDetailTab("info");
    setDetailDialogOpen(true);
  };

  const toggleSelect = (id: number) => {
    const next = new Set(selectedIds);
    if (next.has(id)) {
      next.delete(id);
    } else {
      next.add(id);
    }
    setSelectedIds(next);
  };

  const toggleSelectAll = () => {
    const visibleIds = filteredItems.map((p) => p.id);
    const allSelected = visibleIds.every((id) => selectedIds.has(id));
    if (allSelected) {
      const next = new Set(selectedIds);
      visibleIds.forEach((id) => next.delete(id));
      setSelectedIds(next);
    } else {
      const next = new Set(selectedIds);
      visibleIds.forEach((id) => next.add(id));
      setSelectedIds(next);
    }
  };

  const handleBatchEnable = () => {
    if (selectedIds.size === 0) return;
    batchToggleMutation.mutate({
      ids: Array.from(selectedIds),
      isActive: true,
    });
  };

  const handleBatchDisable = () => {
    if (selectedIds.size === 0) return;
    batchToggleMutation.mutate({
      ids: Array.from(selectedIds),
      isActive: false,
    });
  };

  const isLowStock = (product: Product) =>
    product.stock_quantity < product.safety_stock && product.safety_stock > 0;

  const filteredItems =
    data?.items.filter((product) => {
      if (!filterLowStock) return true;
      return isLowStock(product);
    }) ?? [];

  const lowStockCount =
    activeTab === "finished_product"
      ? (lowStockData?.length ?? data?.items.filter(isLowStock).length ?? 0)
      : 0;

  const renderTableColumns = () => {
    if (activeTab === "finished_product") {
      return (
        <>
          <TableHead className="w-[40px]">
            <input
              type="checkbox"
              className="h-4 w-4 rounded border-gray-300"
              checked={
                filteredItems.length > 0 &&
                filteredItems.every((p) => selectedIds.has(p.id))
              }
              onChange={toggleSelectAll}
            />
          </TableHead>
          <TableHead>编码</TableHead>
          <TableHead>名称</TableHead>
          <TableHead>品牌</TableHead>
          <TableHead>规格</TableHead>
          <TableHead>单位</TableHead>
          <TableHead>重量(kg)</TableHead>
          <TableHead>状态</TableHead>
          <TableHead>操作</TableHead>
        </>
      );
    }
    return (
      <>
        <TableHead className="w-[40px]">
          <input
            type="checkbox"
            className="h-4 w-4 rounded border-gray-300"
            checked={
              filteredItems.length > 0 &&
              filteredItems.every((p) => selectedIds.has(p.id))
            }
            onChange={toggleSelectAll}
          />
        </TableHead>
        <TableHead>编码</TableHead>
        <TableHead>名称</TableHead>
        <TableHead>规格</TableHead>
        <TableHead>单位</TableHead>
        <TableHead>重量(kg)</TableHead>
        <TableHead>状态</TableHead>
        <TableHead>操作</TableHead>
      </>
    );
  };

  const renderProductRow = (product: Product) => {
    const lowStock = isLowStock(product);
    const inactive = !product.is_active;
    const rowClass = cn(
      lowStock && "bg-red-50",
      inactive && "opacity-60 bg-gray-50"
    );

    if (activeTab === "finished_product") {
      return (
        <TableRow key={product.id} className={rowClass}>
          <TableCell>
            <input
              type="checkbox"
              className="h-4 w-4 rounded border-gray-300"
              checked={selectedIds.has(product.id)}
              onChange={() => toggleSelect(product.id)}
            />
          </TableCell>
          <TableCell className="font-medium text-muted-foreground text-xs">
            {product.code}
          </TableCell>
          <TableCell>{product.name}</TableCell>
          <TableCell>
            {product.brand_name ? (
              <Badge variant="outline" className="text-xs">{product.brand_name}</Badge>
            ) : (
              <span className="text-xs text-muted-foreground">-</span>
            )}
          </TableCell>
          <TableCell>
            {product.category === "finished_product" &&
            (product.series_code || product.portion_weight_g) ? (
              <div className="text-xs space-y-0.5">
                <div className="font-medium">
                  {product.series_code}
                  {product.portion_weight_g}
                  {product.portion_boxes ?? ""}
                </div>
                {product.series_name && (
                  <div className="text-muted-foreground">
                    {product.series_name}
                  </div>
                )}
                {product.portion_weight_g && product.portion_boxes && (
                  <div className="text-muted-foreground">
                    {product.portion_weight_g}g/{product.portion_boxes}盒(
                    {Math.round(
                      product.portion_weight_g / product.portion_boxes
                    )}
                    g/盒)
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
              <Badge
                variant="secondary"
                className="bg-green-100 text-green-800"
              >
                启用
              </Badge>
            ) : (
              <Badge
                variant="secondary"
                className="bg-gray-100 text-gray-800"
              >
                停用
              </Badge>
            )}
          </TableCell>
          <TableCell>
            <div className="flex gap-1">
              <Button
                variant="ghost"
                size="icon"
                className="h-8 w-8"
                onClick={() => handleView(product)}
                title="查看"
              >
                <Eye className="h-4 w-4" />
              </Button>
              <Button
                variant="ghost"
                size="icon"
                className="h-8 w-8"
                onClick={() => openEditDialog(product)}
                title="编辑"
              >
                <Pencil className="h-4 w-4" />
              </Button>
              <Button
                variant="ghost"
                size="icon"
                className="h-8 w-8 text-red-500"
                onClick={() => handleDelete(product)}
                title="删除"
              >
                <Trash2 className="h-4 w-4" />
              </Button>
            </div>
          </TableCell>
        </TableRow>
      );
    }

    return (
      <TableRow key={product.id} className={rowClass}>
        <TableCell>
          <input
            type="checkbox"
            className="h-4 w-4 rounded border-gray-300"
            checked={selectedIds.has(product.id)}
            onChange={() => toggleSelect(product.id)}
          />
        </TableCell>
        <TableCell className="font-medium text-muted-foreground text-xs">
          {product.code}
        </TableCell>
        <TableCell>{product.name}</TableCell>
        <TableCell>
          {product.category === "finished_product" &&
          (product.series_code || product.portion_weight_g) ? (
            <div className="text-xs space-y-0.5">
              <div className="font-medium">
                {product.series_code}
                {product.portion_weight_g}
                {product.portion_boxes ?? ""}
              </div>
              {product.series_name && (
                <div className="text-muted-foreground">
                  {product.series_name}
                </div>
              )}
              {product.portion_weight_g && product.portion_boxes && (
                <div className="text-muted-foreground">
                  {product.portion_weight_g}g/{product.portion_boxes}盒(
                  {Math.round(
                    product.portion_weight_g / product.portion_boxes
                  )}
                  g/盒)
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
            <Badge
              variant="secondary"
              className="bg-green-100 text-green-800"
            >
              启用
            </Badge>
          ) : (
            <Badge
              variant="secondary"
              className="bg-gray-100 text-gray-800"
            >
              停用
            </Badge>
          )}
        </TableCell>
        <TableCell>
          <div className="flex gap-1">
            <Button
              variant="ghost"
              size="icon"
              className="h-8 w-8"
              onClick={() => handleView(product)}
              title="查看"
            >
              <Eye className="h-4 w-4" />
            </Button>
            <Button
              variant="ghost"
              size="icon"
              className="h-8 w-8"
              onClick={() => openEditDialog(product)}
              title="编辑"
            >
              <Pencil className="h-4 w-4" />
            </Button>
            <Button
              variant="ghost"
              size="icon"
              className="h-8 w-8 text-red-500"
              onClick={() => handleDelete(product)}
              title="删除"
            >
              <Trash2 className="h-4 w-4" />
            </Button>
          </div>
        </TableCell>
      </TableRow>
    );
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

      <Tabs
        value={activeTab}
        onValueChange={(v) => {
          setActiveTab(v);
          setSelectedIds(new Set());
          setFilterLowStock(false);
        }}
      >
        <TabsList className="grid w-full grid-cols-4">
          <TabsTrigger value="whole_fish">进口规格</TabsTrigger>
          <TabsTrigger value="finished_product">成品定义</TabsTrigger>
          <TabsTrigger value="byproduct">副产品</TabsTrigger>
          <TabsTrigger value="stats">跨品牌统计</TabsTrigger>
        </TabsList>

        {["whole_fish", "finished_product", "byproduct"].map(
          (cat) => (
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

              {/* 低库存预警横幅 */}
              {cat === "finished_product" && lowStockCount > 0 && (
                <button
                  onClick={() => setFilterLowStock((v) => !v)}
                  className={cn(
                    "w-full flex items-center gap-2 px-4 py-3 rounded-lg border text-sm transition-colors",
                    filterLowStock
                      ? "bg-red-100 border-red-300 text-red-800"
                      : "bg-red-50 border-red-200 text-red-700 hover:bg-red-100"
                  )}
                >
                  <AlertTriangle className="h-4 w-4" />
                  <span className="font-medium">
                    {lowStockCount}个产品库存低于安全线
                  </span>
                  <span className="ml-auto text-xs underline">
                    {filterLowStock ? "显示全部" : "仅看低库存"}
                  </span>
                </button>
              )}

              {/* 批量操作栏 */}
              {selectedIds.size > 0 && (
                <div className="flex items-center gap-3 px-4 py-2 bg-muted rounded-lg border">
                  <span className="text-sm text-muted-foreground">
                    已选中 {selectedIds.size} 个产品
                  </span>
                  <div className="ml-auto flex gap-2">
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={handleBatchEnable}
                      disabled={batchToggleMutation.isPending}
                    >
                      批量启用
                    </Button>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={handleBatchDisable}
                      disabled={batchToggleMutation.isPending}
                    >
                      批量停用
                    </Button>
                  </div>
                </div>
              )}

              <div className="border rounded-lg">
                <Table>
                  <TableHeader>
                    <TableRow>{renderTableColumns()}</TableRow>
                  </TableHeader>
                  <TableBody>
                    {isLoading ? (
                      <TableRow>
                        <TableCell
                          colSpan={8}
                          className="text-center py-8"
                        >
                          加载中...
                        </TableCell>
                      </TableRow>
                    ) : filteredItems.length === 0 ? (
                      <TableRow>
                        <TableCell
                          colSpan={8}
                          className="text-center py-8 text-muted-foreground"
                        >
                          暂无数据
                        </TableCell>
                      </TableRow>
                    ) : (
                      filteredItems.map((product) =>
                        renderProductRow(product)
                      )
                    )}
                  </TableBody>
                </Table>
              </div>
            </TabsContent>
          )
        )}

        {/* 跨品牌统计Tab */}
        <TabsContent value="stats" className="space-y-4">
          <div className="flex items-center gap-2">
            <div className="relative flex-1 max-w-sm">
              <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
              <Input
                placeholder="搜索产品名称..."
                value={statsSearch}
                onChange={(e) => setStatsSearch(e.target.value)}
                className="pl-9"
              />
            </div>
          </div>
          {statsLoading ? (
            <div className="text-center py-8">加载中...</div>
          ) : !statsData || statsData.length === 0 ? (
            <div className="text-center py-8 text-muted-foreground">
              暂无数据，请先创建成品定义
            </div>
          ) : (
            <div className="space-y-4">
              {statsData.map((stat) => (
                <div key={stat.product_name} className="border rounded-lg p-4 space-y-3">
                  <div className="flex items-center justify-between">
                    <div>
                      <h3 className="font-bold text-lg">{stat.product_name}</h3>
                      {stat.spec && <p className="text-sm text-muted-foreground">{stat.spec}</p>}
                    </div>
                    <div className="text-right">
                      <div className="text-2xl font-bold">{stat.total_stock}</div>
                      <div className="text-xs text-muted-foreground">总库存 {stat.unit}</div>
                    </div>
                  </div>
                  <div className="grid grid-cols-3 gap-2">
                    {stat.items.map((item) => (
                      <div key={item.product_id} className="bg-muted/50 rounded p-3 space-y-1">
                        <div className="flex items-center gap-2">
                          <span className="font-medium text-sm">{item.brand_name ?? "无品牌"}</span>
                          {item.is_oem && (
                            <Badge variant="secondary" className="text-[10px] bg-purple-100 text-purple-700">OEM</Badge>
                          )}
                        </div>
                        <div className="text-xs text-muted-foreground">{item.code}</div>
                        <div className="flex justify-between text-sm">
                          <span>库存: {item.stock_quantity}</span>
                          <span>安全: {item.safety_stock}</span>
                        </div>
                        {item.cost_price && (
                          <div className="text-xs text-muted-foreground">成本: ¥{item.cost_price.toFixed(2)}</div>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          )}
        </TabsContent>
      </Tabs>

      {/* ==================== 新增/编辑弹窗 ==================== */}
      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <DialogContent className="max-w-[95vw] xl:max-w-[1100px] max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>
              {editingProduct ? "编辑产品" : "新增产品"}
            </DialogTitle>
          </DialogHeader>
          <div className="space-y-5 py-4">
            {/* === 基础信息 === */}
            <div className="grid grid-cols-3 gap-4">
              <div className="space-y-2">
                <Label>产品分类</Label>
                <Select value={formCategory} onValueChange={(v) => setFormCategory(v || "whole_fish")}>
                  <SelectTrigger><SelectValue placeholder="选择分类">{categoryLabels[formCategory]}</SelectValue></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="whole_fish">进口规格</SelectItem>
                    <SelectItem value="finished_product">成品定义</SelectItem>
                    <SelectItem value="byproduct">副产品</SelectItem>
                    <SelectItem value="bom_material">BOM物料</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-2">
                <Label>产品编码</Label>
                <Input value={formCode} onChange={(e) => setFormCode(e.target.value)} placeholder="留空自动生成" className="text-muted-foreground" />
              </div>
              <div className="space-y-2">
                <Label>单位</Label>
                <Select value={formUnit} onValueChange={(v) => setFormUnit(v || "kg")}>
                  <SelectTrigger><SelectValue /></SelectTrigger>
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
            <div className="space-y-2">
              <Label>产品名称 *</Label>
              <Input value={formName} onChange={(e) => setFormName(e.target.value)} placeholder="如: 鱼腩200g+中段200g A4002" />
            </div>

            {formCategory === "finished_product" ? (
              <>
                {/* === 成品定义：宽卡片布局 === */}
                {/* 第一行：系列信息 */}
                <div className="bg-muted/30 rounded-lg p-4 space-y-4">
                  <h4 className="text-sm font-semibold flex items-center gap-2">📦 系列规格</h4>
                  <div className="grid grid-cols-4 gap-4">
                    <div className="space-y-2">
                      <Label>系列代号</Label>
                      <Input list="series-code-list" value={formSeriesCode} onChange={(e) => setFormSeriesCode(e.target.value)} placeholder="如: A" />
                      <datalist id="series-code-list">{seriesOptions?.series_codes.map((code: string) => <option key={code} value={code} />)}</datalist>
                    </div>
                    <div className="space-y-2">
                      <Label>系列名称</Label>
                      <Input list="series-name-list" value={formSeriesName} onChange={(e) => setFormSeriesName(e.target.value)} placeholder="如: 三文鱼纯享" />
                      <datalist id="series-name-list">{seriesOptions?.series_names.map((name: string) => <option key={name} value={name} />)}</datalist>
                    </div>
                    <div className="space-y-2">
                      <Label>份内盒数</Label>
                      <Input type="number" value={formPortionBoxes} onChange={(e) => setFormPortionBoxes(e.target.value)} placeholder="如: 2" />
                    </div>
                    <div className="space-y-2">
                      <Label>规格编码</Label>
                      <Input value={formSpec} onChange={(e) => setFormSpec(e.target.value)} placeholder="如: A4002（留空自动生成）" className="text-muted-foreground" />
                    </div>
                  </div>
                </div>

                {/* 第二行：品牌 + 部位 */}
                <div className="grid grid-cols-3 gap-4">
                  {/* 品牌 */}
                  <div className="bg-muted/30 rounded-lg p-4 space-y-3">
                    <h4 className="text-sm font-semibold">🏷️ 品牌</h4>
                    <div className="space-y-2">
                      <Label>品牌名称</Label>
                      <Select value={formBrandId} onValueChange={(v) => setFormBrandId(v ?? "")}>
                        <SelectTrigger>
                          <SelectValue placeholder="选择品牌">
                            {(() => {
                              const selected = brands.find((b) => String(b.id) === formBrandId);
                              return selected ? selected.name : "选择品牌";
                            })()}
                          </SelectValue>
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="">无品牌</SelectItem>
                          {brands.map((b) => (
                            <SelectItem key={b.id} value={String(b.id)}>
                              <div className="flex items-center gap-2">
                                {b.name}
                                {b.is_oem && <Badge variant="secondary" className="text-[10px] bg-purple-100 text-purple-700">OEM</Badge>}
                              </div>
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    </div>
                    <p className="text-xs text-muted-foreground">品牌关联公司名称，一个公司可有多个品牌</p>
                  </div>

                  {/* 鱼的部位配置 — 占两列更宽 */}
                  <div className="bg-muted/30 rounded-lg p-4 space-y-3 col-span-2">
                    <div className="flex items-center justify-between">
                      <h4 className="text-sm font-semibold">🐟 鱼的部位配置</h4>
                      <span className="text-xs text-muted-foreground">
                        总重量: {formFishParts.reduce((s, p) => s + (p.weight_g || 0), 0)}g
                      </span>
                    </div>
                    <div className="space-y-2">
                      {formFishParts.map((part, idx) => (
                        <div key={idx} className="flex items-center gap-3">
                          <Select value={part.part_name} onValueChange={(v) => {
                            const newParts = [...formFishParts];
                            newParts[idx] = { ...part, part_name: v || "" };
                            setFormFishParts(newParts);
                          }}>
                            <SelectTrigger className="w-[150px] h-10"><SelectValue placeholder="选择部位" /></SelectTrigger>
                            <SelectContent>
                              <SelectItem value="鱼腩">鱼腩</SelectItem>
                              <SelectItem value="中段">中段</SelectItem>
                              <SelectItem value="鱼尾">鱼尾</SelectItem>
                              <SelectItem value="鱼骨">鱼骨</SelectItem>
                              <SelectItem value="鱼头">鱼头</SelectItem>
                              <SelectItem value="鱼皮">鱼皮</SelectItem>
                              <SelectItem value="纯肉">纯肉</SelectItem>
                            </SelectContent>
                          </Select>
                          <Input type="number" className="h-10 flex-1" value={part.weight_g || ""} onChange={(e) => {
                            const newParts = [...formFishParts];
                            newParts[idx] = { ...part, weight_g: Number(e.target.value) || 0 };
                            setFormFishParts(newParts);
                          }} placeholder="每份重量(g)" />
                          <span className="text-sm text-muted-foreground w-8">g</span>
                          <Button variant="ghost" size="icon" className="h-8 w-8 text-red-500 shrink-0" onClick={() => setFormFishParts(formFishParts.filter((_, i) => i !== idx))}>
                            <Trash2 className="h-4 w-4" />
                          </Button>
                        </div>
                      ))}
                      <Button variant="outline" size="sm" className="w-full mt-1" onClick={() => setFormFishParts([...formFishParts, { part_name: "", weight_g: 0 }])}>
                        <Plus className="h-4 w-4 mr-1" />添加部位
                      </Button>
                    </div>
                    {/* 名称预览 */}
                    {formFishParts.filter(p => p.part_name && p.weight_g > 0).length > 0 && (
                      <div className="bg-blue-50 border border-blue-200 rounded-md p-2 text-sm">
                        <span className="text-muted-foreground">名称预览:</span>{" "}
                        <span className="font-medium text-blue-800">
                          {formFishParts.filter((p) => p.part_name && p.weight_g > 0).map((p) => `${p.part_name}${p.weight_g}g`).join("+")}{" "}
                          {formSpec || (formSeriesCode && formPortionWeight && formPortionBoxes ? `${formSeriesCode}${formPortionWeight}${formPortionBoxes}` : "")}
                        </span>
                      </div>
                    )}
                  </div>
                </div>

                {/* 单盒重量 */}
                <div className="space-y-2">
                  <Label>单盒重量(kg)</Label>
                  <Input type="number" step="0.001" value={formWeight} onChange={(e) => setFormWeight(e.target.value)}
                    placeholder={formPortionWeight && formPortionBoxes ? `自动计算: ${(parseInt(formPortionWeight) / parseInt(formPortionBoxes) / 1000).toFixed(3)}` : "自动计算或手动填写"}
                  />
                </div>

                {/* 配套产品配置 */}
                <div className="bg-muted/30 rounded-lg p-4 space-y-3">
                  <div className="flex items-center justify-between">
                    <h4 className="text-sm font-semibold">🍤 配套产品</h4>
                    <span className="text-xs text-muted-foreground">每份成品包含的附加产品</span>
                  </div>
                  <div className="space-y-2">
                    {formAccessories.map((acc, idx) => (
                      <div key={idx} className="flex items-center gap-3">
                        <Select
                          value={String(acc.accessory_id)}
                          onValueChange={(v) => {
                            const newAcc = [...formAccessories];
                            const selected = allProducts.find((p: any) => String(p.id) === (v ?? ""));
                            newAcc[idx] = {
                              ...acc,
                              accessory_id: Number(v) || 0,
                              accessory_name: selected?.name,
                              unit: selected?.unit || "个",
                            };
                            setFormAccessories(newAcc);
                          }}
                        >
                          <SelectTrigger className="flex-1 h-10">
                            <SelectValue placeholder="选择配套产品" />
                          </SelectTrigger>
                          <SelectContent>
                            {(bomMaterials ?? [])
                              .map((p: any) => (
                                <SelectItem key={p.id} value={String(p.id)}>
                                  <div className="flex flex-col">
                                    <span>{p.name} ({p.code})</span>
                                    {p.suppliers && p.suppliers.length > 0 && (
                                      <span className="text-[10px] text-muted-foreground">
                                        {p.suppliers[0].supplier_name} ¥{p.suppliers[0].unit_price?.toFixed(2) ?? '-'}
                                      </span>
                                    )}
                                  </div>
                                </SelectItem>
                              ))}
                          </SelectContent>
                        </Select>
                        <Input
                          type="number"
                          className="w-24 h-10"
                          value={acc.quantity || ""}
                          onChange={(e) => {
                            const newAcc = [...formAccessories];
                            newAcc[idx] = { ...acc, quantity: Number(e.target.value) || 0 };
                            setFormAccessories(newAcc);
                          }}
                          placeholder="数量"
                        />
                        <span className="text-sm text-muted-foreground w-10">{acc.unit || "个"}</span>
                        <Button
                          variant="ghost"
                          size="icon"
                          className="h-8 w-8 text-red-500 shrink-0"
                          onClick={() => setFormAccessories(formAccessories.filter((_, i) => i !== idx))}
                        >
                          <Trash2 className="h-4 w-4" />
                        </Button>
                      </div>
                    ))}
                    <Button
                      variant="outline"
                      size="sm"
                      className="w-full mt-1"
                      onClick={() =>
                        setFormAccessories([...formAccessories, { accessory_id: 0, quantity: 0, unit: "个" }])
                      }
                    >
                      <Plus className="h-4 w-4 mr-1" />
                      添加配套产品
                    </Button>
                  </div>
                </div>

                {/* 包装物配置 */}
                <PackagingConfigSection materials={bomMaterials ?? []} brands={brands} packagings={formPackagings} onChange={setFormPackagings} />
              </>
            ) : (
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2"><Label>规格</Label><Input value={formSpec} onChange={(e) => setFormSpec(e.target.value)} placeholder="如: 6-7kg" /></div>
                <div className="space-y-2"><Label>单位重量(kg)</Label><Input type="number" step="0.001" value={formWeight} onChange={(e) => setFormWeight(e.target.value)} placeholder="可选" /></div>
              </div>
            )}
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label>产品状态</Label>
                <Select value={formIsActive ? "active" : "inactive"} onValueChange={(v) => setFormIsActive(v === "active")}>
                  <SelectTrigger><SelectValue /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="active">启用</SelectItem>
                    <SelectItem value="inactive">停用</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>
            <div className="space-y-2">
              <Label>备注</Label>
              <Input value={formNotes} onChange={(e) => setFormNotes(e.target.value)} placeholder="其他说明..." />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setDialogOpen(false)}>取消</Button>
            <Button onClick={handleSubmit} disabled={isSubmitting}>{editingProduct ? "保存修改" : "创建产品"}</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* ==================== 详情弹窗 ==================== */}
      <Dialog open={detailDialogOpen} onOpenChange={setDetailDialogOpen}>
        <DialogContent className="max-w-[700px] max-h-[90vh] overflow-y-auto">
          <DialogHeader className="pb-4 border-b flex flex-row items-center justify-between">
            <div>
              <DialogTitle>产品详情</DialogTitle>
              <DialogDescription>
                {detailProduct?.code} · {detailProduct?.name}
              </DialogDescription>
            </div>
            <Button
              variant="ghost"
              size="icon"
              className="h-8 w-8"
              onClick={() => setDetailDialogOpen(false)}
            >
              <X className="h-4 w-4" />
            </Button>
          </DialogHeader>

          {detailProduct && (
            <div className="py-4">
              <Tabs value={detailTab} onValueChange={setDetailTab}>
                <TabsList className="grid w-full grid-cols-3">
                  <TabsTrigger value="info">
                    <Package className="h-3 w-3 mr-1" />
                    基本信息
                  </TabsTrigger>
                  <TabsTrigger value="bom">
                    <Layers className="h-3 w-3 mr-1" />
                    BOM成本
                  </TabsTrigger>
                  <TabsTrigger value="packaging">
                    <Package className="h-3 w-3 mr-1" />
                    包装物成本
                  </TabsTrigger>
                </TabsList>

                {/* 基本信息Tab */}
                <TabsContent value="info" className="space-y-4 pt-4">
                  <div className="grid grid-cols-2 gap-3 text-sm">
                    <div>
                      <span className="text-muted-foreground">分类:</span>{" "}
                      <span className="ml-1">
                        {categoryLabels[detailProduct.category]}
                      </span>
                    </div>
                    <div>
                      <span className="text-muted-foreground">编码:</span>{" "}
                      <span className="ml-1">{detailProduct.code}</span>
                    </div>
                    <div>
                      <span className="text-muted-foreground">名称:</span>{" "}
                      <span className="ml-1">{detailProduct.name}</span>
                    </div>
                    <div>
                      <span className="text-muted-foreground">规格:</span>{" "}
                      <span className="ml-1">
                        {detailProduct.spec ?? "-"}
                      </span>
                    </div>
                    <div>
                      <span className="text-muted-foreground">单位:</span>{" "}
                      <span className="ml-1">{detailProduct.unit}</span>
                    </div>
                    <div>
                      <span className="text-muted-foreground">
                        单位重量(kg):
                      </span>{" "}
                      <span className="ml-1">
                        {detailProduct.unit_weight_kg ?? "-"}
                      </span>
                    </div>
                    <div>
                      <span className="text-muted-foreground">状态:</span>{" "}
                      <span className="ml-1">
                        {detailProduct.is_active ? (
                          <Badge
                            variant="secondary"
                            className="bg-green-100 text-green-800"
                          >
                            启用
                          </Badge>
                        ) : (
                          <Badge
                            variant="secondary"
                            className="bg-gray-100 text-gray-800"
                          >
                            停用
                          </Badge>
                        )}
                      </span>
                    </div>
                  </div>

                  {detailProduct.category === "finished_product" && (
                    <div className="border-t pt-3">
                      <h4 className="text-sm font-semibold mb-2">
                        成品规格
                      </h4>
                      <div className="grid grid-cols-2 gap-3 text-sm">
                        <div>
                          <span className="text-muted-foreground">系列代号:</span>{" "}
                          <span className="ml-1">
                            {detailProduct.series_code ?? "-"}
                          </span>
                        </div>
                        <div>
                          <span className="text-muted-foreground">系列名称:</span>{" "}
                          <span className="ml-1">
                            {detailProduct.series_name ?? "-"}
                          </span>
                        </div>
                        <div>
                          <span className="text-muted-foreground">品牌:</span>{" "}
                          <span className="ml-1">
                            {detailProduct.brand_name ? (
                              <Badge variant="outline" className="text-xs">{detailProduct.brand_name}</Badge>
                            ) : "-"}
                          </span>
                        </div>
                        <div>
                          <span className="text-muted-foreground">单份重量(g):</span>{" "}
                          <span className="ml-1">
                            {detailProduct.portion_weight_g ?? "-"}
                          </span>
                        </div>
                        <div>
                          <span className="text-muted-foreground">份内盒数:</span>{" "}
                          <span className="ml-1">
                            {detailProduct.portion_boxes ?? "-"}
                          </span>
                        </div>
                      </div>
                    </div>
                  )}
                </TabsContent>

                {/* BOM成本Tab */}
                <TabsContent value="bom" className="pt-4 space-y-4">
                  {productBOMs && productBOMs.length > 0 ? (
                    <Table>
                      <TableHeader>
                        <TableRow>
                          <TableHead className="text-xs">物料</TableHead>
                          <TableHead className="text-xs">用量</TableHead>
                          <TableHead className="text-xs">单位</TableHead>
                          <TableHead className="text-xs">备注</TableHead>
                        </TableRow>
                      </TableHeader>
                      <TableBody>
                        {productBOMs.map((bom) => (
                          <TableRow key={bom.id}>
                            <TableCell className="text-sm">
                              {bom.material_name ?? "未知物料"}
                            </TableCell>
                            <TableCell className="text-sm">
                              {bom.quantity}
                            </TableCell>
                            <TableCell className="text-sm">
                              {bom.unit}
                            </TableCell>
                            <TableCell className="text-sm">
                              {bom.notes ?? "-"}
                            </TableCell>
                          </TableRow>
                        ))}
                      </TableBody>
                    </Table>
                  ) : (
                    <div className="text-sm text-muted-foreground text-center py-8">
                      暂无BOM配置
                    </div>
                  )}
                  <div className="bg-muted p-3 rounded-md text-sm">
                    <div className="flex justify-between font-semibold">
                      <span>BOM物料总数</span>
                      <span>{productBOMs?.length ?? 0} 项</span>
                    </div>
                  </div>
                </TabsContent>

                {/* 包装物成本Tab */}
                <TabsContent value="packaging" className="pt-4 space-y-4">
                  {productPackagings && productPackagings.length > 0 ? (
                    <Table>
                      <TableHeader>
                        <TableRow>
                          <TableHead className="text-xs">层级</TableHead>
                          <TableHead className="text-xs">物料</TableHead>
                          <TableHead className="text-xs">用量</TableHead>
                          <TableHead className="text-xs">单位</TableHead>
                          <TableHead className="text-xs">备注</TableHead>
                        </TableRow>
                      </TableHeader>
                      <TableBody>
                        {productPackagings.map((pkg) => (
                          <TableRow key={pkg.id}>
                            <TableCell className="text-sm">
                              {pkg.level === "box" ? "盒级" : "份级"}
                            </TableCell>
                            <TableCell className="text-sm">
                              {pkg.material_name ?? "未知物料"}
                            </TableCell>
                            <TableCell className="text-sm">
                              {pkg.quantity}
                            </TableCell>
                            <TableCell className="text-sm">
                              {pkg.unit}
                            </TableCell>
                            <TableCell className="text-sm">
                              {pkg.notes ?? "-"}
                            </TableCell>
                          </TableRow>
                        ))}
                      </TableBody>
                    </Table>
                  ) : (
                    <div className="text-sm text-muted-foreground text-center py-8">
                      暂无包装物配置
                    </div>
                  )}
                  <div className="bg-muted p-3 rounded-md text-sm">
                    <div className="flex justify-between font-semibold">
                      <span>包装物总数</span>
                      <span>{productPackagings?.length ?? 0} 项</span>
                    </div>
                  </div>
                </TabsContent>
              </Tabs>

              {/* 成本汇总 */}
              {detailProduct.category === "finished_product" && (
                <div className="border-t pt-4 mt-4">
                  <h4 className="text-sm font-semibold mb-2 flex items-center gap-2">
                    <Package className="h-4 w-4" />
                    成本汇总
                  </h4>
                  <div className="bg-muted p-3 rounded-md space-y-2 text-sm">
                    <div className="flex justify-between">
                      <span className="text-muted-foreground">BOM物料项</span>
                      <span>{productBOMs?.length ?? 0} 项</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-muted-foreground">
                        包装物项
                      </span>
                      <span>{productPackagings?.length ?? 0} 项</span>
                    </div>
                    <div className="flex justify-between font-semibold border-t pt-2">
                      <span>系统计算总成本</span>
                      <span className="text-primary">
                        {productCost?.cost_price ??
                          detailProduct.cost_price ??
                          "-"}
                      </span>
                    </div>
                  </div>
                </div>
              )}
            </div>
          )}
        </DialogContent>
      </Dialog>

      {/* 删除确认 */}
      <Dialog open={deleteDialogOpen} onOpenChange={setDeleteDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>删除产品</DialogTitle>
            <DialogDescription>
              确定要删除产品{" "}
              <strong>"{productToDelete?.name}"</strong> 吗？
              <br />
              此操作不可恢复。
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => setDeleteDialogOpen(false)}
            >
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
