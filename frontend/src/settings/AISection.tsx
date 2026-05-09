// Settings → AI providers.
//
// Multi-provider design: connect Anthropic, OpenAI, or any compatible
// endpoint, then assign one of their listed models to a role — text
// (powers import / improve / tailor / ATS) or vision (reserved for
// image-first imports). Models come from the provider's own
// /models endpoint, not a hard-coded list, so what you can pick is
// always what your key actually has access to.
//
// Keys are sent to the FastAPI runner over HTTPS, AES-GCM-encrypted
// with a server-side master secret, and stored as ciphertext in the
// `ai_providers` collection. They are never returned to the browser
// after they're saved.

import { useEffect, useMemo, useState } from 'react';
import {
  Eye,
  EyeOff,
  Pencil,
  Plus,
  RefreshCcw,
  Trash2,
  Wand2,
} from 'lucide-react';
import {
  createProvider,
  deleteProvider,
  getSettings,
  listProviders,
  refreshModels,
  saveSettings,
  testProvider,
  updateProvider,
  type AIRoleSettings,
  type Provider,
  type ProviderInput,
  type ProviderKind,
} from '../features/resume/ai/client';
import { endpointsForKind, type EndpointPreset } from './aiProviderEndpoints';

const KINDS: { id: ProviderKind; label: string; needsBaseUrl: boolean; example: string }[] = [
  { id: 'anthropic', label: 'Anthropic', needsBaseUrl: false, example: 'sk-ant-…' },
  { id: 'openai', label: 'OpenAI', needsBaseUrl: false, example: 'sk-…' },
  {
    id: 'openai-compatible',
    label: 'Custom · OpenAI-compatible',
    needsBaseUrl: true,
    example: 'sk-or-v1-… (Ollama, Groq, OpenRouter, DeepSeek, Mistral, …)',
  },
  {
    id: 'anthropic-compatible',
    label: 'Custom · Anthropic-compatible',
    needsBaseUrl: true,
    example: 'sk-ant-…',
  },
];

type EditState =
  | { kind: 'idle' }
  | { kind: 'add'; draft: DraftProvider }
  | { kind: 'edit'; id: string; draft: DraftProvider };

type DraftProvider = {
  kind: ProviderKind;
  label: string;
  base_url: string;
  key: string;
  showKey: boolean;
};

type Status =
  | { kind: 'idle' }
  | { kind: 'busy'; message: string }
  | { kind: 'ok'; message: string }
  | { kind: 'err'; message: string };

const empty: DraftProvider = {
  kind: 'anthropic',
  label: 'Anthropic',
  base_url: '',
  key: '',
  showKey: false,
};

export default function AISection() {
  const [providers, setProviders] = useState<Provider[]>([]);
  const [settings, setSettings] = useState<AIRoleSettings>({
    text_provider_id: null,
    text_model: '',
    vision_provider_id: null,
    vision_model: '',
  });
  const [loading, setLoading] = useState(true);
  const [topStatus, setTopStatus] = useState<Status>({ kind: 'idle' });
  const [editState, setEditState] = useState<EditState>({ kind: 'idle' });
  const [perRow, setPerRow] = useState<Record<string, Status>>({});

  useEffect(() => {
    void Promise.all([listProviders(), getSettings()])
      .then(([p, s]) => {
        setProviders(p);
        setSettings(s);
      })
      .catch((err: Error) => setTopStatus({ kind: 'err', message: err.message }))
      .finally(() => setLoading(false));
  }, []);

  const setRow = (id: string, status: Status) =>
    setPerRow((prev) => ({ ...prev, [id]: status }));

  // --- role pickers ----------------------------------------------------

  const onPickRole = async (
    role: 'text' | 'vision',
    valueOrEmpty: string,
  ) => {
    let next: AIRoleSettings;
    if (!valueOrEmpty) {
      next =
        role === 'text'
          ? { ...settings, text_provider_id: null, text_model: '' }
          : { ...settings, vision_provider_id: null, vision_model: '' };
    } else {
      const [providerId, model] = valueOrEmpty.split('::');
      next =
        role === 'text'
          ? { ...settings, text_provider_id: providerId, text_model: model }
          : { ...settings, vision_provider_id: providerId, vision_model: model };
    }
    setSettings(next);
    setTopStatus({ kind: 'busy', message: 'Saving…' });
    try {
      const saved = await saveSettings(next);
      setSettings(saved);
      setTopStatus({ kind: 'ok', message: 'Saved' });
      window.setTimeout(() => setTopStatus({ kind: 'idle' }), 1500);
    } catch (err) {
      setTopStatus({ kind: 'err', message: (err as Error).message });
    }
  };

  // --- provider form ---------------------------------------------------

  const startAdd = () =>
    setEditState({ kind: 'add', draft: { ...empty } });

  const startEdit = (p: Provider) =>
    setEditState({
      kind: 'edit',
      id: p.id,
      draft: {
        kind: p.kind as ProviderKind,
        label: p.label,
        base_url: p.base_url,
        key: '',
        showKey: false,
      },
    });

  const cancelEdit = () => setEditState({ kind: 'idle' });

  const onSubmitDraft = async () => {
    if (editState.kind === 'idle') return;
    const draft = editState.draft;
    const payload: ProviderInput = {
      kind: draft.kind,
      label: draft.label.trim() || labelFromKind(draft.kind),
      base_url: draft.base_url.trim(),
      // Empty string → "leave existing" on edit; required on create.
      key: editState.kind === 'add' ? draft.key.trim() : draft.key.trim() ? draft.key.trim() : '',
    };
    if (editState.kind === 'add' && !payload.key) {
      setTopStatus({ kind: 'err', message: 'Add a key to create a provider.' });
      return;
    }
    setTopStatus({ kind: 'busy', message: 'Saving provider…' });
    try {
      const saved =
        editState.kind === 'add'
          ? await createProvider(payload)
          : await updateProvider(editState.id, payload);
      setProviders((prev) => {
        const idx = prev.findIndex((p) => p.id === saved.id);
        if (idx < 0) return [...prev, saved];
        const copy = prev.slice();
        copy[idx] = saved;
        return copy;
      });
      setEditState({ kind: 'idle' });
      setTopStatus({ kind: 'ok', message: 'Provider saved' });
      window.setTimeout(() => setTopStatus({ kind: 'idle' }), 1500);
      // Auto-refresh models if we just got a key.
      if (saved.has_key && saved.models.length === 0) {
        await onRefreshModels(saved.id);
      }
    } catch (err) {
      setTopStatus({ kind: 'err', message: (err as Error).message });
    }
  };

  const onDelete = async (p: Provider) => {
    if (!window.confirm(`Delete "${p.label}"? This cannot be undone.`)) return;
    setRow(p.id, { kind: 'busy', message: 'Deleting…' });
    try {
      await deleteProvider(p.id);
      setProviders((prev) => prev.filter((x) => x.id !== p.id));
      // If this provider was assigned to a role, clear those.
      if (settings.text_provider_id === p.id || settings.vision_provider_id === p.id) {
        const next: AIRoleSettings = {
          text_provider_id: settings.text_provider_id === p.id ? null : settings.text_provider_id,
          text_model: settings.text_provider_id === p.id ? '' : settings.text_model,
          vision_provider_id:
            settings.vision_provider_id === p.id ? null : settings.vision_provider_id,
          vision_model: settings.vision_provider_id === p.id ? '' : settings.vision_model,
        };
        const saved = await saveSettings(next);
        setSettings(saved);
      }
    } catch (err) {
      setRow(p.id, { kind: 'err', message: (err as Error).message });
    }
  };

  const onTest = async (id: string) => {
    setRow(id, { kind: 'busy', message: 'Testing…' });
    try {
      const r = await testProvider(id);
      setRow(id, {
        kind: 'ok',
        message: `Connected · model "${r.model}" replied "${(r.reply || '').slice(0, 24)}"`,
      });
    } catch (err) {
      setRow(id, { kind: 'err', message: (err as Error).message });
    }
  };

  const onRefreshModels = async (id: string) => {
    setRow(id, { kind: 'busy', message: 'Refreshing models…' });
    try {
      const { models } = await refreshModels(id);
      setProviders((prev) =>
        prev.map((p) =>
          p.id === id
            ? { ...p, models, models_cached_at: new Date().toISOString() }
            : p,
        ),
      );
      setRow(id, { kind: 'ok', message: `Loaded ${models.length} model${models.length === 1 ? '' : 's'}` });
    } catch (err) {
      setRow(id, { kind: 'err', message: (err as Error).message });
    }
  };

  const optionsByProvider = useMemo(
    () =>
      providers.filter((p) => p.has_key && p.models.length > 0).map((p) => ({
        id: p.id,
        label: p.label,
        kind: p.kind,
        models: p.models,
      })),
    [providers],
  );

  // --- render ---------------------------------------------------------

  return (
    <div className="card p-5 grid gap-3 grid-cols-1 sm:[grid-template-columns:220px_1fr]">
      <div>
        <div className="eyebrow mb-1.5">AI providers</div>
        <p style={{ margin: 0, fontSize: 12, color: 'var(--text-3)', lineHeight: 1.55 }}>
          Bring your own provider — Anthropic, OpenAI, or any compatible endpoint.
        </p>
        <p style={{ margin: '8px 0 0', fontSize: 11.5, color: 'var(--text-4)', lineHeight: 1.5 }}>
          Used for resume import, bullet polish, ATS quality grading, and JD-aware tailoring.
          Keys are encrypted before storage and never shown back to you.
        </p>
      </div>

      <div className="flex flex-col gap-4">
        {loading ? (
          <div style={{ fontSize: 12, color: 'var(--text-3)' }}>Loading…</div>
        ) : (
          <>
            {/* Roles */}
            <div className="flex flex-col gap-2">
              <div className="eyebrow" style={{ fontSize: 9.5 }}>
                Active models
              </div>
              <div
                className="grid gap-3"
                style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))' }}
              >
                <RolePicker
                  label="Text model"
                  hint="Powers import, improve, ATS, and tailor."
                  value={
                    settings.text_provider_id && settings.text_model
                      ? `${settings.text_provider_id}::${settings.text_model}`
                      : ''
                  }
                  onChange={(v) => onPickRole('text', v)}
                  options={optionsByProvider}
                  emptyHint={
                    optionsByProvider.length === 0
                      ? 'Add a provider below to enable.'
                      : undefined
                  }
                />
                <RolePicker
                  label="Vision model (optional)"
                  hint="Reserved for future image-first imports."
                  value={
                    settings.vision_provider_id && settings.vision_model
                      ? `${settings.vision_provider_id}::${settings.vision_model}`
                      : ''
                  }
                  onChange={(v) => onPickRole('vision', v)}
                  options={optionsByProvider}
                  emptyHint={
                    optionsByProvider.length === 0
                      ? 'Add a vision-capable provider below.'
                      : undefined
                  }
                />
              </div>
              <TopStatus s={topStatus} />
            </div>

            {/* Provider list */}
            <div className="flex flex-col gap-2">
              <div className="flex items-center justify-between">
                <div className="eyebrow" style={{ fontSize: 9.5 }}>
                  Configured providers
                </div>
                <button
                  type="button"
                  onClick={startAdd}
                  style={btn('outline')}
                  disabled={editState.kind !== 'idle'}
                >
                  <Plus size={12} strokeWidth={1.8} /> Add provider
                </button>
              </div>

              {providers.length === 0 ? (
                <div
                  className="card"
                  style={{
                    padding: 16,
                    border: '1px dashed var(--border)',
                    background: 'var(--bg-sunken)',
                    color: 'var(--text-3)',
                    fontSize: 12,
                  }}
                >
                  No providers yet — add one to enable AI features.
                </div>
              ) : (
                <div className="flex flex-col gap-1.5">
                  {providers.map((p) => (
                    <ProviderRow
                      key={p.id}
                      provider={p}
                      status={perRow[p.id]}
                      onTest={() => onTest(p.id)}
                      onRefresh={() => onRefreshModels(p.id)}
                      onEdit={() => startEdit(p)}
                      onDelete={() => onDelete(p)}
                      isAssigned={
                        settings.text_provider_id === p.id ||
                        settings.vision_provider_id === p.id
                      }
                    />
                  ))}
                </div>
              )}

              {editState.kind !== 'idle' && (
                <ProviderForm
                  draft={editState.draft}
                  onChange={(next) =>
                    setEditState((cur) =>
                      cur.kind === 'idle' ? cur : { ...cur, draft: next },
                    )
                  }
                  isEdit={editState.kind === 'edit'}
                  hasExistingKey={
                    editState.kind === 'edit'
                      ? Boolean(providers.find((p) => p.id === editState.id)?.has_key)
                      : false
                  }
                  onSubmit={onSubmitDraft}
                  onCancel={cancelEdit}
                />
              )}
            </div>
          </>
        )}
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
//                              Sub-components
// ---------------------------------------------------------------------------

function RolePicker({
  label,
  hint,
  value,
  onChange,
  options,
  emptyHint,
}: {
  label: string;
  hint: string;
  value: string;
  onChange: (v: string) => void;
  options: { id: string; label: string; kind: string; models: string[] }[];
  emptyHint?: string;
}) {
  return (
    <label className="flex flex-col gap-1.5">
      <span className="eyebrow" style={{ fontSize: 9.5 }}>
        {label}
      </span>
      <select
        value={value}
        onChange={(e) => onChange(e.target.value)}
        disabled={options.length === 0}
        aria-label={label}
        style={{
          padding: '8px 10px',
          background: 'var(--bg-elev)',
          boxShadow: 'inset 0 0 0 1px var(--border-strong)',
          borderRadius: 'var(--radius)',
          border: 0,
          fontSize: 12.5,
          color: 'var(--text)',
          outline: 'none',
          width: '100%',
          opacity: options.length === 0 ? 0.6 : 1,
        }}
      >
        <option value="">— Not set —</option>
        {options.map((p) => (
          <optgroup key={p.id} label={`${p.label} · ${p.kind}`}>
            {p.models.map((m) => (
              <option key={m} value={`${p.id}::${m}`}>
                {m}
              </option>
            ))}
          </optgroup>
        ))}
      </select>
      <span style={{ fontSize: 10.5, color: 'var(--text-4)', lineHeight: 1.45 }}>
        {emptyHint ?? hint}
      </span>
    </label>
  );
}

function ProviderRow({
  provider,
  status,
  onTest,
  onRefresh,
  onEdit,
  onDelete,
  isAssigned,
}: {
  provider: Provider;
  status?: Status;
  onTest: () => void;
  onRefresh: () => void;
  onEdit: () => void;
  onDelete: () => void;
  isAssigned: boolean;
}) {
  const kindLabel = KINDS.find((k) => k.id === provider.kind)?.label ?? provider.kind;
  return (
    <div
      className="card"
      style={{
        padding: 12,
        display: 'flex',
        flexDirection: 'column',
        gap: 8,
      }}
    >
      <div className="flex items-start justify-between gap-3 flex-wrap">
        <div style={{ minWidth: 0, flex: 1 }}>
          <div className="flex items-center gap-2 flex-wrap">
            <span
              className="pill"
              style={{
                fontSize: 9.5,
                padding: '2px 8px',
                background: 'var(--bg-sunken)',
                color: 'var(--text-2)',
                boxShadow: 'inset 0 0 0 1px var(--border)',
                letterSpacing: '0.06em',
                textTransform: 'uppercase',
              }}
            >
              {kindLabel}
            </span>
            <span style={{ fontSize: 13, fontWeight: 500 }}>{provider.label}</span>
            {isAssigned && (
              <span
                className="pill"
                style={{
                  fontSize: 9.5,
                  padding: '2px 8px',
                  background: 'var(--accent)',
                  color: 'var(--bg-elev)',
                  letterSpacing: '0.06em',
                }}
              >
                in use
              </span>
            )}
          </div>
          <div
            className="mono"
            style={{
              fontSize: 10.5,
              color: 'var(--text-4)',
              marginTop: 2,
              wordBreak: 'break-all',
            }}
          >
            {provider.base_url || '—'}
          </div>
          <div
            style={{ fontSize: 11, color: 'var(--text-3)', marginTop: 4 }}
          >
            {provider.has_key ? (
              <>
                Key on file ·{' '}
                {provider.models.length === 0
                  ? <span style={{ color: 'var(--ochre)' }}>no models loaded</span>
                  : `${provider.models.length} model${provider.models.length === 1 ? '' : 's'} cached`}
              </>
            ) : (
              <span style={{ color: 'var(--plum)' }}>No key set</span>
            )}
          </div>
        </div>
        <div className="flex items-center gap-1">
          <button type="button" style={btn('outline')} onClick={onTest} disabled={!provider.has_key}>
            <Wand2 size={12} strokeWidth={1.7} /> Test
          </button>
          <button type="button" style={btn('outline')} onClick={onRefresh} disabled={!provider.has_key}>
            <RefreshCcw size={12} strokeWidth={1.7} /> Refresh
          </button>
          <button type="button" style={btn('outline')} onClick={onEdit}>
            <Pencil size={12} strokeWidth={1.7} /> Edit
          </button>
          <button
            type="button"
            style={{ ...btn('outline'), color: 'var(--plum)' }}
            onClick={onDelete}
          >
            <Trash2 size={12} strokeWidth={1.7} />
          </button>
        </div>
      </div>
      <RowStatus s={status} />
    </div>
  );
}

function ProviderForm({
  draft,
  onChange,
  isEdit,
  hasExistingKey,
  onSubmit,
  onCancel,
}: {
  draft: DraftProvider;
  onChange: (next: DraftProvider) => void;
  isEdit: boolean;
  hasExistingKey: boolean;
  onSubmit: () => void;
  onCancel: () => void;
}) {
  const meta = KINDS.find((k) => k.id === draft.kind) ?? KINDS[0];
  const setKind = (k: ProviderKind) => {
    const fresh: DraftProvider = {
      ...draft,
      kind: k,
      label: draft.label || labelFromKind(k),
    };
    onChange(fresh);
  };

  return (
    <div
      className="card"
      style={{
        padding: 14,
        display: 'flex',
        flexDirection: 'column',
        gap: 10,
        background: 'var(--bg-elev)',
        boxShadow: 'inset 0 0 0 1px var(--accent)',
      }}
    >
      <div className="eyebrow" style={{ fontSize: 9.5 }}>
        {isEdit ? 'Edit provider' : 'New provider'}
      </div>

      <Field label="Provider kind">
        <div className="flex flex-wrap gap-1.5">
          {KINDS.map((k) => (
            <button
              type="button"
              key={k.id}
              onClick={() => setKind(k.id)}
              style={{
                padding: '7px 10px',
                border: 0,
                borderRadius: 'var(--radius)',
                background: draft.kind === k.id ? 'var(--accent)' : 'var(--bg-sunken)',
                color: draft.kind === k.id ? 'var(--bg-elev)' : 'var(--text-2)',
                boxShadow: draft.kind === k.id ? 'none' : 'inset 0 0 0 1px var(--border)',
                fontSize: 11.5,
                fontWeight: 500,
                cursor: 'pointer',
              }}
            >
              {k.label}
            </button>
          ))}
        </div>
      </Field>

      <Field label="Label">
        <Input
          value={draft.label}
          onChange={(v) => onChange({ ...draft, label: v })}
          placeholder={labelFromKind(draft.kind)}
        />
      </Field>

      {meta.needsBaseUrl && (
        <Field
          label="Base URL"
          hint="The endpoint root the SDK should hit. Must include the API version path (e.g. /v1)."
        >
          <Input
            value={draft.base_url}
            onChange={(v) => onChange({ ...draft, base_url: v })}
            placeholder={
              draft.kind === 'openai-compatible'
                ? 'https://api.groq.com/openai/v1'
                : 'https://api.example.com/v1'
            }
          />
          <EndpointPresets
            presets={endpointsForKind(draft.kind)}
            currentBaseUrl={draft.base_url}
            onPick={(preset) =>
              onChange({
                ...draft,
                base_url: preset.base_url,
                // Only overwrite the label if it's still the auto-generated
                // default for this kind — don't clobber a label the user
                // typed in by hand.
                label:
                  draft.label === '' || draft.label === labelFromKind(draft.kind)
                    ? preset.label
                    : draft.label,
              })
            }
          />
        </Field>
      )}

      <Field
        label="API key"
        hint={
          isEdit && hasExistingKey
            ? 'Leave blank to keep the existing key.'
            : `Format: ${meta.example}`
        }
      >
        <div className="flex items-center gap-2">
          <input
            type={draft.showKey ? 'text' : 'password'}
            value={draft.key}
            onChange={(e) => onChange({ ...draft, key: e.target.value })}
            placeholder={isEdit && hasExistingKey ? '•••••••• (kept)' : meta.example}
            autoComplete="off"
            spellCheck={false}
            style={inputStyle}
          />
          <button
            type="button"
            onClick={() => onChange({ ...draft, showKey: !draft.showKey })}
            aria-label={draft.showKey ? 'Hide key' : 'Show key'}
            style={btn('outline')}
          >
            {draft.showKey ? (
              <EyeOff size={12} strokeWidth={1.7} />
            ) : (
              <Eye size={12} strokeWidth={1.7} />
            )}
          </button>
        </div>
      </Field>

      <div className="flex items-center gap-2">
        <button type="button" style={btn('primary')} onClick={onSubmit}>
          Save
        </button>
        <button type="button" style={btn('outline')} onClick={onCancel}>
          Cancel
        </button>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
//                                Primitives
// ---------------------------------------------------------------------------

function EndpointPresets({
  presets,
  currentBaseUrl,
  onPick,
}: {
  presets: EndpointPreset[];
  currentBaseUrl: string;
  onPick: (p: EndpointPreset) => void;
}) {
  if (presets.length === 0) return null;
  return (
    <div className="flex flex-col gap-1">
      <span
        className="eyebrow"
        style={{ fontSize: 9, color: 'var(--text-4)', marginTop: 2 }}
      >
        Quick fill
      </span>
      <div className="flex flex-wrap gap-1.5">
        {presets.map((p) => {
          const active = currentBaseUrl.trim() === p.base_url;
          return (
            <button
              key={p.id}
              type="button"
              onClick={() => onPick(p)}
              title={p.hint ?? p.base_url}
              style={{
                padding: '4px 8px',
                border: 0,
                borderRadius: 999,
                background: active ? 'var(--accent)' : 'var(--bg-sunken)',
                color: active ? 'var(--bg-elev)' : 'var(--text-2)',
                boxShadow: active ? 'none' : 'inset 0 0 0 1px var(--border)',
                fontSize: 10.5,
                fontWeight: 500,
                cursor: 'pointer',
                lineHeight: 1.3,
              }}
            >
              {p.label}
            </button>
          );
        })}
      </div>
    </div>
  );
}

function Field({
  label,
  hint,
  children,
}: {
  label: string;
  hint?: string;
  children: React.ReactNode;
}) {
  return (
    <label className="flex flex-col gap-1.5">
      <span className="eyebrow" style={{ fontSize: 9.5 }}>
        {label}
      </span>
      {children}
      {hint && (
        <span style={{ fontSize: 10.5, color: 'var(--text-4)', lineHeight: 1.45 }}>{hint}</span>
      )}
    </label>
  );
}

const inputStyle: React.CSSProperties = {
  flex: 1,
  padding: '8px 10px',
  background: 'var(--bg-elev)',
  boxShadow: 'inset 0 0 0 1px var(--border-strong)',
  borderRadius: 'var(--radius)',
  border: 0,
  fontSize: 12.5,
  color: 'var(--text)',
  outline: 'none',
};

function Input({
  value,
  onChange,
  placeholder,
}: {
  value: string;
  onChange: (v: string) => void;
  placeholder?: string;
}) {
  return (
    <input
      value={value}
      onChange={(e) => onChange(e.target.value)}
      placeholder={placeholder}
      autoComplete="off"
      spellCheck={false}
      style={inputStyle}
    />
  );
}

function btn(kind: 'primary' | 'outline'): React.CSSProperties {
  if (kind === 'primary') {
    return {
      padding: '7px 14px',
      borderRadius: 'var(--radius)',
      border: 0,
      background: 'var(--accent)',
      color: 'var(--bg-elev)',
      fontSize: 12,
      fontWeight: 500,
      cursor: 'pointer',
      display: 'inline-flex',
      alignItems: 'center',
      gap: 5,
    };
  }
  return {
    padding: '6px 10px',
    borderRadius: 'var(--radius)',
    border: 0,
    background: 'transparent',
    boxShadow: 'inset 0 0 0 1px var(--border-strong)',
    color: 'var(--text-2)',
    fontSize: 11.5,
    fontWeight: 500,
    cursor: 'pointer',
    display: 'inline-flex',
    alignItems: 'center',
    gap: 5,
  };
}

function TopStatus({ s }: { s: Status }) {
  if (s.kind === 'idle') return null;
  const color =
    s.kind === 'err' ? 'var(--plum)' : s.kind === 'busy' ? 'var(--text-3)' : 'var(--forest)';
  return (
    <span style={{ fontSize: 11, color }}>{s.message}</span>
  );
}

function RowStatus({ s }: { s?: Status }) {
  if (!s || s.kind === 'idle') return null;
  const color =
    s.kind === 'err' ? 'var(--plum)' : s.kind === 'busy' ? 'var(--text-3)' : 'var(--forest)';
  return (
    <span style={{ fontSize: 11, color, marginTop: 2 }}>{s.message}</span>
  );
}

function labelFromKind(kind: ProviderKind): string {
  switch (kind) {
    case 'anthropic':
      return 'Anthropic';
    case 'openai':
      return 'OpenAI';
    case 'openai-compatible':
      return 'Custom';
    case 'anthropic-compatible':
      return 'Custom Anthropic';
  }
}
