import { useEffect, useState, type RefObject } from 'react';
import type { GuideNavGroup } from '../../shared/GuideNav';
import type { TrackConfig } from '../../guideTypes';
import StudyShell from '../../shared/StudyShell';
import { Section, LaneCard } from '../../shared/primitives';
import { systemDesignContent } from '../../content/systemDesign';
import {
  DEFAULT_INPUTS,
  compute,
  formatBytes,
  formatPerSecond,
  formatRate,
  readStored,
  writeStored,
  type CapacityInputs,
} from './capacityMath';

type Props = {
  config: TrackConfig;
  navGroups: GuideNavGroup[];
  scrollRef: RefObject<HTMLDivElement>;
};

const INPUT_DEFS: { key: keyof CapacityInputs; label: string; hint: string; step: number }[] = [
  { key: 'dau',             label: 'Daily Active Users',  hint: 'DAU',                step: 100_000 },
  { key: 'actionsPerDay',   label: 'Actions / user / day', hint: 'ops/user/day',      step: 1 },
  { key: 'avgPayloadBytes', label: 'Avg payload (bytes)', hint: 'bytes per op',       step: 256 },
  { key: 'peakMultiplier',  label: 'Peak multiplier',     hint: 'peak / avg',         step: 1 },
];

export default function CapacityMath({ config, navGroups, scrollRef }: Props) {
  const { capacityMath } = systemDesignContent;
  const [inputs, setInputs] = useState<CapacityInputs>(() => readStored() ?? DEFAULT_INPUTS);
  useEffect(() => { writeStored(inputs); }, [inputs]);
  const outputs = compute(inputs);

  return (
    <StudyShell
      eyebrow={`${config.eyebrow} · Capacity Math`}
      title="Capacity Math Calculator"
      description="Plug in DAU, actions, payload, and peak multiplier to see avg QPS, peak QPS, storage/day, and bandwidth/sec."
      navGroups={navGroups}
      trackBasePath={config.guidePath}
      scrollRef={scrollRef}
    >
      <Section eyebrow="Formulas" title="The seven you actually use">
        <div className="grid" style={{ gap: 'var(--gap-sm)', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))' }}>
          {capacityMath.formulas.map((entry) => (
            <div key={entry.label} className="card" style={{ padding: 'var(--pad-sm)' }}>
              <div style={{ fontSize: 12.5, fontWeight: 500, color: 'var(--text-2)' }}>{entry.label}</div>
              <div className="mono" style={{ marginTop: 4, fontSize: 12, color: 'var(--accent)' }}>{entry.formula}</div>
            </div>
          ))}
        </div>
      </Section>

      <Section eyebrow="Calculator" title="Tune the inputs; the outputs follow">
        <div
          className="grid xl:grid-cols-[minmax(0,1fr)_minmax(0,1fr)]"
          style={{ gap: 'var(--gap-md)' }}
        >
          <div className="card" style={{ padding: 'var(--pad-md)' }}>
            <div className="eyebrow" style={{ marginBottom: 'var(--gap-sm)' }}>Inputs</div>
            <div className="grid" style={{ gap: 'var(--gap-sm)' }}>
              {INPUT_DEFS.map((def) => (
                <label key={def.key} className="grid" style={{ gap: 4 }}>
                  <span style={{ fontSize: 12.5, color: 'var(--text-2)' }}>{def.label}</span>
                  <input
                    type="number"
                    min={0}
                    step={def.step}
                    value={inputs[def.key]}
                    onChange={(event) => setInputs({ ...inputs, [def.key]: Number(event.target.value) })}
                    style={{
                      padding: '8px 12px',
                      borderRadius: 'var(--radius)',
                      border: 0,
                      background: 'var(--bg-sunken)',
                      boxShadow: 'inset 0 0 0 1px var(--border)',
                      color: 'var(--text)',
                      fontSize: 14,
                    }}
                  />
                  <span className="mono" style={{ fontSize: 10.5, color: 'var(--text-4)', letterSpacing: '0.1em' }}>{def.hint.toUpperCase()}</span>
                </label>
              ))}
            </div>
          </div>

          <div className="card" style={{ padding: 'var(--pad-md)' }}>
            <div className="eyebrow" style={{ marginBottom: 'var(--gap-sm)' }}>Outputs</div>
            <div className="grid" style={{ gap: 'var(--gap-sm)' }}>
              <OutputRow label="Avg QPS" value={formatRate(outputs.avgQps)} />
              <OutputRow label="Peak QPS" value={formatRate(outputs.peakQps)} />
              <OutputRow label="Storage / day" value={formatBytes(outputs.rawStoragePerDayBytes)} />
              <OutputRow label="Bandwidth" value={formatPerSecond(outputs.bandwidthBytesPerSecond)} />
            </div>
          </div>
        </div>
      </Section>

      <Section eyebrow="Interpretation" title="What numbers cross what thresholds">
        <div
          className="grid"
          style={{ gap: 'var(--gap-md)', gridTemplateColumns: 'repeat(auto-fit, minmax(260px, 1fr))' }}
        >
          {capacityMath.interpretations.map((entry) => (
            <LaneCard
              key={entry.threshold}
              eyebrow={entry.threshold}
              title={entry.implication}
            />
          ))}
        </div>
      </Section>

      <Section eyebrow="SLO" title="Translating nines to design choice">
        <div className="card" style={{ padding: 'var(--pad-md)', overflowX: 'auto' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
            <thead>
              <tr>
                <th style={{ textAlign: 'left', padding: 8, color: 'var(--text-4)', fontWeight: 500 }}>Target</th>
                <th style={{ textAlign: 'left', padding: 8, color: 'var(--text-4)', fontWeight: 500 }}>Allowed downtime</th>
                <th style={{ textAlign: 'left', padding: 8, color: 'var(--text-4)', fontWeight: 500 }}>Design choice</th>
              </tr>
            </thead>
            <tbody>
              {capacityMath.sloRows.map((row) => (
                <tr key={row.target} style={{ borderTop: '1px solid var(--border)' }}>
                  <td style={{ padding: 8, color: 'var(--text-2)' }}>{row.target}</td>
                  <td style={{ padding: 8, color: 'var(--text-2)' }}>{row.minutesPerMonth}</td>
                  <td style={{ padding: 8, color: 'var(--text-3)' }}>{row.designChoice}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Section>
    </StudyShell>
  );
}

function OutputRow({ label, value }: { label: string; value: string }) {
  return (
    <div
      className="flex items-baseline"
      style={{
        justifyContent: 'space-between',
        padding: '8px 0',
        borderBottom: '1px solid var(--border)',
        gap: 'var(--gap-sm)',
      }}
    >
      <span style={{ fontSize: 12.5, color: 'var(--text-3)' }}>{label}</span>
      <span className="mono" style={{ fontSize: 16, color: 'var(--accent)', fontWeight: 600 }}>{value}</span>
    </div>
  );
}
