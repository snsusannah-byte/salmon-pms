import { useState, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Loader2, ChevronRight } from "lucide-react";
import { apiFetch } from "@/lib/api";

interface Series { id: number; code: string; name: string; }
interface Template { id: number; code: string; name: string; series_id: number; }
interface Spec { id: number; template_id: number; code: string; name: string; total_weight_g: number | null; box_count: number; }
interface Variant { id: number; code: string; name: string; template_id: number; spec_id: number; brand_id: number; brand_name: string; spec_name: string; cost_price: number | null; }
interface PriceTier { id: number; tier_type: string; tier_key: string; tier_name: string; min_qty: number; max_qty: number | null; price: number; }

interface SelectedProduct {
  series: Series;
  template: Template;
  spec: Spec;
  variant: Variant;
  priceTier: PriceTier | null;
}

interface ProductSelectorV2Props {
  customerLevel: string | null;
  quantity: number;
  onSelect: (product: SelectedProduct | null) => void;
}

export function ProductSelectorV2({ customerLevel, quantity, onSelect }: ProductSelectorV2Props) {
  const [seriesList, setSeriesList] = useState<Series[]>([]);
  const [templates, setTemplates] = useState<Template[]>([]);
  const [specs, setSpecs] = useState<Spec[]>([]);
  const [variants, setVariants] = useState<Variant[]>([]);
  const [tiers, setTiers] = useState<PriceTier[]>([]);
  
  const [selectedSeriesId, setSelectedSeriesId] = useState<string>("");
  const [selectedTemplateId, setSelectedTemplateId] = useState<string>("");
  const [selectedSpecId, setSelectedSpecId] = useState<string>("");
  const [selectedVariantId, setSelectedVariantId] = useState<string>("");
  
  const [loading, setLoading] = useState(false);

  // Load series on mount
  useEffect(() => {
    apiFetch("/v1/finished-products/series").then(res => {
      if (res.ok && Array.isArray(res.data)) setSeriesList(res.data);
    });
  }, []);

  // Load templates when series selected
  useEffect(() => {
    if (!selectedSeriesId) { setTemplates([]); return; }
    apiFetch("/v1/finished-products/templates").then(res => {
      if (res.ok && Array.isArray(res.data)) {
        setTemplates(res.data.filter((t: Template) => t.series_id === Number(selectedSeriesId)));
      }
    });
  }, [selectedSeriesId]);

  // Load specs when template selected
  useEffect(() => {
    if (!selectedTemplateId) { setSpecs([]); return; }
    apiFetch(`/v1/finished-products/templates/${selectedTemplateId}/specs`).then(res => {
      if (res.ok && Array.isArray(res.data)) setSpecs(res.data);
    });
  }, [selectedTemplateId]);

  // Load variants when spec selected
  useEffect(() => {
    if (!selectedSpecId) { setVariants([]); return; }
    setLoading(true);
    apiFetch("/v1/finished-products/variants").then(res => {
      if (res.ok && res.data?.items) {
        const filtered = res.data.items.filter((v: Variant) => v.spec_id === Number(selectedSpecId));
        setVariants(filtered);
      }
      setLoading(false);
    });
  }, [selectedSpecId]);

  // Load price tiers when variant selected
  useEffect(() => {
    if (!selectedVariantId) { setTiers([]); onSelect(null); return; }
    apiFetch(`/v1/finished-products/variants/${selectedVariantId}/price-tiers`).then(res => {
      if (res.ok && Array.isArray(res.data)) {
        setTiers(res.data);
        // Auto-match price tier
        const matched = matchPriceTier(res.data, customerLevel || "normal", quantity);
        const series = seriesList.find(s => s.id === Number(selectedSeriesId));
        const template = templates.find(t => t.id === Number(selectedTemplateId));
        const spec = specs.find(s => s.id === Number(selectedSpecId));
        const variant = variants.find(v => v.id === Number(selectedVariantId));
        if (series && template && spec && variant) {
          onSelect({ series, template, spec, variant, priceTier: matched });
        }
      }
    });
  }, [selectedVariantId, customerLevel, quantity]);

  function matchPriceTier(tiers: PriceTier[], level: string, qty: number): PriceTier | null {
    // 1. Exact customer_level match
    const levelMatch = tiers.filter(t => t.tier_type === "customer_level" && t.tier_key === level);
    if (levelMatch.length) return levelMatch[0];
    // 2. Volume tier match
    const volumeMatch = tiers
      .filter(t => t.tier_type === "volume" && qty >= t.min_qty && (t.max_qty === null || qty <= t.max_qty))
      .sort((a, b) => b.min_qty - a.min_qty);
    if (volumeMatch.length) return volumeMatch[0];
    // 3. Fallback to normal
    return tiers.find(t => t.tier_key === "normal") || null;
  }

  return (
    <div className="space-y-3">
      <div className="flex items-center gap-2 text-sm text-muted-foreground">
        <span>系列</span><ChevronRight className="h-3 w-3" />
        <span>SPU</span><ChevronRight className="h-3 w-3" />
        <span>规格</span><ChevronRight className="h-3 w-3" />
        <span>SKU（品牌）</span>
      </div>
      
      <div className="grid grid-cols-4 gap-2">
        <Select value={selectedSeriesId} onValueChange={v => { setSelectedSeriesId(v); setSelectedTemplateId(""); setSelectedSpecId(""); setSelectedVariantId(""); }}>
          <SelectTrigger><SelectValue placeholder="选择系列" /></SelectTrigger>
          <SelectContent>
            {seriesList.map(s => <SelectItem key={s.id} value={String(s.id)}>{s.name}</SelectItem>)}
          </SelectContent>
        </Select>

        <Select value={selectedTemplateId} onValueChange={v => { setSelectedTemplateId(v); setSelectedSpecId(""); setSelectedVariantId(""); }} disabled={!selectedSeriesId}>
          <SelectTrigger><SelectValue placeholder="选择SPU" /></SelectTrigger>
          <SelectContent>
            {templates.map(t => <SelectItem key={t.id} value={String(t.id)}>{t.name}</SelectItem>)}
          </SelectContent>
        </Select>

        <Select value={selectedSpecId} onValueChange={v => { setSelectedSpecId(v); setSelectedVariantId(""); }} disabled={!selectedTemplateId}>
          <SelectTrigger><SelectValue placeholder="选择规格" /></SelectTrigger>
          <SelectContent>
            {specs.map(s => <SelectItem key={s.id} value={String(s.id)}>{s.name} {s.total_weight_g ? `(${s.total_weight_g}g)` : ""}</SelectItem>)}
          </SelectContent>
        </Select>

        <Select value={selectedVariantId} onValueChange={setSelectedVariantId} disabled={!selectedSpecId || loading}>
          <SelectTrigger>
            {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <SelectValue placeholder="选择SKU" />}
          </SelectTrigger>
          <SelectContent>
            {variants.map(v => <SelectItem key={v.id} value={String(v.id)}>{v.brand_name} · ¥{v.cost_price || "-"}</SelectItem>)}
          </SelectContent>
        </Select>
      </div>

      {selectedVariantId && tiers.length > 0 && (
        <div className="bg-muted/30 rounded p-2 text-sm space-y-1">
          <p className="font-medium">价格层级</p>
          <div className="flex gap-2 flex-wrap">
            {tiers.map(t => (
              <Badge key={t.id} variant={t.tier_key === (customerLevel || "normal") ? "default" : "outline"}>
                {t.tier_name}: ¥{t.price.toFixed(2)}
              </Badge>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
