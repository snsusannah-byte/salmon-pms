import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Check, CheckCheck, Bell, ArrowLeft } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { api } from "@/lib/api";
import { useNavigate } from "react-router-dom";

interface Notification {
  id: number;
  title: string;
  content: string;
  type: string;
  is_read: boolean;
  related_type?: string;
  related_id?: number;
  created_at: string;
  read_at?: string;
}

export default function NotificationsPage() {
  const queryClient = useQueryClient();
  const navigate = useNavigate();
  const [filter, setFilter] = useState<"all" | "unread">("all");

  const { data, isLoading } = useQuery({
    queryKey: ["notifications", "list", filter],
    queryFn: async () => {
      const unreadOnly = filter === "unread" ? "&unread_only=true" : "";
      const res = await api.get(`/v1/notifications/?limit=100${unreadOnly}`);
      return res.data as { total: number; items: Notification[] };
    },
  });

  const markRead = useMutation({
    mutationFn: async (id: number) => {
      await api.post(`/v1/notifications/${id}/read`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["notifications"] });
    },
  });

  const markAllRead = useMutation({
    mutationFn: async () => {
      await api.post("/v1/notifications/read-all");
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["notifications"] });
    },
  });

  const notifications = data?.items || [];
  const unreadCount = notifications.filter((n) => !n.is_read).length;

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-4">
        <Button variant="ghost" size="icon" onClick={() => navigate(-1)}>
          <ArrowLeft className="h-5 w-5" />
        </Button>
        <h1 className="text-2xl font-bold tracking-tight">通知中心</h1>
        {unreadCount > 0 && (
          <Badge variant="destructive">{unreadCount} 条未读</Badge>
        )}
      </div>

      <div className="flex items-center gap-2">
        <Button
          variant={filter === "all" ? "default" : "outline"}
          size="sm"
          onClick={() => setFilter("all")}
        >
          全部
        </Button>
        <Button
          variant={filter === "unread" ? "default" : "outline"}
          size="sm"
          onClick={() => setFilter("unread")}
        >
          未读
        </Button>
        {unreadCount > 0 && (
          <Button
            variant="ghost"
            size="sm"
            className="ml-auto"
            onClick={() => markAllRead.mutate()}
          >
            <CheckCheck className="h-4 w-4 mr-1" />
            全部已读
          </Button>
        )}
      </div>

      <div className="space-y-3">
        {isLoading ? (
          <div className="text-center py-8 text-muted-foreground">加载中...</div>
        ) : notifications.length === 0 ? (
          <div className="text-center py-8 text-muted-foreground">暂无通知</div>
        ) : (
          notifications.map((n) => (
            <Card
              key={n.id}
              className={`cursor-pointer transition-colors hover:bg-muted/50 ${
                !n.is_read ? "border-primary/30 bg-primary/5" : ""
              }`}
              onClick={() => {
                if (!n.is_read) markRead.mutate(n.id);
                if (n.related_type === "import_invoice" && n.related_id) {
                  navigate("/invoices");
                }
              }}
            >
              <CardContent className="p-4">
                <div className="flex items-start gap-3">
                  <div className="mt-1">
                    {!n.is_read ? (
                      <div className="h-2 w-2 rounded-full bg-primary" />
                    ) : (
                      <Check className="h-4 w-4 text-muted-foreground" />
                    )}
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <span className={`font-medium ${n.is_read ? "text-muted-foreground" : ""}`}>
                        {n.title}
                      </span>
                      <Badge variant="outline" className="text-xs">
                        {n.type === "invoice_arrival"
                          ? "到货通知"
                          : n.type === "invoice_tax"
                          ? "税金通知"
                          : n.type}
                      </Badge>
                    </div>
                    <pre className="mt-2 text-sm text-muted-foreground whitespace-pre-wrap font-sans">
                      {n.content}
                    </pre>
                    <div className="mt-2 text-xs text-muted-foreground">
                      {new Date(n.created_at).toLocaleString()}
                      {n.read_at && (
                        <span className="ml-2">
                          已读: {new Date(n.read_at).toLocaleString()}
                        </span>
                      )}
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>
          ))
        )}
      </div>
    </div>
  );
}
