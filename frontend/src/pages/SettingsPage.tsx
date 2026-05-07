import { useState, useEffect } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { toast } from "sonner";
import { Save, User, Bell, Shield, Palette, Loader2 } from "lucide-react";

interface UserProfile {
  id: number;
  username: string;
  email: string;
  full_name: string | null;
  phone: string | null;
  role: string;
  is_active: boolean;
}

interface UserPreferences {
  notify_customs_change: boolean;
  notify_batch_lock: boolean;
  notify_payment: boolean;
  compact_mode: boolean;
  auto_refresh: boolean;
}

interface UserSettings {
  profile: UserProfile;
  preferences: UserPreferences;
}

export function SettingsPage() {
  const qc = useQueryClient();

  // 获取设置
  const { data, isLoading } = useQuery({
    queryKey: ["settings"],
    queryFn: async () => {
      const res = await api.get("/v1/settings/me");
      return res.data as UserSettings;
    },
  });

  // 更新设置
  const updateMutation = useMutation({
    mutationFn: async (payload: any) => {
      const res = await api.put("/v1/settings/me", payload);
      return res.data as UserSettings;
    },
    onSuccess: () => {
      toast.success("设置保存成功");
      qc.invalidateQueries({ queryKey: ["settings"] });
    },
    onError: (err: any) => {
      toast.error(err.response?.data?.detail || "保存失败");
    },
  });

  // 修改密码
  const passwordMutation = useMutation({
    mutationFn: async (payload: any) => {
      const res = await api.post("/v1/settings/me/password", payload);
      return res.data;
    },
    onSuccess: () => {
      toast.success("密码修改成功");
      setOldPassword("");
      setNewPassword("");
      setConfirmPassword("");
    },
    onError: (err: any) => {
      toast.error(err.response?.data?.detail || "密码修改失败");
    },
  });

  // 本地表单状态
  const [displayName, setDisplayName] = useState("");
  const [email, setEmail] = useState("");
  const [phone, setPhone] = useState("");

  const [notifyCustoms, setNotifyCustoms] = useState(true);
  const [notifyBatchLock, setNotifyBatchLock] = useState(true);
  const [notifyPayment, setNotifyPayment] = useState(false);
  const [compactMode, setCompactMode] = useState(false);
  const [autoRefresh, setAutoRefresh] = useState(true);

  const [oldPassword, setOldPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");

  // 数据加载后同步到本地状态
  useEffect(() => {
    if (data) {
      setDisplayName(data.profile.full_name || "");
      setEmail(data.profile.email || "");
      setPhone(data.profile.phone || "");
      setNotifyCustoms(data.preferences.notify_customs_change);
      setNotifyBatchLock(data.preferences.notify_batch_lock);
      setNotifyPayment(data.preferences.notify_payment);
      setCompactMode(data.preferences.compact_mode);
      setAutoRefresh(data.preferences.auto_refresh);
    }
  }, [data]);

  const handleSaveProfile = () => {
    updateMutation.mutate({
      profile: {
        full_name: displayName,
        email: email || undefined,
        phone: phone || undefined,
      },
    });
  };

  const handleSavePreferences = () => {
    updateMutation.mutate({
      preferences: {
        notify_customs_change: notifyCustoms,
        notify_batch_lock: notifyBatchLock,
        notify_payment: notifyPayment,
        compact_mode: compactMode,
        auto_refresh: autoRefresh,
      },
    });
  };

  const handleChangePassword = () => {
    if (!oldPassword || !newPassword || !confirmPassword) {
      toast.error("请填写所有密码字段");
      return;
    }
    passwordMutation.mutate({
      old_password: oldPassword,
      new_password: newPassword,
      confirm_password: confirmPassword,
    });
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
      </div>
    );
  }

  return (
    <div className="space-y-6 max-w-2xl">
      <div>
        <h1 className="text-2xl font-bold">系统设置</h1>
        <p className="text-sm text-muted-foreground">个人偏好、通知、安全设置</p>
      </div>

      {/* 个人资料 */}
      <Card>
        <CardHeader className="flex flex-row items-center gap-2">
          <User className="h-4 w-4 text-muted-foreground" />
          <div>
            <CardTitle className="text-base">个人资料</CardTitle>
            <CardDescription className="text-xs">修改显示名称和联系方式</CardDescription>
          </div>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="display_name">显示名称</Label>
              <Input
                id="display_name"
                value={displayName}
                onChange={(e) => setDisplayName(e.target.value)}
                placeholder="Administrator"
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="email">邮箱</Label>
              <Input
                id="email"
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="admin@salmon.com"
              />
            </div>
          </div>
          <div className="space-y-2">
            <Label htmlFor="phone">电话</Label>
            <Input
              id="phone"
              value={phone}
              onChange={(e) => setPhone(e.target.value)}
              placeholder="可选"
            />
          </div>
          <div className="flex justify-end">
            <Button
              onClick={handleSaveProfile}
              disabled={updateMutation.isPending}
              size="sm"
            >
              <Save className="h-4 w-4 mr-2" />
              {updateMutation.isPending ? "保存中..." : "保存资料"}
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* 通知设置 */}
      <Card>
        <CardHeader className="flex flex-row items-center gap-2">
          <Bell className="h-4 w-4 text-muted-foreground" />
          <div>
            <CardTitle className="text-base">通知设置</CardTitle>
            <CardDescription className="text-xs">配置消息提醒方式</CardDescription>
          </div>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <div className="text-sm font-medium">报关状态变更</div>
              <div className="text-xs text-muted-foreground">发票报关状态更新时通知</div>
            </div>
            <input
              type="checkbox"
              checked={notifyCustoms}
              onChange={(e) => setNotifyCustoms(e.target.checked)}
              className="h-4 w-4"
            />
          </div>
          <div className="border-t" />
          <div className="flex items-center justify-between">
            <div>
              <div className="text-sm font-medium">批次锁定提醒</div>
              <div className="text-xs text-muted-foreground">批次被锁定时通知</div>
            </div>
            <input
              type="checkbox"
              checked={notifyBatchLock}
              onChange={(e) => setNotifyBatchLock(e.target.checked)}
              className="h-4 w-4"
            />
          </div>
          <div className="border-t" />
          <div className="flex items-center justify-between">
            <div>
              <div className="text-sm font-medium">收款到账</div>
              <div className="text-xs text-muted-foreground">销售收款记录新增时通知</div>
            </div>
            <input
              type="checkbox"
              checked={notifyPayment}
              onChange={(e) => setNotifyPayment(e.target.checked)}
              className="h-4 w-4"
            />
          </div>
          <div className="flex justify-end">
            <Button
              onClick={handleSavePreferences}
              disabled={updateMutation.isPending}
              size="sm"
            >
              <Save className="h-4 w-4 mr-2" />
              {updateMutation.isPending ? "保存中..." : "保存偏好"}
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* 安全设置 */}
      <Card>
        <CardHeader className="flex flex-row items-center gap-2">
          <Shield className="h-4 w-4 text-muted-foreground" />
          <div>
            <CardTitle className="text-base">安全设置</CardTitle>
            <CardDescription className="text-xs">修改密码和登录设置</CardDescription>
          </div>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="old_password">当前密码</Label>
            <Input
              id="old_password"
              type="password"
              value={oldPassword}
              onChange={(e) => setOldPassword(e.target.value)}
              placeholder="输入当前密码"
            />
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="new_password">新密码</Label>
              <Input
                id="new_password"
                type="password"
                value={newPassword}
                onChange={(e) => setNewPassword(e.target.value)}
                placeholder="输入新密码"
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="confirm_password">确认新密码</Label>
              <Input
                id="confirm_password"
                type="password"
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                placeholder="再次输入新密码"
              />
            </div>
          </div>
          <div className="flex justify-end">
            <Button
              onClick={handleChangePassword}
              disabled={passwordMutation.isPending}
              size="sm"
            >
              <Save className="h-4 w-4 mr-2" />
              {passwordMutation.isPending ? "修改中..." : "修改密码"}
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* 界面设置 */}
      <Card>
        <CardHeader className="flex flex-row items-center gap-2">
          <Palette className="h-4 w-4 text-muted-foreground" />
          <div>
            <CardTitle className="text-base">界面设置</CardTitle>
            <CardDescription className="text-xs">主题和显示偏好</CardDescription>
          </div>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <div className="text-sm font-medium">紧凑模式</div>
              <div className="text-xs text-muted-foreground">减小表格行高和间距</div>
            </div>
            <input
              type="checkbox"
              checked={compactMode}
              onChange={(e) => setCompactMode(e.target.checked)}
              className="h-4 w-4"
            />
          </div>
          <div className="border-t" />
          <div className="flex items-center justify-between">
            <div>
              <div className="text-sm font-medium">自动刷新</div>
              <div className="text-xs text-muted-foreground">看板数据每 30 秒自动刷新</div>
            </div>
            <input
              type="checkbox"
              checked={autoRefresh}
              onChange={(e) => setAutoRefresh(e.target.checked)}
              className="h-4 w-4"
            />
          </div>
          <div className="flex justify-end">
            <Button
              onClick={handleSavePreferences}
              disabled={updateMutation.isPending}
              size="sm"
            >
              <Save className="h-4 w-4 mr-2" />
              {updateMutation.isPending ? "保存中..." : "保存偏好"}
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
