// ATS scoring tab.
//
// Layout (top → bottom):
//   1. Anchor to a tracked application — collapsible card, default closed.
//      Holds the application picker AND the JD textarea.
//   2. Two score cards side-by-side: STATIC SCORE (rule) and AI SCORE.
//      Each card is independently expandable; the per-card breakdown
//      renders directly underneath the card it belongs to, so when both
//      are expanded the user sees a clean two-column breakdown layout.
//   3. AI Scoring toggle row.
//   4. Suggestions, then missing-JD-keyword chips.
//
// AI score card body adapts to the four AI states (`ok`, `off`,
// `unconfigured`, `error`); when AI isn't producing a number, the
// reason and the link to settings live inside the card itself rather
// than in a separate banner.

import { useEffect, useMemo, useRef, useState } from 'react';
import { Link } from 'react-router-dom';
import { ArrowUpRight, ChevronDown, Sparkles } from 'lucide-react';
import { listApplications } from '../../../../applications/api';
import { usePersistedState } from '../../../../hooks/usePersistedState';
import type { Resume, ResumeData } from '../../types';
import {
  getATSAIScore,
  getATSRuleScore,
  type ATSAIResponse,
  type ATSRuleResponse,
} from '../../ai/client';
import { useEnhancementContext } from '../EnhancementContext';

const DEBOUNCE_MS = 1500;

type Props = { data: ResumeData; resume?: Resume | null };

type AppRow = {
  id: string;
  company: string;
  role: string;
  status?: string;
  job_description?: string;
};

type AIStatus = ATSAIResponse['ai_status'];

// Multi-entry per-resume cache. Each entry pairs a content fingerprint
// with the result it produced and the wall clock at the time of the
// scoring call. We keep up to MAX_CACHE_ENTRIES recent fingerprints
// so things like "restore an older history snapshot" can hit a
// cached score for that snapshot's content. Entries past TTL_MS are
// treated as misses so an aging score is re-queried.
type CachedRuleEntry = {
  fingerprint: string;
  result: ATSRuleResponse;
  timestamp: number;
};
type CachedAIEntry = {
  fingerprint: string;
  result: ATSAIResponse;
  timestamp: number;
};

const TTL_MS = 90 * 24 * 60 * 60 * 1000; // 90 days
const MAX_CACHE_ENTRIES = 10;

// Stable "AI Scoring is off" object so the useEffect that mirrors
// `aiResult` into EnhancementContext doesn't get a fresh reference
// every render (which would re-fire the effect indefinitely).
const AI_OFF_RESULT: ATSAIResponse = {
  ai_score: null,
  ai: null,
  ai_status: 'off',
  ai_suggestions: [],
};

// Stable JSON serialization (sorted object keys) so two semantically
// identical inputs produce the same fingerprint regardless of key
// insertion order.
function stableStringify(value: unknown): string {
  if (value === null || typeof value !== 'object') return JSON.stringify(value);
  if (Array.isArray(value)) {
    return '[' + value.map(stableStringify).join(',') + ']';
  }
  const obj = value as Record<string, unknown>;
  const keys = Object.keys(obj).sort();
  return (
    '{' +
    keys
      .map((k) => JSON.stringify(k) + ':' + stableStringify(obj[k]))
      .join(',') +
    '}'
  );
}

// djb2-style 32-bit hash → base36. Cheap, collision-resistant enough
// for content fingerprinting within a single user's resume cache.
function hashString(s: string): string {
  let h = 5381;
  for (let i = 0; i < s.length; i++) h = ((h << 5) + h) ^ s.charCodeAt(i);
  return (h >>> 0).toString(36);
}

function fingerprint(...inputs: unknown[]): string {
  return hashString(stableStringify(inputs));
}

// Return the cached entry matching fp if it exists AND is within TTL;
// otherwise null (forcing a re-query).
function findFresh<T extends { fingerprint: string; timestamp: number }>(
  cache: T[],
  fp: string,
): T | null {
  const now = Date.now();
  for (const entry of cache) {
    if (entry.fingerprint === fp && now - entry.timestamp < TTL_MS) {
      return entry;
    }
  }
  return null;
}

// Insert/replace an entry at the front, drop duplicates of the same
// fingerprint, and cap the array to MAX_CACHE_ENTRIES so localStorage
// doesn't grow unboundedly.
function upsert<T extends { fingerprint: string; timestamp: number }>(
  cache: T[],
  entry: T,
): T[] {
  const filtered = cache.filter((e) => e.fingerprint !== entry.fingerprint);
  return [entry, ...filtered].slice(0, MAX_CACHE_ENTRIES);
}

export default function ATSTab({ data, resume }: Props) {
  const persistKey = `rounds.resume.ats.${resume?.id ?? 'untitled'}`;
  const [jd, setJd] = usePersistedState<string>(`${persistKey}.jd`, '');
  const [appId, setAppId] = usePersistedState<string | null>(
    `${persistKey}.appId`,
    null,
  );
  const [useAI, setUseAI] = usePersistedState<boolean>(
    `${persistKey}.useAI`,
    true,
  );
  const [anchorOpen, setAnchorOpen] = usePersistedState<boolean>(
    `${persistKey}.anchorOpen`,
    false,
  );
  const [ruleExpanded, setRuleExpanded] = usePersistedState<boolean>(
    `${persistKey}.ruleExpanded`,
    false,
  );
  const [aiExpanded, setAiExpanded] = usePersistedState<boolean>(
    `${persistKey}.aiExpanded`,
    false,
  );

  const [apps, setApps] = useState<AppRow[]>([]);
  const [appsLoading, setAppsLoading] = useState(true);

  // The ATS results are content-cached: each successful call writes
  // an entry to a small per-resume LRU keyed by the input
  // fingerprint. Cache hits short-circuit the network call entirely.
  //
  // - Rule fingerprint: (data, jd). Always cached on success.
  // - AI fingerprint:   (data, jd) — explicitly NOT including useAI,
  //   so toggling AI Scoring off and back on reuses the previous AI
  //   score for the same content.
  // - History restore changes `data` to a prior snapshot. If we
  //   scored that snapshot before (and it's still in the LRU and
  //   within TTL), restore picks the score back up automatically.
  // - Errors / `unconfigured` aren't cached — they live in
  //   `transientAI` until the next run, so transient failures
  //   self-heal on retry.
  const [ruleCache, setRuleCache] = usePersistedState<CachedRuleEntry[]>(
    `${persistKey}.cache.rule.v2`,
    [],
  );
  const [aiCache, setAiCache] = usePersistedState<CachedAIEntry[]>(
    `${persistKey}.cache.ai.v2`,
    [],
  );
  const [transientAI, setTransientAI] = useState<ATSAIResponse | null>(null);
  const ruleFp = useMemo(() => fingerprint('rule', data, jd), [data, jd]);
  const aiFp = useMemo(() => fingerprint('ai', data, jd), [data, jd]);
  const ruleHit = useMemo(
    () => findFresh(ruleCache, ruleFp),
    [ruleCache, ruleFp],
  );
  const aiHit = useMemo(() => findFresh(aiCache, aiFp), [aiCache, aiFp]);
  const ruleResult: ATSRuleResponse | null = ruleHit?.result ?? null;
  // Display rules for the AI card:
  //   useAI off  → synthesise an "off" overlay regardless of cache;
  //                the cache stays intact so toggle-on restores it.
  //   useAI on   → transient (in-flight error/unconfigured) wins,
  //                else the cached result, else null (loading state).
  const aiResult: ATSAIResponse | null = useAI
    ? (transientAI ?? aiHit?.result ?? null)
    : AI_OFF_RESULT;
  const enhancement = useEnhancementContext();

  // Resume content (or JD) changed — drop any stale AI signals from
  // the studio-wide EnhancementContext until a fresh AI result for
  // the new fingerprint lands. Otherwise per-field improve calls
  // would carry forward signals that don't describe the current
  // resume anymore.
  useEffect(() => {
    enhancement.setATS(null);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [aiFp]);

  // Mirror the latest AI scoring snapshot into the studio-wide
  // EnhancementContext so other editors' improve calls can carry
  // the AI-side ATS feedback into their prompts.
  useEffect(() => {
    if (!aiResult || aiResult.ai_status !== 'ok') return;
    enhancement.setATS({
      ai_suggestions: aiResult.ai_suggestions,
      ai_signals: aiResult.ai ?? undefined,
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [aiResult]);
  const [ruleScoring, setRuleScoring] = useState(false);
  const [aiScoring, setAiScoring] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null);
  // Each scoring run is tagged with a token so a slow inflight call
  // that finishes after a fresher one can't clobber the newer state.
  const runTokenRef = useRef(0);

  useEffect(() => {
    setAppsLoading(true);
    listApplications()
      .then(setApps)
      .catch(() => setApps([]))
      .finally(() => setAppsLoading(false));
  }, []);

  const selectedApp = useMemo(
    () => apps.find((a) => a.id === appId) ?? null,
    [apps, appId],
  );

  useEffect(() => {
    if (timer.current) clearTimeout(timer.current);
    timer.current = setTimeout(() => {
      void run();
    }, DEBOUNCE_MS);
    return () => {
      if (timer.current) clearTimeout(timer.current);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [data, jd, useAI]);

  async function run() {
    const myToken = ++runTokenRef.current;
    setError(null);

    // Cache hit on the rule side means no scoring spinner at all —
    // the result is already showing from the derived `ruleResult`.
    setRuleScoring(!ruleHit);
    // AI side: spinner only if AI is on AND we don't have a fresh
    // cache hit for this content. Toggle-on against an existing
    // cache shows the score immediately without spinning.
    setAiScoring(useAI && !aiHit);

    // Clear any transient AI state from a previous failed attempt;
    // a fresh run replaces it (success → cache, failure → transient).
    if (useAI) setTransientAI(null);

    // Rule scoring — fire only on cache miss.
    void (async () => {
      if (ruleHit) return;
      try {
        const r = await getATSRuleScore(data, jd || undefined);
        if (myToken !== runTokenRef.current) return;
        setRuleCache((prev) =>
          upsert(prev, {
            fingerprint: ruleFp,
            result: r,
            timestamp: Date.now(),
          }),
        );
      } catch (err) {
        if (myToken === runTokenRef.current) {
          setError((err as Error).message);
        }
      } finally {
        if (myToken === runTokenRef.current) setRuleScoring(false);
      }
    })();

    // AI scoring — fire only when AI is on AND cache miss.
    void (async () => {
      if (!useAI || aiHit) return;
      try {
        const r = await getATSAIScore(data, jd || undefined, true);
        if (myToken !== runTokenRef.current) return;
        // Only `ok` results are sticky. Other statuses are surfaced
        // via transientAI so the next run retries automatically.
        if (r.ai_status === 'ok') {
          setAiCache((prev) =>
            upsert(prev, {
              fingerprint: aiFp,
              result: r,
              timestamp: Date.now(),
            }),
          );
          setTransientAI(null);
        } else {
          setTransientAI(r);
        }
      } catch (err) {
        if (myToken !== runTokenRef.current) return;
        setTransientAI({
          ai_score: null,
          ai: null,
          ai_status: 'error',
          ai_error: (err as Error).message,
          ai_error_kind: 'unknown',
          ai_suggestions: [],
        });
      } finally {
        if (myToken === runTokenRef.current) setAiScoring(false);
      }
    })();
  }

  function pickApp(id: string | null) {
    setAppId(id);
    if (!id) return;
    const target = apps.find((a) => a.id === id);
    if (target?.job_description) setJd(target.job_description);
  }

  const ruleScore = ruleResult?.rule_score ?? null;
  const aiScore = aiResult?.ai_score ?? null;
  const aiStatus: AIStatus | null = aiResult?.ai_status ?? null;
  const aiOk = aiStatus === 'ok' && Boolean(aiResult?.ai);

  const ruleHasBreakdown = ruleResult !== null;
  const ruleEffective = ruleExpanded && ruleHasBreakdown;
  const aiEffective = aiExpanded && aiOk;

  // Merge rule + AI suggestions. Rule suggestions show as soon as the
  // rule pass returns; AI suggestions append once the AI pass settles.
  const suggestions = useMemo(() => {
    const out: string[] = [];
    if (ruleResult) {
      for (const s of ruleResult.suggestions) {
        if (s && s.trim() && !out.includes(s)) out.push(s);
      }
    }
    if (aiResult) {
      for (const s of aiResult.ai_suggestions ?? []) {
        if (s && s.trim() && !out.includes(s)) out.push(s);
      }
    }
    return out.slice(0, 8);
  }, [ruleResult, aiResult]);

  return (
    <div className="flex flex-col gap-3">
      <SpinnerStyles />

      <AnchorCard
        open={anchorOpen}
        onToggle={() => setAnchorOpen(!anchorOpen)}
        apps={apps}
        appsLoading={appsLoading}
        appId={appId}
        onPickApp={pickApp}
        selectedApp={selectedApp}
        jd={jd}
        setJd={setJd}
      />

      <div
        className="flex items-center gap-2"
        style={{
          padding: '8px 12px',
          background: 'var(--bg-elev)',
          boxShadow: 'inset 0 0 0 1px var(--border)',
          borderRadius: 'var(--radius)',
          fontSize: 12,
        }}
      >
        <Sparkles size={12} strokeWidth={1.7} style={{ color: 'var(--accent)' }} />
        <span style={{ color: 'var(--text-2)', flex: 1 }}>AI Scoring</span>
        <Toggle checked={useAI} onChange={setUseAI} />
      </div>

      {error && (
        <div
          className="card"
          role="alert"
          style={{ padding: 10, fontSize: 11.5, color: 'var(--plum)' }}
        >
          {error}
        </div>
      )}

      <div
        className="grid gap-3"
        style={{ gridTemplateColumns: '1fr 1fr', alignItems: 'start' }}
      >
        <div className="flex flex-col gap-2">
          <ScoreCard
            title="STATIC SCORE"
            score={ruleScore}
            tone="var(--text)"
            loading={ruleScoring}
            expanded={ruleEffective}
            canExpand={ruleHasBreakdown}
            onToggleExpand={() => setRuleExpanded(!ruleExpanded)}
          />
          {ruleEffective && ruleResult && (
            <BreakdownCard>
              {Object.entries(ruleResult.breakdown).map(([k, v]) => (
                <BreakdownRow
                  key={k}
                  label={k.replace(/_/g, ' ')}
                  value={v}
                  max={maxFor(k)}
                />
              ))}
            </BreakdownCard>
          )}
        </div>

        <div className="flex flex-col gap-2">
          <ScoreCard
            title="AI SCORE"
            score={aiScore}
            tone="var(--accent)"
            loading={aiScoring}
            expanded={aiEffective}
            canExpand={aiOk}
            onToggleExpand={() => setAiExpanded(!aiExpanded)}
            altBody={
              aiResult && !aiOk ? (
                <AINotice
                  status={aiStatus ?? (useAI ? 'unconfigured' : 'off')}
                  error={aiResult.ai_error ?? null}
                  errorKind={aiResult.ai_error_kind ?? null}
                />
              ) : null
            }
          />
          {aiEffective && aiResult?.ai && (
            <BreakdownCard>
              {(['impact', 'action_verbs', 'clarity', 'semantic'] as const).map((k) => (
                <BreakdownRow
                  key={k}
                  label={k.replace(/_/g, ' ')}
                  value={(aiResult.ai?.[k] as number | undefined) ?? 0}
                  max={100}
                  accent
                />
              ))}
            </BreakdownCard>
          )}
        </div>
      </div>

      {suggestions.length > 0 && (
        <div className="card" style={{ padding: 12 }}>
          <div className="eyebrow mb-2" style={{ fontSize: 9.5 }}>
            Suggestions
          </div>
          <ul
            style={{
              margin: 0,
              paddingLeft: 18,
              fontSize: 12,
              lineHeight: 1.55,
              listStyleType: 'disc',
              listStylePosition: 'outside',
            }}
          >
            {suggestions.map((s, i) => (
              <li
                key={i}
                style={{ marginBottom: 4, paddingLeft: 2, color: 'var(--text-2)' }}
              >
                {s}
              </li>
            ))}
          </ul>
        </div>
      )}

      {ruleResult?.missing_keywords.length ? (
        <div className="card" style={{ padding: 12 }}>
          <div className="eyebrow mb-2" style={{ fontSize: 9.5 }}>
            Missing JD keywords
          </div>
          <div className="flex flex-wrap gap-1.5">
            {ruleResult.missing_keywords.map((k) => (
              <span
                key={k}
                className="mono"
                style={{
                  padding: '3px 8px',
                  borderRadius: 999,
                  fontSize: 10.5,
                  background: 'var(--bg-elev)',
                  boxShadow: 'inset 0 0 0 1px var(--border-strong)',
                  color: 'var(--text-2)',
                }}
              >
                {k}
              </span>
            ))}
          </div>
        </div>
      ) : null}
    </div>
  );
}

// ---------------------------------------------------------------------------
//                              Anchor card
// ---------------------------------------------------------------------------

function AnchorCard({
  open,
  onToggle,
  apps,
  appsLoading,
  appId,
  onPickApp,
  selectedApp,
  jd,
  setJd,
}: {
  open: boolean;
  onToggle: () => void;
  apps: AppRow[];
  appsLoading: boolean;
  appId: string | null;
  onPickApp: (id: string | null) => void;
  selectedApp: AppRow | null;
  jd: string;
  setJd: (v: string) => void;
}) {
  const summary = (() => {
    const parts: string[] = [];
    if (selectedApp) parts.push(`${selectedApp.company} · ${selectedApp.role}`);
    if (jd.trim()) {
      const words = jd.trim().split(/\s+/).filter(Boolean).length;
      parts.push(`JD ${words} word${words === 1 ? '' : 's'}`);
    }
    return parts.length === 0 ? 'No anchor set' : parts.join(' · ');
  })();

  return (
    <div className="card" style={{ padding: 0, overflow: 'hidden' }}>
      <div
        role="button"
        tabIndex={0}
        aria-expanded={open}
        onClick={onToggle}
        onKeyDown={(e) => {
          if (e.key === 'Enter' || e.key === ' ') {
            e.preventDefault();
            onToggle();
          }
        }}
        style={{
          padding: '10px 14px',
          display: 'flex',
          alignItems: 'center',
          gap: 10,
          cursor: 'pointer',
        }}
      >
        <div style={{ flex: 1, minWidth: 0 }}>
          <div className="eyebrow" style={{ fontSize: 9.5, marginBottom: 2 }}>
            Anchor to a tracked application
          </div>
          <div
            style={{
              fontSize: 12,
              color: 'var(--text-3)',
              whiteSpace: 'nowrap',
              overflow: 'hidden',
              textOverflow: 'ellipsis',
            }}
          >
            {summary}
          </div>
        </div>
        <ChevronDown
          size={14}
          strokeWidth={1.6}
          style={{
            color: 'var(--text-3)',
            flexShrink: 0,
            transform: open ? 'rotate(180deg)' : 'rotate(0deg)',
            transition: 'transform 200ms',
          }}
        />
      </div>
      {open && (
        <div
          style={{
            padding: '12px 14px 14px',
            borderTop: '1px solid var(--border)',
            display: 'flex',
            flexDirection: 'column',
            gap: 10,
          }}
        >
          <Field label="Application">
            <select
              value={appId ?? ''}
              onChange={(e) => onPickApp(e.target.value || null)}
              aria-label="Application"
              style={selectStyle}
            >
              <option value="">{appsLoading ? 'Loading…' : '— No application —'}</option>
              {apps.map((a) => (
                <option key={a.id} value={a.id}>
                  {a.company} — {a.role}
                </option>
              ))}
            </select>
            {selectedApp && (
              <span
                style={{
                  marginTop: 6,
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: 6,
                  fontSize: 11,
                  color: 'var(--text-3)',
                  flexWrap: 'wrap',
                }}
              >
                <span
                  className="pill"
                  style={{
                    background: 'var(--bg-elev)',
                    color: 'var(--accent)',
                    boxShadow: 'inset 0 0 0 1px var(--accent)',
                    fontSize: 10,
                    padding: '2px 8px',
                  }}
                >
                  {selectedApp.company} · {selectedApp.role}
                </span>
                {selectedApp.job_description ? (
                  <span>JD pulled — edit below before scoring.</span>
                ) : (
                  <span style={{ color: 'var(--ochre)' }}>
                    This application has no JD yet — paste one below.
                  </span>
                )}
              </span>
            )}
          </Field>

          <Field label="Target JD">
            <textarea
              value={jd}
              onChange={(e) => setJd(e.target.value)}
              placeholder="Paste a job description to enable keyword-gap analysis."
              rows={4}
              style={{
                ...selectStyle,
                fontFamily: 'inherit',
                lineHeight: 1.45,
                resize: 'vertical',
              }}
            />
          </Field>
        </div>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
//                              Score card
// ---------------------------------------------------------------------------

function ScoreCard({
  title,
  score,
  tone,
  loading,
  expanded,
  canExpand,
  onToggleExpand,
  altBody,
}: {
  title: string;
  score: number | null;
  tone: string;
  loading: boolean;
  expanded: boolean;
  canExpand: boolean;
  onToggleExpand: () => void;
  altBody?: React.ReactNode | null;
}) {
  const interactive = canExpand;
  const showAlt = altBody !== null && altBody !== undefined;
  return (
    <div
      role={interactive ? 'button' : undefined}
      tabIndex={interactive ? 0 : undefined}
      aria-expanded={interactive ? expanded : undefined}
      onClick={interactive ? onToggleExpand : undefined}
      onKeyDown={
        interactive
          ? (e) => {
              if (e.key === 'Enter' || e.key === ' ') {
                e.preventDefault();
                onToggleExpand();
              }
            }
          : undefined
      }
      className="card"
      data-scoring-glow={loading ? 'true' : undefined}
      style={{
        padding: '14px 14px',
        display: 'flex',
        flexDirection: 'column',
        gap: 6,
        cursor: interactive ? 'pointer' : 'default',
      }}
    >
      <div className="flex items-center justify-between">
        <span
          className="eyebrow"
          style={{ fontSize: 9.5, color: 'var(--text-3)', letterSpacing: '0.1em' }}
        >
          {title}
        </span>
        {interactive && (
          <ChevronDown
            size={14}
            strokeWidth={1.6}
            style={{
              color: 'var(--text-3)',
              transform: expanded ? 'rotate(180deg)' : 'rotate(0deg)',
              transition: 'transform 200ms',
            }}
          />
        )}
      </div>
      {showAlt ? (
        altBody
      ) : (
        <div className="flex items-baseline gap-2" style={{ marginTop: 2 }}>
          <span
            className="display"
            style={{
              fontSize: 30,
              fontWeight: 500,
              color: tone,
              lineHeight: 1,
              opacity: loading ? 0.55 : 1,
            }}
          >
            {score !== null ? score : '—'}
          </span>
          {score !== null ? (
            <span className="mono" style={{ fontSize: 10.5, color: 'var(--text-4)' }}>
              / 100
            </span>
          ) : loading ? (
            <span
              className="mono"
              style={{ fontSize: 10.5, color: 'var(--text-3)', letterSpacing: '0.08em' }}
            >
              SCORING…
            </span>
          ) : null}
        </div>
      )}
    </div>
  );
}

function AINotice({
  status,
  error,
  errorKind,
}: {
  status: AIStatus;
  error: string | null;
  errorKind: ATSAIResponse['ai_error_kind'] | null;
}) {
  const showSettingsLink =
    status === 'unconfigured' ||
    (status === 'error' &&
      (errorKind === 'auth' ||
        errorKind === 'quota' ||
        errorKind === 'model_not_found' ||
        errorKind === 'unconfigured'));

  let headline: string;
  let detail: React.ReactNode;
  if (status === 'off') {
    headline = 'Off';
    detail = 'Enable AI Scoring above.';
  } else if (status === 'unconfigured') {
    headline = 'Not set up';
    detail = 'Connect a provider to enable AI grading.';
  } else if (status === 'error') {
    headline = 'Paused';
    detail = error ? (
      <span style={{ color: 'var(--ochre)' }}>{error}</span>
    ) : (
      'Provider error.'
    );
  } else {
    headline = '—';
    detail = null;
  }

  return (
    <div className="flex flex-col" style={{ gap: 4, marginTop: 2 }}>
      <span
        className="display"
        style={{
          fontSize: 22,
          fontWeight: 500,
          color: 'var(--text-3)',
          lineHeight: 1,
        }}
      >
        {headline}
      </span>
      <span
        style={{ fontSize: 11, color: 'var(--text-3)', lineHeight: 1.45 }}
      >
        {detail}
        {showSettingsLink && (
          <>
            {' '}
            <Link
              to="/settings"
              onClick={(e) => e.stopPropagation()}
              style={{ color: 'var(--accent)', textDecoration: 'none' }}
            >
              Open settings{' '}
              <ArrowUpRight
                size={10}
                strokeWidth={2}
                style={{ verticalAlign: '-1px' }}
              />
            </Link>
          </>
        )}
      </span>
    </div>
  );
}

function BreakdownCard({ children }: { children: React.ReactNode }) {
  return (
    <div className="card" style={{ padding: 12 }}>
      <div className="flex flex-col gap-1.5">{children}</div>
    </div>
  );
}

function Toggle({
  checked,
  onChange,
}: {
  checked: boolean;
  onChange: (v: boolean) => void;
}) {
  return (
    <button
      type="button"
      role="switch"
      aria-checked={checked}
      onClick={() => onChange(!checked)}
      style={{
        position: 'relative',
        width: 36,
        height: 20,
        borderRadius: 999,
        background: checked ? 'var(--accent)' : 'var(--border-strong)',
        border: 0,
        cursor: 'pointer',
        transition: 'background 160ms',
        flexShrink: 0,
      }}
    >
      <span
        style={{
          position: 'absolute',
          top: 2,
          left: checked ? 18 : 2,
          width: 16,
          height: 16,
          borderRadius: '50%',
          background: 'var(--bg-elev)',
          transition: 'left 160ms',
          boxShadow: '0 1px 2px rgba(0,0,0,0.2)',
        }}
      />
    </button>
  );
}

// ---------------------------------------------------------------------------
//                              Pieces
// ---------------------------------------------------------------------------

function BreakdownRow({
  label,
  value,
  max,
  accent,
}: {
  label: string;
  value: number;
  max: number;
  accent?: boolean;
}) {
  const pct = Math.max(0, Math.min(100, (value / max) * 100));
  return (
    <div className="flex items-center gap-2" style={{ fontSize: 12 }}>
      <span
        style={{
          flex: '0 0 auto',
          minWidth: 90,
          color: 'var(--text-3)',
          textTransform: 'capitalize',
        }}
      >
        {label}
      </span>
      <div
        style={{
          flex: 1,
          height: 6,
          background: 'var(--bg-sunken)',
          borderRadius: 3,
          overflow: 'hidden',
        }}
      >
        <div
          style={{
            width: `${pct}%`,
            height: '100%',
            background: accent ? 'var(--accent)' : 'var(--text)',
            transition: 'width 350ms ease-out',
          }}
        />
      </div>
      <span
        className="mono"
        style={{ width: 56, textAlign: 'right', color: 'var(--text-3)' }}
      >
        {Math.round(pct)}/100
      </span>
    </div>
  );
}

function Field({
  label,
  children,
}: {
  label: string;
  children: React.ReactNode;
}) {
  return (
    <label className="flex flex-col gap-1.5">
      <span className="eyebrow" style={{ fontSize: 9.5 }}>
        {label}
      </span>
      {children}
    </label>
  );
}

const selectStyle: React.CSSProperties = {
  padding: '8px 10px',
  background: 'var(--bg-elev)',
  boxShadow: 'inset 0 0 0 1px var(--border-strong)',
  borderRadius: 'var(--radius)',
  border: 0,
  fontSize: 12.5,
  color: 'var(--text)',
  outline: 'none',
  width: '100%',
};

function SpinnerStyles() {
  // Running glow + @property declaration now live in globals.css so
  // any component can opt in via `data-scoring-glow="true"`. Only
  // the local pulse keyframe remains here.
  return (
    <style>{`
      @keyframes rounds-pulse {
        0%, 100% { opacity: 1; }
        50% { opacity: 0.45; }
      }
    `}</style>
  );
}

function maxFor(key: string): number {
  switch (key) {
    case 'contact':
    case 'sections':
    case 'keywords':
    case 'formatting':
    case 'bullets':
    case 'action_verbs':
      return 15;
    case 'dates':
      return 10;
    default:
      return 15;
  }
}
