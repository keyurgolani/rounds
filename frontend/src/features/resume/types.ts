// Canonical types for the Resume Studio.
//
// `ResumeData` is the shape stored in `resumes.data` and copied into
// `resume_variants.data`. It's loosely compatible with the JSON Resume
// schema (jsonresume.org) so we can export to/import from that format
// without information loss for the common fields.

export type ResumeId = string;

export type SectionKey =
  | 'personal'
  | 'experience'
  | 'education'
  | 'skills'
  | 'projects'
  | 'publications'
  | 'profiles';

export type Profile = {
  id: string;
  network: string; // 'LinkedIn' | 'GitHub' | 'Portfolio' | etc.
  username?: string;
  url?: string;
};

export type PersonalInfo = {
  fullName: string;
  email?: string;
  phone?: string;
  location?: string;
  website?: string;
  linkedin?: string;
  github?: string;
  title?: string;
  subtitle?: string;
  summary?: string;
};

export type WorkExperience = {
  id: string;
  company: string;
  position: string;
  location?: string;
  startDate?: string; // YYYY-MM
  endDate?: string;
  current?: boolean;
  description?: string;
  highlights: string[]; // bullet points
};

export type Education = {
  id: string;
  institution: string;
  degree?: string;
  field?: string;
  location?: string;
  startDate?: string;
  endDate?: string;
  gpa?: string;
  description?: string;
};

export type SkillGroup = {
  id: string;
  category: string; // e.g. 'Languages', 'Frameworks'
  items: string[];
};

export type Project = {
  id: string;
  name: string;
  description?: string;
  technologies: string[];
  url?: string;
  github?: string;
  startDate?: string;
  endDate?: string;
  highlights: string[];
};

export type Publication = {
  id: string;
  title: string;
  publisher?: string;
  releaseDate?: string;
  url?: string;
  summary?: string;
};

export type ResumeData = {
  personalInfo: PersonalInfo;
  experience: WorkExperience[];
  education: Education[];
  skills: SkillGroup[];
  projects: Project[];
  publications: Publication[];
  profiles: Profile[];
  sectionOrder?: SectionKey[]; // user-customized ordering
  hiddenSections?: SectionKey[];
};

// Template-level customization. Templates ship a default `TemplateConfig`;
// the user's `resumes.design` field overrides it.
export type TemplateConfig = {
  layout?: 'single-column' | 'two-column' | 'sidebar-left' | 'sidebar-right';
  colors?: {
    primary?: string;
    secondary?: string;
    background?: string;
    text?: string;
    accent?: string;
  };
  typography?: {
    heading?: { family?: string; weight?: number; transform?: string; size?: number };
    body?: { family?: string; size?: number; lineHeight?: number };
  };
  spacing?: { margin?: number; padding?: number; gap?: number };
  style?: { borderRadius?: number; borderWidth?: number; shadow?: string };
  showPhoto?: boolean;
  showIcons?: boolean;
  divider?: 'none' | 'line' | 'block';
  // Bullet marker for highlight lists in experience / projects entries.
  // `disc` is the default and matches the legacy look. The CSS that
  // renders these lives in `RESUME_PAGE_CSS` (templates/parts.tsx).
  bulletStyle?:
    | 'disc'
    | 'circle'
    | 'square'
    | 'dash'
    | 'arrow'
    | 'arrow-long'
    | 'chevron'
    | 'triangle'
    | 'check'
    | 'diamond'
    | 'star'
    | 'star-outline'
    | 'plus'
    | 'asterisk'
    | 'dot'
    | 'none';
};

export type Resume = {
  id: ResumeId;
  user_id: string;
  name: string;
  slug: string;
  template_id: string;
  design: TemplateConfig;
  data: ResumeData;
  created_at: string;
  updated_at: string;
};

export type ResumeVariant = {
  id: string;
  user_id: string;
  resume_id: ResumeId;
  name: string;
  target_company?: string;
  job_title?: string;
  job_description?: string;
  tone?: string;
  role_focus?: string[];
  data: ResumeData;
  ats_score?: number;
  ats_breakdown?: ATSBreakdown;
  application_id?: string;
  created_at: string;
  updated_at: string;
};

export type ATSBreakdown = {
  contact?: number;
  sections?: number;
  keywords?: number;
  semantic?: number;
  formatting?: number;
  achievements?: number;
  actionVerbs?: number;
  density?: number;
  suggestions?: string[];
  missingKeywords?: string[];
};

export type ResumeVersion = {
  id: string;
  user_id: string;
  resume_id?: ResumeId;
  variant_id?: string;
  data: ResumeData;
  label?: string;
  is_auto: boolean;
  created_at: string;
};

export type Bullet = {
  id: string;
  user_id: string;
  text: string;
  tags: string[];
  metrics?: { value: number; unit?: string }[];
  created_at: string;
  updated_at: string;
};

export type AIProvider =
  | 'anthropic'
  | 'openai'
  | 'google'
  | 'ollama'
  | 'groq'
  | 'openrouter'
  | 'deepseek'
  | 'mistral'
  | 'custom';

export type AISettings = {
  id: string;
  user_id: string;
  provider: AIProvider;
  model: string;
  import_model?: string;
  base_url?: string;
  encrypted_key?: string;
  key_iv?: string;
  updated_at: string;
};

export type ShareLink = {
  id: string;
  user_id: string;
  variant_id: string;
  token: string;
  is_password: boolean;
  password_hash?: string;
  expires_at?: string;
  created_at: string;
};

// Empty resume factory — used when creating a new blank resume.
export function emptyResumeData(): ResumeData {
  return {
    personalInfo: { fullName: '' },
    experience: [],
    education: [],
    skills: [],
    projects: [],
    publications: [],
    profiles: [],
  };
}
