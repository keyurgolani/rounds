// Request shapes for the six execution routes (ROUNDS-00A-L02).
//
// ROUNDS_GATE_EXECUTION_DEFINITIONS decides them, and the runner and
// the SPA read the same value: runtime-config.js publishes it from the
// frontend container's environment. At `enforce` a request names one
// compiled definition, {track, slug, variant, version}, and sends only
// the candidate's code, files, and inputs. Otherwise it sends #1's
// shapes, which the runner takes at `legacy`. A tab left open across a
// switch gets the runner's typed denial and keeps its draft.

import { gateValue } from './gates';
import { isRunnerError } from './runnerFetch';

export type DefinitionTrack = 'coding' | 'ai-coding' | 'take-home';

export interface DefinitionRef {
  track: DefinitionTrack;
  slug: string;
  variant: string;
  version: number;
}

/** True when the runner takes only definition requests. */
export function definitionsEnforced(): boolean {
  return gateValue('EXECUTION_DEFINITIONS') === 'enforce';
}

/** The version a presentation row records (the definitions expand
 *  migration). A row without one names version 1, and the runner
 *  answers whether that version exists. */
export function definitionVersion(recorded: number | null | undefined): number {
  return typeof recorded === 'number' && Number.isInteger(recorded) && recorded >= 1 ? recorded : 1;
}

export function definitionRef(
  track: DefinitionTrack,
  slug: string,
  variant: string,
  recorded: number | null | undefined,
): DefinitionRef {
  return { track, slug, variant, version: definitionVersion(recorded) };
}

/** The compiled case id for a test case's position, as
 *  backend/definitions/build.py names them, unless the row recorded its
 *  own list. */
export function caseIdFor(index: number, recorded?: readonly string[] | null): string {
  const id = recorded?.[index];
  return typeof id === 'string' && id ? id : `c${String(index).padStart(3, '0')}`;
}

/** Sends with the row's version. A 409 definition_superseded rereads the
 *  row and, when it now names another version, sends once more with
 *  that one. Any other answer, or a second refusal, goes to the caller,
 *  which shows it as a denial. */
export async function retrySuperseded<T>(
  version: number | null | undefined,
  send: (version: number | null | undefined) => Promise<T>,
  reread: () => Promise<number | null | undefined>,
): Promise<T> {
  try {
    return await send(version);
  } catch (err) {
    if (!isRunnerError(err) || err.code !== 'definition_superseded') throw err;
    let next: number | null | undefined;
    try {
      next = await reread();
    } catch {
      throw err;
    }
    if (definitionVersion(next) === definitionVersion(version)) throw err;
    return send(next);
  }
}

/** Reloads the page. Its own function so tests can stand in for it. */
export function reloadPage(): void {
  window.location.reload();
}
