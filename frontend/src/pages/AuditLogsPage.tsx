import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
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
import { Badge } from "@/components/ui/badge";
import { toast } from "sonner";
import { useAuth } from "@/lib/permissions";
import { Shield, Search, ChevronLeft, ChevronRight } from "lucide-react";

interface AuditLogItem {
  id: number;
  user_id: number;
  username: string;
  action: string;
  module: string;
  resource_type: string | null;
  resource_id: number | null;
  details: string | null;
  ip_address: string | null;
  created_at: string;
}

const PAGE_SIZE = 20;

const ACTION_COLORS: Record<string, string> = {
  create: "bg-green-100 text-green-800",
  update: "bg-blue-100 text-blue-800",
  delete: "bg-red-100 text-red-800",
  lock: "bg-yellow-100 text-yellow-800",
  unlock: "bg-orange-100 text-orange-800",
  approve: "bg-purple-100 text-purple-800",
  import: "bg-cyan-100 text-cyan-800",
  hard_delete: "bg-red-200 text-red-900",
};

export function AuditLogsPage() {
  const { isAdmin } = useAuth();
  const [page, setPage] = useState(1);
  const [moduleFilter, setModuleFilter] = useState("");
  const [actionFilter, setActionFilter] = useState("");

  const { data, isLoading } = useQuery<{ total: number; items: AuditLogItem[] }>({
    queryKey: ["audit-logs", page, moduleFilter, actionFilter],
    queryFn: async () => {
      const params = new URLSearchParams();
      params.append("skip", String((page - 1) * PAGE_SIZE));
      params.append("limit", String(PAGE_SIZE));
      if (moduleFilter) params.append("module", moduleFilter);
      if (actionFilter) params.append("action", actionFilter);
      const res = await api.get(`/v1/audit/logs?${params.toString()}`);
      return res.data;
    },
    enabled: isAdmin,
  });

  if (!isAdmin) {
    return (
      <div className="flex items-center justify-center h-96">
        <div className="text-center space-y-4">
          <Shield className="h-12 w-12 text-muted-foreground mx-auto" />
          <p className="text-lg font-medium">权限不足</p>
          <p className="text-sm text-muted-foreground">仅管理员可查看审计日志</p>
        </div>
      </div>
    );
  }

  const totalPages = data ? Math.ceil(data.total / PAGE_SIZE) : 0;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">审计日志</h1>
          <p className="text-sm text-muted-foreground">
            记录所有敏感操作，便于追溯和审计
          </p>
        </div>
      </div>

      {/* 筛选 */}
      <div className="flex gap-3">
        <div className="relative flex-1 max-w-xs">
          <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
          <Input
            placeholder="模块过滤..."
            value={moduleFilter}
            onChange={(e) => { setModuleFilter(e.target.value); setPage(1); }}
            className="pl-8"
          />
        </div>
        <div className="relative flex-1 max-w-xs">
          <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
          <Input
            placeholder="操作类型过滤..."
            value={actionFilter}
            onChange={(e) => { setActionFilter(e.target.value); setPage(1); }}
            className="pl-8"
          />
        </div>
      </div>

      {/* 日志表格 */}
      <div className="border rounded-lg">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>ID</TableHead>
              <TableHead>用户</TableHead>
              <TableHead>操作</TableHead>
              <TableHead>模块</TableHead>
              <TableHead>资源</TableHead>
              <TableHead>详情</TableHead>
              <TableHead>IP</TableHead>
              <TableHead>时间</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {isLoading ? (
              <TableRow>
                <TableCell colSpan={8} className="text-center py-8 text-muted-foreground">
                  加载中...
                </TableCell>
              </TableRow>
            ) : data?.items.length === 0 ? (
              <TableRow>
                <TableCell colSpan={8} className="text-center py-8 text-muted-foreground">
                  暂无审计日志
                </TableCell>
              </TableRow>
            ) : (
              data?.items.map((log) => (
                <TableRow key={log.id}>
                  <TableCell className="font-mono text-xs">{log.id}</TableCell>
                  <TableCell>{log.username || `用户#${log.user_id}`}</TableCell>
                  <TableCell>
                    <Badge className={ACTION_COLORS[log.action] || "bg-gray-100 text-gray-800"}>
                      {log.action}
                    </Badge>
                  </TableCell>
                  <TableCell>{log.module}</TableCell>
                  <TableCell>
                    {log.resource_type ? `${log.resource_type}:${log.resource_id}` : "-"}
                  </TableCell>
                  <TableCell className="max-w-[200px] truncate" title={log.details || ""}>
                    {log.details || "-"}
                  </TableCell>
                  <TableCell className="font-mono text-xs">{log.ip_address || "-"}</TableCell>
                  <TableCell className="text-xs whitespace-nowrap">
                    {new Date(log.created_at).toLocaleString("zh-CN")}
                  </TableCell>
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </div>

      {/* 分页 */}
      {totalPages > 1 && (
        <div className="flex items-center justify-between">
          <p className="text-sm text-muted-foreground">
            共 {data?.total} 条记录，第 {page}/{totalPages} 页
          </p>
          <div className="flex gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() => setPage((p) => Math.max(1, p - 1))}
              disabled={page <= 1}
            >
              <ChevronLeft className="h-4 w-4" />
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
              disabled={page >= totalPages}
            >
              <ChevronRight className="h-4 w-4" />
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}
