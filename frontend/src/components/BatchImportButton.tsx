import { useState, useRef } from "react";
import { Button } from "@/components/ui/button";
import { Upload, FileSpreadsheet, Download, X, AlertCircle } from "lucide-react";
import { toast } from "sonner";
import { api } from "@/lib/api";
import { useQueryClient } from "@tanstack/react-query";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "@/components/ui/dialog";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";
import { Label } from "@/components/ui/label";

type ImportType = "sales" | "companies" | "invoices" | "finance";

interface ImportConfig {
  label: string;
  templateHeaders: { en: string; cn: string }[];
  apiEndpoint: string;
  invalidateKeys: string[];
}

const IMPORT_CONFIG: Record<ImportType, ImportConfig> = {
  sales: {
    label: "销售记录",
    templateHeaders: [
      { en: "customer_name", cn: "客户名称" },
      { en: "contact_person", cn: "联系人" },
      { en: "phone", cn: "电话" },
      { en: "address", cn: "地址" },
      { en: "customer_category", cn: "客户分类" },
      { en: "sale_date", cn: "销售日期" },
      { en: "batch_code", cn: "批次编号" },
      { en: "weight_kg", cn: "重量(kg)" },
      { en: "unit_price", cn: "单价(USD)" },
      { en: "scan_fee", cn: "扫描费" },
      { en: "salesperson_name", cn: "业务员" },
      { en: "notes", cn: "备注" },
    ],
    apiEndpoint: "/v1/sales/batch-import",
    invalidateKeys: ["sales", "customers"],
  },
  companies: {
    label: "主体/客户",
    templateHeaders: [
      { en: "name", cn: "名称" },
      { en: "chinese_name", cn: "中文名称" },
      { en: "type", cn: "类型" },
      { en: "code", cn: "编号" },
      { en: "contact_person", cn: "联系人" },
      { en: "phone", cn: "电话" },
      { en: "email", cn: "邮箱" },
      { en: "address", cn: "地址" },
      { en: "registration_code", cn: "注册号" },
      { en: "coc_cert_no", cn: "COC证书号" },
      { en: "customer_category", cn: "客户分类" },
      { en: "credit_limit", cn: "信用额度" },
      { en: "notes", cn: "备注" },
    ],
    apiEndpoint: "/v1/companies/batch-import",
    invalidateKeys: ["companies", "customers"],
  },
  invoices: {
    label: "进口单证",
    templateHeaders: [
      { en: "invoice_no", cn: "发票号" },
      { en: "invoice_date", cn: "发票日期" },
      { en: "kill_date", cn: "宰杀日期" },
      { en: "processing_plant", cn: "加工厂" },
      { en: "fish_farm", cn: "渔场" },
      { en: "exporter", cn: "出口商" },
      { en: "awb_no", cn: "AWB号" },
      { en: "gross_weight_kg", cn: "毛重(kg)" },
      { en: "eta", cn: "ETA" },
      { en: "departure_date", cn: "发运日期" },
      { en: "flight_info", cn: "航班信息" },
      { en: "customs_status", cn: "报关状态" },
      { en: "notes", cn: "备注" },
    ],
    apiEndpoint: "/v1/invoices/batch-import",
    invalidateKeys: ["invoices"],
  },
  finance: {
    label: "财务记录",
    templateHeaders: [
      { en: "transaction_date", cn: "交易日期" },
      { en: "type", cn: "类型" },
      { en: "amount", cn: "金额" },
      { en: "currency", cn: "币种" },
      { en: "account_id", cn: "账户ID" },
      { en: "related_company", cn: "关联公司" },
      { en: "description", cn: "描述" },
      { en: "category", cn: "分类" },
      { en: "notes", cn: "备注" },
    ],
    apiEndpoint: "/v1/finance/batch-import",
    invalidateKeys: ["finance"],
  },
};

const PREVIEW_COUNT = 5;

export function BatchImportButton({ type }: { type: ImportType }) {
  const queryClient = useQueryClient();
  const [isUploading, setIsUploading] = useState(false);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [previewData, setPreviewData] = useState<any[]>([]);
  const [previewHeaders, setPreviewHeaders] = useState<string[]>([]);
  const [previewErrors, setPreviewErrors] = useState<string[]>([]);
  const [parsedRows, setParsedRows] = useState<any[]>([]);
  const [importFile, setImportFile] = useState<File | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const config = IMPORT_CONFIG[type];

  const downloadTemplate = () => {
    const headers = config.templateHeaders.map((h) => h.cn).join(",");
    const sample = config.templateHeaders.map(() => "").join(",");
    const csvContent = `data:text/csv;charset=utf-8,\uFEFF${headers}\n${sample}`;
    const encodedUri = encodeURI(csvContent);
    const link = document.createElement("a");
    link.setAttribute("href", encodedUri);
    link.setAttribute("download", `${config.label}导入模板.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    toast.success("模板已下载");
  };

  const parseCSV = (text: string) => {
    const lines = text.trim().split("\n");
    if (lines.length < 2) {
      throw new Error("文件内容为空，至少需要表头+一行数据");
    }

    const rawHeaders = lines[0].split(",").map((h) => h.trim().replace(/^\uFEFF/, ""));
    // Map Chinese headers to English
    const headerMap: Record<string, string> = {};
    const displayHeaders: string[] = [];

    rawHeaders.forEach((h) => {
      const found = config.templateHeaders.find((th) => th.cn === h || th.en === h);
      if (found) {
        headerMap[h] = found.en;
        displayHeaders.push(found.cn);
      } else {
        headerMap[h] = h;
        displayHeaders.push(h);
      }
    });

    const rows = lines
      .slice(1)
      .map((line, idx) => {
        const cells = line.split(",").map((c) => c.trim());
        const row: Record<string, any> = {};
        rawHeaders.forEach((h, i) => {
          const key = headerMap[h] || h;
          row[key] = cells[i] || "";
        });
        row.__line = idx + 2;
        return row;
      })
      .filter((r) => Object.values(r).some((v) => String(v).trim() !== "" && v !== r.__line));

    return {
      headers: displayHeaders,
      rawHeaders: rawHeaders.map((h) => headerMap[h] || h),
      rows,
    };
  };

  const validateRows = (rows: any[]) => {
    const errors: string[] = [];

    rows.forEach((row) => {
      if (type === "sales" && !row.customer_name) {
        errors.push(`第${row.__line}行：客户名称不能为空`);
      }
      if (type === "companies" && !row.name) {
        errors.push(`第${row.__line}行：名称不能为空`);
      }
      if (type === "invoices" && !row.invoice_no) {
        errors.push(`第${row.__line}行：发票号不能为空`);
      }
      if (type === "finance" && !row.transaction_date) {
        errors.push(`第${row.__line}行：交易日期不能为空`);
      }
    });

    return errors;
  };

  const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setImportFile(file);
    setIsUploading(true);
    try {
      const text = await file.text();
      const { headers, rawHeaders, rows } = parseCSV(text);

      if (rows.length === 0) {
        toast.error("未解析到有效数据行");
        setImportFile(null);
        return;
      }

      // 验证数据
      const errors = validateRows(rows);
      setPreviewHeaders(headers);
      setPreviewData(rows.slice(0, PREVIEW_COUNT));
      setPreviewErrors(errors);
      setParsedRows(rows);
    } catch (error: any) {
      toast.error(error.message || "解析失败");
      setImportFile(null);
    } finally {
      setIsUploading(false);
      if (fileInputRef.current) {
        fileInputRef.current.value = "";
      }
    }
  };

  const handleClearImport = () => {
    setImportFile(null);
    setPreviewData([]);
    setParsedRows([]);
    setPreviewErrors([]);
    setPreviewHeaders([]);
    if (fileInputRef.current) {
      fileInputRef.current.value = "";
    }
  };

  const handleConfirmImport = async () => {
    if (previewErrors.length > 0) {
      toast.error("请先修正数据错误");
      return;
    }

    setIsUploading(true);
    try {
      const res = await api.post(config.apiEndpoint, {
        rows: parsedRows,
      });

      const result = res.data;
      toast.success(
        `导入完成：新增 ${result.created || 0} 条，更新 ${result.updated || 0} 条`
      );

      config.invalidateKeys.forEach((key) => {
        queryClient.invalidateQueries({ queryKey: [key] });
      });

      setDialogOpen(false);
      handleClearImport();
    } catch (error: any) {
      toast.error(error.response?.data?.detail || error.message || "导入失败");
    } finally {
      setIsUploading(false);
    }
  };

  const templateExample = config.templateHeaders.map((h) => h.cn).join(" | ");

  return (
    <>
      <Button
        variant="outline"
        size="sm"
        onClick={() => setDialogOpen(true)}
      >
        <Upload className="h-4 w-4 mr-2" />
        批量导入
      </Button>

      {/* 导入弹窗 */}
      <Dialog open={dialogOpen} onOpenChange={(v) => { if (!v) { setDialogOpen(false); handleClearImport(); } }}>
        <DialogContent className="max-w-[900px] max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <FileSpreadsheet className="h-5 w-5" />
              批量导入{config.label}
            </DialogTitle>
          </DialogHeader>

          <div className="space-y-4 py-4">
            {/* 文件上传区域 */}
            <div
              className="border-2 border-dashed border-gray-300 rounded-lg p-8 text-center cursor-pointer hover:border-blue-400 hover:bg-blue-50/50 transition-colors"
              onClick={() => fileInputRef.current?.click()}
            >
              <input
                ref={fileInputRef}
                type="file"
                accept=".csv"
                className="hidden"
                onChange={handleFileChange}
              />
              <Upload className="w-12 h-12 text-gray-400 mx-auto mb-4" />
              <p className="text-gray-600 mb-2">
                {importFile ? importFile.name : "点击或拖拽 CSV 文件到此处"}
              </p>
              <p className="text-sm text-gray-400">支持 .csv 格式（UTF-8 编码）</p>
            </div>

            {/* 格式说明 + 模板下载 */}
            <div className="text-sm text-gray-600 space-y-2">
              <div className="flex items-center justify-between">
                <p className="font-medium">CSV 格式要求（第一行标题，数据从第二行开始）：</p>
                <Button variant="ghost" size="sm" onClick={downloadTemplate}>
                  <Download className="h-4 w-4 mr-2" />
                  下载模板
                </Button>
              </div>
              <div className="bg-slate-50 p-3 rounded text-xs font-mono overflow-x-auto">
                {templateExample}
              </div>
              <p className="text-xs text-gray-500">
                💡 请使用中文表头或英文表头，系统会自动匹配字段
              </p>
            </div>

            {/* 错误提示 */}
            {previewErrors.length > 0 && (
              <div className="space-y-2">
                <div className="flex items-center gap-2 text-red-500 font-medium text-sm">
                  <AlertCircle className="h-4 w-4" />
                  发现 {previewErrors.length} 个问题，请修正后重新上传
                </div>
                <div className="bg-red-50 rounded-lg p-3 space-y-1 max-h-32 overflow-y-auto">
                  {previewErrors.map((err, i) => (
                    <p key={i} className="text-xs text-red-600">
                      {err}
                    </p>
                  ))}
                </div>
              </div>
            )}

            {/* 导入预览 */}
            {previewData.length > 0 && (
              <div className="border rounded-lg overflow-hidden">
                <div className="bg-slate-50 px-3 py-2 text-sm font-medium flex items-center justify-between">
                  <span>导入预览</span>
                  <Badge variant="secondary">{parsedRows.length} 条</Badge>
                </div>
                <div className="max-h-60 overflow-y-auto">
                  <Table>
                    <TableHeader className="bg-muted sticky top-0">
                      <TableRow>
                        {previewHeaders.map((key) => (
                          <TableHead key={key} className="text-xs whitespace-nowrap">
                            {key}
                          </TableHead>
                        ))}
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {previewData.map((row, i) => (
                        <TableRow key={i}>
                          {previewHeaders.map((key, j) => {
                            const rawKey =
                              config.templateHeaders.find((th) => th.cn === key)?.en || key;
                            const val = row[rawKey] || "";
                            const hasError =
                              previewErrors.some(
                                (e) =>
                                  e.includes(`第${row.__line}行`) && !val
                              );
                            return (
                              <TableCell
                                key={j}
                                className="text-xs max-w-[120px] truncate"
                                title={String(val)}
                              >
                                {hasError ? (
                                  <Badge variant="destructive" className="text-[10px]">
                                    必填
                                  </Badge>
                                ) : (
                                  String(val) || "-"
                                )}
                              </TableCell>
                            );
                          })}
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                  {parsedRows.length > PREVIEW_COUNT && (
                    <div className="px-2 py-2 text-xs text-gray-500 text-center bg-muted/30">
                      ... 还有 {parsedRows.length - PREVIEW_COUNT} 条数据
                    </div>
                  )}
                </div>
              </div>
            )}
          </div>

          <DialogFooter className="gap-2">
            <Button
              variant="outline"
              onClick={() => {
                setDialogOpen(false);
                handleClearImport();
              }}
            >
              <X className="h-4 w-4 mr-2" />
              取消
            </Button>
            {importFile && (
              <Button variant="ghost" onClick={handleClearImport} disabled={isUploading}>
                重新选择
              </Button>
            )}
            <Button
              onClick={handleConfirmImport}
              disabled={isUploading || parsedRows.length === 0 || previewErrors.length > 0}
            >
              {isUploading ? "导入中..." : `确认导入 (${parsedRows.length} 条)`}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
}
