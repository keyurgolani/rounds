import { Routes, Route, Navigate } from 'react-router-dom';
import Layout from './components/Layout';
import RequireAuth from './auth/RequireAuth';
import Dashboard from './pages/Dashboard';
import SystemDesignList from './pages/SystemDesignList';
import SystemDesignDetail from './pages/SystemDesignDetail';
import GuidePage from './pages/guides/GuidePage';
import CodingList from './pages/CodingList';
import CodingDetail from './pages/CodingDetail';
import BehavioralList from './pages/BehavioralList';
import BehavioralDetail from './pages/BehavioralDetail';
import AICodingList from './pages/ai-coding/AICodingList';
import AICodingDetail from './pages/ai-coding/AICodingDetail';
import TakeHomeList from './pages/take-home/TakeHomeList';
import TakeHomeDetail from './pages/take-home/TakeHomeDetail';
import { AnecdoteEditorPage } from './pages/behavioral/AnecdoteEditorPage';
import Applications from './pages/Applications';
import ApplicationDetail from './pages/ApplicationDetail';
import NewApplication from './pages/NewApplication';
import Login from './pages/Login';
import Signup from './pages/Signup';
import Profile from './pages/Profile';
import Settings from './pages/Settings';
import Campaigns from './pages/Campaigns';
import CampaignDetail from './pages/CampaignDetail';
import Todos from './pages/Todos';
import ResumesList from './pages/ResumesList';
import ResumeStudio from './pages/ResumeStudio';
import PublicResume from './pages/PublicResume';
import { CampaignProvider } from './campaign/CampaignContext';

export default function App() {
  return (
    <Routes>
      <Route path="login" element={<Login />} />
      <Route path="signup" element={<Signup />} />
      <Route path="r/:token" element={<PublicResume />} />

      <Route
        element={
          <RequireAuth>
            <CampaignProvider>
              <Layout />
            </CampaignProvider>
          </RequireAuth>
        }
      >
        <Route index element={<Navigate to="/dashboard" replace />} />
        <Route path="dashboard" element={<Dashboard />} />
        <Route path="system-design" element={<Navigate to="/system-design/guide" replace />} />
        <Route path="system-design/questions" element={<SystemDesignList />} />
        <Route path="system-design/guide" element={<GuidePage />} />
        <Route path="system-design/guide/:slug" element={<GuidePage />} />
        <Route path="system-design/question/:slug" element={<SystemDesignDetail />} />
        <Route path="system-design/question/:slug/guidance" element={<SystemDesignDetail />} />
        <Route path="coding" element={<Navigate to="/coding/guide" replace />} />
        <Route path="coding/questions" element={<CodingList />} />
        <Route path="coding/guide" element={<GuidePage track="coding" />} />
        <Route path="coding/guide/:slug" element={<GuidePage track="coding" />} />
        <Route path="coding/question/:slug" element={<CodingDetail />} />
        <Route path="behavioral" element={<Navigate to="/behavioral/guide" replace />} />
        <Route path="behavioral/questions" element={<BehavioralList />} />
        <Route path="behavioral/guide" element={<GuidePage track="behavioral" />} />
        <Route path="behavioral/guide/:slug" element={<GuidePage track="behavioral" />} />
        <Route path="behavioral/anecdotes/new" element={<AnecdoteEditorPage />} />
        <Route path="behavioral/anecdotes/:slug/edit" element={<AnecdoteEditorPage />} />
        <Route path="behavioral/question/:slug" element={<BehavioralDetail />} />
        <Route path="ai-coding/guide" element={<GuidePage track="ai-coding" />} />
        <Route path="ai-coding/guide/:slug" element={<GuidePage track="ai-coding" />} />
        <Route path="builder/guide" element={<GuidePage track="builder" />} />
        <Route path="builder/guide/:slug" element={<GuidePage track="builder" />} />
        <Route path="builder" element={<Navigate to="/take-home" replace />} />
        <Route path="take-home/guide" element={<GuidePage track="take-home" />} />
        <Route path="ai-coding" element={<AICodingList />} />
        <Route path="ai-coding/round/:slug" element={<AICodingDetail />} />
        <Route path="take-home" element={<TakeHomeList />} />
        <Route path="take-home/assignment/:slug" element={<TakeHomeDetail />} />
        <Route path="applications" element={<Applications />} />
        <Route path="applications/new" element={<NewApplication />} />
        <Route path="applications/:slug" element={<ApplicationDetail />} />
        {/* The standalone Interviews aggregate, the "schedule round"
            page, and the per-round detail page were all removed. All
            round CRUD now happens inline on the application page.
            Legacy interview URLs redirect to /applications. */}
        <Route path="interviews" element={<Navigate to="/applications" replace />} />
        <Route path="interviews/new" element={<Navigate to="/applications" replace />} />
        <Route path="interviews/:id" element={<Navigate to="/applications" replace />} />
        <Route path="campaigns" element={<Campaigns />} />
        <Route path="campaigns/:slug" element={<CampaignDetail />} />
        <Route path="todos" element={<Todos />} />
        <Route path="resumes" element={<ResumesList />} />
        <Route path="resumes/:slug" element={<ResumeStudio />} />
        <Route path="profile" element={<Profile />} />
        <Route path="settings" element={<Settings />} />
      </Route>
    </Routes>
  );
}
