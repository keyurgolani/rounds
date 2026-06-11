import { listJobs, listProjects, listBullets } from '../../../experience/experienceApi';
import { listAllConnections, buildConnectionMap, type ConnectionMap } from '../../../experience/connectionApi';
import type { LibrarySnapshot } from './resolve';

export interface LibraryData extends LibrarySnapshot { connMap: ConnectionMap; }

export async function loadLibrarySnapshot(): Promise<LibraryData> {
  const [jobs, projects, bullets, connections] = await Promise.all([
    listJobs(), listProjects(), listBullets(), listAllConnections(),
  ]);
  const byId = <T extends { id: string }>(xs: T[]) => Object.fromEntries(xs.map((x) => [x.id, x]));
  return { jobs: byId(jobs), projects: byId(projects), bullets: byId(bullets), connMap: buildConnectionMap(connections) };
}
