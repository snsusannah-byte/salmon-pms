import { useState, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
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
  DialogFooter,
} from "@/components/ui/dialog";
import { Plus, Search, ChevronDown, ChevronUp, Pencil, Trash2, Loader2 } from "lucide-react";
import { toast } from "sonner";
import { apiFetch, apiPost } from "@/lib/api";

interface Sku {
  id: number;
  code: string;
  name: string;
  brand_name: string;
  spec_name: string;
  price_tiers: PriceTier[];
}

interface PriceTier {
  id: number;
  tier_type: string;
  tier_key: string;
  tier_name: string;
  min_qty: number;
  max_qty: number | null;
  price: number;
}

export function SkuPricingPage() {
  const [skus, setSkus] = useState<Sku[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [openIds, setOpenIds] = useState<Set<number>>(new Set());
  const [tierDialog, setTierDialog] = useState(false);
  const [selectedSkuId, setSelectedSkuId] = useState<number | null>(null);
  const [tierForm, setTierForm] = useState({
    tier_type: "customer_level",
    tier_key: "normal",
    tier_name: "",
    min_qty: 1,
    max_qty: "",
    price: "",
  });
  const [submitting, setSubmitting] = useState(false);

  const fetchSkus = async () => {
    setLoading(true);
    const res = await apiFetch("/v1/finished-products/variants");
    const items = res.data?.items || [];
    if (res.ok && items.length > 0) {
      const enriched = await Promise.all(
        items.map(async (v: any) => {
          const tiersRes = await apiFetch(`/v1/finished-products/variants/${v.id}/price-tiers`);
          return {
            id: v.id,
            code: v.code,
            name: v.name,
            brand_name: v.brand_name || "-",
            spec_name: v.spec_name || "-",
            price_tiers: tiersRes.ok ? tiersRes.data : [],
          };
        })
      );
      setSkus(enriched);
    } else {
      setSkus([]);
    }
    setLoading(false);
  };

  useEffect(() => {
    fetchSkus();
  }, []);

  const filtered = skus.filter(
    (s) =>
      s.code.toLowerCase().includes(search.toLowerCase()) ||
      s.name.includes(search) ||
      s.brand_name.includes(search)
  );

  const toggle = (id: number) => {
    const next = new Set(openIds);
    if (next.has(id)) next.delete(id);
    else next.add(id);
    setOpenIds(next);
  };

  const openTierDialog = (skuId: number) => {
    setSelectedSkuId(skuId);
    setTierForm({
      tier_type: "customer_level",
      tier_key: "normal",
      tier_name: "",
      min_qty: 1,
      max_qty: "",
      price: "",
    });
    setTierDialog(true);
  };

  const handleCreateTier = async () => {
    if (!selectedSkuId) return;
    setSubmitting(true);
    const payload = {
      ...tierForm,
      min_qty: Number(tierForm.min_qty),
      max_qty: tierForm.max_qty ? Number(tierForm.max_qty) : null,
      price: Number(tierForm.price),
    };
    const res = await apiPost(
      `/v1/finished-products/variants/${selectedSkuId}/price-tiers`,
      payload,
      "价格层级创建成功"
    );
    setSubmitting(false);
    if (res.ok) {
      setTierDialog(false);
      fetchSkus();
    }
  };

  return (
    <div className="h-full flex flex-col gap-4 p-4">
      <div className="flex-none space-y-3">
        <div className="flex items-center justify-between">
          <h2 className="text-xl font-bold">SKU 价格配置</h2>
        </div>
        <div className="flex items-center gap-2">
          <Search className="h-4 w-4 text-muted-foreground" />
          <Input
            placeholder="搜索 SKU 编码、名称或品牌..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="max-w-sm"
          />
        </div>
      </div>

      <div className="flex-1 flex flex-col min-h-0 border rounded-lg overflow-hidden">
        <div className="flex-1 overflow-auto">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead className="sticky top-0 bg-background z-10 w-10"></TableHead>
                <TableHead className="sticky top-0 bg-background z-10">SKU</TableHead>
                <TableHead className="sticky top-0 bg-background z-10">品牌</TableHead>
                <TableHead className="sticky top-0 bg-background z-10">规格</TableHead>
                <TableHead className="sticky top-0 bg-background z-10">价格层级数</TableHead>
                <TableHead className="sticky top-0 bg-background z-10 text-right">操作</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {loading ? (
                <TableRow>
                  <TableCell colSpan={6} className="text-center py-8">
                    <Loader2 className="h-5 w-5 animate-spin mx-auto" />
                  </TableCell>
                </TableRow>
              ) : filtered.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={6} className="text-center py-8 text-muted-foreground">
                    暂无数据
                  </TableCell>
                </TableRow>
              ) : (
                filtered.map((sku) => (
                  <>
                    <TableRow key={sku.id} className="cursor-pointer" onClick={() => toggle(sku.id)}>
                      <TableCell>
                        <Button variant="ghost" size="icon" className="h-6 w-6">
                          {openIds.has(sku.id) ? (
                            <ChevronUp className="h-4 w-4" />
                          ) : (
                            <ChevronDown className="h-4 w-4" />
                          )}
                        </Button>
                      </TableCell>
                      <TableCell>
                        <div className="font-medium">{sku.name}</div>
                        <div className="text-xs text-muted-foreground">{sku.code}</div>
                      </TableCell>
                      <TableCell><Badge variant="outline">{sku.brand_name}</Badge></TableCell>
                      <TableCell><span className="text-sm">{sku.spec_name}</span></TableCell>
                      <TableCell>
                        <Badge variant={sku.price_tiers.length > 0 ? "default" : "secondary"}>
                          {sku.price_tiers.length}
                        </Badge>
                      </TableCell>
                      <TableCell className="text-right">
                        <Button
                          size="sm"
                          onClick={(e) => {
                            e.stopPropagation();
                            openTierDialog(sku.id);
                          }}
                        >
                          <Plus className="h-4 w-4 mr-1" />
                          添加价格
                        </Button>
                      </TableCell>
                    </TableRow>
                    {openIds.has(sku.id) && (
                      <TableRow className="bg-muted/30">
                        <TableCell colSpan={6} className="p-0">
                          <div className="px-4 py-3">
                            <p className="text-sm font-medium mb-2">价格层级</p>
                            {sku.price_tiers.length === 0 ? (
                              <p className="text-muted-foreground text-sm">暂无价格层级</p>
                            ) : (
                              <Table>
                                <TableHeader>
                                  <TableRow>
                                    <TableHead>类型</TableHead>
                                    <TableHead>名称</TableHead>
                                    <TableHead>起订量</TableHead>
                                    <TableHead>封顶量</TableHead>
                                    <TableHead>单价</TableHead>
                                    <TableHead className="text-right">操作</TableHead>
                                  </TableRow>
                                </TableHeader>
                                <TableBody>
                                  {sku.price_tiers.map((tier) => (
                                    <TableRow key={tier.id}>
                                      <TableCell>
                                        <Badge variant="outline">{tier.tier_type}</Badge>
                                      </TableCell>
                                      <TableCell>{tier.tier_name}</TableCell>
                                      <TableCell>{tier.min_qty}</TableCell>
                                      <TableCell>{tier.max_qty ?? "不限"}</TableCell>
                                      <TableCell className="font-medium">¥{tier.price.toFixed(2)}</TableCell>
                                      <TableCell className="text-right space-x-1">
                                        <Button variant="ghost" size="icon" disabled>
                                          <Pencil className="h-4 w-4" />
                                        </Button>
                                        <Button variant="ghost" size="icon" disabled>
                                          <Trash2 className="h-4 w-4 text-destructive" />
                                        </Button>
                                      </TableCell>
                                    </TableRow>
                                  ))}
                                </TableBody>
                              </Table>
                            )}
                          </div>
                        </TableCell>
                      </TableRow>
                    )}
                  </>
                ))
              )}
            </TableBody>
          </Table>
        </div>
        <div className="flex-none px-4 py-2 border-t bg-muted/30 text-sm text-muted-foreground">
          共 {filtered.length} 个 SKU，{filtered.reduce((sum, s) => sum + s.price_tiers.length, 0)} 条价格层级
        </div>
      </div>

      <Dialog open={tierDialog} onOpenChange={setTierDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>添加价格层级</DialogTitle>
          </DialogHeader>
          <div className="space-y-4 py-2">
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <label className="text-sm font-medium">类型</label>
                <Input
                  value={tierForm.tier_type}
                  onChange={(e) => setTierForm({ ...tierForm, tier_type: e.target.value })}
                  placeholder="customer_level / channel / volume"
                />
              </div>
              <div className="space-y-2">
                <label className="text-sm font-medium">键值</label>
                <Input
                  value={tierForm.tier_key}
                  onChange={(e) => setTierForm({ ...tierForm, tier_key: e.target.value })}
                  placeholder="vip / wholesale / bulk_100"
                />
              </div>
            </div>
            <div className="space-y-2">
              <label className="text-sm font-medium">名称</label>
              <Input
                value={tierForm.tier_name}
                onChange={(e) => setTierForm({ ...tierForm, tier_name: e.target.value })}
                placeholder="如 VIP价"
              />
            </div>
            <div className="grid grid-cols-3 gap-4">
              <div className="space-y-2">
                <label className="text-sm font-medium">起订量</label>
                <Input
                  type="number"
                  value={tierForm.min_qty}
                  onChange={(e) => setTierForm({ ...tierForm, min_qty: Number(e.target.value) })}
                />
              </div>
              <div className="space-y-2">
                <label className="text-sm font-medium">封顶量</label>
                <Input
                  type="number"
                  value={tierForm.max_qty}
                  onChange={(e) => setTierForm({ ...tierForm, max_qty: e.target.value })}
                  placeholder="留空=不限"
                />
              </div>
              <div className="space-y-2">
                <label className="text-sm font-medium">单价</label>
                <Input
                  type="number"
                  value={tierForm.price}
                  onChange={(e) => setTierForm({ ...tierForm, price: e.target.value })}
                  placeholder="¥"
                />
              </div>
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setTierDialog(false)}>取消</Button>
            <Button
              onClick={handleCreateTier}
              disabled={submitting || !tierForm.tier_name || !tierForm.price}
            >
              {submitting && <Loader2 className="h-4 w-4 mr-1 animate-spin" />}
              创建
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
