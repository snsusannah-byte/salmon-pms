import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { useState } from "react";
import { api } from "@/lib/api";
import { useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";

interface DeleteConfirmDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  companyId: number | null;
  companyName: string;
}

export function DeleteConfirmDialog({ open, onOpenChange, companyId, companyName }: DeleteConfirmDialogProps) {
  const queryClient = useQueryClient();
  const [isDeleting, setIsDeleting] = useState(false);

  const handleDelete = async () => {
    if (!companyId) return;
    
    setIsDeleting(true);
    try {
      await api.delete(`/v1/companies/${companyId}`);
      toast.success("主体已删除");
      queryClient.invalidateQueries({ queryKey: ["companies"] });
      onOpenChange(false);
    } catch (error: any) {
      const msg = error.response?.data?.detail ?? "删除失败";
      toast.error(msg);
    } finally {
      setIsDeleting(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>确认删除</DialogTitle>
          <DialogDescription>
            确定要删除主体 <strong>"{companyName}"</strong> 吗？
            <br />
            此操作不可撤销，删除后该主体将标记为不活跃。
          </DialogDescription>
        </DialogHeader>
        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)} disabled={isDeleting}>
            取消
          </Button>
          <Button variant="destructive" onClick={handleDelete} disabled={isDeleting}>
            {isDeleting ? "删除中..." : "确认删除"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
