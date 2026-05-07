import * as XLSX from "xlsx";

interface ExportColumn {
  header: string;
  key: string;
  format?: (value: any) => string;
}

export function exportExcel(
  data: any[],
  columns: ExportColumn[],
  filename: string = "export",
) {
  if (!data || data.length === 0) {
    return false;
  }

  // Build rows
  const rows = data.map((row) =>
    columns.map((col) => {
      const raw = row[col.key];
      if (col.format) {
        return col.format(raw);
      }
      if (raw === null || raw === undefined) {
        return "";
      }
      return String(raw);
    }),
  );

  // Build worksheet
  const ws = XLSX.utils.aoa_to_sheet([columns.map((c) => c.header), ...rows]);

  // Auto-width (rough estimate)
  const widths = columns.map((col) => ({
    wch: Math.max(col.header.length, 12),
  }));
  ws["!cols"] = widths;

  // Build workbook
  const wb = XLSX.utils.book_new();
  XLSX.utils.book_append_sheet(wb, ws, "Sheet1");

  // Download
  const dateStr = new Date().toISOString().slice(0, 10).replace(/-/g, "");
  XLSX.writeFile(wb, `${filename}_${dateStr}.xlsx`);
  return true;
}

// 常用格式化函数
export const formatters = {
  currency: (v: number, symbol = "¥") => (v ? `${symbol}${Number(v).toLocaleString()}` : ""),
  date: (v: string) => v || "",
  number: (v: number) => (v !== undefined && v !== null ? String(v) : ""),
  percent: (v: number) => (v ? `${v}%` : ""),
};
