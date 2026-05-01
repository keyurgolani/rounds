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
import AICoding from './pages/AICoding';
import { AnecdoteEditorPage } from './pages/behavioral/AnecdoteEditorPage';
import Applications from './pages/Applications';
import ApplicationDetail from './pages/ApplicationDetail';
import NewApplication from './pages/NewApplication';
import Interviews from './pages/Interviews';
import ScheduleRound from './pages/ScheduleRound';
import Login from './pages/Login';
import Signup from './pages/Signup';
import Profile from './pages/Profile';
import Settings from './pages/Settings';
import Campaigns from './pages/Campaigns';
import CampaignDetail from './pages/CampaignDetail';
import Todos from './pages/Todos';
import RoundDetail from './pages/RoundDetail';
import { CampaignProvider } from './campaign/CampaignContext';

export default function App() {
  return (
    <Routes>
      <Route path="login" element={<Login />} />
      <Route path="signup" element={<Signup />} />

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
        <Route path="ai-coding" element={<AICoding />} />
        <Route path="applications" element={<Applications />} />
        <Route path="applications/new" element={<NewApplication />} />
        <Route path="applications/:slug" element={<ApplicationDetail />} />
        <Route path="interviews" element={<Interviews />} />
        <Route path="interviews/new" element={<ScheduleRound />} />
        <Route path="interviews/:id" element={<RoundDetail />} />
        <Route path="campaigns" element={<Campaigns />} />
        <Route path="campaigns/:slug" element={<CampaignDetail />} />
        <Route path="todos" element={<Todos />} />
        <Route path="profile" element={<Profile />} />
        <Route path="settings" element={<Settings />} />
      </Route>
    </Routes>
  );
}
