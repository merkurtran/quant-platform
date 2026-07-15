"use client";

import { useEffect, useRef } from "react";
import {
  AreaSeries,
  ColorType,
  CrosshairMode,
  createChart,
  type AreaData,
  type IChartApi,
  type Time,
} from "lightweight-charts";
import { useThemeStore } from "@/stores/theme";

interface EquityPoint {
  date: string;
  equity: number;
}

interface EquityCurveChartProps {
  data: EquityPoint[];
}

export function EquityCurveChart({ data }: EquityCurveChartProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const isDark = useThemeStore((state) => state.theme === "dark");

  useEffect(() => {
    if (!containerRef.current) return;

    const background = isDark ? "#1e222d" : "#ffffff";
    const textColor = isDark ? "#868993" : "#6a6d78";
    const gridColor = isDark ? "#2a2e39" : "#f0f3fa";
    const borderColor = isDark ? "#363a45" : "#e0e3eb";
    const chart = createChart(containerRef.current, {
      layout: {
        background: { type: ColorType.Solid, color: background },
        textColor,
        fontSize: 11,
      },
      grid: {
        vertLines: { color: gridColor },
        horzLines: { color: gridColor },
      },
      crosshair: { mode: CrosshairMode.Normal },
      rightPriceScale: { borderColor },
      timeScale: { borderColor, timeVisible: false },
      width: containerRef.current.clientWidth,
      height: containerRef.current.clientHeight,
    });
    chartRef.current = chart;

    const series = chart.addSeries(AreaSeries, {
      lineColor: "#089981",
      topColor: "rgba(8, 153, 129, 0.28)",
      bottomColor: "rgba(8, 153, 129, 0.02)",
      lineWidth: 2,
      priceFormat: { type: "price", precision: 2, minMove: 0.01 },
    });
    const points: AreaData<Time>[] = data
      .filter((point) => Number.isFinite(point.equity))
      .map((point) => ({ time: point.date as Time, value: point.equity }));
    series.setData(points);
    chart.timeScale().fitContent();

    const observer = new ResizeObserver(() => {
      if (!containerRef.current || !chartRef.current) return;
      chartRef.current.applyOptions({
        width: containerRef.current.clientWidth,
        height: containerRef.current.clientHeight,
      });
    });
    observer.observe(containerRef.current);

    return () => {
      observer.disconnect();
      chart.remove();
      chartRef.current = null;
    };
  }, [data, isDark]);

  return <div ref={containerRef} className="h-full w-full" />;
}
