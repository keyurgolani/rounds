// Curated list of popular custom AI provider endpoints, surfaced as
// "quick fill" chips on the provider form so users don't have to type
// (or recall) base URLs by hand.
//
// These URLs change occasionally and a few providers run regional
// variants (Beijing vs international, US-East vs EU, etc.) — the form
// only auto-fills `base_url`, and the user can always edit it after.
// Adding / updating an entry here is meant to be a one-line change.

import type { ProviderKind } from '../features/resume/ai/client';

export type EndpointPreset = {
  /** Stable id used for keying React lists. */
  id: string;
  /** User-visible label on the chip. */
  label: string;
  /** Pre-filled base URL. */
  base_url: string;
  /** Which provider kind this preset applies to. */
  kind: Extract<ProviderKind, 'openai-compatible' | 'anthropic-compatible'>;
  /** One-line tooltip shown on hover (model family, region note, etc.). */
  hint?: string;
};

export const POPULAR_ENDPOINTS: EndpointPreset[] = [
  // ---- OpenAI-compatible ------------------------------------------------
  {
    id: 'groq',
    label: 'Groq',
    base_url: 'https://api.groq.com/openai/v1',
    kind: 'openai-compatible',
    hint: 'Llama, Mixtral, Whisper — fastest inference per dollar.',
  },
  {
    id: 'deepseek',
    label: 'DeepSeek',
    base_url: 'https://api.deepseek.com/v1',
    kind: 'openai-compatible',
    hint: 'DeepSeek-V3, DeepSeek-R1 reasoning.',
  },
  {
    id: 'openrouter',
    label: 'OpenRouter',
    base_url: 'https://openrouter.ai/api/v1',
    kind: 'openai-compatible',
    hint: 'Single key, hundreds of models from every major provider.',
  },
  {
    id: 'together',
    label: 'Together AI',
    base_url: 'https://api.together.xyz/v1',
    kind: 'openai-compatible',
    hint: 'Open-weight inference (Llama, Qwen, Mixtral, …).',
  },
  {
    id: 'fireworks',
    label: 'Fireworks',
    base_url: 'https://api.fireworks.ai/inference/v1',
    kind: 'openai-compatible',
    hint: 'Open-weight inference with function-calling tuning.',
  },
  {
    id: 'mistral',
    label: 'Mistral',
    base_url: 'https://api.mistral.ai/v1',
    kind: 'openai-compatible',
    hint: 'Mistral Large, Codestral, Mixtral.',
  },
  {
    id: 'xai',
    label: 'xAI · Grok',
    base_url: 'https://api.x.ai/v1',
    kind: 'openai-compatible',
    hint: 'Grok-4 and successors via OpenAI-style API.',
  },
  {
    id: 'cerebras',
    label: 'Cerebras',
    base_url: 'https://api.cerebras.ai/v1',
    kind: 'openai-compatible',
    hint: 'Llama 3.1 / 3.3 served from wafer-scale chips.',
  },
  {
    id: 'nvidia-nim',
    label: 'NVIDIA NIM',
    base_url: 'https://integrate.api.nvidia.com/v1',
    kind: 'openai-compatible',
    hint: 'NIM-hosted Llama, Mixtral, Nemotron, Phi-3, etc.',
  },
  {
    id: 'zai',
    label: 'z.ai (Zhipu / GLM)',
    base_url: 'https://api.z.ai/api/paas/v4',
    kind: 'openai-compatible',
    hint: 'GLM-4, GLM-4.5, ChatGLM family.',
  },
  {
    id: 'zai-coding',
    label: 'z.ai · Coding Plan',
    base_url: 'https://api.z.ai/api/coding/paas/v4',
    kind: 'openai-compatible',
    hint: 'Dedicated coding endpoint for the z.ai coding plan.',
  },
  {
    id: 'kimi',
    label: 'Moonshot · Kimi',
    base_url: 'https://api.moonshot.cn/v1',
    kind: 'openai-compatible',
    hint: 'Kimi long-context models (use api.moonshot.ai for the international plan).',
  },
  {
    id: 'minimax',
    label: 'MiniMax',
    base_url: 'https://api.minimaxi.com/v1',
    kind: 'openai-compatible',
    hint: 'MiniMax abab / m1 family. Use api.minimax.chat for the China plan.',
  },
  {
    id: 'qwen',
    label: 'Alibaba · Qwen',
    base_url: 'https://dashscope.aliyuncs.com/compatible-mode/v1',
    kind: 'openai-compatible',
    hint: 'Qwen 2 / 2.5 / 3 via DashScope compatibility shim.',
  },
  {
    id: 'siliconflow',
    label: 'SiliconFlow',
    base_url: 'https://api.siliconflow.com/v1',
    kind: 'openai-compatible',
    hint: 'Aggregator: DeepSeek, Qwen, GLM, Llama, FLUX, …',
  },
  {
    id: 'ollama-local',
    label: 'Ollama (local)',
    base_url: 'http://localhost:11434/v1',
    kind: 'openai-compatible',
    hint: 'Local Ollama daemon. Any pulled model is available.',
  },
  {
    id: 'vllm-local',
    label: 'vLLM (local)',
    base_url: 'http://localhost:8000/v1',
    kind: 'openai-compatible',
    hint: 'Local vLLM server (default port).',
  },
  {
    id: 'lmstudio-local',
    label: 'LM Studio (local)',
    base_url: 'http://localhost:1234/v1',
    kind: 'openai-compatible',
    hint: 'Local LM Studio inference server.',
  },

  // ---- Anthropic-compatible --------------------------------------------
  {
    id: 'zai-anthropic',
    label: 'z.ai · Anthropic mode',
    base_url: 'https://api.z.ai/api/anthropic',
    kind: 'anthropic-compatible',
    hint: 'GLM models accessible via Anthropic-style /messages.',
  },
  {
    id: 'openrouter-anthropic',
    label: 'OpenRouter · Anthropic',
    base_url: 'https://openrouter.ai/api/v1',
    kind: 'anthropic-compatible',
    hint: 'OpenRouter accepts Anthropic-style requests on Claude routes.',
  },
  {
    id: 'kimi-anthropic',
    label: 'Moonshot · Kimi (Anthropic mode)',
    base_url: 'https://api.moonshot.ai/anthropic',
    kind: 'anthropic-compatible',
    hint: 'Kimi /messages-shaped endpoint for Anthropic SDK clients.',
  },
];

export function endpointsForKind(kind: string): EndpointPreset[] {
  return POPULAR_ENDPOINTS.filter((e) => e.kind === kind);
}
