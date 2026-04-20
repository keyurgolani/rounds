import { Routes, Route, Navigate } from 'react-router-dom';
import Layout from './components/Layout';
import RequireAuth from './auth/RequireAuth';
import Dashboard from './pages/Dashboard';
import SystemDesignList from './pages/SystemDesignList';
import SystemDesignDetail from './pages/SystemDesignDetail';
import CodingList from './pages/CodingList';
import CodingDetail from './pages/CodingDetail';
import BehavioralList from './pages/BehavioralList';
import BehavioralDetail from './pages/BehavioralDetail';
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

export default function App() {
  return (
    <Routes>
      <Route path="login" element={<Login />} />
      <Route path="signup" element={<Signup />} />

      <Route
        element={
          <RequireAuth>
            <Layout />
          </RequireAuth>
        }
      >
        <Route index element={<Navigate to="/dashboard" replace />} />
        <Route path="dashboard" element={<Dashboard />} />
        <Route path="system-design" element={<SystemDesignList />} />
        <Route path="system-design/question/:slug" element={<SystemDesignDetail />} />
        <Route path="coding" element={<CodingList />} />
        <Route path="coding/question/:slug" element={<CodingDetail />} />
        <Route path="behavioral" element={<BehavioralList />} />
        <Route path="behavioral/anecdotes/new" element={<AnecdoteEditorPage />} />
        <Route path="behavioral/anecdotes/:slug/edit" element={<AnecdoteEditorPage />} />
        <Route path="behavioral/question/:slug" element={<BehavioralDetail />} />
        <Route path="applications" element={<Applications />} />
        <Route path="applications/new" element={<NewApplication />} />
        <Route path="applications/:slug" element={<ApplicationDetail />} />
        <Route path="interviews" element={<Interviews />} />
        <Route path="interviews/new" element={<ScheduleRound />} />
        <Route path="profile" element={<Profile />} />
        <Route path="settings" element={<Settings />} />
      </Route>
    </Routes>
  );
}
