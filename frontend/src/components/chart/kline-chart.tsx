"use client";

import { useEffect, useRef, useState } from "react";
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
} from "lightweight-charts";
import type { KlineItem } from "@/types";

const UP_COLOR = "#ef4444"; // A 股红涨
const DOWN_COLOR = "#22c55e"; // A 股绿跌

export function KlineChart({ data }: KlineChartProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const [isDark, setIsDark] = useState(false);

  // 监听主题变化
  useEffect(() => {
    const update = () => {
      setIsDark(document.documentElement.classList.contains("dark"));
    };
    update();
    const observer = new MutationObserver(update);
    observer.observe(document.documentElement, {
      attributes: true,
      attributeFilter: ["class"],
    });
    return () => observer.disconnect();
  }, []);

  useEffect(() => {
    if (!containerRef.current) return;

    const bg = isDark ? "#0a0a0a" : "#ffffff";
    const textColor = isDark ? "#9ca3af" : "#6b7280";
    const gridColor = isDark ? "#1c1c1c" : "#f8f9fb";
    const borderColor = isDark ? "#2a2a2a" : "#e5e7eb";

    const chart = createChart(containerRef.current, {
      layout: {
        background: { type: ColorType.Solid, color: bg },
        textColor,
        fontSize: 12,
      },
      grid: {
        vertLines: { color: gridColor },
        horzLines: { color: gridColor },
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
