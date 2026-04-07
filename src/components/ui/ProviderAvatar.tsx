"use client";

import { getProviderFromModelId } from "@/lib/providerIcons";

interface Props {
  modelId: string;
  size?: number;
  className?: string;
}

export function ProviderAvatar({ modelId, size = 24, className = "" }: Props) {
  const provider = getProviderFromModelId(modelId);
  const initials = provider.label.slice(0, 2).toUpperCase();

  return (
    <span
      className={`inline-flex items-center justify-center rounded-full font-bold text-xs shrink-0 ${className}`}
      style={{
        width: size,
        height: size,
        backgroundColor: provider.bgColor,
        color: provider.color,
        fontSize: size * 0.38,
        border: `1.5px solid ${provider.color}22`,
      }}
      title={provider.label}
    >
      {initials}
    </span>
  );
}
