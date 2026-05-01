export type CampaignStatus = 'planning' | 'active' | 'wrapped';

export interface Campaign {
  id: string;
  slug: string;
  name: string;
  description: string;
  target_role_level: string;
  target_companies: string[];
  start_date: string;
  end_date: string;
  status: CampaignStatus;
  color: string;
  is_default: boolean;
  created_at?: string;
  updated_at?: string;
}

export interface UserPreferences {
  id?: string;
  theme?: string;
  accent?: string;
  type_variant?: string;
  density?: string;
  nav_style?: string;
  card_treatment?: string;
  current_campaign_id?: string;
}

export interface ProgressRow {
  id: string;
  campaign_id: string;
  question_type: 'system' | 'coding' | 'behavioral';
  question_slug: string;
  status: 'todo' | 'in-progress' | 'mastered';
  notes?: string;
  confidence?: number | null;
  completed_at?: string | null;
}

export interface CodeDraftRow {
  id: string;
  campaign_id: string;
  question: string;
  language: string;
  code: string;
  updated_at?: string;
}
