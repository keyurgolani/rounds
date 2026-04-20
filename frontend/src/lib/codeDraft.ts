import { supabase, supabaseEnabled } from './supabase';

const keyFor = (userId: string | null, questionId: number, language: string) =>
  `rounds.codeDraft.v1:${userId ?? 'guest'}:${questionId}:${language}`;

export function loadLocal(userId: string | null, questionId: number, language: string): string | null {
  try {
    return localStorage.getItem(keyFor(userId, questionId, language));
  } catch {
    return null;
  }
}

export function saveLocal(userId: string | null, questionId: number, language: string, code: string): void {
  try {
    localStorage.setItem(keyFor(userId, questionId, language), code);
  } catch {
    /* noop */
  }
}

export async function loadRemote(
  userId: string,
  questionId: number,
  language: string,
): Promise<string | null> {
  if (!supabaseEnabled || !supabase) return null;
  const { data, error } = await supabase
    .from('code_drafts')
    .select('code')
    .eq('user_id', userId)
    .eq('question_id', questionId)
    .eq('language', language)
    .maybeSingle();
  if (error || !data) return null;
  return data.code ?? null;
}

export async function saveRemote(
  userId: string,
  questionId: number,
  language: string,
  code: string,
): Promise<void> {
  if (!supabaseEnabled || !supabase) return;
  await supabase
    .from('code_drafts')
    .upsert(
      { user_id: userId, question_id: questionId, language, code },
      { onConflict: 'user_id,question_id,language' },
    );
}
