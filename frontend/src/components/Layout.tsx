import { NavLink, Link, Outlet, useLocation, useNavigate } from 'react-router-dom';
import { useEffect, useRef, useState, type ReactNode } from 'react';
import {
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
  AppsGlyph,
  BehaviorGlyph,
  CalendarGlyph,
  CodeGlyph,
  DashGlyph,
  SystemGlyph,
} from './shell/Glyphs';
import { useTheme } from '../theme/ThemeProvider';
import { initials, useAuth } from '../auth/AuthProvider';

type NavDef = {
  path: string;
  label: string;
  glyph: (p: { size?: number }) => ReactNode;
};

const primaryNav: NavDef[] = [
  { path: '/dashboard', label: 'Today', glyph: DashGlyph },
];

const practiceNav: NavDef[] = [
  { path: '/system-design', label: 'System Design', glyph: SystemGlyph },
  { path: '/coding', label: 'Coding', glyph: CodeGlyph },
  { path: '/behavioral', label: 'Behavioral', glyph: BehaviorGlyph },
];

const trackingNav: NavDef[] = [
  { path: '/applications', label: 'Applications', glyph: AppsGlyph },
  { path: '/interviews', label: 'Interviews', glyph: CalendarGlyph },
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
    <div
      className={topbar ? 'h-dvh flex flex-col overflow-hidden' : 'h-dvh flex overflow-hidden'}
      style={{ background: 'var(--bg)' }}
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
              position: 'relative',
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
                <NavRow key={item.path} item={item} collapsed={collapsed} />
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
            className="lg:hidden flex-shrink-0 flex items-center h-[52px] px-3"
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
    </div>
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
          {!collapsed && <span>{item.label}</span>}
          {!collapsed && isActive && (
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
  const items = [...practiceNav, ...trackingNav];
  const { user } = useAuth();
  const navigate = useNavigate();
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
      <nav className="flex gap-1 ml-3 overflow-x-auto no-scrollbar">
        {items.map((it) => (
          <NavLink
            key={it.path}
            to={it.path}
            className="relative whitespace-nowrap"
            style={({ isActive }) => ({
              padding: '8px 12px',
              border: 0,
              background: 'transparent',
              color: isActive ? 'var(--text)' : 'var(--text-3)',
              fontSize: 13,
              fontWeight: isActive ? 500 : 400,
              textDecoration: 'none',
            })}
          >
            {({ isActive }) => (
              <>
                {it.label}
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
        ))}
      </nav>
      <div className="ml-auto flex items-center gap-3">
        <span className="mono" style={{ fontSize: 11, color: 'var(--text-3)' }}>
          ⌘K
        </span>
        {user && (
          <button
            type="button"
            onClick={() => navigate('/profile')}
            className="display-italic flex items-center justify-center"
            aria-label="Profile"
            style={{
              width: 30,
              height: 30,
              borderRadius: 999,
              background: 'var(--accent-soft)',
              color: 'var(--accent)',
              fontSize: 14,
              border: 0,
              cursor: 'pointer',
            }}
          >
            {initials(user.name)}
          </button>
        )}
      </div>
    </header>
  );
}
