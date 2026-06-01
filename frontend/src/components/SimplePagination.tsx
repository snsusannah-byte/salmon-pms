import { Button } from "@/components/ui/button";
import { ChevronLeft, ChevronRight } from "lucide-react";

export function SimplePagination({
  current,
  total,
  pageSize,
  onChange,
}: {
  current: number;
  total: number;
  pageSize: number;
  onChange: (page: number) => void;
}) {
  const totalPages = Math.max(1, Math.ceil(total / pageSize));
  if (totalPages <= 1) return null;
  return (
    <div className="flex items-center justify-between px-2 py-3">
      <span className="text-xs text-muted-foreground">
        第 {current + 1} / {totalPages} 页，共 {total} 条
      </span>
      <div className="flex gap-1">
        <Button
          variant="outline"
          size="sm"
          disabled={current === 0}
          onClick={() => onChange(current - 1)}
        >
          <ChevronLeft className="h-3 w-3" />
        </Button>
        <Button
          variant="outline"
          size="sm"
          disabled={current >= totalPages - 1}
          onClick={() => onChange(current + 1)}
        >
          <ChevronRight className="h-3 w-3" />
        </Button>
      </div>
    </div>
  );
}
