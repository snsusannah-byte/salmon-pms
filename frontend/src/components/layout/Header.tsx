import { NotificationBell } from "@/components/NotificationBell";

export function Header() {
  return (
    <header className="h-14 border-b bg-card flex items-center justify-between px-6">
      <h2 className="text-sm font-medium text-muted-foreground">
        三文鱼项目管理系统
      </h2>
      <div className="flex items-center gap-2">
        <NotificationBell />
      </div>
    </header>
  );
}
