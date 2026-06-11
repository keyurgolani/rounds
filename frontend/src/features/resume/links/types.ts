// The reference graph that sits beside a resume's materialized ResumeData.
// `bulletRefs`/`bulletEdited` are index-aligned to the entry's highlights[].

export interface EntryLink {
  ref: string | null;            // library job/project id; null = manual entry
  headerEdited: boolean;         // header fields detached from the library
  bulletRefs: (string | null)[]; // per-highlight library bullet id (or null)
  bulletEdited: boolean[];       // per-highlight detach flag
}

export interface ResumeLinks {
  experience: Record<string, EntryLink>; // keyed by WorkExperience.id
  projects: Record<string, EntryLink>;   // keyed by Project.id
}

export function emptyLinks(): ResumeLinks {
  return { experience: {}, projects: {} };
}

export function emptyEntryLink(): EntryLink {
  return { ref: null, headerEdited: false, bulletRefs: [], bulletEdited: [] };
}
