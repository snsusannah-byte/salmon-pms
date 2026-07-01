import re

with open('BatchReportsTab.tsx', 'r') as f:
    content = f.read()

# === FIX 1: PAGE UI - Add simplified profit/loss for unguohui ===
# Find the unguohui branch closing </div> after import costs, before "=== 销售明细 ==="

old_unguohui_end = '''                        <div className="flex justify-between text-xs font-bold border-t-2 border-amber-200 pt-1"><span>{detailLang === "zh" ? "合计" : "Total"}</span><span className="text-amber-700">{fmt$(Number(detailData.total_taxes || 0) + Number(detailData.total_clearance_cost || 0))}</span></div>
                      </div>
                    </div>
                  </>
                );
              })()}

              {/* === 销售明细 === */}
              {/* === 第四行：销售明细 === */}'''

new_unguohui_end = '''                        <div className="flex justify-between text-xs font-bold border-t-2 border-amber-200 pt-1"><span>{detailLang === "zh" ? "合计" : "Total"}</span><span className="text-amber-700">{fmt$(Number(detailData.total_taxes || 0) + Number(detailData.total_clearance_cost || 0))}</span></div>
                      </div>
                      {/* 未购汇：简化损益分析（仅销售净额） */}
                      <div className="border rounded-lg p-2.5 space-y-1.5">
                        <p className="text-xs font-semibold text-purple-600">{detailLang === "zh" ? "销售净额" : "Net Sales"}</p>
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
                      </div>
                    </div>
                  </>
                );
              })()}

              {/* === 销售明细 === */}
              {/* === 第四行：销售明细 === */}'''

if old_unguohui_end in content:
    content = content.replace(old_unguohui_end, new_unguohui_end, 1)
    print("Replaced page unguohui end block")
else:
    print("WARNING: Could not find page unguohui end block")

# === FIX 2: PRINT TEMPLATE - Add simplified profit/loss for unguohui ===
old_print_unguohui_end = '''      <div class="row bold" style="border-top:2px solid #d97706;margin-top:2pt;padding-top:2pt"><span>${isEn ? \'Total\' : \'合计\'}</span><span>${fmt$(Number(detailData.total_taxes || 0) + Number(detailData.total_clearance_cost || 0))}</span></div>
    </div>
  </div>
    `;
  })()}

  <!-- 销售明细 -->
  <!-- 销售明细 -->'''

new_print_unguohui_end = '''      <div class="row bold" style="border-top:2px solid #d97706;margin-top:2pt;padding-top:2pt"><span>${isEn ? \'Total\' : \'合计\'}</span><span>${fmt$(Number(detailData.total_taxes || 0) + Number(detailData.total_clearance_cost || 0))}</span></div>
    </div>
    <!-- 未购汇：简化销售净额 -->
    <div class="section">
      <div class="section-title" style="color:#7c3aed">📈 ${isEn ? \'Net Sales\' : \'销售净额\'}</div>
      <div class="row"><span>${isEn ? \'Gross Sales\' : \'销售毛额\'}</span><span>${fmt$(detailData.total_sales_amount)}</span></div>
      ${Number(detailData.total_scan_fee || 0) !== 0 ? `<div class="row red"><span>${isEn ? \'Scan Fee\' : \'扫码费\'}</span><span>-${fmt$(detailData.total_scan_fee)}</span></div>` : \'\'}
      ${Number(detailData.total_rounding || 0) !== 0 ? `<div class="row red"><span>${isEn ? \'Rounding\' : \'抹零\'}</span><span>-${fmt$(detailData.total_rounding)}</span></div>` : \'\'}
      ${Number(detailData.total_after_sales || 0) !== 0 ? `<div class="row red"><span>${isEn ? \'After Sales\' : \'售后调整\'}</span><span>-${fmt$(detailData.total_after_sales)}</span></div>` : \'\'}
      ${Number(detailData.total_discount || 0) !== 0 ? `<div class="row red"><span>${isEn ? \'Discount\' : \'折扣\'}</span><span>-${fmt$(detailData.total_discount)}</span></div>` : \'\'}
      <div class="row bold" style="border-top:1px solid #ddd;margin-top:2pt;padding-top:2pt"><span>${isEn ? \'Net Sales\' : \'销售净额\'}</span><span class="bold">${fmt$(detailData.total_sales_net)}</span></div>
    </div>
  </div>
    `;
  })()}

  <!-- 销售明细 -->
  <!-- 销售明细 -->'''

if old_print_unguohui_end in content:
    content = content.replace(old_print_unguohui_end, new_print_unguohui_end, 1)
    print("Replaced print unguohui end block")
else:
    print("WARNING: Could not find print unguohui end block")

with open('BatchReportsTab.tsx', 'w') as f:
    f.write(content)

print("Done!")
