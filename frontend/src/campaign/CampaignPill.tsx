import { useEffect, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Check, ChevronDown, Layers, Plus } from 'lucide-react';
import { useCampaign } from './CampaignContext';
import type { Campaign } from './types';

interface Props {
  compact?: boolean;
  // Where to anchor the popover menu relative to the trigger.
  align?: 'left' | 'right';
  // Placement "down" puts the popover below the trigger (default,
  // topbar). "up" opens above — used in the sidebar where the pill
  // sits near the bottom of the screen and the menu would otherwise
  // clip off.
  placement?: 'down' | 'up';
  // Emphasise the label ("Campaign · Name") so users understand what
  // the control does. Enabled by default.
  showRole?: boolean;
  // Fill the trigger to the container's width.
  fullWidth?: boolean;
}

export default function CampaignPill({
  compact = false,
  align = 'left',
  placement = 'down',
  showRole = true,
  fullWidth = false,
}: Props) {
  const { campaigns, currentId, currentCampaign, setCurrent, ready } = useCampaign();
  const [open, setOpen] = useState(false);
  const anchorRef = useRef<HTMLDivElement>(null);
  const navigate = useNavigate();

  useEffect(() => {
    function onDocClick(e: MouseEvent) {
      if (!anchorRef.current?.contains(e.target as Node)) setOpen(false);
    }
    function onKey(e: KeyboardEvent) {
      if (e.key === 'Escape' && open) setOpen(false);
    }
    document.addEventListener('mousedown', onDocClick);
    document.addEventListener('keydown', onKey);
    return () => {
      document.removeEventListener('mousedown', onDocClick);
      document.removeEventListener('keydown', onKey);
    };
  }, [open]);

  if (!ready || campaigns.length === 0) {
    return null;
  }

  const label = currentCampaign ? currentCampaign.name : 'All active';
  const active = campaigns.filter((c) => c.status === 'active');
  const accent = 'var(--accent)';

  return (
    <div
      ref={anchorRef}
      style={{ position: 'relative', width: fullWidth ? '100%' : undefined }}
    >
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        aria-label={`Campaign: ${label}. Click to switch.`}
        aria-haspopup="listbox"
        aria-expanded={open}
        className="flex items-center gap-2"
        style={{
          width: fullWidth ? '100%' : undefined,
          padding: compact ? '7px 10px' : '8px 12px',
          borderRadius: 'var(--radius)',
          border: '1px solid var(--border)',
          background: open ? 'var(--bg-sunken)' : 'var(--bg-elev)',
          color: 'var(--text)',
          fontSize: 12.5,
          fontWeight: 500,
          cursor: 'pointer',
          textAlign: 'left',
          fontFamily: 'inherit',
          boxShadow: 'var(--shadow-flat)',
        }}
      >
        <CampaignSwatch campaign={currentCampaign} />
        <span className="flex flex-col min-w-0" style={{ flex: 1 }}>
          {showRole && (
            <span
              className="eyebrow"
              style={{
                fontSize: 9,
                color: 'var(--text-4)',
                letterSpacing: '0.12em',
                lineHeight: 1,
                marginBottom: 2,
              }}
            >
              CAMPAIGN
            </span>
          )}
          <span
            style={{
              whiteSpace: 'nowrap',
              overflow: 'hidden',
              textOverflow: 'ellipsis',
              lineHeight: 1.2,
            }}
          >
            {label}
          </span>
        </span>
        <ChevronDown
          size={12}
          strokeWidth={1.8}
          style={{
            color: 'var(--text-4)',
            transform: open ? 'rotate(180deg)' : undefined,
            transition: 'transform 120ms',
            flexShrink: 0,
          }}
        />
      </button>
      {open && (
        <div
          className="card"
          role="listbox"
          style={{
            position: 'absolute',
            ...(placement === 'up'
              ? { bottom: 'calc(100% + 6px)' }
              : { top: 'calc(100% + 6px)' }),
            ...(align === 'right' ? { right: 0 } : { left: 0 }),
            minWidth: 260,
            maxWidth: 320,
            boxShadow: 'var(--shadow-elev)',
            padding: 6,
            zIndex: 80,
            background: 'var(--bg-elev)',
          }}
        >
          <ListHeader text="Switch campaign" />
          <CampaignOption
            swatch={<AllDot />}
            label="All active (rollup)"
            sub={`${active.length} active campaign${active.length === 1 ? '' : 's'}`}
            selected={currentId === null}
            onClick={() => {
              setCurrent(null);
              setOpen(false);
            }}
          />
          {active.length > 0 && (
            <>
              <Divider />
              <ListHeader text="Active" />
              {active.map((c) => (
                <CampaignOption
                  key={c.id}
                  swatch={<CampaignSwatch campaign={c} />}
                  label={c.name}
                  sub={c.target_role_level || '—'}
                  selected={currentId === c.id}
                  onClick={() => {
                    setCurrent(c.id);
                    setOpen(false);
                  }}
                />
              ))}
            </>
          )}
          {campaigns.some((c) => c.status !== 'active') && (
            <>
              <Divider />
              <ListHeader text="Other" />
              {campaigns
                .filter((c) => c.status !== 'active')
                .map((c) => (
                  <CampaignOption
                    key={c.id}
                    swatch={<CampaignSwatch campaign={c} />}
                    label={c.name}
                    sub={c.status}
                    selected={currentId === c.id}
                    onClick={() => {
                      setCurrent(c.id);
                      setOpen(false);
                    }}
                  />
                ))}
            </>
          )}
          <Divider />
          <ActionRow
            Icon={Layers}
            label="Manage campaigns"
            onClick={() => {
              setOpen(false);
              navigate('/campaigns');
            }}
          />
          <ActionRow
            Icon={Plus}
            label="New campaign"
            onClick={() => {
              setOpen(false);
              navigate('/campaigns?new=1');
            }}
            accent
          />
        </div>
      )}
      {/* Hint swatch variable for static analyzers */}
      <span aria-hidden style={{ display: 'none' }}>{accent}</span>
    </div>
  );
}

function CampaignSwatch({ campaign }: { campaign: Campaign | null }) {
  if (!campaign) return <AllDot />;
  const color = campaignColor(campaign.color);
  return (
    <span
      aria-hidden
      style={{
        width: 18,
        height: 18,
        borderRadius: 999,
        background: color.soft,
        display: 'inline-flex',
        alignItems: 'center',
        justifyContent: 'center',
        flexShrink: 0,
      }}
    >
      <span
        style={{
          width: 8,
          height: 8,
          borderRadius: 999,
          background: color.strong,
        }}
      />
    </span>
  );
}

function AllDot() {
  return (
    <span
      aria-hidden
      style={{
        width: 18,
        height: 18,
        borderRadius: 999,
        display: 'inline-flex',
        alignItems: 'center',
        justifyContent: 'center',
        border: '1px dashed var(--border-strong)',
        flexShrink: 0,
      }}
    >
      <span
        style={{
          width: 6,
          height: 6,
          borderRadius: 999,
          background: 'var(--text-4)',
        }}
      />
    </span>
  );
}

function campaignColor(key: string | undefined): { soft: string; strong: string } {
  switch (key) {
    case 'forest':
      return { soft: 'var(--forest-soft)', strong: 'var(--forest)' };
    case 'plum':
      return { soft: 'var(--plum-soft)', strong: 'var(--plum)' };
    case 'ochre':
      return { soft: 'var(--ochre-soft, var(--bg-sunken))', strong: 'var(--ochre)' };
    case 'ink':
      return { soft: 'var(--bg-sunken)', strong: 'var(--ink)' };
    case 'accent':
    default:
      return { soft: 'var(--accent-soft)', strong: 'var(--accent)' };
  }
}

function CampaignOption({
  swatch,
  label,
  sub,
  selected,
  onClick,
}: {
  swatch: React.ReactNode;
  label: string;
  sub: string;
  selected: boolean;
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      role="option"
      aria-selected={selected}
      className="flex items-center gap-2 w-full"
      style={{
        padding: '8px 10px',
        border: 0,
        background: selected ? 'var(--bg-sunken)' : 'transparent',
        color: 'var(--text)',
        cursor: 'pointer',
        borderRadius: 'var(--radius)',
        textAlign: 'left',
        fontFamily: 'inherit',
      }}
      onMouseEnter={(e) => {
        if (!selected) e.currentTarget.style.background = 'var(--bg-sunken)';
      }}
      onMouseLeave={(e) => {
        if (!selected) e.currentTarget.style.background = 'transparent';
      }}
    >
      {swatch}
      <span className="flex flex-col" style={{ minWidth: 0, flex: 1 }}>
        <span
          style={{
            fontSize: 13,
            fontWeight: selected ? 500 : 400,
            whiteSpace: 'nowrap',
            overflow: 'hidden',
            textOverflow: 'ellipsis',
          }}
        >
          {label}
        </span>
        {sub && (
          <span
            className="mono"
            style={{
              fontSize: 10.5,
              color: 'var(--text-4)',
              letterSpacing: '0.04em',
              whiteSpace: 'nowrap',
              overflow: 'hidden',
              textOverflow: 'ellipsis',
            }}
          >
            {sub}
          </span>
        )}
      </span>
      {selected && (
        <Check size={13} strokeWidth={2} style={{ color: 'var(--accent)', flexShrink: 0 }} />
      )}
    </button>
  );
}

function ActionRow({
  Icon,
  label,
  onClick,
  accent,
}: {
  Icon: (p: { size?: number; strokeWidth?: number }) => React.ReactNode;
  label: string;
  onClick: () => void;
  accent?: boolean;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className="flex items-center gap-2 w-full"
      style={{
        padding: '8px 10px',
        border: 0,
        background: 'transparent',
        color: accent ? 'var(--accent)' : 'var(--text-2)',
        cursor: 'pointer',
        borderRadius: 'var(--radius)',
        fontSize: 12.5,
        textAlign: 'left',
        fontFamily: 'inherit',
        fontWeight: accent ? 500 : 400,
      }}
      onMouseEnter={(e) => {
        e.currentTarget.style.background = 'var(--bg-sunken)';
      }}
      onMouseLeave={(e) => {
        e.currentTarget.style.background = 'transparent';
      }}
    >
      <Icon size={13} strokeWidth={1.7} />
      {label}
    </button>
  );
}

function ListHeader({ text }: { text: string }) {
  return (
    <div
      className="eyebrow"
      style={{ padding: '6px 10px 2px', letterSpacing: '0.08em', fontSize: 9.5 }}
    >
      {text}
    </div>
  );
}

function Divider() {
  return <div style={{ height: 1, margin: '4px 8px', background: 'var(--border)' }} />;
}

export type { Campaign };
