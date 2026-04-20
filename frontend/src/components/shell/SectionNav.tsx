import { useEffect, useRef, useState } from 'react';
import type { MouseEvent, RefObject } from 'react';

export type SectionNavItem = { id: string; label: string };

interface SectionNavProps {
  items: SectionNavItem[];
  scrollContainer?: RefObject<HTMLElement | null>;
  offset?: number;
}

export default function SectionNav({ items, scrollContainer, offset = 0 }: SectionNavProps) {
  const [activeId, setActiveId] = useState<string>(items[0]?.id ?? '');
  const observerRef = useRef<IntersectionObserver | null>(null);

  useEffect(() => {
    if (items.length === 0) return;
    const targets = items
      .map(({ id }) => document.getElementById(id))
      .filter((el): el is HTMLElement => el !== null);

    observerRef.current = new IntersectionObserver(
      (entries) => {
        const visible = entries
          .filter((e) => e.isIntersecting)
          .sort((a, b) => a.boundingClientRect.top - b.boundingClientRect.top);
        if (visible.length === 0) return;
        const nextId = (visible[0].target as HTMLElement).id;
        setActiveId(nextId);
        const nextHash = `#${nextId}`;
        if (location.hash !== nextHash) {
          const { pathname, search } = location;
          history.replaceState(null, '', `${pathname}${search}${nextHash}`);
        }
      },
      {
        root: scrollContainer?.current ?? null,
        rootMargin: `-${offset}px 0px -40% 0px`,
        threshold: 0,
      }
    );

    targets.forEach((t) => observerRef.current!.observe(t));
    return () => observerRef.current?.disconnect();
  }, [items, scrollContainer, offset]);

  useEffect(() => {
    if (items.length === 0) return;
    const hash = location.hash.replace(/^#/, '');
    if (!hash) return;
    if (!items.some((i) => i.id === hash)) return;
    const target = document.getElementById(hash);
    if (target) {
      // eslint-disable-next-line no-undef
      requestAnimationFrame(() => {
        target.scrollIntoView({ behavior: 'auto', block: 'start' });
      });
      setActiveId(hash);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  if (items.length === 0) return null;

  const handleClick = (e: MouseEvent<HTMLAnchorElement>, id: string) => {
    e.preventDefault();
    setActiveId(id);
    const target = document.getElementById(id);
    if (target) {
      target.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
    const { pathname, search } = location;
    history.replaceState(null, '', `${pathname}${search}#${id}`);
  };

  return (
    <>
      <nav
        aria-label="On this page"
        className="hidden lg:block"
        style={{ position: 'sticky', top: offset + 16 }}
      >
        <div className="eyebrow mb-3">On this page</div>
        <ol className="flex flex-col gap-1.5 list-none p-0 m-0">
          {items.map((item) => {
            const on = activeId === item.id;
            return (
              <li key={item.id}>
                <a
                  href={`#${item.id}`}
                  onClick={(e) => handleClick(e, item.id)}
                  aria-current={on ? 'location' : undefined}
                  className="block"
                  style={{
                    fontSize: 13,
                    padding: '4px 12px',
                    color: on ? 'var(--text)' : 'var(--text-3)',
                    fontWeight: on ? 500 : 400,
                    borderLeft: on ? '2px solid var(--accent)' : '2px solid transparent',
                    textDecoration: 'none',
                  }}
                >
                  {item.label}
                </a>
              </li>
            );
          })}
        </ol>
      </nav>
      <nav
        aria-label="On this page"
        className="hidden md:flex lg:hidden"
        style={{
          position: 'sticky',
          top: offset,
          gap: 6,
          padding: '8px 0',
          background: 'var(--paper)',
          borderBottom: '1px solid var(--border)',
          overflowX: 'auto',
          zIndex: 2,
        }}
      >
        {items.map((item) => {
          const on = activeId === item.id;
          return (
            <a
              key={item.id}
              href={`#${item.id}`}
              onClick={(e) => handleClick(e, item.id)}
              aria-current={on ? 'location' : undefined}
              className="pill whitespace-nowrap"
              style={{
                fontSize: 11.5,
                background: on ? 'var(--accent-soft)' : 'transparent',
                color: on ? 'var(--accent)' : 'var(--text-3)',
                boxShadow: on ? 'none' : 'inset 0 0 0 1px var(--border-strong)',
                textDecoration: 'none',
              }}
            >
              {item.label}
            </a>
          );
        })}
      </nav>
    </>
  );
}
