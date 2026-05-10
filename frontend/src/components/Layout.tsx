import { NavLink, Link, Outlet, useLocation, useNavigate } from 'react-router-dom';
import { useEffect, useRef, useState, type ReactNode } from 'react';
import {
  Briefcase,
  ChevronLeft,
  ChevronRight,
  ChevronUp,
  ChevronDown,
  LogOut,
  Menu,
  Settings2,
  UserRound,
  X,
} from 'lucide-react';
import { RoundsLockup, RoundsMark } from './Logo';
import {
  AIGlyph,
  AppsGlyph,
  BehaviorGlyph,
  CalendarGlyph,
  CodeGlyph,
  DashGlyph,
  ResumeGlyph,
  SystemGlyph,
  TodoGlyph,
} from './shell/Glyphs';
import { useTheme } from '../theme/ThemeProvider';
import { initials, useAuth } from '../auth/AuthProvider';
import CampaignPill from '../campaign/CampaignPill';
import { CommandCenterProvider } from '../command-center/CommandCenterProvider';
import { CommandCenter } from '../command-center/CommandCenter';
import { usePlatform } from '../hooks/usePlatform';

type NavDef = {
  path: string;
  label: string;
  glyph: (p: { size?: number }) => ReactNode;
  comingSoon?: boolean;
};

type PracticeNavGroup = {
  basePath: string;
  label: string;
  shortLabel: string;
  glyph: (p: { size?: number }) => ReactNode;
  children: Array<Pick<NavDef, 'path' | 'label' | 'comingSoon'>>;
};

const primaryNav: NavDef[] = [
  { path: '/dashboard', label: 'Today', glyph: DashGlyph },
];

const practiceNav: PracticeNavGroup[] = [
  {
    basePath: '/system-design',
    label: 'System Design',
    shortLabel: 'System',
    glyph: SystemGlyph,
    children: [
      { path: '/system-design/guide', label: 'Guide' },
      { path: '/system-design/questions', label: 'Problem List' },
    ],
  },
  {
    basePath: '/coding',
    label: 'Coding',
    shortLabel: 'Coding',
    glyph: CodeGlyph,
    children: [
      { path: '/coding/guide', label: 'Guide' },
      { path: '/coding/questions', label: 'Problem List' },
    ],
  },
  {
    basePath: '/ai-coding',
    label: 'AI Assisted Coding',
    shortLabel: 'AI Coding',
    glyph: AIGlyph,
    children: [
      { path: '/ai-coding', label: 'Rounds' },
    ],
  },
  {
    basePath: '/take-home',
    label: 'Take-Home Assignments',
    shortLabel: 'Take-Home',
    glyph: AIGlyph,
    children: [
      { path: '/take-home', label: 'Assignments' },
    ],
  },
  {
    basePath: '/behavioral',
    label: 'Behavioral',
    shortLabel: 'Behavioral',
    glyph: BehaviorGlyph,
    children: [
      { path: '/behavioral/guide', label: 'Guide' },
      { path: '/behavioral/questions', label: 'Problem List' },
    ],
  },
];

const trackingNav: NavDef[] = [
  { path: '/applications', label: 'Applications', glyph: AppsGlyph },
  { path: '/interviews', label: 'Interviews', glyph: CalendarGlyph },
  { path: '/todos', label: 'Todos', glyph: TodoGlyph },
  { path: '/resumes', label: 'Resumes', glyph: ResumeGlyph },
];

export default function Layout() {
  const location = useLocation();
  const { navStyle } = useTheme();
  const [collapsed, setCollapsed] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);

  useEffect(() => {
    setMobileOpen(false);
  }, [location.pathname]);

  const topbar = navStyle === 'topbar';

  return (
    <CommandCenterProvider>
    <div
      className={topbar ? 'h-dvh flex flex-col overflow-hidden' : 'h-dvh flex overflow-hidden'}
      style={{ background: 'transparent' }}
    >
      {topbar ? (
        <TopBar />
      ) : (
        <>
          {mobileOpen && (
            <button
              type="button"
              aria-label="Close menu"
              onClick={() => setMobileOpen(false)}
              className="lg:hidden fixed inset-0 z-30"
              style={{ background: 'rgba(0,0,0,0.35)' }}
            />
          )}

          <aside
            className={`
              fixed inset-y-0 left-0 z-40 flex flex-col
              transition-[transform,width] duration-200 ease-out
              ${mobileOpen ? 'translate-x-0' : '-translate-x-full'}
              lg:translate-x-0 lg:relative lg:flex-shrink-0
              ${collapsed ? 'lg:w-[64px]' : 'lg:w-[232px]'}
              w-[260px]
            `}
            style={{
              background: 'var(--bg)',
              borderRight: '1px solid var(--border)',
            }}
          >
            <Link
              to="/dashboard"
              aria-label="Rounds · Dashboard"
              className="flex items-center h-[60px] flex-shrink-0"
              style={{
                borderBottom: '1px solid var(--border)',
                padding: collapsed ? '0 0 0 18px' : '0 16px',
                textDecoration: 'none',
              }}
            >
              {collapsed ? <RoundsMark size={28} /> : <RoundsLockup markSize={24} textSize={22} />}
            </Link>

            <nav className="flex-1 overflow-y-auto py-2.5 px-2.5 flex flex-col gap-0.5">
              {primaryNav.map((item) => (
                <NavRow key={item.path} item={item} collapsed={collapsed} />
              ))}

              {!collapsed ? (
                <div className="eyebrow px-3 pt-3.5 pb-1" style={{ fontSize: 9.5 }}>
                  Practice
                </div>
              ) : (
                <div
                  style={{
                    height: 1,
                    margin: '8px 10px',
                    background: 'var(--border)',
                  }}
                />
              )}
              {practiceNav.map((item) => (
                <PracticeGroup key={item.basePath} item={item} collapsed={collapsed} currentPath={location.pathname} />
              ))}

              <div style={{ flex: 1 }} />

              {!collapsed ? (
                <div className="eyebrow px-3 pt-3.5 pb-1" style={{ fontSize: 9.5 }}>
                  Track
                </div>
              ) : (
                <div
                  style={{
                    height: 1,
                    margin: '8px 10px',
                    background: 'var(--border)',
                  }}
                />
              )}
              {trackingNav.map((item) => (
                <NavRow key={item.path} item={item} collapsed={collapsed} />
              ))}
            </nav>

            {!collapsed && (
              <div style={{ padding: '0 12px 10px' }}>
                <CampaignPill compact placement="up" fullWidth />
              </div>
            )}

            <UserMenu collapsed={collapsed} />

            <button
              type="button"
              onClick={() => setCollapsed(!collapsed)}
              aria-label={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
              className="hidden lg:flex items-center justify-center"
              style={{
                position: 'absolute',
                left: collapsed ? 52 : 220,
                top: 72,
                width: 20,
                height: 20,
                borderRadius: 999,
                border: '1px solid var(--border-strong)',
                background: 'var(--bg-elev)',
                color: 'var(--text-3)',
                fontSize: 10,
                lineHeight: 1,
                transition: 'left 200ms ease',
                zIndex: 45,
                cursor: 'pointer',
              }}
            >
              {collapsed ? (
                <ChevronRight size={12} strokeWidth={1.8} />
              ) : (
                <ChevronLeft size={12} strokeWidth={1.8} />
              )}
            </button>

            <button
              type="button"
              onClick={() => setMobileOpen(false)}
              className="lg:hidden absolute top-3 right-3 flex items-center justify-center"
              style={{
                border: 0,
                background: 'transparent',
                color: 'var(--text-3)',
                padding: 4,
                cursor: 'pointer',
              }}
              aria-label="Close menu"
            >
              <X size={16} strokeWidth={1.8} />
            </button>
          </aside>
        </>
      )}

      <div className="flex-1 min-w-0 flex flex-col overflow-hidden">
        {!topbar && (
          <div
            className="lg:hidden flex-shrink-0 flex items-center h-[60px] px-3"
            style={{ borderBottom: '1px solid var(--border)', background: 'var(--bg)' }}
          >
            <button
              type="button"
              onClick={() => setMobileOpen(true)}
              className="p-2 -ml-2 flex items-center justify-center"
              style={{ border: 0, background: 'transparent', color: 'var(--text-2)', cursor: 'pointer' }}
              aria-label="Open menu"
            >
              <Menu size={18} strokeWidth={1.7} />
            </button>
            <Link to="/dashboard" className="ml-2" aria-label="Rounds · Dashboard" style={{ textDecoration: 'none' }}>
              <RoundsLockup markSize={20} textSize={18} />
            </Link>
          </div>
        )}

        <main className="flex-1 min-h-0 flex flex-col overflow-hidden">
          <Outlet />
        </main>
      </div>
      <CommandCenter />
    </div>
    </CommandCenterProvider>
  );
}

function NavRow({ item, collapsed }: { item: NavDef; collapsed: boolean }) {
  const Glyph = item.glyph;
  return (
    <NavLink
      to={item.path}
      title={collapsed ? item.label : undefined}
      style={({ isActive }) => ({
        display: 'flex',
        alignItems: 'center',
        justifyContent: collapsed ? 'center' : 'flex-start',
        gap: 12,
        padding: collapsed ? '10px 0' : '9px 12px',
        border: 0,
        borderRadius: 'var(--radius)',
        background: isActive ? 'var(--bg-elev)' : 'transparent',
        boxShadow: isActive ? 'inset 0 0 0 1px var(--border)' : 'none',
        color: isActive ? 'var(--text)' : 'var(--text-3)',
        fontSize: 13,
        fontWeight: isActive ? 500 : 400,
        textDecoration: 'none',
        transition: 'background 120ms, color 120ms',
      })}
    >
      {({ isActive }) => (
        <>
          <span
            className="inline-flex"
            style={{
              width: 18,
              height: 18,
              color: isActive ? 'var(--accent)' : 'var(--text-3)',
            }}
          >
            <Glyph />
          </span>
          {!collapsed && (
            <span style={{ display: 'inline-flex', alignItems: 'center', gap: 6 }}>
              {item.label}
            </span>
          )}
          {!collapsed && item.comingSoon && (
            <span
              className="mono"
              style={{
                marginLeft: 'auto',
                padding: '1px 6px',
                borderRadius: 999,
                background: 'var(--bg-sunken)',
                color: 'var(--text-4)',
                fontSize: 9,
                letterSpacing: '0.1em',
                boxShadow: 'inset 0 0 0 1px var(--border)',
              }}
            >
              SOON
            </span>
          )}
          {!collapsed && !item.comingSoon && isActive && (
            <span
              style={{
                marginLeft: 'auto',
                width: 4,
                height: 4,
                borderRadius: 999,
                background: 'var(--accent)',
              }}
            />
          )}
        </>
      )}
    </NavLink>
  );
}

function PracticeGroup({
  item,
  collapsed,
  currentPath,
}: {
  item: PracticeNavGroup;
  collapsed: boolean;
  currentPath: string;
}) {
  const Glyph = item.glyph;
  const active = currentPath === item.basePath || currentPath.startsWith(`${item.basePath}/`);

  if (collapsed) {
    return (
      <NavRow
        item={{ path: item.children[0].path, label: item.label, glyph: item.glyph, comingSoon: item.children[0].comingSoon }}
        collapsed
      />
    );
  }

  return (
    <div className="grid gap-0.5" style={{ marginTop: 2 }}>
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: 12,
          padding: '9px 12px 5px',
          color: active ? 'var(--text)' : 'var(--text-3)',
          fontSize: 13,
          fontWeight: active ? 500 : 400,
        }}
      >
        <span
          className="inline-flex"
          style={{
            width: 18,
            height: 18,
            color: active ? 'var(--accent)' : 'var(--text-3)',
          }}
        >
          <Glyph />
        </span>
        <span>{item.label}</span>
      </div>
      <div className="grid gap-0.5" style={{ marginLeft: 30 }}>
        {item.children.map((child) => (
          <NavLink
            key={child.path}
            to={child.path}
            className="relative"
            style={({ isActive }) => ({
              display: 'flex',
              alignItems: 'center',
              gap: 8,
              padding: '7px 10px',
              borderRadius: 'var(--radius)',
              background: isActive ? 'var(--bg-elev)' : 'transparent',
              boxShadow: isActive ? 'inset 0 0 0 1px var(--border)' : 'none',
              color: isActive ? 'var(--text)' : 'var(--text-4)',
              fontSize: 12.5,
              fontWeight: isActive ? 500 : 400,
              textDecoration: 'none',
              transition: 'background 120ms, color 120ms',
            })}
          >
            {({ isActive }) => (
              <>
                <span
                  style={{
                    width: 5,
                    height: 5,
                    borderRadius: 999,
                    background: isActive ? 'var(--accent)' : 'var(--border-strong)',
                    flex: '0 0 auto',
                  }}
                />
                <span>{child.label}</span>
                {child.comingSoon && (
                  <span
                    className="mono"
                    style={{
                      marginLeft: 'auto',
                      padding: '1px 6px',
                      borderRadius: 999,
                      background: 'var(--bg-sunken)',
                      color: 'var(--text-4)',
                      fontSize: 9,
                      letterSpacing: '0.1em',
                      boxShadow: 'inset 0 0 0 1px var(--border)',
                    }}
                  >
                    SOON
                  </span>
                )}
              </>
            )}
          </NavLink>
        ))}
      </div>
    </div>
  );
}

function UserMenu({ collapsed }: { collapsed: boolean }) {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    function onDocClick(e: MouseEvent) {
      if (!ref.current?.contains(e.target as Node)) setOpen(false);
    }
    document.addEventListener('mousedown', onDocClick);
    return () => document.removeEventListener('mousedown', onDocClick);
  }, []);

  if (!user) return null;
  const ini = initials(user.name || 'You');

  async function handleLogout() {
    setOpen(false);
    await logout();
    navigate('/login', { replace: true });
  }

  if (collapsed) {
    return (
      <div style={{ padding: 10, borderTop: '1px solid var(--border)' }} ref={ref}>
        <button
          type="button"
          onClick={() => setOpen((v) => !v)}
          className="display-italic flex items-center justify-center mx-auto"
          aria-label="User menu"
          style={{
            width: 36,
            height: 36,
            borderRadius: 999,
            background: 'var(--accent-soft)',
            color: 'var(--accent)',
            fontSize: 15,
            border: 0,
            cursor: 'pointer',
          }}
        >
          {ini}
        </button>
        {open && <MenuPopover onNavigate={(p) => { setOpen(false); navigate(p); }} onLogout={handleLogout} />}
      </div>
    );
  }

  return (
    <div style={{ padding: 12, borderTop: '1px solid var(--border)', position: 'relative' }} ref={ref}>
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="card card-hover flex items-center gap-2.5 w-full"
        style={{ padding: '10px 12px', border: 0, cursor: 'pointer', textAlign: 'left' }}
      >
        <div
          className="display-italic flex items-center justify-center flex-shrink-0"
          style={{
            width: 28,
            height: 28,
            borderRadius: 999,
            background: 'var(--accent-soft)',
            color: 'var(--accent)',
            fontSize: 14,
          }}
        >
          {ini}
        </div>
        <div className="min-w-0 flex-1">
          <div
            style={{
              fontSize: 12.5,
              fontWeight: 500,
              color: 'var(--text)',
              whiteSpace: 'nowrap',
              overflow: 'hidden',
              textOverflow: 'ellipsis',
            }}
          >
            {user.name}
          </div>
          {user.target && (
            <div className="mono" style={{ fontSize: 10, color: 'var(--text-4)' }}>
              {user.target}
            </div>
          )}
        </div>
        <span style={{ color: 'var(--text-4)', display: 'inline-flex' }}>
          {open ? <ChevronUp size={12} strokeWidth={1.8} /> : <ChevronDown size={12} strokeWidth={1.8} />}
        </span>
      </button>

      {open && <MenuPopover onNavigate={(p) => { setOpen(false); navigate(p); }} onLogout={handleLogout} />}
    </div>
  );
}

function MenuPopover({
  onNavigate,
  onLogout,
}: {
  onNavigate: (path: string) => void;
  onLogout: () => void;
}) {
  return (
    <div
      className="card"
      style={{
        position: 'absolute',
        bottom: 'calc(100% + 6px)',
        left: 12,
        right: 12,
        boxShadow: 'var(--shadow-elev)',
        padding: 4,
        zIndex: 50,
      }}
    >
      <MenuItem label="Profile" onClick={() => onNavigate('/profile')} Icon={UserRound} />
      <MenuItem label="Campaigns" onClick={() => onNavigate('/campaigns')} Icon={Briefcase} />
      <MenuItem label="Settings" onClick={() => onNavigate('/settings')} Icon={Settings2} />
      <div style={{ height: 1, margin: '4px 8px', background: 'var(--border)' }} />
      <MenuItem
        label="Sign out"
        onClick={onLogout}
        Icon={LogOut}
        color="var(--plum)"
      />
    </div>
  );
}

function MenuItem({
  label,
  onClick,
  Icon,
  color,
}: {
  label: string;
  onClick: () => void;
  Icon: (p: { size?: number; strokeWidth?: number }) => ReactNode;
  color?: string;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className="flex items-center gap-2.5 w-full text-left"
      style={{
        padding: '8px 10px',
        border: 0,
        background: 'transparent',
        borderRadius: 6,
        fontSize: 12.5,
        color: color ?? 'var(--text-2)',
        cursor: 'pointer',
      }}
      onMouseEnter={(e) => {
        e.currentTarget.style.background = 'var(--bg-sunken)';
      }}
      onMouseLeave={(e) => {
        e.currentTarget.style.background = 'transparent';
      }}
    >
      <span
        className="inline-flex items-center justify-center"
        style={{ width: 16, color: color ?? 'var(--text-4)' }}
      >
        <Icon size={14} strokeWidth={1.7} />
      </span>
      {label}
    </button>
  );
}

function TopBar() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const [menuOpen, setMenuOpen] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);
  const location = useLocation();
  const { modifierSymbol } = usePlatform();

  useEffect(() => {
    function onDocClick(e: MouseEvent) {
      if (!menuRef.current?.contains(e.target as Node)) setMenuOpen(false);
    }
    document.addEventListener('mousedown', onDocClick);
    return () => document.removeEventListener('mousedown', onDocClick);
  }, []);

  async function handleLogout() {
    setMenuOpen(false);
    await logout();
    navigate('/login', { replace: true });
  }

  function go(path: string) {
    setMenuOpen(false);
    navigate(path);
  }

  type CategoryDef = {
    id: string;
    label: string;
    children: Array<{
      path: string;
      label: string;
      group?: string;
      glyph?: (p: { size?: number }) => ReactNode;
      comingSoon?: boolean;
    }>;
  };

  const categories: Array<CategoryDef | { path: string; label: string }> = [
    { path: '/dashboard', label: 'Today' },
    {
      id: 'system-design',
      label: 'System Design',
      children: [
        { path: '/system-design/guide', label: 'Guide', glyph: SystemGlyph },
        { path: '/system-design/questions', label: 'Problem List', glyph: SystemGlyph },
      ],
    },
    {
      id: 'coding',
      label: 'Coding',
      children: [
        { path: '/coding/guide', label: 'Guide', glyph: CodeGlyph },
        { path: '/coding/questions', label: 'Problem List', glyph: CodeGlyph },
      ],
    },
    {
      id: 'behavioral',
      label: 'Behavioral',
      children: [
        { path: '/behavioral/guide', label: 'Guide', glyph: BehaviorGlyph },
        { path: '/behavioral/questions', label: 'Problem List', glyph: BehaviorGlyph },
      ],
    },
    { path: '/applications', label: 'Applications' },
    { path: '/interviews', label: 'Interview' },
    { path: '/todos', label: 'Todo' },
  ];

  return (
    <header
      className="flex-shrink-0 flex items-center px-6 gap-8"
      style={{
        height: 60,
        borderBottom: '1px solid var(--border)',
        background: 'var(--bg)',
      }}
    >
      <Link to="/dashboard" aria-label="Rounds · Dashboard" style={{ textDecoration: 'none' }}>
        <RoundsLockup markSize={22} textSize={22} />
      </Link>
      <nav className="flex gap-1 ml-3">
        {categories.map((cat) => {
          if ('path' in cat && !('children' in cat)) {
            return (
              <NavLink
                key={cat.path}
                to={cat.path}
                end={cat.path === '/dashboard'}
                className="relative whitespace-nowrap"
                style={({ isActive }) => ({
                  padding: '8px 12px',
                  border: 0,
                  background: 'transparent',
                  color: isActive ? 'var(--text)' : 'var(--text-3)',
                  fontSize: 13,
                  fontWeight: isActive ? 500 : 400,
                  textDecoration: 'none',
                  cursor: 'pointer',
                })}
              >
                {({ isActive }) => (
                  <>
                    {cat.label}
                    {isActive && (
                      <span
                        style={{
                          position: 'absolute',
                          left: 12,
                          right: 12,
                          bottom: -19,
                          height: 2,
                          background: 'var(--accent)',
                          borderRadius: 1,
                        }}
                      />
                    )}
                  </>
                )}
              </NavLink>
            );
          }

          const c = cat as CategoryDef;
          const active = c.children.some((ch) => location.pathname === ch.path || location.pathname.startsWith(ch.path + '/'));
          return <TopBarDropdown key={c.id} category={c} active={active} onNavigate={go} />;
        })}
      </nav>
      <div className="ml-auto flex items-center gap-3">
        <CampaignPill compact align="right" showRole={false} />
        <span className="mono" style={{ fontSize: 11, color: 'var(--text-3)' }}>
          {modifierSymbol === '⌘' ? '⌘K' : 'Ctrl K'}
        </span>
        {user && (
          <div ref={menuRef} style={{ position: 'relative' }}>
            <button
              type="button"
              onClick={() => setMenuOpen((v) => !v)}
              className="display-italic flex items-center gap-2"
              aria-label="User menu"
              aria-expanded={menuOpen}
              style={{
                padding: '4px 10px 4px 4px',
                borderRadius: 999,
                background: menuOpen ? 'var(--bg-sunken)' : 'transparent',
                border: 0,
                cursor: 'pointer',
                color: 'var(--text)',
              }}
            >
              <span
                className="display-italic flex items-center justify-center"
                style={{
                  width: 30,
                  height: 30,
                  borderRadius: 999,
                  background: 'var(--accent-soft)',
                  color: 'var(--accent)',
                  fontSize: 14,
                }}
              >
                {initials(user.name)}
              </span>
              <span
                style={{
                  fontFamily: 'var(--font-sans)',
                  fontSize: 12.5,
                  fontWeight: 500,
                  maxWidth: 120,
                  whiteSpace: 'nowrap',
                  overflow: 'hidden',
                  textOverflow: 'ellipsis',
                }}
              >
                {user.name}
              </span>
              <ChevronDown
                size={12}
                strokeWidth={1.8}
                style={{
                  color: 'var(--text-4)',
                  transform: menuOpen ? 'rotate(180deg)' : undefined,
                  transition: 'transform 120ms',
                }}
              />
            </button>
            {menuOpen && (
              <div
                className="card"
                style={{
                  position: 'absolute',
                  top: 'calc(100% + 6px)',
                  right: 0,
                  minWidth: 180,
                  boxShadow: 'var(--shadow-elev)',
                  padding: 4,
                  zIndex: 50,
                }}
              >
                <MenuItem label="Profile" onClick={() => go('/profile')} Icon={UserRound} />
                <MenuItem label="Campaigns" onClick={() => go('/campaigns')} Icon={Briefcase} />
                <MenuItem label="Settings" onClick={() => go('/settings')} Icon={Settings2} />
                <div style={{ height: 1, margin: '4px 8px', background: 'var(--border)' }} />
                <MenuItem
                  label="Sign out"
                  onClick={handleLogout}
                  Icon={LogOut}
                  color="var(--plum)"
                />
              </div>
            )}
          </div>
        )}
      </div>
    </header>
  );
}

function TopBarDropdown({
  category,
  active,
  onNavigate,
}: {
  category: {
    id: string;
    label: string;
    children: Array<{
      path: string;
      label: string;
      group?: string;
      glyph?: (p: { size?: number }) => ReactNode;
      comingSoon?: boolean;
    }>;
  };
  active: boolean;
  onNavigate: (path: string) => void;
}) {
  const [open, setOpen] = useState(false);
  const triggerRef = useRef<HTMLButtonElement>(null);
  const panelRef = useRef<HTMLDivElement>(null);
  const timeoutRef = useRef<ReturnType<typeof setTimeout>>();

  function scheduleClose() {
    timeoutRef.current = setTimeout(() => setOpen(false), 150);
  }

  function cancelClose() {
    if (timeoutRef.current) clearTimeout(timeoutRef.current);
  }

  useEffect(() => {
    function onDoc(e: MouseEvent) {
      if (!triggerRef.current?.contains(e.target as Node) && !panelRef.current?.contains(e.target as Node)) {
        setOpen(false);
      }
    }
    if (open) {
      document.addEventListener('mousedown', onDoc);
      return () => document.removeEventListener('mousedown', onDoc);
    }
  }, [open]);

  let lastGroup = '';

  return (
    <div
      onMouseEnter={cancelClose}
      onMouseLeave={scheduleClose}
      style={{ position: 'relative' }}
    >
      <button
        ref={triggerRef}
        type="button"
        onClick={() => setOpen((v) => !v)}
        onMouseEnter={() => { cancelClose(); setOpen(true); }}
        className="relative whitespace-nowrap flex items-center gap-1"
        style={{
          padding: '8px 12px',
          border: 0,
          background: open ? 'var(--bg-sunken)' : 'transparent',
          color: active || open ? 'var(--text)' : 'var(--text-3)',
          fontSize: 13,
          fontWeight: active ? 500 : 400,
          cursor: 'pointer',
          borderRadius: 'var(--radius)',
        }}
      >
        {category.label}
        <ChevronDown
          size={11}
          strokeWidth={1.8}
          style={{
            marginTop: 1,
            transform: open ? 'rotate(180deg)' : undefined,
            transition: 'transform 120ms',
          }}
        />
        {active && !open && (
          <span
            style={{
              position: 'absolute',
              left: 12,
              right: 12,
              bottom: -19,
              height: 2,
              background: 'var(--accent)',
              borderRadius: 1,
            }}
          />
        )}
      </button>

      {open && (
        <div
          ref={panelRef}
          onMouseEnter={cancelClose}
          className="card"
          style={{
            position: 'absolute',
            top: 'calc(100% + 8px)',
            left: -8,
            minWidth: 220,
            boxShadow: 'var(--shadow-elev)',
            padding: 4,
            zIndex: 50,
          }}
        >
          {category.children.map((child, i) => {
            const showGroup = child.group && child.group !== lastGroup;
            if (child.group) lastGroup = child.group;
            const Glyph = child.glyph;
            return (
              <div key={child.path}>
                {showGroup && i > 0 && (
                  <div style={{ height: 1, margin: '4px 8px', background: 'var(--border)' }} />
                )}
                {showGroup && (
                  <div
                    className="flex items-center gap-2 px-3 pt-2 pb-1"
                    style={{ fontSize: 11, fontWeight: 600, color: 'var(--text-3)', letterSpacing: '0.04em' }}
                  >
                    {Glyph && <span className="inline-flex" style={{ width: 14, height: 14 }}><Glyph size={14} /></span>}
                    {child.group}
                  </div>
                )}
                <button
                  type="button"
                  onClick={() => { setOpen(false); onNavigate(child.path); }}
                  className="flex items-center gap-2.5 w-full text-left"
                  style={{
                    padding: '7px 10px',
                    border: 0,
                    background: 'transparent',
                    borderRadius: 6,
                    fontSize: 12.5,
                    color: child.comingSoon ? 'var(--text-4)' : 'var(--text-2)',
                    cursor: child.comingSoon ? 'default' : 'pointer',
                  }}
                  onMouseEnter={(e) => {
                    if (!child.comingSoon) e.currentTarget.style.background = 'var(--bg-sunken)';
                  }}
                  onMouseLeave={(e) => {
                    e.currentTarget.style.background = 'transparent';
                  }}
                >
                  {child.label}
                  {child.comingSoon && (
                    <span
                      className="mono"
                      style={{
                        marginLeft: 'auto',
                        padding: '1px 6px',
                        borderRadius: 999,
                        background: 'var(--bg-sunken)',
                        color: 'var(--text-4)',
                        fontSize: 9,
                        letterSpacing: '0.1em',
                        boxShadow: 'inset 0 0 0 1px var(--border)',
                      }}
                    >
                      SOON
                    </span>
                  )}
                </button>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
