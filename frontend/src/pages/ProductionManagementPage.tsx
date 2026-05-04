import React, { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { DailySlaughterPage } from "./DailySlaughterPage";
import { LossRecordsPage } from "./LossRecordsPage";
import { Scissors, AlertTriangle } from "lucide-react";

export function ProductionManagementPage() {
  const [activeTab, setActiveTab] = useState("slaughter");

  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-2xl font-bold">生产管理</h1>
        <p className="text-sm text-muted-foreground">宰杀记录与损耗处理</p>
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
