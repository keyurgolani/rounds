import { NavLink } from 'react-router-dom';
import type { CSSProperties } from 'react';

export type GuideNavItem = { slug: string; label: string };
export type GuideNavGroup = { label: string; items: GuideNavItem[] };

type Props = {
  groups: GuideNavGroup[];
  trackBasePath: string;
  orientation: 'vertical' | 'horizontal';
};

export default function GuideNav({ groups, trackBasePath, orientation }: Props) {
  if (orientation === 'horizontal') {
    return <HorizontalNav groups={groups} trackBasePath={trackBasePath} />;
  }
  return <VerticalNav groups={groups} trackBasePath={trackBasePath} />;
}

function VerticalNav({
  groups,
  trackBasePath,
}: Omit<Props, 'orientation'>) {
  return (
    <nav aria-label="Study center pages" className="grid" style={{ gap: 'var(--gap-md)' }}>
      {groups.map((group) => (
        <div key={group.label} className="grid" style={{ gap: 'var(--gap-sm)' }}>
          <div className="eyebrow">{group.label}</div>
          {/* gap: 4 — tighter than --gap-sm so multi-item groups stay compact */}
          <ul className="grid list-none p-0 m-0" style={{ gap: 4 }}>
            {group.items.map((item) => (
              <li key={item.slug}>
                <RailLink to={hrefFor(trackBasePath, item.slug)} label={item.label} />
              </li>
            ))}
          </ul>
        </div>
      ))}
    </nav>
  );
}

function HorizontalNav({
  groups,
  trackBasePath,
}: Omit<Props, 'orientation'>) {
  // Groups are intentionally flattened in the horizontal pill row; the small
  // mobile/sub-xl layout has no room for group headers.
  const flat = groups.flatMap((g) => g.items);
  return (
    <nav
      aria-label="Study center pages"
      className="flex"
      style={{
        gap: 'var(--gap-sm)',
        overflowX: 'auto',
        paddingBottom: 6, // scrollbar clearance for browsers that render one
      }}
    >
      {flat.map((item) => (
        <PillLink key={item.slug} to={hrefFor(trackBasePath, item.slug)} label={item.label} />
      ))}
    </nav>
  );
}

function hrefFor(basePath: string, slug: string) {
  return slug === '' ? basePath : `${basePath}/${slug}`;
}

const RAIL_LINK_BASE: CSSProperties = {
  display: 'block',
  padding: 'var(--pad-xs) var(--pad-sm)',
  borderRadius: 'var(--radius)',
  fontSize: 13,
  textDecoration: 'none',
  transition: 'background 160ms ease, box-shadow 160ms ease, color 160ms ease',
};

function RailLink({ to, label }: { to: string; label: string }) {
  return (
    <NavLink
      to={to}
      end
      style={({ isActive }) => ({
        ...RAIL_LINK_BASE,
        color: isActive ? 'var(--text)' : 'var(--text-3)',
        background: isActive ? 'var(--accent-soft)' : 'transparent',
        boxShadow: isActive
          ? 'inset 3px 0 0 var(--accent)'
          : 'inset 3px 0 0 transparent',
        fontWeight: isActive ? 600 : 400,
      })}
    >
      {label}
    </NavLink>
  );
}

const PILL_LINK_BASE: CSSProperties = {
  display: 'inline-flex',
  alignItems: 'center',
  padding: '6px var(--pad-sm)',
  borderRadius: 999,
  fontSize: 12.5,
  textDecoration: 'none',
  whiteSpace: 'nowrap',
};

function PillLink({ to, label }: { to: string; label: string }) {
  return (
    <NavLink
      to={to}
      end
      style={({ isActive }) => ({
        ...PILL_LINK_BASE,
        color: isActive ? 'var(--accent)' : 'var(--text-2)',
        background: isActive ? 'var(--accent-soft)' : 'var(--bg-elev)',
        boxShadow: `inset 0 0 0 1px ${isActive ? 'var(--accent)' : 'var(--border)'}`,
        fontWeight: isActive ? 600 : 400,
      })}
    >
      {label}
    </NavLink>
  );
}
