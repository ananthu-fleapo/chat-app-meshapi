import { useQuery } from "@tanstack/react-query";
import { fetchModels } from "@/lib/api";
import type { MeshModel } from "@/lib/types";

export function useModels() {
  return useQuery<MeshModel[]>({
    queryKey: ["models"],
    queryFn: fetchModels,
    staleTime: 1000 * 60 * 5, // 5 minutes (matches server cache)
    retry: 2,
  });
}

export function useGroupedModels() {
  const query = useModels();

  const grouped = query.data
    ? groupModelsByMonth(query.data)
    : [];

  return { ...query, grouped };
}

function groupModelsByMonth(models: MeshModel[]): Array<{ label: string; models: MeshModel[] }> {
  // Models come ordered by recency from the API — group by a synthetic date
  // We'll just show them all under a single group if no date info, or chunk into groups of ~10
  const groups: Array<{ label: string; models: MeshModel[] }> = [];

  // Try to infer groupings from common naming patterns or just show as a flat list
  // The API response doesn't include a release date, so we group alphabetically by provider
  const providerGroups = new Map<string, MeshModel[]>();

  for (const model of models) {
    const id = model.id.toLowerCase();
    let provider = "Other";
    if (id.startsWith("gpt") || id.startsWith("o1") || id.startsWith("o3") || id.startsWith("o4") || id.startsWith("chatgpt")) provider = "OpenAI";
    else if (id.startsWith("claude")) provider = "Anthropic";
    else if (id.startsWith("gemini") || id.startsWith("gemma")) provider = "Google";
    else if (id.startsWith("grok")) provider = "xAI";
    else if (id.startsWith("mistral") || id.startsWith("mixtral")) provider = "Mistral";
    else if (id.startsWith("llama") || id.startsWith("meta")) provider = "Meta";
    else if (id.startsWith("qwen") || id.startsWith("qwq")) provider = "Alibaba";
    else if (id.startsWith("deepseek")) provider = "DeepSeek";
    else if (id.startsWith("glm")) provider = "Zhipu";

    if (!providerGroups.has(provider)) {
      providerGroups.set(provider, []);
    }
    providerGroups.get(provider)!.push(model);
  }

  const order = ["OpenAI", "Anthropic", "Google", "xAI", "Mistral", "Meta", "Alibaba", "DeepSeek", "Zhipu", "Other"];
  for (const label of order) {
    const group = providerGroups.get(label);
    if (group && group.length > 0) {
      groups.push({ label, models: group });
    }
  }

  return groups;
}
