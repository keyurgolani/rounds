export type TypeName =
  | 'int' | 'float' | 'string' | 'bool'
  | 'int[]' | 'string[]' | 'int[][]'
  | 'node' | 'any';

export interface ParamSpec {
  name: string;
  type: TypeName;
  hint?: string;
}

export interface NodeTemplate {
  name: string;
  fields: { name: string; type: TypeName }[];
  links: {
    name: string;
    arity: 'single' | 'list';
    nullable?: boolean;
    edge_fields?: { name: string; type: TypeName }[];
  }[];
}

export type Entry =
  | { kind: 'function'; name: string; params: ParamSpec[]; returns: TypeName }
  | {
      kind: 'class_ops';
      class: string;
      constructor?: { params: ParamSpec[] };
      methods?: { name: string; params: ParamSpec[]; returns: TypeName }[];
    }
  | {
      kind: 'linked_list' | 'tree' | 'graph';
      name: string;
      params: ParamSpec[];
      returns: TypeName;
      node_template?: NodeTemplate;
      input_shape?: string;
    }
  | { kind: 'in_place_mutation'; name: string; mutates: string; params: ParamSpec[] }
  | { kind: 'custom'; drivers: Record<string, string> };

export interface TestCase {
  input: Record<string, unknown> | unknown[];
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
