"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import type { IChartApi, ISeriesApi, SeriesType } from "lightweight-charts";
import {
  Arrow,
  DrawingManager,
  FibRetracement,
  HorizontalLine,
  Rectangle,
  TrendLine,
  type Anchor,
  type DrawingOptions,
  type DrawingStyle,
  type IDrawing,
  type SerializedDrawing,
} from "lightweight-charts-drawing";

export type CoreDrawingTool =
  | "trend-line"
  | "horizontal-line"
  | "fib-retracement"
  | "rectangle"
  | "arrow";

const PREVIEW_ID = "drawing-preview";
const REQUIRED_ANCHORS: Record<CoreDrawingTool, number> = {
  "trend-line": 2,
  "horizontal-line": 1,
  "fib-retracement": 2,
  rectangle: 2,
  arrow: 2,
};
const DEFAULT_STYLE: Partial<DrawingStyle> = {
  lineColor: "#2962ff",
  lineWidth: 2,
  fillColor: "rgba(41, 98, 255, 0.14)",
  labelColor: "#2962ff",
};

export function useChartDrawings(storageKey: string) {
  const [activeTool, setActiveTool] = useState<CoreDrawingTool | null>(null);
  const [hasSelection, setHasSelection] = useState(false);
  const managerRef = useRef<DrawingManager | null>(null);
  const activeToolRef = useRef<CoreDrawingTool | null>(null);
  const pendingAnchorsRef = useRef<Anchor[]>([]);
  const previewRef = useRef<IDrawing | null>(null);
  const drawingCounterRef = useRef(0);
  const savedDrawingsRef = useRef<SerializedDrawing[]>([]);

  useEffect(() => {
    try {
      const saved = window.localStorage.getItem(storageKey);
      savedDrawingsRef.current = saved ? JSON.parse(saved) : [];
    } catch {
      savedDrawingsRef.current = [];
    }
  }, [storageKey]);

  const removePreview = useCallback(() => {
    if (previewRef.current && managerRef.current) {
      managerRef.current.removeDrawing(PREVIEW_ID);
    }
    previewRef.current = null;
  }, []);

  const cancelPlacement = useCallback(() => {
    removePreview();
    pendingAnchorsRef.current = [];
  }, [removePreview]);

  const selectTool = useCallback((tool: CoreDrawingTool | null) => {
    cancelPlacement();
    const nextTool = activeToolRef.current === tool ? null : tool;
    activeToolRef.current = nextTool;
    managerRef.current?.setActiveTool(nextTool);
    setActiveTool(nextTool);
  }, [cancelPlacement]);

  const deleteSelected = useCallback(() => {
    const manager = managerRef.current;
    const selected = manager?.getSelectedDrawing();
    if (selected) {
      manager?.removeDrawing(selected.id);
      setHasSelection(false);
    }
  }, []);

  const clearAll = useCallback(() => {
    cancelPlacement();
    managerRef.current?.clearAll();
    setHasSelection(false);
  }, [cancelPlacement]);

  const attach = useCallback((
    chart: IChartApi,
    series: ISeriesApi<SeriesType>,
    container: HTMLElement
  ) => {
    const manager = new DrawingManager();
    managerRef.current = manager;
    manager.attach(chart, series, container);
    manager.setActiveTool(activeToolRef.current);

    for (const item of savedDrawingsRef.current) {
      const drawing = createDrawing(item.type, item.id, item.anchors, item.style, item.options);
      if (drawing) manager.addDrawing(drawing);
    }

    const persist = () => {
      const drawings = manager.exportDrawings().filter((item) => item.id !== PREVIEW_ID);
      savedDrawingsRef.current = drawings;
      window.localStorage.setItem(storageKey, JSON.stringify(drawings));
    };
    const unsubscribers = [
      manager.on("drawing:added", persist),
      manager.on("drawing:removed", persist),
      manager.on("drawing:updated", persist),
      manager.on("drawing:cleared", persist),
      manager.on("drawing:selected", () => setHasSelection(true)),
      manager.on("drawing:deselected", () => setHasSelection(false)),
    ];

    const handleClick = (event: MouseEvent) => {
      const tool = activeToolRef.current;
      if (!tool) return;
      const anchor = eventToAnchor(event, chart, series, container);
      if (!anchor) return;

      pendingAnchorsRef.current.push(anchor);
      if (pendingAnchorsRef.current.length < REQUIRED_ANCHORS[tool]) {
        removePreview();
        const previewAnchors = [...pendingAnchorsRef.current, anchor];
        const preview = createDrawing(tool, PREVIEW_ID, previewAnchors, DEFAULT_STYLE);
        if (preview) {
          previewRef.current = preview;
          manager.addDrawing(preview);
        }
        return;
      }

      removePreview();
      const drawing = createDrawing(
        tool,
        `drawing-${Date.now()}-${++drawingCounterRef.current}`,
        pendingAnchorsRef.current,
        DEFAULT_STYLE
      );
      pendingAnchorsRef.current = [];
      if (drawing) {
        manager.addDrawing(drawing);
        manager.selectDrawing(drawing.id);
      }
    };

    const handleMouseMove = (event: MouseEvent) => {
      const tool = activeToolRef.current;
      const preview = previewRef.current;
      if (!tool || !preview || pendingAnchorsRef.current.length === 0) return;
      const anchor = eventToAnchor(event, chart, series, container);
      if (anchor) preview.updateAnchor(pendingAnchorsRef.current.length, anchor);
    };

    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.target instanceof HTMLInputElement || event.target instanceof HTMLTextAreaElement) return;
      if (event.key === "Escape") selectTool(null);
      if (event.key === "Delete" || event.key === "Backspace") deleteSelected();
    };

    container.addEventListener("click", handleClick);
    container.addEventListener("mousemove", handleMouseMove);
    document.addEventListener("keydown", handleKeyDown);

    return () => {
      persist();
      unsubscribers.forEach((unsubscribe) => unsubscribe());
      container.removeEventListener("click", handleClick);
      container.removeEventListener("mousemove", handleMouseMove);
      document.removeEventListener("keydown", handleKeyDown);
      manager.detach();
      if (managerRef.current === manager) managerRef.current = null;
    };
  }, [deleteSelected, removePreview, selectTool, storageKey]);

  return { activeTool, hasSelection, selectTool, deleteSelected, clearAll, attach };
}

function eventToAnchor(
  event: MouseEvent,
  chart: IChartApi,
  series: ISeriesApi<SeriesType>,
  container: HTMLElement
): Anchor | null {
  const rect = container.getBoundingClientRect();
  const time = chart.timeScale().coordinateToTime(event.clientX - rect.left);
  const price = series.coordinateToPrice(event.clientY - rect.top);
  return time === null || price === null ? null : { time, price };
}

function createDrawing(
  type: string,
  id: string,
  anchors: Anchor[],
  style: Partial<DrawingStyle> = {},
  options: Partial<DrawingOptions> = {}
): IDrawing | null {
  switch (type) {
    case "trend-line": return new TrendLine(id, anchors, style, options);
    case "horizontal-line": return new HorizontalLine(id, anchors, style, options);
    case "fib-retracement": return new FibRetracement(id, anchors, style, options);
    case "rectangle": return new Rectangle(id, anchors, style, options);
    case "arrow": return new Arrow(id, anchors, style, options);
    default: return null;
  }
}
