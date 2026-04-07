export const MODEL_CATEGORIES = {
  flagship: {
    label: "Flagship models",
    description: "The best general-purpose models from top providers",
    modelIds: [
      "gpt-4o",
      "gpt-5",
      "claude-opus-4-6",
      "gemini-3-pro-preview",
      "grok-4",
    ],
  },
  roleplay: {
    label: "Best roleplay models",
    description: "Models excelling at creative and character roleplay",
    modelIds: [
      "claude-opus-4-6",
      "gpt-4o",
      "mistral-large",
      "grok-4",
    ],
  },
  coding: {
    label: "Best coding models",
    description: "Top performers on coding benchmarks",
    modelIds: [
      "gpt-4o",
      "claude-opus-4-6",
      "grok-4",
      "gemini-3-pro-preview",
      "deepseek-coder",
    ],
  },
  reasoning: {
    label: "Reasoning models",
    description: "Models with advanced chain-of-thought reasoning",
    modelIds: [
      "o3",
      "o4-mini",
      "claude-opus-4-6",
      "gemini-3-pro-preview",
      "grok-4",
    ],
  },
} as const;

export type CategoryKey = keyof typeof MODEL_CATEGORIES;

export const PROMPT_SUGGESTIONS = [
  { label: "Educational Advances", prompt: "What are the biggest recent advances in higher education?" },
  { label: "9.9 vs 9.11", prompt: "9.9 and 9.11, which one is larger?" },
  { label: "Strawberry Test", prompt: "How many r's are in the word strawberry?" },
  { label: "Poem Riddle", prompt: "Compose a 12-line poem that contains a hidden riddle." },
  { label: "Personal Finance", prompt: "Draft up a portfolio management strategy for a 30-year-old." },
  { label: "Code Challenge", prompt: "Write a recursive function to solve the Tower of Hanoi." },
  { label: "Explain Quantum", prompt: "Explain quantum entanglement in simple terms." },
];
