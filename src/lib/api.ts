import OpenAI from "openai";
import type { MeshModel } from "./types";

const API_URL = process.env.NEXT_PUBLIC_MESH_API_URL ?? "http://localhost:8000/v1";
const API_KEY = process.env.NEXT_PUBLIC_MESH_API_KEY ?? "";

// Use native fetch for /models as required
export async function fetchModels(): Promise<MeshModel[]> {
  const res = await fetch(`${API_URL}/models`, {
    headers: {
      Authorization: `Bearer ${API_KEY}`,
    },
  });

  if (!res.ok) {
    throw new Error(`Failed to fetch models: ${res.status} ${res.statusText}`);
  }

  const data = await res.json();

  // API returns array directly
  if (!Array.isArray(data)) return [];

  // Filter and normalize: exclude models with empty pricing strings
  return data.filter((model): model is MeshModel => {
    if (!model.id || !model.name) return false;

    // Ensure pricing object exists and has at least one valid price
    if (!model.pricing) return false;

    const hasValidPrice =
      (model.pricing.prompt_usd_per_1k && model.pricing.prompt_usd_per_1k.trim()) ||
      (model.pricing.completion_usd_per_1k && model.pricing.completion_usd_per_1k.trim());

    return model.is_free || hasValidPrice;
  });
}

// OpenAI SDK client for chat completions with streaming
export const meshClient = new OpenAI({
  baseURL: API_URL,
  apiKey: API_KEY,
  dangerouslyAllowBrowser: true,
});
