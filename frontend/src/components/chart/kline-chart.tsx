"use client";

import { useEffect, useRef } from "react";
import {
  createChart,
  CandlestickSeries,
  HistogramSeries,
  type IChartApi,
  type CandlestickData,
  type HistogramData,
  type UTCTimestamp,
  ColorType,
  CrosshairMode,
  LineStyle,
} from "lightweight-charts";
import { useThemeStore } from "@/stores/theme";
import type { KlineItem } from "@/types";

const UP_COLOR = "#ef4444"; // A 股红涨
const DOWN_COLOR = "#22c55e"; // A 股绿跌

export function KlineChart({ data }: KlineChartProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const isDark = useThemeStore((state) => state.theme === "dark");

  useEffect(() => {
    if (!containerRef.current) return;

    const bg = isDark ? "#1e222d" : "#ffffff";
    const textColor = isDark ? "#868993" : "#6a6d78";
    const gridColor = isDark ? "#2a2e39" : "#f0f3fa";
    const borderColor = isDark ? "#2a2e39" : "#e0e3eb";

    const chart = createChart(containerRef.current, {
      layout: {
        background: { type: ColorType.Solid, color: bg },
        textColor,
        fontSize: 12,
      },
      grid: {
        vertLines: { color: gridColor, style: LineStyle.Dotted },
        horzLines: { color: gridColor, style: LineStyle.Dotted },
      },
      crosshair: {
        mode: CrosshairMode.Normal,
        vertLine: { color: borderColor, labelBackgroundColor: "#2563eb" },
        horzLine: { color: borderColor, labelBackgroundColor: "#2563eb" },
      },
      rightPriceScale: { borderColor },
      timeScale: { borderColor, timeVisible: true, secondsVisible: false },
      width: containerRef.current.clientWidth,
      height: containerRef.current.clientHeight,
    });

    chartRef.current = chart;

    const candleSeries = chart.addSeries(CandlestickSeries, {
      upColor: UP_COLOR,
      downColor: DOWN_COLOR,
      borderUpColor: UP_COLOR,
      borderDownColor: DOWN_COLOR,
      wickUpColor: UP_COLOR,
      wickDownColor: DOWN_COLOR,
    });

    const candleData: CandlestickData[] = data.map((k) => ({
      time: (new Date(k.ts).getTime() / 1000) as UTCTimestamp,
      open: parseFloat(k.open),
      high: parseFloat(k.high),
      low: parseFloat(k.low),
      close: parseFloat(k.close),
    }));

    candleSeries.setData(candleData);

    const volumeSeries = chart.addSeries(HistogramSeries, {
      priceFormat: { type: "volume" },
      priceScaleId: "vol",
    });
    chart.priceScale("vol").applyOptions({
      scaleMargins: { top: 0.8, bottom: 0 },
    });

    volumeSeries.setData(
      data.map((k): HistogramData => ({
        time: (new Date(k.ts).getTime() / 1000) as UTCTimestamp,
        value: parseFloat(k.volume),
        color: parseFloat(k.close) >= parseFloat(k.open)
          ? UP_COLOR + "40"
          : DOWN_COLOR + "40",
      }))
    );

    chart.timeScale().fitContent();

    // 响应式
    const ro = new ResizeObserver(() => {
      if (containerRef.current && chartRef.current) {
        chartRef.current.applyOptions({
          width: containerRef.current.clientWidth,
          height: containerRef.current.clientHeight,
        });
      }
    });
    ro.observe(containerRef.current);

    return () => {
      ro.disconnect();
      chart.remove();
      chartRef.current = null;
    };
  }, [data, isDark]);

  return <div ref={containerRef} className="h-full w-full" />;
}

interface KlineChartProps {
  data: KlineItem[];
}
