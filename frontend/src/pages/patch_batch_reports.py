#!/usr/bin/env python3
"""BatchReportsTab.tsx 批量打印功能重构脚本"""
import re

with open('/home/sannah/.openclaw/workspace-codeingman/projects/salmon-pms/frontend/src/pages/BatchReportsTab.tsx', 'r') as f:
    content = f.read()

# 1. 在导入中添加 Checkbox
old_import = 'import { Loader2, Eye, Printer, Languages, Search } from "lucide-react";'
new_import = 'import { Loader2, Eye, Printer, Languages, Search } from "lucide-react";\nimport { Checkbox } from "@/components/ui/checkbox";'
if old_import in content:
    content = content.replace(old_import, new_import)
    print("✓ 添加 Checkbox 导入")
else:
    print("✗ 未找到导入行")

# 2. 添加 selectedBatchIds 状态（在 detailLang 之后）
old_state = '''const [lockConfirmOpen, setLockConfirmOpen] = useState(false);
  const queryClient = useQueryClient();'''
new_state = '''const [lockConfirmOpen, setLockConfirmOpen] = useState(false);
  const [selectedBatchIds, setSelectedBatchIds] = useState<number[]>([]);
  const queryClient = useQueryClient();'''
if old_state in content:
    content = content.replace(old_state, new_state)
    print("✓ 添加 selectedBatchIds 状态")
else:
    print("✗ 未找到状态声明位置")

# 3. 在表格上方工具栏添加批量打印按钮（在 searchKey Input 之后、Card 之前）
old_toolbar = '''      <div className="flex flex-wrap items-end gap-3">
        <DateFilter
          startDate={startDate}
          endDate={endDate}
          onStartChange={setStartDate}
          onEndChange={setEndDate}
          onSearch={() => setPage(0)}
        />
        <div className="ml-auto">
          <Input
            placeholder="搜索批次名称/编号"
            className="h-8 w-48"
            value={searchKey}
            onChange={(e) => { setSearchKey(e.target.value); setPage(0); }}
          />
        </div>
      </div>'''
new_toolbar = '''      <div className="flex flex-wrap items-end gap-3">
        <DateFilter
          startDate={startDate}
          endDate={endDate}
          onStartChange={setStartDate}
          onEndChange={setEndDate}
          onSearch={() => setPage(0)}
        />
        <div className="ml-auto flex items-center gap-2">
          {selectedBatchIds.length > 0 && (
            <span className="text-xs text-muted-foreground">
              已选 {selectedBatchIds.length} 项
            </span>
          )}
          {selectedBatchIds.length > 0 && (
            <Button
              size="sm"
              variant="outline"
              className="h-8 gap-1"
              onClick={async () => {
                // 批量打印
                const printLang = detailLang;
                try {
                  const responses = await Promise.all(
                    selectedBatchIds.map(id => api.get(`/v1/reports/batch/${id}`))
                  );
                  const pages: string[] = [];
                  for (let i = 0; i < responses.length; i++) {
                    const d = responses[i].data;
                    const pageHTML = generateBatchReportHTML(d, printLang);
                    // 提取 .page 内容
                    const match = pageHTML.match(/<div class="page">([\\s\\S]*?)<\\/div><\\/body><\\/html>/);
                    const bodyContent = match ? match[1] : pageHTML;
                    pages.push(`<div class="page">${bodyContent}</div>`);
                    if (i < responses.length - 1) {
                      pages.push('<div style="page-break-after: always;"></div>');
                    }
                  }
                  const fullHTML = `<!DOCTYPE html>
<html><head><meta charset="UTF-8"><title>批次财报批量打印</title>
<style>
  @page { size: A4; margin: 10mm; }
  body { font-family: system-ui, sans-serif; margin: 0; padding: 0; color: #333; font-size: 10pt; }
  .page { max-width: 190mm; margin: 0 auto; padding: 10mm; }
  h1 { font-size: 16pt; font-weight: bold; color: #1e293b; margin-bottom: 4pt; }
  h2 { font-size: 10pt; font-weight: normal; color: #64748b; margin-bottom: 8pt; }
  .section { margin-bottom: 10pt; border: 1px solid #ddd; border-radius: 4pt; padding: 8pt; }
  .section-title { font-size: 10pt; font-weight: bold; margin-bottom: 4pt; }
  .grid-2 { display: grid; grid-template-columns: 1fr 1fr; gap: 8pt; }
  .grid-3 { display: grid; grid-template-columns: repeat(3, 1fr); gap: 8pt; }
  .row { display: flex; justify-content: space-between; padding: 2pt 0; border-bottom: 1px solid #eee; font-size: 9pt; }
  .row.bold { font-weight: bold; }
  .row.pl { padding-left: 8pt; }
  table { width: 100%; border-collapse: collapse; font-size: 8.5pt; margin-top: 4pt; }
  th, td { border: 1px solid #ddd; padding: 2pt 4pt; text-align: left; }
  th { background: #f5f5f5; }
  td.num, th.num { text-align: right; }
  .highlight { background: #eff6ff; padding: 4pt; border-radius: 2pt; }
  .red { color: #dc2626; }
  .green { color: #16a34a; }
  .blue { color: #2563eb; }
  .purple { color: #7c3aed; }
  .footer { text-align: center; font-size: 8pt; color: #999; margin-top: 10pt; padding-top: 4pt; border-top: 1px solid #ddd; }
  .trace-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 6pt; text-align: center; }
  .trace-item .icon { font-size: 14pt; margin-bottom: 2pt; }
  .trace-item .label { font-size: 7.5pt; color: #999; }
  .trace-item .value { font-size: 8pt; font-weight: 500; }
  .profit-bar { display: grid; grid-template-columns: repeat(3, 1fr); gap: 6pt; text-align: center; background: #f3f4f6; border-radius: 4pt; padding: 6pt; }
  .profit-bar .label { font-size: 8pt; color: #6b7280; margin-bottom: 2pt; }
  .profit-bar .value { font-size: 9pt; font-weight: 600; }
  .totals-bar { display: flex; justify-content: space-between; align-items: center; background: #1e293b; color: white; border-radius: 4pt; padding: 6pt 10pt; font-size: 9pt; }
  .totals-bar .label { font-weight: 600; }
  .totals-bar .green { color: #4ade80; }
</style></head><body>
  ${pages.join('')}
  <div class="footer">由 Salmon PMS 生成<br>打印时间: ${new Date().toLocaleString('zh-CN')}</div>
</body></html>`;
                  const w = window.open('', '_blank');
                  if (w) {
                    w.document.write(fullHTML);
                    w.document.close();
                    setTimeout(() => w.print(), 500);
                  }
                } catch (e: any) {
                  toast.error(`批量打印失败: ${e.message}`);
                }
              }}
            >
              <Printer className="h-3.5 w-3.5" />
              批量打印
            </Button>
          )}
          <Input
            placeholder="搜索批次名称/编号"
            className="h-8 w-48"
            value={searchKey}
            onChange={(e) => { setSearchKey(e.target.value); setPage(0); }}
          />
        </div>
      </div>'''
if old_toolbar in content:
    content = content.replace(old_toolbar, new_toolbar)
    print("✓ 添加批量打印按钮")
else:
    print("✗ 未找到工具栏位置")

# 4. 修改表格列：首列加 Checkbox，colSpan 从 14 改为 15
content = content.replace('colSpan={14}', 'colSpan={15}')
print("✓ 修改 colSpan")

# 5. 在表格头添加 Checkbox 列
old_thead = '''<TableHead className="text-xs">批次编号</TableHead>
                <TableHead className="text-xs">批次名称</TableHead>'''
new_thead = '''<TableHead className="text-xs w-8">
                  <Checkbox
                    checked={filtered.length > 0 && filtered.every((item: any) => selectedBatchIds.includes(item.batch_id))}
                    onCheckedChange={(checked) => {
                      if (checked) {
                        setSelectedBatchIds(filtered.map((item: any) => item.batch_id));
                      } else {
                        setSelectedBatchIds([]);
                      }
                    }}
                  />
                </TableHead>
                <TableHead className="text-xs">批次编号</TableHead>
                <TableHead className="text-xs">批次名称</TableHead>'''
if old_thead in content:
    content = content.replace(old_thead, new_thead)
    print("✓ 添加表头 Checkbox")
else:
    print("✗ 未找到表头位置")

# 6. 在表格行添加 Checkbox 列
old_row_start = '''<TableRow key={item.batch_id}>
                    <TableCell className="text-xs font-medium">{item.batch_code}</TableCell>'''
new_row_start = '''<TableRow key={item.batch_id}>
                    <TableCell className="text-xs w-8">
                      <Checkbox
                        checked={selectedBatchIds.includes(item.batch_id)}
                        onCheckedChange={(checked) => {
                          if (checked) {
                            setSelectedBatchIds(prev => [...prev, item.batch_id]);
                          } else {
                            setSelectedBatchIds(prev => prev.filter(id => id !== item.batch_id));
                          }
                        }}
                      />
                    </TableCell>
                    <TableCell className="text-xs font-medium">{item.batch_code}</TableCell>'''
if old_row_start in content:
    content = content.replace(old_row_start, new_row_start)
    print("✓ 添加行 Checkbox")
else:
    print("✗ 未找到行位置")

# 7. 提取 generateBatchReportHTML 函数（放在 fmtDate 之后、DateFilter 之前）
# 在 function DateFilter 之前插入
insert_point = 'function DateFilter({'
if insert_point in content:
    # 构造 generateBatchReportHTML 函数
    gen_func = '''function generateBatchReportHTML(detailData: any, lang: "zh" | "en"): string {
  const isEn = lang === 'en';
  const t = {
    title: isEn ? 'Financial Report' : '财务报告',
    purchaseInfo: isEn ? 'Purchase Info' : '采购信息',
    importCost: isEn ? 'Import Costs' : '进口费用',
    exchange: isEn ? 'Exchange' : '购汇登记',
    profitLoss: isEn ? 'Profit/Loss' : '损益分析',
    salesDetail: isEn ? 'Sales Details' : '销售明细',
    traceInfo: isEn ? 'Traceability' : '溯源信息',
    invoiceNo: isEn ? 'Invoice No.' : '发票号',
    date: isEn ? 'Date' : '日期',
    customer: isEn ? 'Customer' : '客户',
    spec: isEn ? 'Spec' : '规格',
    weight: isEn ? 'Weight' : '重量',
    price: isEn ? 'Unit Price' : '单价',
    net: isEn ? 'Net Amount' : '净额',
    totalPurchase: isEn ? 'Total Purchase' : '总采购',
    totalSales: isEn ? 'Total Sales' : '总销售',
    netProfit: isEn ? 'Net Profit' : '净利润',
    footer: isEn ? 'Generated by Salmon PMS' : '由 Salmon PMS 生成',
  };
  const proportion = Number(detailData.sales_proportion || 1);
  const salesRows = (detailData.sales || []).map((s: any) => `
    <tr><td>${fmtDate(s.sale_date)}</td><td>${s.customer_name || '-'}</td><td>${s.spec || '-'}</td><td style="text-align:right">${s.box_count || 0}</td><td style="text-align:right">${Number((s.weight_kg || 0) * proportion).toLocaleString()}</td><td style="text-align:right">${fmt$(s.unit_price)}</td><td style="text-align:right">${fmt$(Number(s.net_amount || 0) * proportion)}</td></tr>
  `).join('');
  const salesSummaryRow = (detailData.sales && detailData.sales.length > 0) ? `
    <tr style="font-weight:bold;background:#f5f5f5">
      <td colspan="3" style="text-align:right">合计${proportion < 1 ? ' (' + Math.round(proportion * 100) + '%)' : ''}:</td>
      <td style="text-align:right">${detailData.sales.reduce((sum: number, s: any) => sum + (s.box_count || 0), 0)}</td>
      <td style="text-align:right">${Number(detailData.total_sales_weight || 0).toLocaleString()}</td>
      <td></td>
      <td style="text-align:right">${fmt$(detailData.total_sales_net)}</td>
    </tr>
  ` : '';
  const purchaseRows = (detailData.invoices || []).map((inv: any) => {
    const prodRows = (inv.products || []).map((p: any) => `
      <tr>
        <td>${p.product_spec || '-'}</td>
        <td style="text-align:right">${p.box_count || 0}</td>
        <td style="text-align:right">${Number(p.net_weight_kg || 0).toLocaleString()}</td>
        <td style="text-align:right">$${Number(p.unit_price || 0).toFixed(2)}</td>
        <td style="text-align:right">$${Number(p.total_amount || 0).toLocaleString()}</td>
      </tr>
    `).join('');
    const prodSummary = inv.products && inv.products.length > 0 ? `
      <tr style="font-weight:bold;background:#f5f5f5">
        <td style="text-align:left">${isEn ? 'Total' : '合计'}</td>
        <td style="text-align:right">${inv.total_boxes || 0}</td>
        <td style="text-align:right">${Number(inv.total_weight_kg || 0).toLocaleString()}</td>
        <td style="text-align:right">—</td>
        <td style="text-align:right">$${Number(inv.total_amount_usd || 0).toLocaleString()}</td>
      </tr>
    ` : '';
    return `
      <div style="margin-bottom:6pt">
        <div style="font-size:8.5pt;font-weight:600;margin-bottom:2pt">${inv.invoice_no}${inv.products && inv.products.length > 0 ? ' · ' + inv.products[0].product_name : ''}</div>
        <table style="width:100%;border-collapse:collapse;font-size:8pt">
          <thead>
            <tr style="background:#f5f5f5">
              <th style="text-align:left;border:1px solid #ddd;padding:1pt 3pt">${isEn ? 'Spec' : '规格'}</th>
              <th style="text-align:right;border:1px solid #ddd;padding:1pt 3pt">${isEn ? 'Boxes' : '箱数'}</th>
              <th style="text-align:right;border:1px solid #ddd;padding:1pt 3pt">${isEn ? 'Weight(kg)' : '重量(kg)'}</th>
              <th style="text-align:right;border:1px solid #ddd;padding:1pt 3pt">${isEn ? 'Price' : '单价'}</th>
              <th style="text-align:right;border:1px solid #ddd;padding:1pt 3pt">${isEn ? 'Amount' : '金额'}</th>
            </tr>
          </thead>
          <tbody>
            ${prodRows}
            ${prodSummary}
          </tbody>
        </table>
      </div>
    `;
  }).join('');
  const cb = detailData.clearance_breakdown || {};
  let clearanceRows = '';
  if (Number(cb.clearance_fee || 0) > 0) clearanceRows += `<div class="row"><span>${isEn ? 'Pickup Fee' : '提货费'}</span><span>${fmt$(cb.clearance_fee)}</span></div>`;
  if (Number(cb.freight_fee || 0) > 0) clearanceRows += `<div class="row"><span>${isEn ? 'Freight' : '运费'}</span><span>${fmt$(cb.freight_fee)}</span></div>`;
  if (Number(cb.other_costs || 0) > 0) clearanceRows += `<div class="row"><span>${isEn ? 'Customs Service' : '报关服务费'}</span><span>${fmt$(cb.other_costs)}</span></div>`;
  if (Number(cb.inspection_fee || 0) > 0) clearanceRows += `<div class="row"><span>${isEn ? 'Inspection Fee' : '目的地查验费'}</span><span>${fmt$(cb.inspection_fee)}</span></div>`;
  if (Number(cb.quarantine_fee || 0) > 0) clearanceRows += `<div class="row"><span>${isEn ? 'Cold Storage' : '冷藏费'}</span><span>${fmt$(cb.quarantine_fee)}</span></div>`;
  if (Number(cb.extra_expenses || 0) > 0) clearanceRows += `<div class="row"><span>${isEn ? 'Extra Expenses' : '额外支出'}${detailData.clearance_extra_items?.[0]?.description ? ` (${detailData.clearance_extra_items[0].description})` : ''}</span><span>${fmt$(cb.extra_expenses)}</span></div>`;
  if (clearanceRows) clearanceRows += `<div class="row bold" style="border-top:1px solid #ddd;margin-top:2pt;padding-top:2pt"><span>${isEn ? 'Clearance Total' : '清关费合计'}</span><span>${fmt$(detailData.total_clearance_cost)}</span></div>`;

  const bodyHTML = `
<div class="page">
  <div style="display:flex;align-items:baseline;gap:8pt;margin-bottom:4pt">
    <span style="font-size:16pt;font-weight:bold;color:#1e293b">${t.title}</span>
    <span style="font-size:11pt;font-weight:600;color:#334155">${detailData.invoice_nos ? detailData.invoice_nos.replace(/\u0026/g, ', ') : detailData.batch_code}</span>
    <span style="font-size:9pt;color:#64748b">${isEn ? 'Kill Date: ' : '宰杀日期：'}${detailData.invoices?.[0]?.kill_date || fmtDate(detailData.batch_date)}</span>
  </div>

  ${(() => {
    return `
  <!-- 第一行：采购信息 + 购汇登记 -->
  <div class="grid-2">
    <div class="section">
      <div class="section-title blue">📦 ${t.purchaseInfo}</div>
      ${purchaseRows}
    </div>
    <div class="section">
      <div class="section-title green">💱 ${t.exchange}${detailData.is_exchange_estimated ? ' <span style="font-size:8pt;color:#d97706;font-weight:normal">(估算)</span>' : ''}</div>
      <div class="row"><span>${isEn ? 'Rate' : '汇率'}</span><span>${detailData.exchange_rate || '-'}</span></div>
      <div class="row"><span>${isEn ? 'Payment' : '购汇金额'}</span><span>${fmt$(detailData.total_exchange_payment)}</span></div>
      <div class="row"><span>${isEn ? 'Fee' : '手续费'}</span><span>${fmt$(detailData.total_exchange_fee)}</span></div>
      <div class="row bold" style="border-top:1px solid #ddd;margin-top:2pt;padding-top:2pt"><span>${isEn ? 'Exchange Total' : '购汇合计'}</span><span>${fmt$(Number(detailData.total_exchange_payment || 0) + Number(detailData.total_exchange_fee || 0))}</span></div>
    </div>
  </div>

  <!-- 第二行：进口费用 + 损益分析 -->
  <div class="grid-2">
    <div class="section">
      <div class="section-title" style="color:#d97706">💰 ${t.importCost}</div>
      <div class="row"><span>${isEn ? 'Import Duty' : '进口关税'}</span><span>${fmt$(detailData.total_import_duty)}</span></div>
      <div class="row"><span>${isEn ? 'Import VAT' : '进口增值税'}</span><span>${fmt$(detailData.total_import_vat)}</span></div>
      <div class="row bold" style="border-top:1px solid #ddd;margin-top:2pt;padding-top:2pt"><span>${isEn ? 'Total Taxes' : '税费合计'}</span><span>${fmt$(detailData.total_taxes)}</span></div>
      ${clearanceRows}
      <div class="row bold" style="border-top:2px solid #d97706;margin-top:2pt;padding-top:2pt"><span>${isEn ? 'Total' : '合计'}</span><span>${fmt$(Number(detailData.total_taxes || 0) + Number(detailData.total_clearance_cost || 0))}</span></div>
    </div>
    <div class="section">
      <div class="section-title" style="color:#7c3aed">📈 ${t.profitLoss}</div>
      <div class="row"><span>${isEn ? 'Gross Sales' : '销售毛额'}</span><span>${fmt$(detailData.total_sales_amount)}</span></div>
      ${Number(detailData.total_scan_fee || 0) !== 0 ? `<div class="row red"><span>${isEn ? 'Scan Fee' : '扫码费'}</span><span>-${fmt$(detailData.total_scan_fee)}</span></div>` : ''}
      ${Number(detailData.total_rounding || 0) !== 0 ? `<div class="row red"><span>${isEn ? 'Rounding' : '抹零'}</span><span>-${fmt$(detailData.total_rounding)}</span></div>` : ''}
      ${Number(detailData.total_after_sales || 0) !== 0 ? `<div class="row red"><span>${isEn ? 'After Sales' : '售后调整'}</span><span>-${fmt$(detailData.total_after_sales)}</span></div>` : ''}
      ${Number(detailData.total_discount || 0) !== 0 ? `<div class="row red"><span>${isEn ? 'Discount' : '折扣'}</span><span>-${fmt$(detailData.total_discount)}</span></div>` : ''}
      <div class="row bold"><span>${isEn ? 'Net Sales' : '销售净额'}</span><span class="bold">${fmt$(detailData.total_sales_net)}</span></div>
      ${Number(detailData.shrinkage || 0) !== 0 ? `<div class="row red"><span>${isEn ? 'Shrinkage' : '账面损耗'}(${Number(detailData.total_weight_kg || 0).toLocaleString()}kg - ${Number(detailData.total_sales_weight || 0).toLocaleString()}kg = ${Number((detailData.total_weight_kg || 0) - (detailData.total_sales_weight || 0)).toLocaleString()}kg)</span><span>-${fmt$(detailData.shrinkage)}</span></div>` : ''}
      ${Number(detailData.total_commission || 0) !== 0 ? `<div class="row red"><span>${isEn ? 'Commission' : '业务员提成'}</span><span>-${fmt$(detailData.total_commission)}</span></div>` : ''}
      <div class="row red"><span>${isEn ? 'Exchange Total' : '购汇合计'}</span><span>-${fmt$(Number(detailData.total_exchange_payment || 0) + Number(detailData.total_exchange_fee || 0))}</span></div>
      <div class="row red"><span>${isEn ? 'Import Cost Total' : '进口费用合计'}</span><span>-${fmt$(Number(detailData.total_taxes || 0) + Number(detailData.total_clearance_cost || 0))}</span></div>
      ${Number(detailData.total_other_expenses || 0) !== 0 ? `<div class="row red"><span>${isEn ? 'Other Expenses' : '其他支出'}</span><span>-${fmt$(detailData.total_other_expenses)}</span></div>` : ''}
      <div class="row bold ${Number(detailData.net_profit) >= 0 ? 'green' : 'red'}" style="border-top:1px solid #ddd;margin-top:2pt;padding-top:2pt"><span>${t.netProfit}</span><span>${fmt$(detailData.net_profit)}</span></div>
    </div>
  </div>
    `;
  })()}

  <!-- 销售明细 -->
  <div class="section">
    <div class="section-title" style="color:#9333ea">🛒 ${t.salesDetail}</div>
    <table><thead><tr><th>${t.date}</th><th>${t.customer}</th><th>${t.spec}</th><th class="num">${isEn ? 'Boxes' : '箱数'}</th><th class="num">${t.weight}</th><th class="num">${t.price}</th><th class="num">${t.net}</th></tr></thead>
    <tbody>${salesRows}${salesSummaryRow}</tbody></table>
  </div>

  <!-- 溯源信息 -->
  <div class="section">
    <div class="section-title" style="color:#4f46e5">📍 ${t.traceInfo}</div>
    <div class="trace-grid">
      <div class="trace-item"><div class="icon">🏭</div><div class="label">${isEn ? 'Plant' : '加工厂'}</div><div class="value">${detailData.invoices?.[0]?.processing_plant_name || '-'}</div></div>
      <div class="trace-item"><div class="icon">📍</div><div class="label">${isEn ? 'Farm' : '养殖场'}</div><div class="value">${detailData.invoices?.[0]?.fish_farm_name || '-'}</div></div>
      <div class="trace-item"><div class="icon">🚢</div><div class="label">${isEn ? 'Exporter' : '出口商'}</div><div class="value">${detailData.invoices?.[0]?.exporter_name || '-'}</div></div>
    </div>
    <div style="margin-top:6pt; font-size:8.5pt; line-height:1.6; display:flex; flex-wrap:wrap; gap:6pt 12pt">
      ${detailData.invoices?.[0]?.processing_plant_eu_code ? `<span><span style="color:#999">${isEn ? 'EU Code:' : 'EU注册号：'}</span>${detailData.invoices[0].processing_plant_eu_code}</span>` : ''}
      ${detailData.invoices?.[0]?.processing_plant_customs_code ? `<span><span style="color:#999">${isEn ? 'CN Customs:' : 'CN海关准入：'}</span>${detailData.invoices[0].processing_plant_customs_code}</span>` : ''}
      ${detailData.invoices?.[0]?.fish_farm_ggn ? `<span><span style="color:#999">${isEn ? 'GGN:' : '养殖GGN：'}</span>${detailData.invoices[0].fish_farm_ggn}</span>` : ''}
      ${detailData.invoices?.[0]?.fish_farm_coc_no ? `<span><span style="color:#999">${isEn ? 'COC:' : '监管链COC：'}</span>${detailData.invoices[0].fish_farm_coc_no}</span>` : ''}
      ${detailData.invoices?.[0]?.processing_plant_coc_no ? `<span><span style="color:#999">${isEn ? 'COC(Plant):' : '监管链COC(加工厂)：'}</span>${detailData.invoices[0].processing_plant_coc_no}</span>` : ''}
      ${detailData.invoices?.[0]?.fish_farm_area ? `<span><span style="color:#999">${isEn ? 'Area:' : '养殖区：'}</span>${detailData.invoices[0].fish_farm_area}</span>` : ''}
    </div>
  </div>

  <div class="footer">${t.footer}<br>${isEn ? 'Printed:' : '打印时间:'} ${new Date().toLocaleString(isEn ? 'en-US' : 'zh-CN')}</div>
</div>
  `;

  return `<!DOCTYPE html>
<html><head><meta charset="UTF-8"><title>${t.title} · ${detailData.batch_code}</title>
<style>
  @page { size: A4; margin: 10mm; }
  body { font-family: system-ui, sans-serif; margin: 0; padding: 0; color: #333; font-size: 10pt; }
  .page { max-width: 190mm; margin: 0 auto; padding: 10mm; }
  h1 { font-size: 16pt; font-weight: bold; color: #1e293b; margin-bottom: 4pt; }
  h2 { font-size: 10pt; font-weight: normal; color: #64748b; margin-bottom: 8pt; }
  .section { margin-bottom: 10pt; border: 1px solid #ddd; border-radius: 4pt; padding: 8pt; }
  .section-title { font-size: 10pt; font-weight: bold; margin-bottom: 4pt; }
  .grid-2 { display: grid; grid-template-columns: 1fr 1fr; gap: 8pt; }
  .grid-3 { display: grid; grid-template-columns: repeat(3, 1fr); gap: 8pt; }
  .row { display: flex; justify-content: space-between; padding: 2pt 0; border-bottom: 1px solid #eee; font-size: 9pt; }
  .row.bold { font-weight: bold; }
  .row.pl { padding-left: 8pt; }
  table { width: 100%; border-collapse: collapse; font-size: 8.5pt; margin-top: 4pt; }
  th, td { border: 1px solid #ddd; padding: 2pt 4pt; text-align: left; }
  th { background: #f5f5f5; }
  td.num, th.num { text-align: right; }
  .highlight { background: #eff6ff; padding: 4pt; border-radius: 2pt; }
  .red { color: #dc2626; }
  .green { color: #16a34a; }
  .blue { color: #2563eb; }
  .purple { color: #7c3aed; }
  .footer { text-align: center; font-size: 8pt; color: #999; margin-top: 10pt; padding-top: 4pt; border-top: 1px solid #ddd; }
  .trace-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 6pt; text-align: center; }
  .trace-item .icon { font-size: 14pt; margin-bottom: 2pt; }
  .trace-item .label { font-size: 7.5pt; color: #999; }
  .trace-item .value { font-size: 8pt; font-weight: 500; }
  .profit-bar { display: grid; grid-template-columns: repeat(3, 1fr); gap: 6pt; text-align: center; background: #f3f4f6; border-radius: 4pt; padding: 6pt; }
  .profit-bar .label { font-size: 8pt; color: #6b7280; margin-bottom: 2pt; }
  .profit-bar .value { font-size: 9pt; font-weight: 600; }
  .totals-bar { display: flex; justify-content: space-between; align-items: center; background: #1e293b; color: white; border-radius: 4pt; padding: 6pt 10pt; font-size: 9pt; }
  .totals-bar .label { font-weight: 600; }
  .totals-bar .green { color: #4ade80; }
</style></head><body>
${bodyHTML}
</body></html>`;
}

'''
    content = content.replace(insert_point, gen_func + insert_point)
    print("✓ 添加 generateBatchReportHTML 函数")
else:
    print("✗ 未找到插入位置")

# 8. 替换弹窗内的打印逻辑为调用 generateBatchReportHTML
# 找到弹窗打印按钮的 onClick 并替换
old_print_click = '''onClick={() => {
                  if (!detailData) return;
                  const printWindow = window.open('', '_blank');
                  if (!printWindow) return;
                  const isEn = detailLang === 'en';'''

# 由于打印逻辑太长，我们直接替换整个 onClick 内容
# 用正则匹配从 onClick={() => { 到 }}> 之间的内容
pattern = r'onClick=\{\(\) => \{\s*if \(!detailData\) return;\s*const printWindow = window\.open\(\'\', \'_blank\'\);\s*if \(!printWindow\) return;\s*const isEn = detailLang === \'en\';'
replacement = '''onClick={() => {
                  if (!detailData) return;
                  const html = generateBatchReportHTML(detailData, detailLang);
                  const printWindow = window.open('', '_blank');
                  if (!printWindow) return;
                  printWindow.document.write(html);
                  printWindow.document.close();
                  setTimeout(() => printWindow.print(), 500);
                }}
                disabled={!detailData}
              >
                <Printer className="h-3.5 w-3.5" />
                {detailLang === "zh" ? "打印" : "Print"}
              </Button>
            </div>
          </DialogHeader>
          {detailData ? (
            <div className="space-y-3 text-sm">
              {/* === 第一行：标题 === */}
              <div className="border-b pb-3 mb-2 flex items-baseline gap-3">
                <h2 className="text-xl font-bold text-slate-800">
                  {detailLang === "zh" ? "财务报告" : "Financial Report"}
                </h2>
                <span className="text-sm text-slate-600 font-medium">
                  {detailData.invoice_nos ? detailData.invoice_nos.replace(/\\u0026/g, ', ') : detailData.batch_code}'''

# 实际上上面的正则太复杂了，让我用更简单的方式
# 找到 printWindow.document.close(); 到 </Button> 之间的内容
# 但我们已经把 generateBatchReportHTML 插入了，现在需要替换弹窗打印按钮
# 由于弹窗打印代码非常长（200+行），让我直接标记这个按钮的位置

# 先写入当前版本，然后手动处理弹窗打印按钮
with open('/home/sannah/.openclaw/workspace-codeingman/projects/salmon-pms/frontend/src/pages/BatchReportsTab.tsx', 'w') as f:
    f.write(content)

print("\n文件已写入。需要手动替换弹窗打印按钮。")
print("弹窗打印按钮位置：在 DialogHeader 内，'打印' 按钮处。")
