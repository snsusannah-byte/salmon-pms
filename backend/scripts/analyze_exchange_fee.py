#!/usr/bin/env python3
"""
分析购汇手续费规律，推导估算公式
"""

# 从旧系统导出的数据 (exchange_payment, exchange_fee)
# payment = 购汇金额(CNY), fee = 手续费(CNY)
data = [
    (532311.24, 678.89),
    (488477.22, 894.71),
    (390507.29, 814.18),
    (375582.67, 553.51),
    (261813.36, 463.34),
    (244734.45, 449.68),
    (240656.83, 442.59),
    (233900.87, 439.45),
    (191915.12, 405.54),
    (169603.52, 390.55),
    (83191.02, 318.42),
]

print("=" * 70)
print("原始数据分析")
print("=" * 70)
print(f"{'购汇金额(CNY)':>16} | {'手续费(CNY)':>12} | {'费率(%)':>10} | {'手续费/万':>10}")
print("-" * 70)

ratios = []
for payment, fee in data:
    ratio = fee / payment * 100
    per_wan = fee / (payment / 10000)
    ratios.append(ratio)
    print(f"{payment:16.2f} | {fee:12.2f} | {ratio:10.4f} | {per_wan:10.2f}")

print()
print("=" * 70)
print("模型一：固定比例")
print("=" * 70)

avg_ratio = sum(ratios) / len(ratios)
print(f"平均费率: {avg_ratio:.4f}%")

# 最小二乘拟合比例
from functools import reduce
numerator = sum(p * f for p, f in data)
denominator = sum(p * p for p, _ in data)
k = numerator / denominator
print(f"最优固定比例 k = {k*100:.4f}%")
print(f"公式: 手续费 = 购汇金额 × {k*100:.4f}%")
print()

# 计算误差
print("误差分析：")
for payment, fee in data:
    est = payment * k
    err = est - fee
    err_pct = abs(err) / fee * 100
    print(f"  金额 {payment:12.2f} | 实际 {fee:8.2f} | 估算 {est:8.2f} | 误差 {err:+8.2f} ({err_pct:.1f}%)")

print()
print("=" * 70)
print("模型二：固定费用 + 比例")
print("=" * 70)

# 线性回归: fee = a + b * payment
n = len(data)
sum_x = sum(p for p, _ in data)
sum_y = sum(f for _, f in data)
sum_xy = sum(p * f for p, f in data)
sum_x2 = sum(p * p for p, _ in data)

b = (n * sum_xy - sum_x * sum_y) / (n * sum_x2 - sum_x * sum_x)
a = (sum_y - b * sum_x) / n

print(f"固定费用 a = {a:.2f} CNY")
print(f"比例费率 b = {b*100:.4f}%")
print(f"公式: 手续费 = {a:.2f} + 购汇金额 × {b*100:.4f}%")
print()

print("误差分析：")
for payment, fee in data:
    est = a + b * payment
    err = est - fee
    err_pct = abs(err) / fee * 100
    print(f"  金额 {payment:12.2f} | 实际 {fee:8.2f} | 估算 {est:8.2f} | 误差 {err:+8.2f} ({err_pct:.1f}%)")

print()
print("=" * 70)
print("模型三：阶梯费率（按金额分段）")
print("=" * 70)

# 尝试找出阶梯
for payment, fee in sorted(data, key=lambda x: x[0]):
    ratio = fee / payment * 100
    per_wan = fee / (payment / 10000)
    print(f"  金额 {payment:12.2f} | 手续费 {fee:8.2f} | 费率 {ratio:.4f}% | 每万元 {per_wan:.2f}")

print()

# 尝试阶梯分段
# 观察发现：
# 8万级别：费率 0.38%，每万约 38元
# 16-26万：费率 0.18-0.23%，每万约 17-23元
# 37-53万：费率 0.13-0.21%，每万约 13-21元

print("=" * 70)
print("模型四：每万元固定费用")
print("=" * 70)

# 计算每万元费用
per_wan_values = [fee / (payment / 10000) for payment, fee in data]
avg_per_wan = sum(per_wan_values) / len(per_wan_values)
print(f"平均每万元手续费: {avg_per_wan:.2f} 元")

# 看看中位数
sorted_per_wan = sorted(per_wan_values)
median_per_wan = sorted_per_wan[len(sorted_per_wan)//2]
print(f"中位数每万元手续费: {median_per_wan:.2f} 元")

print()
print("=" * 70)
print("推荐算法")
print("=" * 70)

# 基于线性回归结果，给出推荐公式
print(f"""
基于11条历史购汇记录的线性回归分析：

【推荐估算公式】
    手续费 = {max(0, a):.2f} + 购汇金额 × {b*100:.4f}%

即：
    - 基础费用约 {max(0, a):.0f} 元
    - 加上购汇金额的 {b*100:.2f}%

【简化版本】
    手续费 ≈ 购汇金额 × {k*100:.3f}%

【阶梯估算（更贴近银行实际）】
    根据历史数据观察，手续费率随金额增大而降低：
    - 金额 < 10万：  费率约 0.35%-0.40%
    - 金额 10-30万： 费率约 0.18%-0.23%
    - 金额 30-50万： 费率约 0.13%-0.21%

【每万元参考】
    - 平均每万元手续费: {avg_per_wan:.1f} 元
    - 范围: {min(per_wan_values):.1f} ~ {max(per_wan_values):.1f} 元/万元
""")

# 验证推荐公式
print("=" * 70)
print("推荐公式验证")
print("=" * 70)
formula_type = "linear"  # linear: a + b*x

print(f"公式: 手续费 = {max(0, a):.2f} + 金额 × {b*100:.4f}%")
print()
total_err = 0
for payment, fee in data:
    est = max(0, a) + b * payment
    err = abs(est - fee)
    err_pct = err / fee * 100
    total_err += err_pct
    print(f"  金额 {payment:12.2f} | 实际 {fee:8.2f} | 估算 {est:8.2f} | 偏差 {err_pct:.1f}%")

print(f"\n平均偏差: {total_err / len(data):.1f}%")
