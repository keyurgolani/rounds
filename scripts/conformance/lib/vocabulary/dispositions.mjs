// Disposition vocabulary (DR-0001 G10). Feature level: Preserve, Transform, or
// owner-approved Retire plus an optional qualifier (spec 335-374). Item level:
// migrate, archive, rebuild, reconcile, or owner-approved drop (spec 2666-2670),
// with the catalog words bridge, quarantine, and retire mapped onto them.

export function parseFeatureDisposition(text, dispositions) {
  const trimmed = String(text ?? '').trim();
  for (const { value, requiresOwnerApproval } of dispositions.feature.values) {
    if (trimmed === value || trimmed.startsWith(`${value} `)) {
      const qualifier = trimmed.slice(value.length).trim() || null;
      return { ok: true, value, qualifier, requiresOwnerApproval: Boolean(requiresOwnerApproval) };
    }
  }
  const allowed = dispositions.feature.values.map((v) => v.value).join(', ');
  return { ok: false, reason: `"${trimmed}" does not start with ${allowed}` };
}

export function parseItemDisposition(text, dispositions) {
  const word = String(text ?? '').trim().toLowerCase();
  const direct = dispositions.item.values.find((v) => v.value === word);
  if (direct) return { ok: true, value: direct.value, via: null, condition: null, requiresOwnerApproval: Boolean(direct.requiresOwnerApproval) };
  const mapped = dispositions.item.catalogWords.find((w) => w.word === word);
  if (mapped) {
    const target = dispositions.item.values.find((v) => v.value === mapped.value);
    return {
      ok: Boolean(target),
      value: mapped.value,
      via: mapped.word,
      condition: mapped.condition || null,
      requiresOwnerApproval: Boolean(target?.requiresOwnerApproval),
    };
  }
  const allowed = dispositions.item.values.map((v) => v.value).join(', ');
  return { ok: false, reason: `"${word}" is not one of ${allowed} or a mapped catalog word` };
}
