export interface TestCase {
  input: Record<string, unknown>;
  expected: unknown;
  description?: string;
  tags?: string[];
}

export interface CodeRunResult {
  stdout: string;
  stderr: string;
  return_value: unknown;
  error: string | null;
  duration_ms: number;
  truncated: boolean;
}

export interface EvaluateCaseResult {
  index: number;
  passed: boolean;
  description: string;
  tags: string[];
  output: unknown;
  expected: unknown;
  error: string | null;
  duration_ms: number;
}

export interface CodeEvaluateResult {
  passed: number;
  failed: number;
  results: EvaluateCaseResult[];
}

export interface EvaluateFilter {
  tags?: string[];
  indices?: number[];
}
