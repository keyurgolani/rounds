// Conformance rule for the transformation program (ROUNDS-01-L03 S2,
// DR-0003): S1's checks on the program files (scripts/program/lib.mjs) and
// the leaf DAG's (scripts/program/dag.mjs): the issue export's checksum,
// node ids against leaf-ids.json, every edge's reason and target, cycles,
// and decision-record references. generate() rebuilds leaf-dag.json from
// the export and docs/program/leaf-program.json, so a hand edit or a stale
// DAG fails as CONFORMANCE_DRIFT.

import { createContext } from '../lib/context.mjs';
import { checkProgram } from '../../program/lib.mjs';
import { DAG_PATH, EXPORT_PATH, GATE_PATH, checkDag, findCycles, generateDag, renderDag, stageGraph } from '../../program/dag.mjs';

export const id = 'program';
export const owningLeaf = 'ROUNDS-01-L03';
export const description = 'Transformation program files and the leaf DAG: schemas, producers, export checksum, ids, edges, cycles, and decision references';

export function check(repoRoot, ctx = createContext(repoRoot)) {
  return [...checkProgram(ctx), ...checkDag(ctx)];
}

export function generate(repoRoot, ctx = createContext(repoRoot)) {
  const built = generateDag(ctx);
  return built ? [{ path: DAG_PATH, content: renderDag(built.dag) }] : [];
}

export function summary(repoRoot, ctx = createContext(repoRoot)) {
  const lines = [];
  try {
    const dag = ctx.readJson(DAG_PATH);
    const staged = dag.nodes.filter((n) => n.stages?.length);
    const edges = dag.nodes.reduce((sum, n) => sum + n.filedPrerequisites.length, 0);
    const vertices = staged.reduce((sum, n) => sum + n.stages.length, 0) + dag.nodes.length - staged.length;
    lines.push(`${DAG_PATH}: ${dag.nodes.length} leaves, ${staged.length} staged (${vertices} stage nodes), ${edges} edges, ${findCycles(stageGraph(dag)).length} cycles, ${dag.dropped.length} dropped ids, edge set ${dag.edgeSet}, ${dag.decision}`);
    lines.push(`${EXPORT_PATH}: exported ${dag.source.exportedOn}, sha256 ${dag.source.exportSha256.slice(0, 12)}...`);
  } catch {
    lines.push(`${DAG_PATH}: unreadable`);
  }
  try {
    lines.push(`${GATE_PATH}: mode ${ctx.readJson(GATE_PATH).mode}`);
  } catch {
    lines.push(`${GATE_PATH}: unreadable`);
  }
  return lines;
}
