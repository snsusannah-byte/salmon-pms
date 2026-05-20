import Decimal from "decimal.js";

/**
 * 安全金额运算工具
 *
 * 后端使用 Numeric(15,2)，前端直接用 Number() 转换大金额会产生浮点精度误差。
 * 例如：Number("9449761.28") + Number("0.01") 可能得到 9449761.289999999
 *
 * 本模块提供基于 decimal.js 的安全金额运算和格式化函数。
 */

// 全局配置：保留2位小数（与后端 Numeric(15,2) 一致）
Decimal.set({ precision: 20, rounding: Decimal.ROUND_HALF_UP });

/** 任意值转为 Decimal */
export function toDecimal(value: unknown): Decimal {
  if (value === null || value === undefined || value === "") {
    return new Decimal(0);
  }
  if (value instanceof Decimal) {
    return value;
  }
  try {
    return new Decimal(String(value));
  } catch {
    return new Decimal(0);
  }
}

/** 加法 */
export function add(a: unknown, b: unknown): Decimal {
  return toDecimal(a).plus(toDecimal(b));
}

/** 减法 */
export function sub(a: unknown, b: unknown): Decimal {
  return toDecimal(a).minus(toDecimal(b));
}

/** 乘法 */
export function mul(a: unknown, b: unknown): Decimal {
  return toDecimal(a).times(toDecimal(b));
}

/** 除法 */
export function div(a: unknown, b: unknown): Decimal {
  const divisor = toDecimal(b);
  if (divisor.isZero()) {
    return new Decimal(0);
  }
  return toDecimal(a).dividedBy(divisor);
}

/** 数组求和 */
export function sum(values: unknown[]): Decimal {
  return values.reduce((acc, v) => acc.plus(toDecimal(v)), new Decimal(0));
}

/** 取绝对值 */
export function abs(value: unknown): Decimal {
  return toDecimal(value).abs();
}

/** 比较：a > b */
export function gt(a: unknown, b: unknown): boolean {
  return toDecimal(a).gt(toDecimal(b));
}

/** 比较：a >= b */
export function gte(a: unknown, b: unknown): boolean {
  return toDecimal(a).gte(toDecimal(b));
}

/** 比较：a < b */
export function lt(a: unknown, b: unknown): boolean {
  return toDecimal(a).lt(toDecimal(b));
}

/** 比较：a <= b */
export function lte(a: unknown, b: unknown): boolean {
  return toDecimal(a).lte(toDecimal(b));
}

/** 比较：a === b */
export function eq(a: unknown, b: unknown): boolean {
  return toDecimal(a).eq(toDecimal(b));
}

/** 最大 */
export function max(a: unknown, b: unknown): Decimal {
  return Decimal.max(toDecimal(a), toDecimal(b));
}

/** 最小 */
export function min(a: unknown, b: unknown): Decimal {
  return Decimal.min(toDecimal(a), toDecimal(b));
}

/** 保留 N 位小数，返回 Decimal（默认2位） */
export function round(value: unknown, dp = 2): Decimal {
  return toDecimal(value).toDecimalPlaces(dp);
}

/** 转为指定精度字符串（用于提交后端） */
export function toStr(value: unknown, dp = 2): string {
  return toDecimal(value).toFixed(dp);
}

/** 转为数字（仅在确实需要 Number 时使用，如 input 的 value） */
export function toNumber(value: unknown): number {
  return toDecimal(value).toNumber();
}

/**
 * 格式化金额显示
 * @param value 金额值
 * @param currency 币种标识 "cny" | "usd" | null
 * @param dp 小数位
 * @returns 格式化字符串，如 "¥1,234.56" 或 "$1,234.56"
 */
export function fmt(
  value: unknown,
  currency?: "cny" | "usd",
  dp = 2,
): string {
  if (value === undefined || value === null || value === "" || Number.isNaN(Number(value))) {
    return "-";
  }
  const d = toDecimal(value);
  const absVal = d.abs();
  const num = absVal.toNumber();
  const formatted = num.toLocaleString("en-US", {
    minimumFractionDigits: dp,
    maximumFractionDigits: dp,
  });
  const sign = d.isNegative() ? "-" : "";
  const prefix = currency === "cny" ? "¥" : currency === "usd" ? "$" : "";
  return `${sign}${prefix}${formatted}`;
}

/** 人民币格式 */
export function fmtCNY(value: unknown, dp = 2): string {
  return fmt(value, "cny", dp);
}

/** 美元格式 */
export function fmtUSD(value: unknown, dp = 2): string {
  return fmt(value, "usd", dp);
}

/** 仅数字格式化（无币种前缀） */
export function fmtNum(value: unknown, dp = 2): string {
  return fmt(value, undefined, dp);
}

/** 重量格式化（3位小数） */
export function fmtWeight(value: unknown): string {
  return fmt(value, undefined, 3);
}

/**
 * 安全 reduce 求和工具
 * 替代：arr.reduce((s, r) => s + Number(r.amount || 0), 0)
 * 使用：arr.reduce((s, r) => s.plus(toDecimal(r.amount)), new Decimal(0)).toNumber()
 */
export function reduceSum(
  arr: any[],
  getter: (item: any) => unknown,
): Decimal {
  return arr.reduce((acc, item) => acc.plus(toDecimal(getter(item))), new Decimal(0));
}
