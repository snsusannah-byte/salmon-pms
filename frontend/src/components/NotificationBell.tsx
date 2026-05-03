import { useState, useRef, useEffect } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Bell, BellRing, CheckCheck, Copy, Check } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { api } from "@/lib/api";
import { useNavigate } from "react-router-dom";
import { toast } from "sonner";

interface Notification {
  id: number;
  title: string;
  content: string;
  type: string;
  is_read: boolean;
  related_type?: string;
  related_id?: number;
  created_at: string;
}

export function NotificationBell() {
  const [open, setOpen] = useState(false);
  const [copiedId, setCopiedId] = useState<number | null>(null);
  const dropdownRef = useRef<HTMLDivElement>(null);
  const queryClient = useQueryClient();
  const navigate = useNavigate();

  // 点击外部关闭
  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  // 未读数量
  const { data: unreadData } = useQuery({
    queryKey: ["notifications", "unread-count"],
    queryFn: async () => {
      const res = await api.get("/v1/notifications/unread-count");
      return res.data.count as number;
    },
    refetchInterval: 30000,
  });

  // 最近通知
  const { data: notificationsData } = useQuery({
    queryKey: ["notifications", "recent"],
    queryFn: async () => {
      const res = await api.get("/v1/notifications/?limit=10");
      return res.data.items as Notification[];
    },
    enabled: open,
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

  const unreadCount = unreadData || 0;
  const notifications = notificationsData || [];

  const handleClick = (n: Notification) => {
    if (!n.is_read) {
      markRead.mutate(n.id);
    }
    if (n.related_type === "import_invoice" && n.related_id) {
      navigate("/invoices");
    }
    setOpen(false);
  };

  // 复制通知内容到剪贴板（兼容非 HTTPS 环境）
  const copyNotification = async (n: Notification, e: React.MouseEvent) => {
    e.stopPropagation();
    try {
      // 优先使用现代 API
      if (navigator.clipboard && window.isSecureContext) {
        await navigator.clipboard.writeText(n.content);
      } else {
        // Fallback：创建 textarea 并执行复制命令
        const textarea = document.createElement("textarea");
        textarea.value = n.content;
        textarea.style.position = "fixed";
        textarea.style.left = "-9999px";
        document.body.appendChild(textarea);
        textarea.focus();
        textarea.select();
        const success = document.execCommand("copy");
        document.body.removeChild(textarea);
        if (!success) throw new Error("execCommand failed");
      }
      setCopiedId(n.id);
      toast.success("已复制到剪贴板");
      setTimeout(() => setCopiedId(null), 2000);
    } catch (err) {
      toast.error("复制失败，请手动复制");
    }
  };

  return (
    <div className="relative" ref={dropdownRef}>
      <Button variant="ghost" size="icon" className="relative" onClick={() => setOpen(!open)}>
        {unreadCount > 0 ? (
          <BellRing className="h-5 w-5 text-primary" />
        ) : (
          <Bell className="h-5 w-5" />
        )}
        {unreadCount > 0 && (
          <Badge
            variant="destructive"
            className="absolute -top-1 -right-1 h-5 w-5 flex items-center justify-center p-0 text-xs"
          >
            {unreadCount > 99 ? "99+" : unreadCount}
          </Badge>
        )}
      </Button>

      {open && (
        <div className="absolute right-0 top-full mt-2 w-96 bg-popover border rounded-md shadow-lg z-50">
          <div className="flex items-center justify-between px-3 py-2 border-b">
            <span className="text-sm font-semibold">通知中心</span>
            {unreadCount > 0 && (
              <Button
                variant="ghost"
                size="sm"
                className="h-7 text-xs"
                onClick={() => markAllRead.mutate()}
              >
                <CheckCheck className="h-3 w-3 mr-1" />
                全部已读
              </Button>
            )}
          </div>

          <div className="max-h-80 overflow-y-auto">
            {notifications.length === 0 ? (
              <div className="px-3 py-4 text-center text-sm text-muted-foreground">
                暂无通知
              </div>
            ) : (
              notifications.map((n) => (
                <div
                  key={n.id}
                  className={`px-3 py-2 cursor-pointer hover:bg-muted border-b last:border-b-0 ${
                    !n.is_read ? "bg-primary/5" : ""
                  }`}
                  onClick={() => handleClick(n)}
                >
                  <div className="flex items-center gap-2">
                    {!n.is_read && (
                      <div className="h-2 w-2 rounded-full bg-primary shrink-0" />
                    )}
                    <span className={`text-sm font-medium flex-1 ${n.is_read ? "text-muted-foreground" : ""}`}>
                      {n.title}
                    </span>
                    <Button
                      variant="ghost"
                      size="sm"
                      className="h-6 w-6 p-0 shrink-0"
                      onClick={(e) => copyNotification(n, e)}
                      title="复制到剪贴板"
                    >
                      {copiedId === n.id ? (
                        <Check className="h-3 w-3 text-green-500" />
                      ) : (
                        <Copy className="h-3 w-3" />
                      )}
                    </Button>
                  </div>
                  <p className="text-xs text-muted-foreground mt-1 line-clamp-2">
                    {n.content?.replace(/【.*?】/g, "").substring(0, 50)}...
                  </p>
                </div>
              ))
            )}
          </div>

          <div
            className="px-3 py-2 text-center text-sm text-primary cursor-pointer hover:bg-muted border-t"
            onClick={() => {
              navigate("/notifications");
              setOpen(false);
            }}
          >
            查看全部通知
          </div>
        </div>
      )}
    </div>
  );
}
