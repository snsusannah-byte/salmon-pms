import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { toast } from "sonner";
import { Save, User, Bell, Shield, Palette } from "lucide-react";

export function SettingsPage() {
  const [loading, setLoading] = useState(false);

  const handleSave = () => {
    setLoading(true);
    setTimeout(() => {
      toast.success("设置保存成功（演示）");
      setLoading(false);
    }, 600);
  };

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
              <Input id="display_name" placeholder="Administrator" />
            </div>
            <div className="space-y-2">
              <Label htmlFor="email">邮箱</Label>
              <Input id="email" type="email" placeholder="admin@salmon.com" />
            </div>
          </div>
          <div className="space-y-2">
            <Label htmlFor="phone">电话</Label>
            <Input id="phone" placeholder="可选" />
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
            <input type="checkbox" defaultChecked className="h-4 w-4" />
          </div>
          <div className="border-t" />
          <div className="flex items-center justify-between">
            <div>
              <div className="text-sm font-medium">批次锁定提醒</div>
              <div className="text-xs text-muted-foreground">批次被锁定时通知</div>
            </div>
            <input type="checkbox" defaultChecked className="h-4 w-4" />
          </div>
          <div className="border-t" />
          <div className="flex items-center justify-between">
            <div>
              <div className="text-sm font-medium">收款到账</div>
              <div className="text-xs text-muted-foreground">销售收款记录新增时通知</div>
            </div>
            <input type="checkbox" className="h-4 w-4" />
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
            <Input id="old_password" type="password" placeholder="输入当前密码" />
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="new_password">新密码</Label>
              <Input id="new_password" type="password" placeholder="输入新密码" />
            </div>
            <div className="space-y-2">
              <Label htmlFor="confirm_password">确认新密码</Label>
              <Input id="confirm_password" type="password" placeholder="再次输入新密码" />
            </div>
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
            <input type="checkbox" className="h-4 w-4" />
          </div>
          <div className="border-t" />
          <div className="flex items-center justify-between">
            <div>
              <div className="text-sm font-medium">自动刷新</div>
              <div className="text-xs text-muted-foreground">看板数据每 30 秒自动刷新</div>
            </div>
            <input type="checkbox" defaultChecked className="h-4 w-4" />
          </div>
        </CardContent>
      </Card>

      <div className="flex justify-end">
        <Button onClick={handleSave} disabled={loading}>
          <Save className="h-4 w-4 mr-2" />
          {loading ? "保存中..." : "保存设置"}
        </Button>
      </div>
    </div>
  );
}
