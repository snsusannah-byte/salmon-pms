import React, { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Card, CardContent } from "@/components/ui/card";
import { DailySlaughterPage } from "./DailySlaughterPage";
import { LossRecordsPage } from "./LossRecordsPage";
import { Scissors, AlertTriangle, TrendingUp, Calendar, Scale } from "lucide-react";

interface SlaughterSummary {
  total_days: number;
  total_fish_count: number;
  total_meat_kg: number;
  avg_meat_rate: number;
  avg_cost_price: number;
  total_loss_kg: number;
  avg_loss_rate: number;
}

interface LossSummary {
  total_records: number;
  total_weight_kg: number;
  total_quantity: number;
  by_type: Record<string, { count: number; weight_kg: number }>;
}

export function ProductionManagementPage() {
  const [activeTab, setActiveTab] = useState("slaughter");

  const { data: slaughterSummary } = useQuery<SlaughterSummary>({
    queryKey: ["slaughter-summary"],
    queryFn: async () => {
      const res = await api.get("/v1/daily-slaughter/summary/stats");
      return res.data;
    },
  });

  const { data: lossSummary } = useQuery<LossSummary>({
    queryKey: ["loss-summary"],
    queryFn: async () => {
      const res = await api.get("/v1/loss-records/summary/stats");
      return res.data;
    },
  });

  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-2xl font-bold">生产管理</h1>
        <p className="text-sm text-muted-foreground">宰杀记录与损耗处理</p>
      </div>

      {/* 汇总卡片 */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <div className="space-y-1">
                <p className="text-xs text-muted-foreground">宰杀天数</p>
                <p className="text-xl font-bold">{slaughterSummary?.total_days ?? 0} 天</p>
              </div>
              <div className="p-2 bg-blue-100 rounded-full">
                <Calendar className="h-4 w-4 text-blue-600" />
              </div>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <div className="space-y-1">
                <p className="text-xs text-muted-foreground">成品肉产出</p>
                <p className="text-xl font-bold">{slaughterSummary?.total_meat_kg?.toFixed(1) ?? "0.0"} kg</p>
              </div>
              <div className="p-2 bg-green-100 rounded-full">
                <Scale className="h-4 w-4 text-green-600" />
              </div>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <div className="space-y-1">
                <p className="text-xs text-muted-foreground">平均出肉率</p>
                <p className="text-xl font-bold">{slaughterSummary?.avg_meat_rate?.toFixed(1) ?? "0.0"}%</p>
              </div>
              <div className="p-2 bg-amber-100 rounded-full">
                <TrendingUp className="h-4 w-4 text-amber-600" />
              </div>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <div className="space-y-1">
                <p className="text-xs text-muted-foreground">损耗记录</p>
                <p className="text-xl font-bold">{lossSummary?.total_records ?? 0} 条</p>
              </div>
              <div className="p-2 bg-red-100 rounded-full">
                <AlertTriangle className="h-4 w-4 text-red-600" />
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList className="grid w-full grid-cols-2">
          <TabsTrigger value="slaughter">
            <Scissors className="h-4 w-4 mr-1" />
            宰杀记录
          </TabsTrigger>
          <TabsTrigger value="loss">
            <AlertTriangle className="h-4 w-4 mr-1" />
            损耗处理
          </TabsTrigger>
        </TabsList>

        <TabsContent value="slaughter" className="pt-4">
          <DailySlaughterPage />
        </TabsContent>
        <TabsContent value="loss" className="pt-4">
          <LossRecordsPage />
        </TabsContent>
      </Tabs>
    </div>
  );
}
