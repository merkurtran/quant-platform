export interface StrategyParameterField {
  id: string;
  name: string;
  value: string;
  valueKind?: "string";
}

export function createParameterField(
  name = "",
  value = "",
  valueKind?: "string"
): StrategyParameterField {
  return { id: crypto.randomUUID(), name, value, valueKind };
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
  params: Record<string, unknown>
): StrategyParameterField[] {
  return Object.entries(params).map(([name, value]) =>
    createParameterField(
      name,
      typeof value === "string" ? value : (JSON.stringify(value) ?? ""),
      typeof value === "string" ? "string" : undefined
    )
  );
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
