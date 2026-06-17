import { useCallback, useEffect, useMemo, useState } from 'react';
import { useCampaign } from '../../campaign/CampaignContext';
import { effectiveStatus, useStatusMapVersion } from '../../hooks/usePracticeStatus';
import { listApplications, listRounds, getOffer } from '../../applications/api';
import {
  listCodingQuestions, listSystemDesignQuestions, listBehavioralQuestions, listBehavioralCategories,
} from '../../content/api';
import { listRounds as listAiRounds } from '../../pages/ai-coding/aiCodingApi';
import { listAssignments } from '../../pages/take-home/takeHomeApi';
import { listAnecdotes, listJobs, listProjects, listBullets } from '../../experience/experienceApi';
import { listAllConnections, buildReverseMap } from '../../experience/connectionApi';
import { listResumes, listVariants } from '../../features/resume/api';
import { listTodos } from '../../todos/api';
import {
  readinessTracks, pickNextReps, pickNextInterview, upcomingRounds,
  behavioralDepth, resumeCoverage, experienceOverview, computeAtRisk,
  type ReadinessLists, type StatusItem, type DashApp, type DashRound, type DashOffer, type DashTodo,
} from './derive';

type ListItem = { id: string; title?: string; difficulty?: string };
const toStatusItems = (rows: ListItem[]): StatusItem[] =>
  rows.map((r) => ({ id: r.id, title: r.title ?? '(untitled)', difficulty: r.difficulty }));

export function useDashboardData() {
  const { currentId } = useCampaign();
  const statusVersion = useStatusMapVersion();

  const [loading, setLoading] = useState(true);
  const [apps, setApps] = useState<DashApp[]>([]);
  const [rounds, setRounds] = useState<DashRound[]>([]);
  const [offers, setOffers] = useState<DashOffer[]>([]);
  const [todos, setTodos] = useState<DashTodo[]>([]);
  const [lists, setLists] = useState<ReadinessLists>({ coding: [], system: [], behavioral: [], 'ai-coding': [], 'take-home': [] });
  const [behQuestions, setBehQuestions] = useState<{ id: string }[]>([]);
  const [behCategories, setBehCategories] = useState<{ id: string; name: string; color?: string }[]>([]);
  const [anecdotes, setAnecdotes] = useState<{ created_at?: string; linked_question_ids: string[]; category_ids: string[] }[]>([]);
  const [jobs, setJobs] = useState<{ created_at?: string }[]>([]);
  const [projects, setProjects] = useState<{ created_at?: string }[]>([]);
  const [bullets, setBullets] = useState<{ id: string; created_at?: string }[]>([]);
  const [connections, setConnections] = useState<Awaited<ReturnType<typeof listAllConnections>>>([]);
  const [resumes, setResumes] = useState<{ updated_at?: string }[]>([]);
  const [variants, setVariants] = useState<{ application_id?: string }[]>([]);

  const load = useCallback(async () => {
    setLoading(true);
    const cid = currentId ?? undefined;
    try {
      const appList = await listApplications(cid).catch(() => [] as DashApp[]);
      setApps(appList);
      const [roundLists, offerList] = await Promise.all([
        Promise.all(appList.map((a) => listRounds(a.id).catch(() => [] as DashRound[]))),
        Promise.all(appList.map((a) => getOffer(a.id).catch(() => null))),
      ]);
      setRounds(roundLists.flat());
      setOffers(offerList.filter((o): o is NonNullable<typeof o> => !!o) as DashOffer[]);

      const [coding, system, behavioral, behCats, aiRounds, assignments, anec, jb, pj, bl, conns, res, vars, td] = await Promise.all([
        listCodingQuestions<ListItem>().catch(() => []),
        listSystemDesignQuestions<ListItem>().catch(() => []),
        listBehavioralQuestions<ListItem>().catch(() => []),
        listBehavioralCategories<{ id: string; name: string; color?: string }>().catch(() => []),
        listAiRounds().catch(() => []),
        listAssignments().catch(() => []),
        listAnecdotes().catch(() => []),
        listJobs().catch(() => []),
        listProjects().catch(() => []),
        listBullets().catch(() => []),
        listAllConnections().catch(() => []),
        listResumes().catch(() => []),
        listVariants().catch(() => []),
        listTodos(cid).catch(() => [] as DashTodo[]),
      ]);
      setLists({
        coding: toStatusItems(coding),
        system: toStatusItems(system),
        behavioral: toStatusItems(behavioral),
        'ai-coding': toStatusItems(aiRounds as ListItem[]),
        'take-home': toStatusItems(assignments as ListItem[]),
      });
      setBehQuestions(behavioral.map((q) => ({ id: q.id })));
      setBehCategories(behCats);
      setAnecdotes(anec);
      setJobs(jb);
      setProjects(pj);
      setBullets(bl);
      setConnections(conns);
      setResumes(res);
      setVariants(vars);
      setTodos(td);
    } finally {
      setLoading(false);
    }
  }, [currentId]);

  useEffect(() => {
    void load();
    const refresh = () => void load();
    for (const ev of ['rounds:applications-changed', 'rounds:interviews-changed', 'rounds:campaigns-changed', 'rounds:todos-changed']) {
      window.addEventListener(ev, refresh);
    }
    return () => {
      for (const ev of ['rounds:applications-changed', 'rounds:interviews-changed', 'rounds:campaigns-changed', 'rounds:todos-changed']) {
        window.removeEventListener(ev, refresh);
      }
    };
  }, [load]);

  const reverseMap = useMemo(() => buildReverseMap(connections), [connections]);

  const model = useMemo(() => {
    void statusVersion; // recompute when practice status changes
    const now = Date.now();
    const nextInterview = pickNextInterview(rounds, now);
    const statusCounts: Record<string, number> = {};
    for (const a of apps) statusCounts[a.status] = (statusCounts[a.status] ?? 0) + 1;
    return {
      today: {
        nextInterview,
        nextInterviewApp: nextInterview ? apps.find((a) => a.id === nextInterview.application_id) ?? null : null,
        nextReps: pickNextReps(lists, (t, id) => effectiveStatus(t, id), 2),
        atRisk: computeAtRisk(todos, apps, rounds, offers),
      },
      readiness: readinessTracks(lists, (t, id) => effectiveStatus(t, id)),
      behavioral: behavioralDepth(behQuestions, behCategories, anecdotes),
      pipeline: { counts: statusCounts },
      upcoming: upcomingRounds(rounds, now).slice(0, 5),
      resume: resumeCoverage(resumes, variants, apps),
      experience: experienceOverview(jobs, projects, anecdotes, bullets, reverseMap, now),
      apps,
    };
  }, [apps, rounds, offers, todos, lists, behQuestions, behCategories, anecdotes, jobs, projects, bullets, reverseMap, resumes, variants, statusVersion]);

  return { loading, ...model };
}
