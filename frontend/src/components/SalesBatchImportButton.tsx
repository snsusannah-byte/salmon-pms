import { useState, useRef } from "react";
import { Button } from "@/components/ui/button";
import { Upload, FileSpreadsheet } from "lucide-react";
import { toast } from "sonner";
import { api } from "@/lib/api";
import { useQueryClient } from "@tanstack/react-query";

export function SalesBatchImportButton() {
  const queryClient = useQueryClient();
  const [isUploading, setIsUploading] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleFileSelect = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setIsUploading(true);
    try {
      const text = await file.text();
      const lines = text.trim().split("\n");
      if (lines.length < 2) {
        toast.error("文件内容为空或格式错误");
        return;
      }

      // 解析CSV（简单实现：假设第一行是表头）
      const headers = lines[0].split(",").map((h) => h.trim());
      const rows = lines.slice(1).map((line) => {
        const cells = line.split(",").map((c) => c.trim());
        const row: Record<string, string> = {};
        headers.forEach((h, i) => {
          row[h] = cells[i] || "";
        });
        return row;
      });

      // 提取客户信息并批量导入客户
      const customers = rows
        .filter((r) => r.customer_name)
        .map((r) => ({
          name: r.customer_name,
          contact_person: r.contact_person || undefined,
          phone: r.phone || undefined,
          address: r.address || undefined,
          customer_category: r.customer_category || undefined,
        }));

      if (customers.length > 0) {
        const customerRes = await api.post("/v1/companies/batch-import", customers);
        toast.success(
          `客户导入完成：新增 ${customerRes.data.created} 个，更新 ${customerRes.data.updated} 个`
        );
      }

      // TODO: 继续导入销售记录
      toast.success(`解析到 ${rows.length} 条销售记录，客户已自动处理`);
      queryClient.invalidateQueries({ queryKey: ["customers"] });
      queryClient.invalidateQueries({ queryKey: ["sales"] });
    } catch (error: any) {
      toast.error(error.response?.data?.detail || "导入失败");
    } finally {
      setIsUploading(false);
      if (fileInputRef.current) {
        fileInputRef.current.value = "";
      }
    }
  };

  return (
    <>
      <input
        ref={fileInputRef}
        type="file"
        accept=".csv"
        className="hidden"
        onChange={handleFileSelect}
      />
      <Button
        variant="outline"
        onClick={() => fileInputRef.current?.click()}
        disabled={isUploading}
      >
        <Upload className="h-4 w-4 mr-2" />
        {isUploading ? "导入中..." : "批量导入"}
      </Button>
    </>
  );
}
