export interface ModelPricing {
  prompt_usd_per_1k: string | null;  // Can be empty string, null, or valid decimal string
  completion_usd_per_1k: string | null;
  image_usd_per_image?: string | null;
  discount_pct?: string | null;
  prompt_usd_per_1k_discounted?: string | null;
  completion_usd_per_1k_discounted?: string | null;
}

export interface MeshModel {
  id: string;
  name: string;
  context_length: number | null;
  is_free: boolean;
  description: string | null;
  pricing: ModelPricing | null;
}

export interface ResponseUsage {
  prompt_tokens: number;
  completion_tokens: number;
  total_tokens: number;
  cost?: number;
}

export interface ModelResponseState {
  content: string;
  done: boolean;
  error?: string;
  usage?: ResponseUsage;
}

export interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  responses: Record<string, ModelResponseState>;
  createdAt: number;
}

export interface ChatRoom {
  id: string;
  title: string;
  messages: ChatMessage[];
  selectedModelIds: string[];
  createdAt: number;
}

export type ProviderKey =
  | "openai"
  | "anthropic"
  | "google"
  | "xai"
  | "mistral"
  | "meta"
  | "alibaba"
  | "zhipu"
  | "deepseek"
  | "cohere"
  | "perplexity"
  | "unknown";

export interface ProviderInfo {
  key: ProviderKey;
  label: string;
  color: string;
  bgColor: string;
}
