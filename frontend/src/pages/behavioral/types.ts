export interface Anecdote {
  id: string;
  title: string;
  description: string;
  situation: string;
  task: string;
  action: string;
  result: string;
  category_ids: string[];
  linked_question_ids: string[];
  notes: string;
  created_at?: string;
  updated_at?: string;
}

export interface BehavioralCategoryLite {
  id: string;
  name: string;
  color: string;
  icon: string;
}

export interface BehavioralQuestionLite {
  id: string;
  title: string;
}
