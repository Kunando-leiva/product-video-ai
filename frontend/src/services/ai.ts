import { api } from "./api";

export interface AIProviderInfo {
  name: string;
  enabled: boolean;
  available: boolean;
  requires_internet: boolean;
  model: string | null;
  note: string | null;
}

export interface AIProvidersResponse {
  providers: AIProviderInfo[];
  active: string;
}

export interface AITextResponse {
  text: string;
  provider: string;
  model: string;
  tokens_in: number;
  tokens_out: number;
}

export interface AIScriptSection {
  text: string;
  duration: number;
}

export interface AIScriptResponse {
  hook: string;
  sections: AIScriptSection[];
  cta: string;
  provider: string;
  model: string;
}

export interface AIUsageRow {
  id: number;
  provider: string;
  task: string;
  status: string;
  tokens: number;
  cost_estimate: number;
  detail: string | null;
  created_at: string;
}

export const aiApi = {
  providers: () => api.get<AIProvidersResponse>("/ai/providers"),

  testText: (
    prompt: string,
    opts: {
      system?: string;
      json_schema?: Record<string, unknown>;
      provider?: string;
    } = {}
  ) =>
    api.post<AITextResponse>("/ai/test/text", { prompt, ...opts }),

  testScript: (
    productName: string,
    productDescription: string,
    duration: number,
    provider?: string
  ) =>
    api.post<AIScriptResponse>("/ai/test/script", {
      product_name: productName,
      product_description: productDescription,
      duration,
      provider,
    }),

  usage: (limit = 30) =>
    api.get<{ rows: AIUsageRow[] }>(`/ai/usage?limit=${limit}`),
};