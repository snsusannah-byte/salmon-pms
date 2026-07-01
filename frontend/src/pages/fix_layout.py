import re

with open('BatchReportsTab.tsx', 'r') as f:
    content = f.read()

# ============================================================
# FIX 1: PAGE UI - Change unguohui layout for rows 2+3
# ============================================================

# Current structure for NOT hasExchange:
# Row 2: 采购信息 + (empty 购汇登记 hidden) → single column with empty right side
# Row 3: 进口费用 + (empty 损益分析 hidden) → single column with empty right side
#
# Target for NOT hasExchange:
# Row 2: 采购信息 + 进口费用 (grid-cols-2)
# Row 3: 销售明细 (full width)

# Find the block starting with "{/* === 第二行：采购信息 + 购汇登记 === */}"
# and ending just before "{/* === 第四行：销售明细 === */}"

old_unguohui_ui = '''              {/* === 第二行：采购信息 + 购汇登记 === */}
              <div className="grid grid-cols-2 gap-3">
                <div className="border rounded-lg p-2.5 space-y-2">
                  <p className="text-xs font-semibold text-blue-600">{detailLang === "zh" ? "采购信息" : "Purchase Info"}</p>'''

# We need to restructure this. Let me find a better anchor point.
# The key is: when NOT hasExchange, we want 采购信息 and 进口费用 side by side.

# Strategy: Replace the entire section from "{/* === 第二行..." through "{/* === 第四行...*/}"
# with a conditional block that renders differently for hasExchange vs !hasExchange

pattern_start = '              {/* === 第二行：采购信息 + 购汇登记 === */}'
pattern_end = '              {/* === 第四行：销售明细 === */}'

idx_start = content.find(pattern_start)
idx_end = content.find(pattern_end)

if idx_start == -1 or idx_end == -1:
    print(f"ERROR: Could not find markers. start={idx_start}, end={idx_end}")
    exit(1)

# Extract the section to replace
old_section_ui = content[idx_start:idx_end]

# Build new section
new_section_ui = '''              {/* === 第二行+第三行：根据购汇状态切换布局 === */}
              {(() => {
                const hasExchange = Number(detailData.total_exchange_payment || 0) > 0 || Number(detailData.total_exchange_fee || 0) > 0;
                return hasExchange ? (
                  <>
                    {/* 已购汇：采购信息 + 购汇登记 */}
                    <div className="grid grid-cols-2 gap-3">
                      <div className="border rounded-lg p-2.5 space-y-2">
                        <p className="text-xs font-semibold text-blue-600">{detailLang === "zh" ? "采购信息" : "Purchase Info"}</p>
                        {detailData.invoices && detailData.invoices.length > 0 ? (
                          <div className="space-y-2">
                            {detailData.invoices.map((inv: any, idx: number) => (
                              <div key={idx} className={idx > 0 ? "pt-2 border-t" : ""}>
                                <div className="text-xs font-medium text-slate-700 mb-1">
                                  {inv.invoice_no}
                                  {inv.products && inv.products.length === 1 && (
                                    <span className="text-muted-foreground font-normal ml-1">· {inv.products[0].product_name}</span>
                                  )}
                                  {inv.products && inv.products.length > 1 && (
                                    <span className="text-muted-foreground font-normal ml-1">· {inv.products[0].product_name} 等</span>
                                  )}
                                </div>
                                {inv.products && inv.products.length > 0 ? (
                                  <table className="w-full text-xs border-collapse">
                                    <thead>
                                      <tr className="bg-slate-50">
                                        <th className="text-left px-1 py-0.5 font-medium text-muted-foreground border">{detailLang === "zh" ? "规格" : "Spec"}</th>
                                        <th className="text-right px-1 py-0.5 font-medium text-muted-foreground border">{detailLang === "zh" ? "箱数" : "Boxes"}</th>
                                        <th className="text-right px-1 py-0.5 font-medium text-muted-foreground border">{detailLang === "zh" ? "重量(kg)" : "Weight"}</th>
                                        <th className="text-right px-1 py-0.5 font-medium text-muted-foreground border">{detailLang === "zh" ? "单价" : "Price"}</th>
                                        <th className="text-right px-1 py-0.5 font-medium text-muted-foreground border">{detailLang === "zh" ? "金额" : "Amount"}</th>
                                      </tr>
                                    </thead>
                                    <tbody>
                                      {inv.products.map((p: any, pidx: number) => (
                                        <tr key={pidx} className="hover:bg-slate-50/50">
                                          <td className="text-left px-1 py-0.5 border">{p.product_spec || "-"}</td>
                                          <td className="text-right px-1 py-0.5 border">{p.box_count || 0}</td>
                                          <td className="text-right px-1 py-0.5 border">{Number(p.net_weight_kg || 0).toLocaleString()}</td>
                                          <td className="text-right px-1 py-0.5 border">${Number(p.unit_price || 0).toFixed(2)}</td>
                                          <td className="text-right px-1 py-0.5 border font-medium">${Number(p.total_amount || 0).toLocaleString()}</td>
                                        </tr>
                                      ))}
                                      <tr className="font-semibold bg-slate-50">
                                        <td className="text-left px-1 py-0.5 border">{detailLang === "zh" ? "合计" : "Total"}</td>
                                        <td className="text-right px-1 py-0.5 border">{inv.total_boxes || 0}</td>
                                        <td className="text-right px-1 py-0.5 border">{Number(inv.total_weight_kg || 0).toLocaleString()}</td>
                                        <td className="text-right px-1 py-0.5 border">—</td>
                                        <td className="text-right px-1 py-0.5 border">${Number(inv.total_amount_usd || 0).toLocaleString()}</td>
                                      </tr>
                                    </tbody>
                                  </table>
                                ) : (
                                  <div className="text-xs text-muted-foreground py-1">{detailLang === "zh" ? "无产品明细" : "No product details"}</div>
                                )}
                              </div>
                            ))}
                          </div>
                        ) : (
                          <div className="text-xs text-muted-foreground">{detailLang === "zh" ? "无采购数据" : "No purchase data"}</div>
                        )}
                      </div>
                      <div className="border rounded-lg p-2.5 space-y-1.5">
                        <p className="text-xs font-semibold text-green-600">{detailLang === "zh" ? "购汇登记" : "Exchange"}</p>
                        <div className="flex justify-between text-xs"><span className="text-muted-foreground">{detailLang === "zh" ? "汇率" : "Rate"}</span><span>{detailData.exchange_rate || "-"}</span></div>
                        <div className="flex justify-between text-xs"><span className="text-muted-foreground">{detailLang === "zh" ? "购汇金额" : "Payment"}</span><span>{fmt$(detailData.total_exchange_payment)}</span></div>
                        <div className="flex justify-between text-xs"><span className="text-muted-foreground">{detailLang === "zh" ? "手续费" : "Fee"}</span><span>{fmt$(detailData.total_exchange_fee)}</span></div>
                        <div className="flex justify-between text-xs font-medium border-t pt-1"><span>{detailLang === "zh" ? "购汇合计" : "Total"}</span><span>{fmt$(Number(detailData.total_exchange_payment || 0) + Number(detailData.total_exchange_fee || 0))}</span></div>
                      </div>
                    </div>

                    {/* 已购汇：进口费用 + 损益分析 */}
                    <div className="grid grid-cols-2 gap-3">
                      <div className="border rounded-lg p-2.5 space-y-1.5">
                        <p className="text-xs font-semibold text-amber-600">{detailLang === "zh" ? "进口费用" : "Import Costs"}</p>
                        <div className="flex justify-between text-xs"><span className="text-muted-foreground">{detailLang === "zh" ? "进口关税" : "Import Duty"}</span><span>{fmt$(detailData.total_import_duty)}</span></div>
                        <div className="flex justify-between text-xs"><span className="text-muted-foreground">{detailLang === "zh" ? "进口增值税" : "Import VAT"}</span><span>{fmt$(detailData.total_import_vat)}</span></div>
                        <div className="flex justify-between text-xs font-medium border-t pt-1"><span>{detailLang === "zh" ? "税费合计" : "Total Taxes"}</span><span>{fmt$(detailData.total_taxes)}</span></div>
                        {(() => {
                          const cb = detailData.clearance_breakdown || {};
                          const hasClearance = Number(cb.clearance_fee || 0) > 0 || Number(cb.freight_fee || 0) > 0 || Number(cb.other_costs || 0) > 0 || Number(cb.inspection_fee || 0) > 0 || Number(cb.quarantine_fee || 0) > 0;
                          return (
                            <>
                              {Number(cb.clearance_fee || 0) > 0 && <div className="flex justify-between text-xs"><span className="text-muted-foreground">{detailLang === "zh" ? "提货费" : "Pickup Fee"}</span><span>{fmt$(cb.clearance_fee)}</span></div>}
                              {Number(cb.freight_fee || 0) > 0 && <div className="flex justify-between text-xs"><span className="text-muted-foreground">{detailLang === "zh" ? "运费" : "Freight"}</span><span>{fmt$(cb.freight_fee)}</span></div>}
                              {Number(cb.other_costs || 0) > 0 && <div className="flex justify-between text-xs"><span className="text-muted-foreground">{detailLang === "zh" ? "报关服务费" : "Customs Service"}</span><span>{fmt$(cb.other_costs)}</span></div>}
                              {Number(cb.inspection_fee || 0) > 0 && <div className="flex justify-between text-xs"><span className="text-muted-foreground">{detailLang === "zh" ? "目的地查验费" : "Inspection Fee"}</span><span>{fmt$(cb.inspection_fee)}</span></div>}
                              {Number(cb.quarantine_fee || 0) > 0 && <div className="flex justify-between text-xs"><span className="text-muted-foreground">{detailLang === "zh" ? "冷藏费" : "Cold Storage"}</span><span>{fmt$(cb.quarantine_fee)}</span></div>}
                              {hasClearance && <div className="flex justify-between text-xs font-medium border-t pt-1"><span>{detailLang === "zh" ? "清关费合计" : "Clearance Total"}</span><span>{fmt$(detailData.total_clearance_cost)}</span></div>}
                            </>
                          );
                        })()}
                        <div className="flex justify-between text-xs font-bold border-t-2 border-amber-200 pt-1"><span>{detailLang === "zh" ? "合计" : "Total"}</span><span className="text-amber-700">{fmt$(Number(detailData.total_taxes || 0) + Number(detailData.total_clearance_cost || 0))}</span></div>
                      </div>
                      <div className="border rounded-lg p-2.5 space-y-1.5">
                        <p className="text-xs font-semibold text-purple-600">{detailLang === "zh" ? "损益分析" : "Profit/Loss"}</p>
                        <div className="flex justify-between text-xs"><span className="text-muted-foreground">{detailLang === "zh" ? "销售毛额" : "Gross Sales"}</span><span className="font-medium">{fmt$(detailData.total_sales_amount)}</span></div>
                        {Number(detailData.total_scan_fee || 0) !== 0 && (
                          <div className="flex justify-between text-xs"><span className="text-muted-foreground pl-2">{detailLang === "zh" ? "扫码费" : "Scan Fee"}</span><span className="text-red-500">-{fmt$(detailData.total_scan_fee)}</span></div>
                        )}
                        {Number(detailData.total_rounding || 0) !== 0 && (
                          <div className="flex justify-between text-xs"><span className="text-muted-foreground pl-2">{detailLang === "zh" ? "抹零" : "Rounding"}</span><span className="text-red-500">-{fmt$(detailData.total_rounding)}</span></div>
                        )}
                        {Number(detailData.total_after_sales || 0) !== 0 && (
                          <div className="flex justify-between text-xs"><span className="text-muted-foreground pl-2">{detailLang === "zh" ? "售后调整" : "After Sales"}</span><span className="text-red-500">-{fmt$(detailData.total_after_sales)}</span></div>
                        )}
                        {Number(detailData.total_discount || 0) !== 0 && (
                          <div className="flex justify-between text-xs"><span className="text-muted-foreground pl-2">{detailLang === "zh" ? "折扣" : "Discount"}</span><span className="text-red-500">-{fmt$(detailData.total_discount)}</span></div>
                        )}
                        <div className="flex justify-between text-xs font-medium border-t border-dashed pt-1">
                          <span className="text-muted-foreground">{detailLang === "zh" ? "销售净额" : "Net Sales"}</span>
                          <span className="font-medium">{fmt$(detailData.total_sales_net)}</span>
                        </div>
                        {Number(detailData.total_commission || 0) !== 0 && (
                          <div className="flex justify-between text-xs"><span className="text-muted-foreground pl-2">{detailLang === "zh" ? "业务员提成" : "Commission"}</span><span className="text-red-500">-{fmt$(detailData.total_commission)}</span></div>
                        )}
                        {Number(detailData.shrinkage || 0) !== 0 && (
                          <div className="flex justify-between text-xs">
                            <span className="text-muted-foreground pl-2">{detailLang === "zh" ? `账面损耗(采购${Number(detailData.total_weight_kg || 0).toLocaleString()}kg - 销售${Number(detailData.total_sales_weight || 0).toLocaleString()}kg = ${Number((detailData.total_weight_kg || 0) - (detailData.total_sales_weight || 0)).toLocaleString()}kg)` : "Shrinkage"}</span>
                            <span className="text-red-500">-{fmt$(detailData.shrinkage)}</span>
                          </div>
                        )}
                        <div className="flex justify-between text-xs">
                          <span className="text-muted-foreground pl-2">{detailLang === "zh" ? "购汇合计" : "Exchange Total"}</span>
                          <span className="text-red-500">-{fmt$(Number(detailData.total_exchange_payment || 0) + Number(detailData.total_exchange_fee || 0))}</span>
                        </div>
                        <div className="flex justify-between text-xs">
                          <span className="text-muted-foreground pl-2">{detailLang === "zh" ? "进口费用合计" : "Import Cost Total"}</span>
                          <span className="text-red-500">-{fmt$(Number(detailData.total_taxes || 0) + Number(detailData.total_clearance_cost || 0))}</span>
                        </div>
                        <div className="flex justify-between text-xs font-medium border-t pt-1">
                          <span className={clsProfit(Number(detailData.net_profit))}>{detailLang === "zh" ? "净利润" : "Net Profit"}</span>
                          <span className={clsProfit(Number(detailData.net_profit))}>{fmt$(detailData.net_profit)}</span>
                        </div>
                      </div>
                    </div>
                  </>
                ) : (
                  <>
                    {/* 未购汇：采购信息 + 进口费用 并排 */}
                    <div className="grid grid-cols-2 gap-3">
                      <div className="border rounded-lg p-2.5 space-y-2">
                        <p className="text-xs font-semibold text-blue-600">{detailLang === "zh" ? "采购信息" : "Purchase Info"}</p>
                        {detailData.invoices && detailData.invoices.length > 0 ? (
                          <div className="space-y-2">
                            {detailData.invoices.map((inv: any, idx: number) => (
                              <div key={idx} className={idx > 0 ? "pt-2 border-t" : ""}>
                                <div className="text-xs font-medium text-slate-700 mb-1">
                                  {inv.invoice_no}
                                  {inv.products && inv.products.length === 1 && (
                                    <span className="text-muted-foreground font-normal ml-1">· {inv.products[0].product_name}</span>
                                  )}
                                  {inv.products && inv.products.length > 1 && (
                                    <span className="text-muted-foreground font-normal ml-1">· {inv.products[0].product_name} 等</span>
                                  )}
                                </div>
                                {inv.products && inv.products.length > 0 ? (
                                  <table className="w-full text-xs border-collapse">
                                    <thead>
                                      <tr className="bg-slate-50">
                                        <th className="text-left px-1 py-0.5 font-medium text-muted-foreground border">{detailLang === "zh" ? "规格" : "Spec"}</th>
                                        <th className="text-right px-1 py-0.5 font-medium text-muted-foreground border">{detailLang === "zh" ? "箱数" : "Boxes"}</th>
                                        <th className="text-right px-1 py-0.5 font-medium text-muted-foreground border">{detailLang === "zh" ? "重量(kg)" : "Weight"}</th>
                                        <th className="text-right px-1 py-0.5 font-medium text-muted-foreground border">{detailLang === "zh" ? "单价" : "Price"}</th>
                                        <th className="text-right px-1 py-0.5 font-medium text-muted-foreground border">{detailLang === "zh" ? "金额" : "Amount"}</th>
                                      </tr>
                                    </thead>
                                    <tbody>
                                      {inv.products.map((p: any, pidx: number) => (
                                        <tr key={pidx} className="hover:bg-slate-50/50">
                                          <td className="text-left px-1 py-0.5 border">{p.product_spec || "-"}</td>
                                          <td className="text-right px-1 py-0.5 border">{p.box_count || 0}</td>
                                          <td className="text-right px-1 py-0.5 border">{Number(p.net_weight_kg || 0).toLocaleString()}</td>
                                          <td className="text-right px-1 py-0.5 border">${Number(p.unit_price || 0).toFixed(2)}</td>
                                          <td className="text-right px-1 py-0.5 border font-medium">${Number(p.total_amount || 0).toLocaleString()}</td>
                                        </tr>
                                      ))}
                                      <tr className="font-semibold bg-slate-50">
                                        <td className="text-left px-1 py-0.5 border">{detailLang === "zh" ? "合计" : "Total"}</td>
                                        <td className="text-right px-1 py-0.5 border">{inv.total_boxes || 0}</td>
                                        <td className="text-right px-1 py-0.5 border">{Number(inv.total_weight_kg || 0).toLocaleString()}</td>
                                        <td className="text-right px-1 py-0.5 border">—</td>
                                        <td className="text-right px-1 py-0.5 border">${Number(inv.total_amount_usd || 0).toLocaleString()}</td>
                                      </tr>
                                    </tbody>
                                  </table>
                                ) : (
                                  <div className="text-xs text-muted-foreground py-1">{detailLang === "zh" ? "无产品明细" : "No product details"}</div>
                                )}
                              </div>
                            ))}
                          </div>
                        ) : (
                          <div className="text-xs text-muted-foreground">{detailLang === "zh" ? "无采购数据" : "No purchase data"}</div>
                        )}
                      </div>
                      <div className="border rounded-lg p-2.5 space-y-1.5">
                        <p className="text-xs font-semibold text-amber-600">{detailLang === "zh" ? "进口费用" : "Import Costs"}</p>
                        <div className="flex justify-between text-xs"><span className="text-muted-foreground">{detailLang === "zh" ? "进口关税" : "Import Duty"}</span><span>{fmt$(detailData.total_import_duty)}</span></div>
                        <div className="flex justify-between text-xs"><span className="text-muted-foreground">{detailLang === "zh" ? "进口增值税" : "Import VAT"}</span><span>{fmt$(detailData.total_import_vat)}</span></div>
                        <div className="flex justify-between text-xs font-medium border-t pt-1"><span>{detailLang === "zh" ? "税费合计" : "Total Taxes"}</span><span>{fmt$(detailData.total_taxes)}</span></div>
                        {(() => {
                          const cb = detailData.clearance_breakdown || {};
                          const hasClearance = Number(cb.clearance_fee || 0) > 0 || Number(cb.freight_fee || 0) > 0 || Number(cb.other_costs || 0) > 0 || Number(cb.inspection_fee || 0) > 0 || Number(cb.quarantine_fee || 0) > 0;
                          return (
                            <>
                              {Number(cb.clearance_fee || 0) > 0 && <div className="flex justify-between text-xs"><span className="text-muted-foreground">{detailLang === "zh" ? "提货费" : "Pickup Fee"}</span><span>{fmt$(cb.clearance_fee)}</span></div>}
                              {Number(cb.freight_fee || 0) > 0 && <div className="flex justify-between text-xs"><span className="text-muted-foreground">{detailLang === "zh" ? "运费" : "Freight"}</span><span>{fmt$(cb.freight_fee)}</span></div>}
                              {Number(cb.other_costs || 0) > 0 && <div className="flex justify-between text-xs"><span className="text-muted-foreground">{detailLang === "zh" ? "报关服务费" : "Customs Service"}</span><span>{fmt$(cb.other_costs)}</span></div>}
                              {Number(cb.inspection_fee || 0) > 0 && <div className="flex justify-between text-xs"><span className="text-muted-foreground">{detailLang === "zh" ? "目的地查验费" : "Inspection Fee"}</span><span>{fmt$(cb.inspection_fee)}</span></div>}
                              {Number(cb.quarantine_fee || 0) > 0 && <div className="flex justify-between text-xs"><span className="text-muted-foreground">{detailLang === "zh" ? "冷藏费" : "Cold Storage"}</span><span>{fmt$(cb.quarantine_fee)}</span></div>}
                              {hasClearance && <div className="flex justify-between text-xs font-medium border-t pt-1"><span>{detailLang === "zh" ? "清关费合计" : "Clearance Total"}</span><span>{fmt$(detailData.total_clearance_cost)}</span></div>}
                            </>
                          );
                        })()}
                        <div className="flex justify-between text-xs font-bold border-t-2 border-amber-200 pt-1"><span>{detailLang === "zh" ? "合计" : "Total"}</span><span className="text-amber-700">{fmt$(Number(detailData.total_taxes || 0) + Number(detailData.total_clearance_cost || 0))}</span></div>
                      </div>
                    </div>
                  </>
                );
              })()}

              {/* === 销售明细 === */}
'''

content = content[:idx_start] + new_section_ui + content[idx_end:]

# ============================================================
# FIX 2: PRINT TEMPLATE - Same layout change
# ============================================================

# Find print template section
pattern_print_start = '  <!-- 第一行：采购信息 + 购汇登记 -->'
pattern_print_end = '  <!-- 销售明细 -->'

idx_pstart = content.find(pattern_print_start)
idx_pend = content.find(pattern_print_end)

if idx_pstart == -1 or idx_pend == -1:
    print(f"WARNING: Could not find print markers. start={idx_pstart}, end={idx_pend}")
else:
    old_print_section = content[idx_pstart:idx_pend]
    
    new_print_section = '''  ${(() => {
    const hasExchange = Number(detailData.total_exchange_payment || 0) > 0 || Number(detailData.total_exchange_fee || 0) > 0;
    return hasExchange ? `
  <!-- 第一行：采购信息 + 购汇登记 -->
  <div class="grid-2">
    <div class="section">
      <div class="section-title blue">📦 ${t.purchaseInfo}</div>
      ${purchaseRows}
    </div>
    <div class="section">
      <div class="section-title green">💱 ${t.exchange}</div>
      <div class="row"><span>${isEn ? \'Rate\' : \'汇率\'}</span><span>${detailData.exchange_rate || \'-\'}</span></div>
      <div class="row"><span>${isEn ? \'Payment\' : \'购汇金额\'}</span><span>${fmt$(detailData.total_exchange_payment)}</span></div>
      <div class="row"><span>${isEn ? \'Fee\' : \'手续费\'}</span><span>${fmt$(detailData.total_exchange_fee)}</span></div>
      <div class="row bold" style="border-top:1px solid #ddd;margin-top:2pt;padding-top:2pt"><span>${isEn ? \'Exchange Total\' : \'购汇合计\'}</span><span>${fmt$(Number(detailData.total_exchange_payment || 0) + Number(detailData.total_exchange_fee || 0))}</span></div>
    </div>
  </div>

  <!-- 第二行：进口费用 + 损益分析 -->
  <div class="grid-2">
    <div class="section">
      <div class="section-title" style="color:#d97706">💰 ${t.importCost}</div>
      <div class="row"><span>${isEn ? \'Import Duty\' : \'进口关税\'}</span><span>${fmt$(detailData.total_import_duty)}</span></div>
      <div class="row"><span>${isEn ? \'Import VAT\' : \'进口增值税\'}</span><span>${fmt$(detailData.total_import_vat)}</span></div>
      <div class="row bold" style="border-top:1px solid #ddd;margin-top:2pt;padding-top:2pt"><span>${isEn ? \'Total Taxes\' : \'税费合计\'}</span><span>${fmt$(detailData.total_taxes)}</span></div>
      ${clearanceRows}
      <div class="row bold" style="border-top:2px solid #d97706;margin-top:2pt;padding-top:2pt"><span>${isEn ? \'Total\' : \'合计\'}</span><span>${fmt$(Number(detailData.total_taxes || 0) + Number(detailData.total_clearance_cost || 0))}</span></div>
    </div>
    <div class="section">
      <div class="section-title" style="color:#7c3aed">📈 ${t.profitLoss}</div>
      <div class="row"><span>${isEn ? \'Gross Sales\' : \'销售毛额\'}</span><span>${fmt$(detailData.total_sales_amount)}</span></div>
      ${Number(detailData.total_scan_fee || 0) !== 0 ? `<div class="row red"><span>${isEn ? \'Scan Fee\' : \'扫码费\'}</span><span>-${fmt$(detailData.total_scan_fee)}</span></div>` : \'\'}
      ${Number(detailData.total_rounding || 0) !== 0 ? `<div class="row red"><span>${isEn ? \'Rounding\' : \'抹零\'}</span><span>-${fmt$(detailData.total_rounding)}</span></div>` : \'\'}
      ${Number(detailData.total_after_sales || 0) !== 0 ? `<div class="row red"><span>${isEn ? \'After Sales\' : \'售后调整\'}</span><span>-${fmt$(detailData.total_after_sales)}</span></div>` : \'\'}
      ${Number(detailData.total_discount || 0) !== 0 ? `<div class="row red"><span>${isEn ? \'Discount\' : \'折扣\'}</span><span>-${fmt$(detailData.total_discount)}</span></div>` : \'\'}
      <div class="row bold"><span>${isEn ? \'Net Sales\' : \'销售净额\'}</span><span class="bold">${fmt$(detailData.total_sales_net)}</span></div>
      ${Number(detailData.total_commission || 0) !== 0 ? `<div class="row red"><span>${isEn ? \'Commission\' : \'业务员提成\'}</span><span>-${fmt$(detailData.total_commission)}</span></div>` : \'\'}
      ${Number(detailData.shrinkage || 0) !== 0 ? `<div class="row red"><span>${isEn ? \'Shrinkage\' : \'账面损耗\'}(${Number(detailData.total_weight_kg || 0).toLocaleString()}kg - ${Number(detailData.total_sales_weight || 0).toLocaleString()}kg = ${Number((detailData.total_weight_kg || 0) - (detailData.total_sales_weight || 0)).toLocaleString()}kg)</span><span>-${fmt$(detailData.shrinkage)}</span></div>` : \'\'}
      <div class="row red"><span>${isEn ? \'Exchange Total\' : \'购汇合计\'}</span><span>-${fmt$(Number(detailData.total_exchange_payment || 0) + Number(detailData.total_exchange_fee || 0))}</span></div>
      <div class="row red"><span>${isEn ? \'Import Cost Total\' : \'进口费用合计\'}</span><span>-${fmt$(Number(detailData.total_taxes || 0) + Number(detailData.total_clearance_cost || 0))}</span></div>
      <div class="row bold ${Number(detailData.net_profit) >= 0 ? \'green\' : \'red\'}" style="border-top:1px solid #ddd;margin-top:2pt;padding-top:2pt"><span>${t.netProfit}</span><span>${fmt$(detailData.net_profit)}</span></div>
    </div>
  </div>
    ` : `
  <!-- 未购汇：采购信息 + 进口费用 并排 -->
  <div class="grid-2">
    <div class="section">
      <div class="section-title blue">📦 ${t.purchaseInfo}</div>
      ${purchaseRows}
    </div>
    <div class="section">
      <div class="section-title" style="color:#d97706">💰 ${t.importCost}</div>
      <div class="row"><span>${isEn ? \'Import Duty\' : \'进口关税\'}</span><span>${fmt$(detailData.total_import_duty)}</span></div>
      <div class="row"><span>${isEn ? \'Import VAT\' : \'进口增值税\'}</span><span>${fmt$(detailData.total_import_vat)}</span></div>
      <div class="row bold" style="border-top:1px solid #ddd;margin-top:2pt;padding-top:2pt"><span>${isEn ? \'Total Taxes\' : \'税费合计\'}</span><span>${fmt$(detailData.total_taxes)}</span></div>
      ${clearanceRows}
      <div class="row bold" style="border-top:2px solid #d97706;margin-top:2pt;padding-top:2pt"><span>${isEn ? \'Total\' : \'合计\'}</span><span>${fmt$(Number(detailData.total_taxes || 0) + Number(detailData.total_clearance_cost || 0))}</span></div>
    </div>
  </div>
    `;
  })()}

  <!-- 销售明细 -->
'''
    
    content = content[:idx_pstart] + new_print_section + content[idx_pend:]
    print("Replaced print template section")

with open('BatchReportsTab.tsx', 'w') as f:
    f.write(content)

print("Done! File updated successfully.")
