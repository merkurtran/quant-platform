export interface StrategyParameterField {
  id: string;
  name: string;
  value: string;
  valueKind?: "string";
  description?: string;
}

export function createParameterField(
  name = "",
  value = "",
  valueKind?: "string",
  description?: string
): StrategyParameterField {
  return { id: crypto.randomUUID(), name, value, valueKind, description };
}

function parseParameterValue(
  name: string,
  value: string,
  valueKind?: "string"
): unknown {
  if (valueKind === "string") return value;
  const trimmed = value.trim();
  if (trimmed === "") return "";
  if (trimmed === "true") return true;
  if (trimmed === "false") return false;
  if (trimmed === "null") return null;
  if (/^-?(?:\d+\.?\d*|\.\d+)(?:e[+-]?\d+)?$/i.test(trimmed)) {
    const numberValue = Number(trimmed);
    if (Number.isFinite(numberValue)) return numberValue;
  }
  if (trimmed.startsWith("[") || trimmed.startsWith("{")) {
    try {
      return JSON.parse(trimmed) as unknown;
    } catch {
      throw new Error(`INVALID_PARAMETER_VALUE:${name}`);
    }
  }
  return value;
}

export function paramsToFields(
  params: Record<string, unknown>,
  code = ""
): StrategyParameterField[] {
  const definitions = extractParameterDefinitions(code);
  const orderedNames = [
    ...definitions.map((item) => item.name),
    ...Object.keys(params).filter((name) => !definitions.some((item) => item.name === name)),
  ];
  return orderedNames.map((name) => {
    const definition = definitions.find((item) => item.name === name);
    const value = Object.hasOwn(params, name) ? params[name] : definition?.defaultValue;
    return createParameterField(
      name,
      serializeValue(value),
      typeof value === "string" ? "string" : undefined,
      definition?.description ?? parameterMeta(name).description
    );
  });
}

export function syncParameterFieldsFromCode(
  code: string,
  fields: StrategyParameterField[]
): StrategyParameterField[] {
  const definitions = extractParameterDefinitions(code);
  if (definitions.length === 0) return fields;
  const existing = new Map(fields.map((field) => [field.name, field]));
  return definitions.map((definition) => {
    const field = existing.get(definition.name);
    if (field) {
      return {
        ...field,
        description: definition.description ?? parameterMeta(definition.name).description,
      };
    }
    const value = definition.defaultValue;
    return createParameterField(
      definition.name,
      serializeValue(value),
      typeof value === "string" ? "string" : undefined,
      definition.description ?? parameterMeta(definition.name).description
    );
  });
}

export function parameterMeta(name: string) {
  const normalized = name.toLowerCase();
  if (normalized.includes("fast")) return { label: "快速周期", description: "短周期指标使用的 K 线数量，数值越小越敏感。" };
  if (normalized.includes("slow")) return { label: "慢速周期", description: "长周期指标使用的 K 线数量，用于判断主要趋势。" };
  if (normalized.includes("stop") && normalized.includes("loss")) return { label: "止损比例", description: "亏损达到该比例时退出持仓，例如 0.05 表示 5%。" };
  if (normalized.includes("take") && normalized.includes("profit")) return { label: "止盈比例", description: "盈利达到该比例时退出持仓，例如 0.15 表示 15%。" };
  if (normalized.includes("position") || normalized.includes("size")) return { label: "仓位参数", description: "控制单次交易使用的资金或下单数量。" };
  if (normalized.includes("threshold")) return { label: "触发阈值", description: "策略信号达到该阈值后触发交易。" };
  if (normalized.includes("period") || normalized.includes("window")) return { label: "计算周期", description: "指标计算使用的历史 K 线数量。" };
  return { label: humanizeName(name), description: "策略代码中定义的可调参数，修改后仅影响后续回测。" };
}

interface ParameterDefinition {
  name: string;
  defaultValue: unknown;
  description?: string;
}

function extractParameterDefinitions(code: string): ParameterDefinition[] {
  const definitions: ParameterDefinition[] = [];
  const pattern = /^\s*\(\s*["']([A-Za-z_]\w*)["']\s*,\s*(.*?)\s*\)\s*,?\s*(?:#\s*(.*))?$/gm;
  for (const match of code.matchAll(pattern)) {
    definitions.push({
      name: match[1],
      defaultValue: parseCodeValue(match[2]),
      description: match[3]?.trim() || undefined,
    });
  }
  return definitions;
}

function parseCodeValue(value: string): unknown {
  const trimmed = value.trim();
  if ((trimmed.startsWith('"') && trimmed.endsWith('"')) || (trimmed.startsWith("'") && trimmed.endsWith("'"))) {
    return trimmed.slice(1, -1);
  }
  return parseParameterValue("code", trimmed);
}

function serializeValue(value: unknown) {
  if (value === undefined) return "";
  return typeof value === "string" ? value : (JSON.stringify(value) ?? "");
}

function humanizeName(name: string) {
  return name
    .split("_")
    .filter(Boolean)
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
}

export function fieldsToParams(
  fields: StrategyParameterField[]
): Record<string, unknown> {
  const result: Record<string, unknown> = {};
  for (const field of fields) {
    const name = field.name.trim();
    if (!name) throw new Error("INVALID_PARAMETER_NAME");
    if (Object.hasOwn(result, name)) {
      throw new Error(`DUPLICATE_PARAMETER:${name}`);
    }
    result[name] = parseParameterValue(name, field.value, field.valueKind);
  }
  return result;
}
