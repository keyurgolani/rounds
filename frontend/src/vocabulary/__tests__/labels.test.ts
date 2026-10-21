import { describe, expect, it } from 'vitest';
import {
  VOCABULARY_RECORD,
  VOCABULARY_REVISION,
  inspectionTerms,
  label,
  labelAxes,
  specLabels,
  type TermId,
} from '../labels';

describe('vocabulary labels', () => {
  it('names the registry revision consumers cite', () => {
    expect(VOCABULARY_REVISION).toBe(2);
    expect(VOCABULARY_RECORD).toBe('DR-0001@2');
  });

  it('returns the spec 1000-1014 labels', () => {
    expect(label('extracted-claim')).toBe('Proposed change');
    expect(label('generation-proposal')).toBe('Writing suggestion');
    expect(label('transaction-change-set')).toBe('Saved changes');
    expect(label('profile-revision')).toBe('Profile update');
    expect(label('campaign-goal')).toBe('Campaign');
    expect(label('practice-attempt')).toBe('Attempt');
    expect(label('readiness-snapshot')).toBe('Readiness');
    expect(label('artifact-revision')).toBe('Version');
    expect(label('artifact-revision', { option: 'submitted-version' })).toBe('Submitted version');
    expect(specLabels['artifact-revision']).toBe('Version or Submitted version');
    expect(specLabels.pursuit).toBe('Application, Opportunity, or Pipeline item according to stage');
    expect(Object.keys(specLabels)).toHaveLength(13);
  });

  it('picks options and plurals', () => {
    expect(label('extracted-claim', { count: 2 })).toBe('Proposed changes');
    expect(label('extracted-claim', { count: 1 })).toBe('Proposed change');
    expect(label('pursuit', { option: 'pipeline-item', count: 3 })).toBe('Pipeline items');
    expect(label('career-activity', { option: 'interview' })).toBe('Interview');
    expect(label('person', { count: 0 })).toBe('People');
  });

  it('defaults to the catch-all where no leaf owns the mapping yet', () => {
    expect(label('artifact-edition')).toBe('Material');
    expect(label('artifact-edition', { count: 2 })).toBe('Materials');
    expect(label('career-activity')).toBe('Activity');
    expect(labelAxes['artifact-edition'].mappingOwner).toEqual([]);
    expect(labelAxes.pursuit).toEqual({ axis: 'stage', mappingOwner: ['ROUNDS-20-L01'] });
  });

  it('has no internal-term fallback', () => {
    expect(() => label('domain-event' as unknown as TermId)).toThrow(/No user-facing label/);
    expect(() => label('audit-entry' as unknown as TermId)).toThrow(/No user-facing label/);
    expect(() => label('not-a-term' as unknown as TermId)).toThrow(/No user-facing label/);
    expect(() => label('pursuit', { option: 'wishlist' as never })).toThrow(/no label option/);
  });

  it('keeps technical names for inspection surfaces only', () => {
    expect(inspectionTerms['processing-attempt']).toBe('Processing Attempt');
    expect(inspectionTerms['execution-attempt']).toBe('Execution Attempt');
    expect(Object.keys(inspectionTerms)).not.toContain('extracted-claim');
    expect(Object.keys(inspectionTerms)).not.toContain('domain-event');
  });

  it('labels the Profile page as Account and track names as written', () => {
    expect(label('account')).toBe('Account');
    expect(label('account-preference', { count: 2 })).toBe('Settings');
    expect(label('track-ai-coding')).toBe('AI-Assisted Coding');
    expect(label('track-take-home')).toBe('Take-Home');
    expect(label('share-capability')).toBe('Share link');
  });
});
