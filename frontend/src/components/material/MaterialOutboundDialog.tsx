import React, { useState, useEffect } from "react";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter,
} from "@/components/ui/dialog";
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from "@/components/ui/select";

interface Batch {
  id: number;
  batch_no: string;
  inbound_date: string;
  supplier_name: string | null;
  remaining_qty: number;
  unit_cost: number;
}

interface Material {
  id: number;
  code: string;
  name: string;
  unit: string;
  total_qty: number;
  batches: Batch[];
}

interface MaterialOutboundDialogProps {
  open: boolean;
  onClose: () => void;
  preSelectedMaterialId?: number;
  onSuccess?: () => void;
}

export default function MaterialOutboundDialog({
  open,
  onClose,
  preSelectedMaterialId,
  onSuccess,
}: MaterialOutboundDialogProps) {
  const [materialId, setMaterialId] = useState<string>("");
  const [qty, setQty] = useState<string>("");
  const [strategy, setStrategy] = useState<string>("fifo");
  const [batchId, setBatchId] = useState<string>("");
  const [reason, setReason] = useState("");

  const { data: materials = [] } = useQuery<Material[]>({
    queryKey: ["materials-for-outbound"],
    queryFn: async () => {
      const res = await api.get("/v1/material-purchases/materials");
      return res.data || [];
    },
    enabled: open,
  });

  const selectedMaterial = materials.find((m) => String(m.id) === materialId);
  const selectedBatch = selectedMaterial?.batches?.find((b) => String(b.id) === batchId);

  useEffect(() => {
    if (open && preSelectedMaterialId) {
      setMaterialId(String(preSelectedMaterialId));
    }
  }, [open, preSelectedMaterialId]);

  const handleSubmit = async () => {
    if (!materialId) {
      toast.error("请选择物料");
      return;
    }
    const qtyNum = Number(qty);
    if (!qtyNum || qtyNum <= 0) {
      toast.error("请输入出库数量");
      return;
    }
    if (strategy === "specific" && !batchId) {
      toast.error("请选择批次");
      return;
    }

    try {
      await api.post("/v1/material-purchases/outbound", {
        product_id: Number(materialId),
        qty: qtyNum,
        strategy,
        batch_id: strategy === "specific" ? Number(batchId) : null,
        reason,
      });
      toast.success("出库成功");
      onSuccess?.();
      onClose();
      setQty("");
      setBatchId("");
      setReason("");
      setStrategy("fifo");
    } catch (error: any) {
      toast.error(error.response?.data?.detail || "出库失败");
    }
  };

  return (
    <Dialog open={open} onOpenChange={(v) => !v && onClose()}>
      <DialogContent className="max-w-lg">
        <DialogHeader>
          <DialogTitle>物料出库</DialogTitle>
        </DialogHeader>

        <div className="space-y-4 py-4">
          <div className="space-y-2">
            <Label>物料</Label>
            <Select value={materialId} onValueChange={setMaterialId}>
              <SelectTrigger>
                <SelectValue placeholder="选择物料" />
              </SelectTrigger>
              <SelectContent>
                {materials.map((m) => (
                  <SelectItem key={m.id} value={String(m.id)}>
                    {m.code} {m.name} · 库存{m.total_qty}{m.unit}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          {selectedMaterial && (
            <div className="text-sm text-muted-foreground">
              当前库存：{selectedMaterial.total_qty} {selectedMaterial.unit} · 共{selectedMaterial.batches?.length || 0}个批次
            </div>
          )}

          <div className="space-y-2">
            <Label>出库数量</Label>
            <Input
              type="number"
              min={1}
              value={qty}
              onChange={(e) => setQty(e.target.value)}
              placeholder={`输入数量（${selectedMaterial?.unit || "个"}）`}
            />
          </div>

          <div className="space-y-2">
            <Label>出库策略</Label>
            <div className="flex gap-2">
              <Button
                variant={strategy === "fifo" ? "default" : "outline"}
                size="sm"
                onClick={() => setStrategy("fifo")}
              >
                先进先出（FIFO）
              </Button>
              <Button
                variant={strategy === "specific" ? "default" : "outline"}
                size="sm"
                onClick={() => setStrategy("specific")}
              >
                指定批次
              </Button>
            </div>
          </div>

          {strategy === "specific" && selectedMaterial?.batches && (
            <div className="space-y-2">
              <Label>选择批次</Label>
              <Select value={batchId} onValueChange={setBatchId}>
                <SelectTrigger>
                  <SelectValue placeholder="选择批次" />
                </SelectTrigger>
                <SelectContent>
                  {selectedMaterial.batches.map((b) => (
                    <SelectItem key={b.id} value={String(b.id)}>
                      {b.batch_no} · 余{b.remaining_qty} · ¥{b.unit_cost.toFixed(4)} · {b.supplier_name || "—"}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              {selectedBatch && (
                <div className="text-xs text-muted-foreground">
                  入库日期：{selectedBatch.inbound_date} · 成本单价：¥{selectedBatch.unit_cost.toFixed(4)}
                </div>
              )}
            </div>
          )}

          <div className="space-y-2">
            <Label>用途/备注</Label>
            <Input
              value={reason}
              onChange={(e) => setReason(e.target.value)}
              placeholder="如：生产领用、损耗报废..."
            />
          </div>
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={onClose}>
            取消
          </Button>
          <Button onClick={handleSubmit}>
            确认出库
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
