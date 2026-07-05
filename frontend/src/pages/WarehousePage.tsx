import React, { useState, useEffect, useMemo } from "react";
import { api } from "../lib/api";
import { useNavigate } from "react-router-dom";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "../components/ui/table";
import { toast } from "sonner";
import { Loader2, Search } from "lucide-react";
import { Badge } from "../components/ui/badge";

interface Stock {
  id: number;
  product_name: string;
  product_category: string;
  warehouse_name: string;
  warehouse_type: string;
  current_qty: string;
  current_box_count?: number;
  available_qty: string;
  available_box_count?: number;
  unit: string;
  unit_cost: string | null;
  total_cost: string | null;
  is_below_warning?: boolean;
  warehouse_id: number;
  batch_no?: string | null;
}

function fmt(n: number | string | undefined) {
  if (n === undefined || n === null) return "0";
  const val = typeof n === "string" ? parseFloat(n) : n;
  if (isNaN(val)) return "0";
  return val.toLocaleString("zh-CN", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

export function WarehousePage() {
  const navigate = useNavigate();
  const [stocks, setStocks] = useState<Stock[]>([]);
  const [loading, setLoading] = useState(false);
  const [search, setSearch] = useState("");
  const [warehouseFilter, setWarehouseFilter] = useState<string>("");

  const fetchStocks = async () => {
    setLoading(true);
    try {
      const res = await api.get("/v1/warehouse/stocks");
      setStocks(res.data.items || []);
    } catch (err: any) {
      toast.error(err.response?.data?.detail || "获取库存失败");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchStocks();
  }, []);

  const filtered = stocks.filter((s) => {
    const matchesSearch =
      !search ||
      s.product_name.toLowerCase().includes(search.toLowerCase()) ||
      s.product_category.toLowerCase().includes(search.toLowerCase());
    const matchesWarehouse = !warehouseFilter || s.warehouse_name === warehouseFilter;
    return matchesSearch && matchesWarehouse;
  });

  // 按仓库分组
  const groupedByWarehouse = useMemo(() => {
    const map = new Map<number, { warehouse_id: number; warehouse_name: string; warehouse_type: string; product_count: number; total_current: number; total_box_count: number; items: Stock[] }>();
    filtered.forEach((s) => {
      const existing = map.get(s.warehouse_id);
      const qty = parseFloat(s.current_qty) || 0;
      const boxes = s.current_box_count || 0;
      if (existing) {
        existing.product_count += 1;
        existing.total_current += qty;
        existing.total_box_count += boxes;
        existing.items.push(s);
      } else {
        map.set(s.warehouse_id, {
          warehouse_id: s.warehouse_id,
          warehouse_name: s.warehouse_name,
          warehouse_type: s.warehouse_type,
          product_count: 1,
          total_current: qty,
          total_box_count: boxes,
          items: [s],
        });
      }
    });
    return Array.from(map.values());
  }, [filtered]);

  const warehouses = Array.from(new Set(stocks.map((s) => s.warehouse_name)));

  return (
    <div className="p-4 space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-xl font-semibold flex items-center gap-2">
          <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M20 7l-8-4-8 4m16 0l-8 4m8-4v10l-8 4m0-10L4 7m8 4v10M4 7v10l8 4" /></svg>
          仓库管理
        </h2>
        <div className="flex gap-2">
          <Button variant="outline" onClick={() => navigate("/warehouse/inbound")}>
            <svg className="w-4 h-4 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 14l-7 7m0 0l-7-7m7 7V3" /></svg>
            入库
          </Button>
          <Button variant="outline" onClick={() => navigate("/warehouse/outbound")}>
            <svg className="w-4 h-4 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 10l7-7m0 0l7 7m-7-7v18" /></svg>
            出库
          </Button>
          <Button variant="outline" onClick={() => navigate("/warehouse/transfer")}>
            <svg className="w-4 h-4 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 7h12m0 0l-4-4m4 4l-4 4m0 6H4m0 0l4 4m-4-4l4-4" /></svg>
            调拨
          </Button>
        </div>
      </div>

      {/* 筛选 */}
      <div className="flex gap-4">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
          <Input
            placeholder="搜索产品名称或分类..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="pl-10"
          />
        </div>
        <select
          className="border rounded-md px-3 py-2"
          value={warehouseFilter}
          onChange={(e) => setWarehouseFilter(e.target.value)}
        >
          <option value="">全部仓库</option>
          {warehouses.map((w) => (
            <option key={w} value={w}>{w}</option>
          ))}
        </select>
        <span className="text-sm text-muted-foreground flex items-center">
          共 {filtered.length} 条记录
        </span>
      </div>

      {/* 按仓库分区块显示 */}
      {loading ? (
        <div className="flex justify-center py-8">
          <Loader2 className="w-8 h-8 animate-spin" />
        </div>
      ) : groupedByWarehouse.length === 0 ? (
        <div className="text-center py-8 text-gray-500">暂无库存记录</div>
      ) : (
        <div className="space-y-4">
          {groupedByWarehouse.map((w) => (
            <div key={w.warehouse_id} className="border rounded-lg overflow-hidden">
              {/* 仓库标题 */}
              <div className="bg-muted/50 px-4 py-2 flex items-center justify-between">
                <div className="font-semibold">{w.warehouse_name}</div>
                <div className="text-sm text-muted-foreground">
                  {w.warehouse_type === "self" ? "自营仓" : "第三方仓"} · {w.product_count} 种产品 · {fmt(w.total_current)} kg · {w.total_box_count ? `${w.total_box_count} 箱` : ""}
                </div>
              </div>
              {/* 该仓库的产品列表 */}
              <Table>
                <TableHeader>
                  <TableRow className="bg-muted/20">
                    <TableHead className="text-xs">产品名称</TableHead>
                    <TableHead className="text-xs">分类</TableHead>
                    <TableHead className="text-xs text-right">当前数量</TableHead>
                    <TableHead className="text-xs text-right">箱数</TableHead>
                    <TableHead className="text-xs text-right">可用数量</TableHead>
                    <TableHead className="text-xs text-right">平均成本</TableHead>
                    <TableHead className="text-xs text-right">总成本</TableHead>
                    <TableHead className="text-xs text-center">状态</TableHead>
                    <TableHead className="text-xs text-center">操作记录</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {w.items.map((s) => (
                    <TableRow key={s.id}>
                      <TableCell className="text-sm font-medium">{s.product_name}</TableCell>
                      <TableCell className="text-xs text-muted-foreground">{s.product_category}</TableCell>
                      <TableCell className="text-sm text-right">
                        <span className={s.is_below_warning ? "text-red-600 font-semibold" : ""}>
                          {fmt(s.current_qty)} {s.unit}
                        </span>
                      </TableCell>
                      <TableCell className="text-sm text-right">
                        {s.current_box_count ? `${s.current_box_count} 箱` : "-"}
                      </TableCell>
                      <TableCell className="text-sm text-right">{fmt(s.available_qty)} {s.unit}</TableCell>
                      <TableCell className="text-sm text-right">
                        {s.unit_cost ? `¥${fmt(parseFloat(s.unit_cost))}` : "-"}
                      </TableCell>
                      <TableCell className="text-sm text-right">
                        {s.total_cost ? `¥${fmt(parseFloat(s.total_cost))}` : "-"}
                      </TableCell>
                      <TableCell className="text-center">
                        {s.is_below_warning ? (
                          <Badge variant="destructive">库存不足</Badge>
                        ) : (
                          <Badge variant="outline">正常</Badge>
                        )}
                      </TableCell>
                      <TableCell className="text-center">
                        <Button variant="ghost" size="sm" onClick={() => navigate(`/warehouse/stock/${s.id}/history`)}>
                          查看
                        </Button>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
