import React, { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter,
} from "@/components/ui/dialog";
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import { toast } from "sonner";
import { ArrowDown, Loader2 } from "lucide-react";

interface Warehouse { id: number; code: string; name: string; type: string; }
interface Product { id: number; name: string; category: string; unit: string; }

const fetchWarehouses = async () => {
  const { data } = await api.get("/v1/warehouse-v2/warehouses");
  return data.items as Warehouse[];
};

const fetchProducts = async () => {
  const { data } = await api.get("/v1/products?limit=500");
  return data.items as Product[];
};

export function StockInboundDialog({ open, onOpenChange }: { open: boolean; onOpenChange: (v: boolean) => void }) {
  const queryClient = useQueryClient();
  const [warehouseId, setWarehouseId] = useState("");
  const [productId, setProductId] = useState("");
  const [qty, setQty] = useState("");
  const [unit, setUnit] = useState("box");
  const [unitCost, setUnitCost] = useState("");
  const [sourceType, setSourceType] = useState("purchase_order");
  const [sourceNo, setSourceNo] = useState("");
  const [inboundDate, setInboundDate] = useState(new Date().toISOString().split("T")[0]);
  const [notes, setNotes] = useState("");

  const { data: warehouses } = useQuery({ queryKey: ["warehouses"], queryFn: fetchWarehouses });
  const { data: products } = useQuery({ queryKey: ["products-all"], queryFn: fetchProducts });

  const createInbound = useMutation({
    mutationFn: async (payload: any) => {
      const { data } = await api.post("/v1/warehouse-v2/inbounds", payload);
      return data;
    },
    onSuccess: (data) => {
      toast.success(`入库单 ${data.inbound_no} 创建成功`);
      queryClient.invalidateQueries({ queryKey: ["warehouse-v2-stocks"] });
      queryClient.invalidateQueries({ queryKey: ["warehouse-v2-summary"] });
      queryClient.invalidateQueries({ queryKey: ["warehouse-v2-movements"] });
      onOpenChange(false);
      resetForm();
    },
    onError: (err: any) => {
      toast.error(err.response?.data?.detail || "创建失败");
    },
  });

  const resetForm = () => {
    setWarehouseId(""); setProductId(""); setQty(""); setUnitCost("");
    setSourceNo(""); setNotes("");
  };

  const handleSubmit = () => {
    if (!warehouseId || !productId || !qty || !unitCost) {
      toast.error("请填写必填项");
      return;
    }
    createInbound.mutate({
      warehouse_id: Number(warehouseId),
      product_id: Number(productId),
      qty: Number(qty),
      unit,
      unit_cost: Number(unitCost),
      source_type: sourceType,
      source_no: sourceNo || undefined,
      inbound_date: inboundDate,
      notes: notes || undefined,
    });
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-lg">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <ArrowDown className="h-5 w-5 text-green-600" />
            创建入库单
          </DialogTitle>
        </DialogHeader>
        <div className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label>仓库 *</Label>
              <Select value={warehouseId} onValueChange={setWarehouseId}>
                <SelectTrigger><SelectValue placeholder="选择仓库" /></SelectTrigger>
                <SelectContent>
                  {warehouses?.map((w) => (
                    <SelectItem key={w.id} value={String(w.id)}>{w.name} ({w.code})</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label>产品 *</Label>
              <Select value={productId} onValueChange={setProductId}>
                <SelectTrigger><SelectValue placeholder="选择产品" /></SelectTrigger>
                <SelectContent>
                  {products?.map((p) => (
                    <SelectItem key={p.id} value={String(p.id)}>{p.name}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>

          <div className="grid grid-cols-3 gap-4">
            <div className="space-y-2">
              <Label>数量 *</Label>
              <Input type="number" step="0.001" value={qty} onChange={(e) => setQty(e.target.value)} placeholder="0.000" />
            </div>
            <div className="space-y-2">
              <Label>单位 *</Label>
              <Select value={unit} onValueChange={setUnit}>
                <SelectTrigger><SelectValue /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="box">箱</SelectItem>
                  <SelectItem value="piece">条</SelectItem>
                  <SelectItem value="board">板</SelectItem>
                  <SelectItem value="kg">kg</SelectItem>
                  <SelectItem value="plate">盘</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label>单位成本 *</Label>
              <Input type="number" step="0.0001" value={unitCost} onChange={(e) => setUnitCost(e.target.value)} placeholder="0.0000" />
            </div>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label>来源类型</Label>
              <Select value={sourceType} onValueChange={setSourceType}>
                <SelectTrigger><SelectValue /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="purchase_order">采购单</SelectItem>
                  <SelectItem value="import_invoice">进口单证</SelectItem>
                  <SelectItem value="transfer_in">调拨入</SelectItem>
                  <SelectItem value="return">退货</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label>来源单号</Label>
              <Input value={sourceNo} onChange={(e) => setSourceNo(e.target.value)} placeholder="如：发票号/采购单号" />
            </div>
          </div>

          <div className="space-y-2">
            <Label>入库日期</Label>
            <Input type="date" value={inboundDate} onChange={(e) => setInboundDate(e.target.value)} />
          </div>

          <div className="space-y-2">
            <Label>备注</Label>
            <Textarea value={notes} onChange={(e) => setNotes(e.target.value)} rows={2} />
          </div>
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>取消</Button>
          <Button onClick={handleSubmit} disabled={createInbound.isPending}>
            {createInbound.isPending && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
            创建入库单
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

export function StockOutboundDialog({ open, onOpenChange }: { open: boolean; onOpenChange: (v: boolean) => void }) {
  const queryClient = useQueryClient();
  const [warehouseId, setWarehouseId] = useState("");
  const [productId, setProductId] = useState("");
  const [qty, setQty] = useState("");
  const [unit, setUnit] = useState("kg");
  const [destType, setDestType] = useState("sale");
  const [destNo, setDestNo] = useState("");
  const [outboundDate, setOutboundDate] = useState(new Date().toISOString().split("T")[0]);
  const [notes, setNotes] = useState("");

  const { data: warehouses } = useQuery({ queryKey: ["warehouses"], queryFn: fetchWarehouses });
  const { data: products } = useQuery({ queryKey: ["products-all"], queryFn: fetchProducts });

  const createOutbound = useMutation({
    mutationFn: async (payload: any) => {
      const { data } = await api.post("/v1/warehouse-v2/outbounds", payload);
      return data;
    },
    onSuccess: (data) => {
      toast.success(`出库单 ${data.outbound_no} 创建成功`);
      queryClient.invalidateQueries({ queryKey: ["warehouse-v2-stocks"] });
      queryClient.invalidateQueries({ queryKey: ["warehouse-v2-summary"] });
      queryClient.invalidateQueries({ queryKey: ["warehouse-v2-movements"] });
      onOpenChange(false);
      resetForm();
    },
    onError: (err: any) => {
      toast.error(err.response?.data?.detail || "创建失败");
    },
  });

  const resetForm = () => {
    setWarehouseId(""); setProductId(""); setQty(""); setDestNo(""); setNotes("");
  };

  const handleSubmit = () => {
    if (!warehouseId || !productId || !qty) {
      toast.error("请填写必填项");
      return;
    }
    createOutbound.mutate({
      warehouse_id: Number(warehouseId),
      product_id: Number(productId),
      qty: Number(qty),
      unit,
      dest_type: destType,
      dest_no: destNo || undefined,
      outbound_date: outboundDate,
      notes: notes || undefined,
    });
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-lg">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <ArrowDown className="h-5 w-5 text-red-600 rotate-180" />
            创建出库单
          </DialogTitle>
        </DialogHeader>
        <div className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label>仓库 *</Label>
              <Select value={warehouseId} onValueChange={setWarehouseId}>
                <SelectTrigger><SelectValue placeholder="选择仓库" /></SelectTrigger>
                <SelectContent>
                  {warehouses?.map((w) => (
                    <SelectItem key={w.id} value={String(w.id)}>{w.name} ({w.code})</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label>产品 *</Label>
              <Select value={productId} onValueChange={setProductId}>
                <SelectTrigger><SelectValue placeholder="选择产品" /></SelectTrigger>
                <SelectContent>
                  {products?.map((p) => (
                    <SelectItem key={p.id} value={String(p.id)}>{p.name}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label>数量 *</Label>
              <Input type="number" step="0.001" value={qty} onChange={(e) => setQty(e.target.value)} placeholder="0.000" />
            </div>
            <div className="space-y-2">
              <Label>单位 *</Label>
              <Select value={unit} onValueChange={setUnit}>
                <SelectTrigger><SelectValue /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="box">箱</SelectItem>
                  <SelectItem value="piece">条</SelectItem>
                  <SelectItem value="board">板</SelectItem>
                  <SelectItem value="kg">kg</SelectItem>
                  <SelectItem value="plate">盘</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label>去向类型</Label>
              <Select value={destType} onValueChange={setDestType}>
                <SelectTrigger><SelectValue /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="sale">销售</SelectItem>
                  <SelectItem value="transfer_out">调拨出</SelectItem>
                  <SelectItem value="production">生产领用</SelectItem>
                  <SelectItem value="loss">损耗</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label>去向单号</Label>
              <Input value={destNo} onChange={(e) => setDestNo(e.target.value)} placeholder="如：销售单号" />
            </div>
          </div>

          <div className="space-y-2">
            <Label>出库日期</Label>
            <Input type="date" value={outboundDate} onChange={(e) => setOutboundDate(e.target.value)} />
          </div>

          <div className="space-y-2">
            <Label>备注</Label>
            <Textarea value={notes} onChange={(e) => setNotes(e.target.value)} rows={2} />
          </div>
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>取消</Button>
          <Button onClick={handleSubmit} disabled={createOutbound.isPending}>
            {createOutbound.isPending && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
            创建出库单
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

export function StockTransferDialog({ open, onOpenChange }: { open: boolean; onOpenChange: (v: boolean) => void }) {
  const queryClient = useQueryClient();
  const [fromWarehouseId, setFromWarehouseId] = useState("");
  const [toWarehouseId, setToWarehouseId] = useState("");
  const [productId, setProductId] = useState("");
  const [fromQty, setFromQty] = useState("");
  const [fromUnit, setFromUnit] = useState("box");
  const [toQty, setToQty] = useState("");
  const [toUnit, setToUnit] = useState("piece");
  const [transferDate, setTransferDate] = useState(new Date().toISOString().split("T")[0]);
  const [notes, setNotes] = useState("");

  const { data: warehouses } = useQuery({ queryKey: ["warehouses"], queryFn: fetchWarehouses });
  const { data: products } = useQuery({ queryKey: ["products-all"], queryFn: fetchProducts });

  const createTransfer = useMutation({
    mutationFn: async (payload: any) => {
      const { data } = await api.post("/v1/warehouse-v2/transfers", payload);
      return data;
    },
    onSuccess: (data) => {
      toast.success(`调拨单 ${data.transfer_no} 创建成功`);
      queryClient.invalidateQueries({ queryKey: ["warehouse-v2-stocks"] });
      queryClient.invalidateQueries({ queryKey: ["warehouse-v2-summary"] });
      queryClient.invalidateQueries({ queryKey: ["warehouse-v2-movements"] });
      onOpenChange(false);
      resetForm();
    },
    onError: (err: any) => {
      toast.error(err.response?.data?.detail || "创建失败");
    },
  });

  const resetForm = () => {
    setFromWarehouseId(""); setToWarehouseId(""); setProductId("");
    setFromQty(""); setToQty(""); setNotes("");
  };

  const handleSubmit = () => {
    if (!fromWarehouseId || !toWarehouseId || !productId || !fromQty || !toQty) {
      toast.error("请填写必填项");
      return;
    }
    if (fromWarehouseId === toWarehouseId) {
      toast.error("调出仓和调入仓不能相同");
      return;
    }
    const fqty = Number(fromQty);
    const tqty = Number(toQty);
    const ratio = tqty / fqty;
    createTransfer.mutate({
      from_warehouse_id: Number(fromWarehouseId),
      to_warehouse_id: Number(toWarehouseId),
      product_id: Number(productId),
      from_qty: fqty,
      from_unit: fromUnit,
      to_qty: tqty,
      to_unit: toUnit,
      conversion_ratio: ratio,
      transfer_date: transferDate,
      notes: notes || undefined,
    });
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-lg">
        <DialogHeader>
          <DialogTitle>创建调拨单</DialogTitle>
        </DialogHeader>
        <div className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label>调出仓库 *</Label>
              <Select value={fromWarehouseId} onValueChange={setFromWarehouseId}>
                <SelectTrigger><SelectValue placeholder="选择仓库" /></SelectTrigger>
                <SelectContent>
                  {warehouses?.map((w) => (
                    <SelectItem key={w.id} value={String(w.id)}>{w.name}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label>调入仓库 *</Label>
              <Select value={toWarehouseId} onValueChange={setToWarehouseId}>
                <SelectTrigger><SelectValue placeholder="选择仓库" /></SelectTrigger>
                <SelectContent>
                  {warehouses?.map((w) => (
                    <SelectItem key={w.id} value={String(w.id)}>{w.name}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>

          <div className="space-y-2">
            <Label>产品 *</Label>
            <Select value={productId} onValueChange={setProductId}>
              <SelectTrigger><SelectValue placeholder="选择产品" /></SelectTrigger>
              <SelectContent>
                {products?.map((p) => (
                  <SelectItem key={p.id} value={String(p.id)}>{p.name}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          <div className="grid grid-cols-4 gap-4">
            <div className="space-y-2">
              <Label>调出数量 *</Label>
              <Input type="number" step="0.001" value={fromQty} onChange={(e) => setFromQty(e.target.value)} />
            </div>
            <div className="space-y-2">
              <Label>调出单位</Label>
              <Select value={fromUnit} onValueChange={setFromUnit}>
                <SelectTrigger><SelectValue /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="box">箱</SelectItem>
                  <SelectItem value="piece">条</SelectItem>
                  <SelectItem value="board">板</SelectItem>
                  <SelectItem value="kg">kg</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label>调入数量 *</Label>
              <Input type="number" step="0.001" value={toQty} onChange={(e) => setToQty(e.target.value)} />
            </div>
            <div className="space-y-2">
              <Label>调入单位</Label>
              <Select value={toUnit} onValueChange={setToUnit}>
                <SelectTrigger><SelectValue /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="box">箱</SelectItem>
                  <SelectItem value="piece">条</SelectItem>
                  <SelectItem value="board">板</SelectItem>
                  <SelectItem value="kg">kg</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>

          <div className="space-y-2">
            <Label>调拨日期</Label>
            <Input type="date" value={transferDate} onChange={(e) => setTransferDate(e.target.value)} />
          </div>

          <div className="space-y-2">
            <Label>备注</Label>
            <Textarea value={notes} onChange={(e) => setNotes(e.target.value)} rows={2} />
          </div>
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>取消</Button>
          <Button onClick={handleSubmit} disabled={createTransfer.isPending}>
            {createTransfer.isPending && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
            创建调拨单
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
