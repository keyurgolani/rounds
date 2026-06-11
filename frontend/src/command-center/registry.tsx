import {
  BriefcaseBusiness,
  CalendarPlus,
  Code2,
  FilePlus2,
  FolderKanban,
  Layers,
  MessagesSquare,
  NotebookPen,
  Palette,
  Plus,
} from 'lucide-react';
import type { ReactNode } from 'react';
import type { NavigateFunction } from 'react-router-dom';
import AddApplicationView from './views/AddApplicationView';
import AddTodoView from './views/AddTodoView';
import CampaignView from './views/CampaignView';
import ScheduleInterviewView from './views/ScheduleInterviewView';
import ThemeView from './views/ThemeView';
import { createResume } from '../features/resume/api';

// A Command Center entry is either an inline-form view (the original
// pattern: `Component` renders inside the modal) or a one-shot action
// (`run` fires immediately and the modal auto-closes on the resulting
// route change). One of `Component` or `run` must be provided.
export type CommandView = {
  id: string;
  label: string;
  description?: string;
  icon?: ReactNode;
  Component?: React.FC<{ onComplete: () => void }>;
  run?: (ctx: {
    navigate: NavigateFunction;
    close: () => void;
  }) => void | Promise<void>;
};

export const registry: CommandView[] = [
  {
    id: 'add-todo',
    label: 'Add todo',
    description: 'Capture a quick task in the current campaign.',
    icon: <Plus size={14} strokeWidth={1.7} />,
    Component: AddTodoView,
  },
  {
    id: 'add-application',
    label: 'Add application',
    description: 'Create a company and role in the active campaign.',
    icon: <BriefcaseBusiness size={14} strokeWidth={1.7} />,
    Component: AddApplicationView,
  },
  {
    id: 'schedule-interview',
    label: 'Add round',
    description: 'Log a new round under an existing application.',
    icon: <CalendarPlus size={14} strokeWidth={1.7} />,
    Component: ScheduleInterviewView,
  },
  {
    id: 'new-resume',
    label: 'New resume',
    description: 'Create a blank resume in Resume Studio and start editing.',
    icon: <FilePlus2 size={14} strokeWidth={1.7} />,
    run: async ({ navigate }) => {
      const created = await createResume({ name: 'Untitled resume' });
      navigate(`/resumes/${created.slug}`);
    },
  },
  {
    id: 'new-anecdote',
    label: 'New anecdote',
    description: 'Open the anecdote editor with a blank STAR story.',
    icon: <NotebookPen size={14} strokeWidth={1.7} />,
    run: ({ navigate }) => {
      navigate('/experience/list?anecdote=new');
    },
  },
  {
    id: 'practice-coding',
    label: 'Practice coding',
    description: 'Open the coding question list with practice-status filter.',
    icon: <Code2 size={14} strokeWidth={1.7} />,
    run: ({ navigate }) => {
      navigate('/coding/questions');
    },
  },
  {
    id: 'practice-system-design',
    label: 'Practice system design',
    description: 'Open the system design problem list.',
    icon: <Layers size={14} strokeWidth={1.7} />,
    run: ({ navigate }) => {
      navigate('/system-design/questions');
    },
  },
  {
    id: 'practice-behavioral',
    label: 'Practice behavioral',
    description: 'Open the behavioral question list.',
    icon: <MessagesSquare size={14} strokeWidth={1.7} />,
    run: ({ navigate }) => {
      navigate('/behavioral/questions');
    },
  },
  {
    id: 'campaigns',
    label: 'Campaigns',
    description: 'Switch workspace or create a new campaign.',
    icon: <FolderKanban size={14} strokeWidth={1.7} />,
    Component: CampaignView,
  },
  {
    id: 'theme',
    label: 'Theme',
    description: 'Customize colors, fonts, corners, density, and layout.',
    icon: <Palette size={14} strokeWidth={1.7} />,
    Component: ThemeView,
  },
];
