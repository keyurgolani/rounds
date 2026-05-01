import { BriefcaseBusiness, CalendarPlus, FolderKanban, Palette, Plus } from 'lucide-react';
import type { ReactNode } from 'react';
import AddApplicationView from './views/AddApplicationView';
import AddTodoView from './views/AddTodoView';
import CampaignView from './views/CampaignView';
import ScheduleInterviewView from './views/ScheduleInterviewView';
import ThemeView from './views/ThemeView';

export type CommandView = {
  id: string;
  label: string;
  description?: string;
  icon?: ReactNode;
  Component: React.FC<{ onComplete: () => void }>;
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
    label: 'Schedule interview',
    description: 'Add a round to an existing application.',
    icon: <CalendarPlus size={14} strokeWidth={1.7} />,
    Component: ScheduleInterviewView,
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
