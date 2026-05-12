import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from "@/components/ui/table";
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from "@/components/ui/select";
import { Badge } from "@/components/ui/badge";
import { Plus, Trash2 } from "lucide-react";

interface PackagingItem {
  id?: number;
  level: string;
  material_id: number;
  material_name?: string;
  brand_id?: number;
  brand_name?: string;
  quantity: number;
  unit: string;
  notes?: string;
}

interface MaterialOption {
  id: number;
  name: string;
  code: string;
  unit: string;
  spec?: string | null;
  suppliers?: { supplier_name: string | null; unit_price: number | null }[];
}

interface BrandOption {
  id: number;
  name: string;
  is_oem: boolean;
}

interface PackagingConfigSectionProps {
  materials: MaterialOption[];
  brands: BrandOption[];
  packagings: PackagingItem[];
  onChange: (items: PackagingItem[]) => void;
}

export function PackagingConfigSection({ materials, brands, packagings, onChange }: PackagingConfigSectionProps) {
  const addItem = (level: string) => {
    onChange([
      ...packagings,
      { level, material_id: 0, quantity: 1, unit: "个" },
    ]);
  };

  const removeItem = (index: number) => {
    const next = packagings.filter((_, i) => i !== index);
    onChange(next);
  };

  const updateItem = (index: number, field: keyof PackagingItem, value: any) => {
    const next = packagings.map((item, i) => {
      if (i !== index) return item;
      if (field === "material_id") {
        const mat = materials.find((m) => m.id === Number(value));
        return { ...item, material_id: Number(value), material_name: mat?.name, unit: mat?.unit ?? "个" };
      }
      if (field === "brand_id") {
        const brand = brands.find((b) => b.id === Number(value));
        return { ...item, brand_id: Number(value) || undefined, brand_name: brand?.name };
      }
      return { ...item, [field]: value };
    });
    onChange(next);
  };

  const boxItems = packagings.filter((p) => p.level === "box");
  const portionItems = packagings.filter((p) => p.level === "portion");

  const renderTable = (items: PackagingItem[], levelLabel: string, level: string) => (
    <div className="space-y-2">
      <div className="flex items-center justify-between">
        <Label className="text-sm font-medium">{levelLabel}</Label>
        <Button type="button" variant="outline" size="sm" onClick={() => addItem(level)}>
          <Plus className="h-3 w-3 mr-1" />添加
        </Button>
      </div>
      {items.length === 0 ? (
        <p className="text-xs text-muted-foreground">暂无配置，点击"添加"</p>
      ) : (
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead className="text-xs w-[160px]">物料</TableHead>
              <TableHead className="text-xs w-[100px]">品牌</TableHead>
              <TableHead className="text-xs w-[60px]">数量</TableHead>
              <TableHead className="text-xs w-[50px]">单位</TableHead>
              <TableHead className="text-xs">备注</TableHead>
              <TableHead className="text-xs w-[40px]"></TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {items.map((item, idx) => {
              const globalIdx = packagings.findIndex(
                (p) => p.level === level && p === item
              );
              return (
                <TableRow key={globalIdx}>
                  <TableCell>
                    <Select
                      value={String(item.material_id)}
                      onValueChange={(v) => updateItem(globalIdx, "material_id", Number(v))}
                    >
                      <SelectTrigger className="h-8 text-xs">
                        <SelectValue placeholder="选择物料" />
                      </SelectTrigger>
                      <SelectContent>
                        {materials.map((m) => (
                          <SelectItem key={m.id} value={String(m.id)} className="text-xs">
                            <div className="flex flex-col">
                              <span>{m.name} ({m.code})</span>
                              {m.suppliers && m.suppliers.length > 0 && (
                                <span className="text-[10px] text-muted-foreground">
                                  {m.suppliers[0].supplier_name} ¥{m.suppliers[0].unit_price?.toFixed(2) ?? '-'}
                                </span>
                              )}
                            </div>
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </TableCell>
                  <TableCell>
                    <Select
                      value={item.brand_id ? String(item.brand_id) : ""}
                      onValueChange={(v) => updateItem(globalIdx, "brand_id", v ? Number(v) : undefined)}
                    >
                      <SelectTrigger className="h-8 text-xs">
                        <SelectValue placeholder="通用">
                          {(() => {
                            if (!item.brand_id) return "通用";
                            const brand = brands.find((b) => b.id === item.brand_id);
                            return brand ? brand.name : `品牌${item.brand_id}`;
                          })()}
                        </SelectValue>
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="" className="text-xs">通用（所有品牌）</SelectItem>
                        {brands.map((b) => (
                          <SelectItem key={b.id} value={String(b.id)} className="text-xs">
                            <div className="flex items-center gap-1">
                              {b.name}
                              {b.is_oem && <Badge variant="secondary" className="text-[10px] bg-purple-100 text-purple-700">OEM</Badge>}
                            </div>
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </TableCell>
                  <TableCell>
                    <Input
                      type="number"
                      className="h-8 text-xs"
                      value={item.quantity}
                      onChange={(e) => updateItem(globalIdx, "quantity", parseFloat(e.target.value) || 0)}
                    />
                  </TableCell>
                  <TableCell className="text-xs">{item.unit || "个"}</TableCell>
                  <TableCell>
                    <Input
                      className="h-8 text-xs"
                      value={item.notes ?? ""}
                      onChange={(e) => updateItem(globalIdx, "notes", e.target.value)}
                      placeholder="备注"
                    />
                  </TableCell>
                  <TableCell>
                    <Button type="button" variant="ghost" size="icon" className="h-7 w-7 text-red-500" onClick={() => removeItem(globalIdx)}>
                      <Trash2 className="h-3 w-3" />
                    </Button>
                  </TableCell>
                </TableRow>
              );
            })}
          </TableBody>
        </Table>
      )}
    </div>
  );

  return (
    <div className="space-y-4 border rounded-lg p-4 bg-muted/30">
      <div className="flex items-center justify-between">
        <h4 className="text-sm font-semibold">包装物配置</h4>
        {brands.length > 0 && (
          <span className="text-xs text-muted-foreground">
            支持按品牌配置不同包装物
          </span>
        )}
      </div>
      {renderTable(boxItems, "盒级包装（每盒）", "box")}
      {renderTable(portionItems, "份级包装（每份 = 份内盒数 × 盒级 + 外箱）", "portion")}
    </div>
  );
}
