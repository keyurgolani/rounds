import { BriefcaseBusiness, CalendarClock, FolderKanban } from 'lucide-react';
import { useAuth } from '../auth/AuthProvider';
import { useCampaign } from '../campaign/CampaignContext';
import { useCommandCenter } from '../command-center/CommandCenterProvider';
import AppHeader from '../components/shell/AppHeader';
import StreakCard from '../components/shell/StreakCard';
import TodosWidget from '../components/dashboard/TodosWidget';
import TodayZone from '../components/dashboard/TodayZone';
import PracticeReadiness from '../components/dashboard/PracticeReadiness';
import BehavioralDepth from '../components/dashboard/BehavioralDepth';
import PipelinePulse from '../components/dashboard/PipelinePulse';
import UpcomingInterviews from '../components/dashboard/UpcomingInterviews';
import ResumeCoverage from '../components/dashboard/ResumeCoverage';
import ExperienceLibraryOverview from '../components/dashboard/ExperienceLibraryOverview';
import { useDashboardData } from '../components/dashboard/useDashboardData';

function greeting(hour: number) {
  if (hour < 12) return 'Good morning';
  if (hour < 17) return 'Good afternoon';
  if (hour < 21) return 'Good evening';
  return 'Working late';
}
function firstName(full: string) { return full.split(/\s+/)[0] ?? full; }
function formatDate(d: Date) { return d.toLocaleDateString(undefined, { weekday: 'long', month: 'long', day: 'numeric' }); }

export default function Dashboard() {
  const { user } = useAuth();
  const { currentCampaign, campaigns } = useCampaign();
  const cc = useCommandCenter();
  const d = useDashboardData();

  const name = user ? firstName(user.name) : 'there';
  const hour = new Date().getHours();
  const campaignLabel = currentCampaign?.name ?? (campaigns.length > 1 ? 'All active campaigns' : campaigns[0]?.name ?? 'Default');
  const activeApps = d.apps.filter((a) => ['Wishlist', 'Applied', 'Interviewing', 'Offer'].includes(a.status)).length;
  const description = `${activeApps} active ${activeApps === 1 ? 'application' : 'applications'} · ${d.upcoming.length} upcoming ${d.upcoming.length === 1 ? 'round' : 'rounds'} · ${d.readiness.reduce((n, t) => n + t.inProgress, 0)} reps in motion`;

  return (
    <div className="h-full flex flex-col">
      <AppHeader
        title={`${greeting(hour)}, ${name}.`}
        eyebrow={<span className="eyebrow">{formatDate(new Date())} / {campaignLabel}</span>}
        description={description}
        actions={<StreakCard compact="header" />}
        compactActions={<StreakCard compact />}
      />
      <div className="flex-1 min-h-0 overflow-y-auto">
        <div style={{ padding: 'var(--page-pad-y) var(--page-pad-x)', display: 'grid', gap: 'var(--gap-lg)' }}>
          <div className="flex flex-wrap gap-2">
            <button type="button" onClick={() => cc.openView('add-application')} className="inline-flex items-center gap-2" style={actionBtn}><BriefcaseBusiness size={14} /> Add application</button>
            <button type="button" onClick={() => cc.openView('schedule-interview')} className="inline-flex items-center gap-2" style={actionBtn}><CalendarClock size={14} /> Add round</button>
            <button type="button" onClick={() => cc.openView('campaigns')} className="inline-flex items-center gap-2" style={subtleBtn}><FolderKanban size={14} /> Campaigns</button>
          </div>

          <TodayZone
            nextInterview={d.today.nextInterview}
            nextInterviewApp={d.today.nextInterviewApp}
            nextReps={d.today.nextReps}
            atRisk={d.today.atRisk}
          />

          <section className="grid" style={{ gap: 'var(--gap-md)', gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))', alignItems: 'start' }}>
            <div className="grid gap-3" style={{ alignContent: 'start' }}>
              <div className="eyebrow" style={{ color: 'var(--forest)' }}>Prepare — get interview-ready</div>
              <PracticeReadiness tracks={d.readiness} />
              <BehavioralDepth depth={d.behavioral} />
            </div>
            <div className="grid gap-3" style={{ alignContent: 'start' }}>
              <div className="eyebrow" style={{ color: 'var(--accent)' }}>Apply — land the offer</div>
              <PipelinePulse counts={d.pipeline.counts} />
              <UpcomingInterviews rounds={d.upcoming} apps={d.apps} />
              <ResumeCoverage coverage={d.resume} />
            </div>
          </section>

          <section className="grid" style={{ gap: 'var(--gap-md)', gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))', alignItems: 'start' }}>
            <ExperienceLibraryOverview overview={d.experience} />
            <TodosWidget />
          </section>
        </div>
      </div>
    </div>
  );
}

const actionBtn: React.CSSProperties = { border: 0, borderRadius: 'var(--radius)', padding: '9px 13px', background: 'var(--accent)', color: 'var(--bg-elev)', fontSize: 12.5, fontWeight: 600, cursor: 'pointer' };
const subtleBtn: React.CSSProperties = { border: 0, borderRadius: 'var(--radius)', padding: '9px 13px', background: 'var(--bg)', color: 'var(--text-2)', boxShadow: 'inset 0 0 0 1px var(--border)', fontSize: 12.5, fontWeight: 600, cursor: 'pointer' };
