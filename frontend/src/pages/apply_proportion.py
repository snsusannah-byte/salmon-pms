import re

with open('BatchReportsTab.tsx', 'r') as f:
    content = f.read()

# ============================================================
# FIX 1: PAGE UI - Apply sales_proportion to sales detail rows
# ============================================================

# Find the sales detail table body start and modify rows
old_sales_rows = '''                    <TableBody>
                      {detailData.sales.map((sale: any, idx: number) => (
                        <TableRow key={idx}>
                          <TableCell className="text-xs py-1">{fmtDate(sale.sale_date)}</TableCell>
                          <TableCell className="text-xs py-1">{sale.customer_name || "-"}</TableCell>
                          <TableCell className="text-xs py-1">{sale.spec || "-"}</TableCell>
                          <TableCell className="text-xs py-1 text-right">{sale.box_count || 0}</TableCell>
                          <TableCell className="text-xs py-1 text-right">{Number(sale.weight_kg || 0).toLocaleString()}</TableCell>
                          <TableCell className="text-xs py-1 text-right">{fmt$(sale.unit_price)}</TableCell>
                          <TableCell className="text-xs py-1 text-right font-medium">{fmt$(sale.net_amount)}</TableCell>
                        </TableRow>
                      ))}
                      {/* 汇总行 */}
                      <TableRow className="border-t-2 font-medium bg-muted/30">
                        <TableCell className="text-xs py-1" colSpan={3}>{detailLang === "zh" ? "合计" : "Total"}</TableCell>
                        <TableCell className="text-xs py-1 text-right">{detailData.sales.reduce((sum: number, s: any) => sum + (s.box_count || 0), 0)}</TableCell>'''

new_sales_rows = '''                    {(() => {
                      const proportion = Number(detailData.sales_proportion || 1);
                      return (
                        <TableBody>
                          {detailData.sales.map((sale: any, idx: number) => (
                            <TableRow key={idx}>
                              <TableCell className="text-xs py-1">{fmtDate(sale.sale_date)}</TableCell>
                              <TableCell className="text-xs py-1">{sale.customer_name || "-"}</TableCell>
                              <TableCell className="text-xs py-1">{sale.spec || "-"}</TableCell>
                              <TableCell className="text-xs py-1 text-right">{Math.round((sale.box_count || 0) * proportion)}</TableCell>
                              <TableCell className="text-xs py-1 text-right">{Number((sale.weight_kg || 0) * proportion).toLocaleString()}</TableCell>
                              <TableCell className="text-xs py-1 text-right">{fmt$(sale.unit_price)}</TableCell>
                              <TableCell className="text-xs py-1 text-right font-medium">{fmt$(Number(sale.net_amount || 0) * proportion)}</TableCell>
                            </TableRow>
                          ))}
                          {/* 汇总行 */}
                          <TableRow className="border-t-2 font-medium bg-muted/30">
                            <TableCell className="text-xs py-1" colSpan={3}>{detailLang === "zh" ? "合计" : "Total"}{proportion < 1 ? ` (${Math.round(proportion * 100)}%)` : ""}</TableCell>
                            <TableCell className="text-xs py-1 text-right">{detailData.sales.reduce((sum: number, s: any) => sum + Math.round((s.box_count || 0) * proportion), 0)}</TableCell>'''

if old_sales_rows in content:
    content = content.replace(old_sales_rows, new_sales_rows, 1)
    print("Replaced page sales rows")
else:
    print("WARNING: Could not find page sales rows")

# Also need to close the IIFE properly. Find the closing </TableBody>
old_table_body_end = '''                        <TableCell className="text-xs py-1 text-right">{Number(detailData.total_sales_weight || 0).toLocaleString()} kg</TableCell>
                        <TableCell className="text-xs py-1 text-right">—</TableCell>
                        <TableCell className="text-xs py-1 text-right font-bold">{fmt$(detailData.total_sales_net)}</TableCell>
                      </TableRow>
                    </TableBody>'''

new_table_body_end = '''                        <TableCell className="text-xs py-1 text-right">{Number(detailData.total_sales_weight || 0).toLocaleString()} kg</TableCell>
                        <TableCell className="text-xs py-1 text-right">—</TableCell>
                        <TableCell className="text-xs py-1 text-right font-bold">{fmt$(detailData.total_sales_net)}</TableCell>
                      </TableRow>
                    </TableBody>
                    );
                  })()}'''

if old_table_body_end in content:
    content = content.replace(old_table_body_end, new_table_body_end, 1)
    print("Replaced table body end")
else:
    print("WARNING: Could not find table body end")

# ============================================================
# FIX 2: PRINT TEMPLATE - Apply sales_proportion
# ============================================================

old_print_sales = '''                  const salesRows = (detailData.sales || []).map((s: any) => `
                    <tr><td>${fmtDate(s.sale_date)}</td><td>${s.customer_name || '-'}</td><td>${s.spec || '-'}</td><td style="text-align:right">${s.box_count || 0}</td><td style="text-align:right">${Number(s.weight_kg || 0).toLocaleString()}</td><td style="text-align:right">${fmt$(s.unit_price)}</td><td style="text-align:right">${fmt$(s.net_amount)}</td></tr>
                  `).join('');
                  const salesSummaryRow = (detailData.sales && detailData.sales.length > 0) ? `
                    <tr style="font-weight:bold;background:#f5f5f5">
                      <td colspan="3" style="text-align:right">合计:</td>
                      <td style="text-align:right">${detailData.sales.reduce((sum: number, s: any) => sum + (s.box_count || 0), 0)}</td>'''

new_print_sales = '''                  const proportion = Number(detailData.sales_proportion || 1);
                  const salesRows = (detailData.sales || []).map((s: any) => `
                    <tr><td>${fmtDate(s.sale_date)}</td><td>${s.customer_name || '-'}</td><td>${s.spec || '-'}</td><td style="text-align:right">${Math.round((s.box_count || 0) * proportion)}</td><td style="text-align:right">${Number((s.weight_kg || 0) * proportion).toLocaleString()}</td><td style="text-align:right">${fmt$(s.unit_price)}</td><td style="text-align:right">${fmt$(Number(s.net_amount || 0) * proportion)}</td></tr>
                  `).join('');
                  const salesSummaryRow = (detailData.sales && detailData.sales.length > 0) ? `
                    <tr style="font-weight:bold;background:#f5f5f5">
                      <td colspan="3" style="text-align:right">合计${proportion < 1 ? ' (' + Math.round(proportion * 100) + '%)' : ''}:</td>
                      <td style="text-align:right">${detailData.sales.reduce((sum: number, s: any) => sum + Math.round((s.box_count || 0) * proportion), 0)}</td>'''

if old_print_sales in content:
    content = content.replace(old_print_sales, new_print_sales, 1)
    print("Replaced print sales rows")
else:
    print("WARNING: Could not find print sales rows")

with open('BatchReportsTab.tsx', 'w') as f:
    f.write(content)

print("Done!")
