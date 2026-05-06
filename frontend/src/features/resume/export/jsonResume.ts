// JSON Resume schema (jsonresume.org/schema/) export. Provides
// portability — once the user has their resume in this format, they
// can pipe it through dozens of community themes outside Rounds.

import type { ResumeData } from '../types';
import { downloadString } from './index';

type JsonResume = {
  $schema: string;
  basics: {
    name: string;
    label?: string;
    email?: string;
    phone?: string;
    url?: string;
    summary?: string;
    location?: { city?: string };
    profiles?: { network: string; username?: string; url?: string }[];
  };
  work: Array<{
    name: string; // company
    position?: string;
    location?: string;
    startDate?: string;
    endDate?: string;
    summary?: string;
    highlights?: string[];
  }>;
  education: Array<{
    institution: string;
    area?: string;
    studyType?: string;
    startDate?: string;
    endDate?: string;
    score?: string;
    note?: string;
  }>;
  skills: Array<{ name: string; keywords: string[] }>;
  projects: Array<{
    name: string;
    description?: string;
    keywords?: string[];
    url?: string;
    startDate?: string;
    endDate?: string;
    highlights?: string[];
  }>;
  publications: Array<{
    name: string;
    publisher?: string;
    releaseDate?: string;
    url?: string;
    summary?: string;
  }>;
};

export function toJsonResume(data: ResumeData): JsonResume {
  const p = data.personalInfo;
  return {
    $schema: 'https://jsonresume.org/schema/',
    basics: {
      name: p.fullName,
      label: p.title,
      email: p.email,
      phone: p.phone,
      url: p.website,
      summary: p.summary,
      location: p.location ? { city: p.location } : undefined,
      profiles: [
        ...(p.linkedin ? [{ network: 'LinkedIn', url: ensureUrl(p.linkedin) }] : []),
        ...(p.github ? [{ network: 'GitHub', url: ensureUrl(p.github) }] : []),
        ...data.profiles.map((pf) => ({
          network: pf.network,
          username: pf.username,
          url: pf.url ? ensureUrl(pf.url) : undefined,
        })),
      ],
    },
    work: data.experience.map((e) => ({
      name: e.company,
      position: e.position,
      location: e.location,
      startDate: e.startDate,
      endDate: e.current ? undefined : e.endDate,
      summary: e.description,
      highlights: e.highlights,
    })),
    education: data.education.map((ed) => ({
      institution: ed.institution,
      area: ed.field,
      studyType: ed.degree,
      startDate: ed.startDate,
      endDate: ed.endDate,
      score: ed.gpa,
      note: ed.description,
    })),
    skills: data.skills.map((sk) => ({
      name: sk.category,
      keywords: sk.items,
    })),
    projects: data.projects.map((pr) => ({
      name: pr.name,
      description: pr.description,
      keywords: pr.technologies,
      url: pr.url ? ensureUrl(pr.url) : undefined,
      startDate: pr.startDate,
      endDate: pr.endDate,
      highlights: pr.highlights,
    })),
    publications: data.publications.map((pb) => ({
      name: pb.title,
      publisher: pb.publisher,
      releaseDate: pb.releaseDate,
      url: pb.url ? ensureUrl(pb.url) : undefined,
      summary: pb.summary,
    })),
  };
}

function ensureUrl(s: string): string {
  if (/^https?:\/\//i.test(s)) return s;
  return `https://${s}`;
}

export function exportJsonResume(data: ResumeData, base: string): void {
  const json = JSON.stringify(toJsonResume(data), null, 2);
  downloadString(json, `${base}.json`, 'application/json;charset=utf-8');
}
