import type { MeshModel } from "./types";

// Fetches models via the Next.js server route — no API key or upstream URL exposed to browser
export async function fetchModels(): Promise<MeshModel[]> {
  const res = await fetch("/api/models");

  if (!res.ok) {
    throw new Error(`Failed to fetch models: ${res.status} ${res.statusText}`);
  }

  const data = await res.json();

  if (!Array.isArray(data)) return [];

  // Filter out models with missing/empty pricing
  return data.filter((model): model is MeshModel => {
    if (!model.id || !model.name) return false;
    if (!model.pricing) return false;

    const hasValidPrice =
      (model.pricing.prompt_usd_per_1k && model.pricing.prompt_usd_per_1k.trim()) ||
      (model.pricing.completion_usd_per_1k && model.pricing.completion_usd_per_1k.trim());

    return model.is_free || hasValidPrice;
  });
}
