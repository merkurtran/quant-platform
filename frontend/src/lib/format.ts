import dayjs from "dayjs";
import relativeTime from "dayjs/plugin/relativeTime";
import "dayjs/locale/zh-cn";

dayjs.extend(relativeTime);
dayjs.locale("zh-cn");

/**
 * 格式化价格 — 2 位小数
 */
export function formatPrice(value: number | string | null | undefined): string {
  if (value == null) return "--";
  const num = typeof value === "string" ? parseFloat(value) : value;
  if (isNaN(num)) return "--";
  return num.toFixed(2);
}

/**
 * 格式化百分比 — 带 +/- 前缀，2 位小数
 */
export function formatPercent(value: number | null | undefined): string {
  if (value == null || isNaN(value)) return "--";
  const sign = value > 0 ? "+" : "";
  return `${sign}${value.toFixed(2)}%`;
}

/**
 * 格式化金额 — 千分位 + 2 位小数
 */
export function formatMoney(value: number | string | null | undefined): string {
  if (value == null) return "--";
  const num = typeof value === "string" ? parseFloat(value) : value;
  if (isNaN(num)) return "--";
  return num.toLocaleString("zh-CN", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
}

/**
 * 格式化数量 — 千分位，无小数
 */
export function formatVolume(value: number | string | null | undefined): string {
  if (value == null) return "--";
  const num = typeof value === "string" ? parseFloat(value) : value;
  if (isNaN(num)) return "--";
  return num.toLocaleString("zh-CN", {
    maximumFractionDigits: 0,
  });
}

/**
 * 大金额缩写：1.2万 / 3.5亿
 */
export function formatCompact(value: number | string | null | undefined): string {
  if (value == null) return "--";
  const num = typeof value === "string" ? parseFloat(value) : value;
  if (isNaN(num)) return "--";
  const abs = Math.abs(num);
  if (abs >= 1e8) return (num / 1e8).toFixed(2) + "亿";
  if (abs >= 1e4) return (num / 1e4).toFixed(2) + "万";
  return num.toFixed(2);
}

/**
 * 日期格式化
 */
export function formatDate(value: string | null | undefined): string {
  if (!value) return "--";
  return dayjs(value).format("YYYY-MM-DD");
}

/**
 * 日期时间格式化
 */
export function formatDateTime(value: string | null | undefined): string {
  if (!value) return "--";
  return dayjs(value).format("YYYY-MM-DD HH:mm");
}

/**
 * 精确到秒
 */
export function formatDateTimeSec(value: string | null | undefined): string {
  if (!value) return "--";
  return dayjs(value).format("YYYY-MM-DD HH:mm:ss");
}

/**
 * 相对时间（3 分钟前）
 */
export function formatRelative(value: string | null | undefined): string {
  if (!value) return "--";
  return dayjs(value).fromNow();
}

/**
 * 涨跌色 class
 */
export function priceColor(value: number | null | undefined): string {
  if (value == null || value === 0) return "text-flat";
  return value > 0 ? "text-up" : "text-down";
}
