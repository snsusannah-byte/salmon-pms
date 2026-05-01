import { useState } from "react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import {
  FileBarChart,
  FileSpreadsheet,
  FileText,
  Download,
  TrendingUp,
  Package,
  DollarSign,
  Calendar,
} from "lucide-react";

interface ReportItem {
  id: string;
  title: string;
  description: string;
  icon: React.ElementType;
  status: "ready" | "wip" | "placeholder";
  formats: string[];
}

const reports: ReportItem[] = [
  {
    id: "batch-report",
    title: "批次财报",
    description: "按批次汇总：采购成本、税费、清关费、销售总额、净利润",
    icon: Package,
    status: "wip",
    formats: ["Excel", "PDF"],
  },
  {
    id: "invoice-report",
    title: "单票财报",
    description: "按发票明细：采购金额、税费、清关费、分摊利润",
    icon: FileText,
    status: "wip",
    formats: ["Excel", "PDF"],
  },
  {
    id: "financial-statements",
    title: "三大财务报表",
    description: "利润表、资产负债表、现金流量表",
    icon: TrendingUp,
    status: "placeholder",
    formats: ["Excel"],
  },
  {
    id: "sales-summary",
    title: "销售汇总",
    description: "按客户/月份汇总销售额、收款、欠款",
    icon: DollarSign,
    status: "wip",
    formats: ["Excel"],
  },
  {
    id: "inventory-report",
    title: "库存报表",
    description: "实时库存、批次分布、规格汇总",
    icon: FileBarChart,
    status: "placeholder",
    formats: ["Excel"],
  },
  {
    id: "customs-report",
    title: "报关汇总",
    description: "按月份统计报关状态、清关时长",
    icon: Calendar,
    status: "placeholder",
    formats: ["Excel"],
  },
];

const statusMap: Record<string, { label: string; color: string }> = {
  ready: { label: "可用", color: "bg-green-100 text-green-800" },
  wip: { label: "开发中", color: "bg-yellow-100 text-yellow-800" },
  placeholder: { label: "规划中", color: "bg-gray-100 text-gray-800" },
};

export function ReportsPage() {
  const [exporting, setExporting] = useState<string | null>(null);

  const handleExport = (reportId: string, format: string) => {
    setExporting(`${reportId}-${format}`);
    // Simulate export
    setTimeout(() => {
      toast.info(`${format} 导出功能开发中`);
      setExporting(null);
    }, 800);
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">报表中心</h1>
        <p className="text-sm text-muted-foreground">
          财务报表、业务报表、数据导出
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {reports.map((report) => {
          const Icon = report.icon;
          const status = statusMap[report.status];
          return (
            <Card key={report.id} className="flex flex-col">
              <CardHeader className="pb-3">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <div className="p-2 bg-muted rounded-md">
                      <Icon className="h-4 w-4" />
                    </div>
                    <CardTitle className="text-base">{report.title}</CardTitle>
                  </div>
                  <Badge variant="secondary" className={`text-xs ${status.color}`}>
                    {status.label}
                  </Badge>
                </div>
                <CardDescription className="text-xs mt-1">
                  {report.description}
                </CardDescription>
              </CardHeader>
              <CardContent className="flex-1 flex flex-col justify-end pt-0">
                <div className="flex gap-2">
                  {report.formats.map((fmt) => (
                    <Button
                      key={fmt}
                      variant="outline"
                      size="sm"
                      className="text-xs h-8"
                      disabled={report.status !== "ready"}
                      onClick={() => handleExport(report.id, fmt)}
                    >
                      {exporting === `${report.id}-${fmt}` ? (
                        "导出中..."
                      ) : (
                        <>
                          <Download className="h-3 w-3 mr-1" />
                          {fmt}
                        </>
                      )}
                    </Button>
                  ))}
                </div>
              </CardContent>
            </Card>
          );
        })}
      </div>
    </div>
  );
}
