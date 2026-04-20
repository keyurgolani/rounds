export interface Anecdote {
  id: number;
  title: string;
  description: string;
  situation: string;
  task: string;
  action: string;
  result: string;
  category_ids: number[];
  linked_question_ids: number[];
  notes: string;
  created_at?: string;
  updated_at?: string;
}

export interface BehavioralCategoryLite {
  id: number;
  name: string;
  color: string;
  icon: string;
}

export interface BehavioralQuestionLite {
  id: number;
  title: string;
}
