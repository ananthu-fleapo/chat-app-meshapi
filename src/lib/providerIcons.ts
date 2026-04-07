import type { ProviderInfo, ProviderKey } from "./types";

const PROVIDER_MAP: Record<ProviderKey, ProviderInfo> = {
  openai: { key: "openai", label: "OpenAI", color: "#000000", bgColor: "#f0f0f0" },
  anthropic: { key: "anthropic", label: "Anthropic", color: "#cc785c", bgColor: "#fdf3ef" },
  google: { key: "google", label: "Google", color: "#4285F4", bgColor: "#e8f0fe" },
  xai: { key: "xai", label: "xAI", color: "#1a1a1a", bgColor: "#f5f5f5" },
  mistral: { key: "mistral", label: "Mistral", color: "#ff7000", bgColor: "#fff3e8" },
  meta: { key: "meta", label: "Meta", color: "#0082fb", bgColor: "#e7f3ff" },
  alibaba: { key: "alibaba", label: "Alibaba", color: "#ff6a00", bgColor: "#fff2e8" },
  zhipu: { key: "zhipu", label: "Zhipu", color: "#6366f1", bgColor: "#eef2ff" },
  deepseek: { key: "deepseek", label: "DeepSeek", color: "#1677ff", bgColor: "#e6f4ff" },
  cohere: { key: "cohere", label: "Cohere", color: "#39594d", bgColor: "#ecf5f2" },
  perplexity: { key: "perplexity", label: "Perplexity", color: "#20808d", bgColor: "#e6f6f8" },
  unknown: { key: "unknown", label: "AI", color: "#6b7280", bgColor: "#f3f4f6" },
};

export function getProviderFromModelId(modelId: string): ProviderInfo {
  const id = modelId.toLowerCase();

  if (id.startsWith("gpt") || id.startsWith("o1") || id.startsWith("o3") || id.startsWith("o4") || id.startsWith("chatgpt")) {
    return PROVIDER_MAP.openai;
  }
  if (id.startsWith("claude")) {
    return PROVIDER_MAP.anthropic;
  }
  if (id.startsWith("gemini") || id.startsWith("gemma") || id.startsWith("palm")) {
    return PROVIDER_MAP.google;
  }
  if (id.startsWith("grok")) {
    return PROVIDER_MAP.xai;
  }
  if (id.startsWith("mistral") || id.startsWith("mixtral") || id.startsWith("codestral") || id.startsWith("pixtral")) {
    return PROVIDER_MAP.mistral;
  }
  if (id.startsWith("llama") || id.startsWith("meta")) {
    return PROVIDER_MAP.meta;
  }
  if (id.startsWith("qwen") || id.startsWith("qwq")) {
    return PROVIDER_MAP.alibaba;
  }
  if (id.startsWith("glm") || id.startsWith("chatglm")) {
    return PROVIDER_MAP.zhipu;
  }
  if (id.startsWith("deepseek")) {
    return PROVIDER_MAP.deepseek;
  }
  if (id.startsWith("command") || id.startsWith("cohere")) {
    return PROVIDER_MAP.cohere;
  }
  if (id.startsWith("sonar") || id.startsWith("pplx")) {
    return PROVIDER_MAP.perplexity;
  }

  return PROVIDER_MAP.unknown;
}

export function getProviderInitials(modelId: string): string {
  const provider = getProviderFromModelId(modelId);
  const label = provider.label;
  return label.slice(0, 2).toUpperCase();
}

export { PROVIDER_MAP };
