import { render, screen, fireEvent, act } from '@testing-library/react';
import { afterEach, describe, it, expect, vi, beforeEach } from 'vitest';
import SectionNav from '../SectionNav';

type IOCallback = (entries: IntersectionObserverEntry[]) => void;
type IORecord = { cb: IOCallback; targets: Element[] };
const observers: IORecord[] = [];

class CapturingIO {
  root: Element | Document | null = null;
  rootMargin = '';
  thresholds: readonly number[] = [];
  private cb: IOCallback;
  private targets: Element[] = [];
  constructor(cb: IOCallback) {
    this.cb = cb;
    observers.push({ cb, targets: this.targets });
  }
  observe(t: Element) {
    this.targets.push(t);
  }
  unobserve() {}
  disconnect() {}
  takeRecords(): IntersectionObserverEntry[] {
    return [];
  }
}

function fireIntersection(id: string, isIntersecting: boolean) {
  const el = document.getElementById(id);
  if (!el) return;
  observers.forEach((o) => {
    if (o.targets.includes(el)) {
      o.cb([
        {
          isIntersecting,
          target: el,
          intersectionRatio: isIntersecting ? 1 : 0,
          boundingClientRect: el.getBoundingClientRect(),
          intersectionRect: el.getBoundingClientRect(),
          rootBounds: null,
          time: 0,
        } as IntersectionObserverEntry,
      ]);
    }
  });
}

const items = [
  { id: 'architecture', label: 'Architecture' },
  { id: 'database', label: 'Database' },
  { id: 'api', label: 'API' },
];

function renderWithSections() {
  document.body.innerHTML = '';
  items.forEach(({ id }) => {
    const sec = document.createElement('section');
    sec.id = id;
    sec.innerHTML = `<h2>${id}</h2>`;
    document.body.appendChild(sec);
  });
  render(<SectionNav items={items} />);
}

beforeEach(() => {
  history.replaceState(null, '', '/');
  Element.prototype.scrollIntoView = vi.fn();
  (globalThis as unknown as { IntersectionObserver: typeof IntersectionObserver }).IntersectionObserver =
    CapturingIO as unknown as typeof IntersectionObserver;
  observers.length = 0;
});

afterEach(() => {
  // @ts-expect-error — restore: jsdom never defined it; we added it for the test.
  delete Element.prototype.scrollIntoView;
});

describe('SectionNav — rendering', () => {
  it('renders an "On this page" label and one entry per item', () => {
    renderWithSections();
    const wideNav = screen
      .getAllByRole('navigation', { name: /on this page/i })
      .find((n) => n.classList.contains('lg:block'))!;
    expect(wideNav.textContent).toMatch(/on this page/i);
    expect(wideNav.querySelector('a[href="#architecture"]')).toBeTruthy();
    expect(wideNav.querySelector('a[href="#database"]')).toBeTruthy();
    expect(wideNav.querySelector('a[href="#api"]')).toBeTruthy();
  });

  it('renders nothing when items is empty', () => {
    render(<SectionNav items={[]} />);
    expect(screen.queryByText(/on this page/i)).not.toBeInTheDocument();
  });
});

describe('SectionNav — click behavior', () => {
  it('clicking an entry calls scrollIntoView on the target and updates location.hash', () => {
    renderWithSections();
    const wideNav = screen
      .getAllByRole('navigation', { name: /on this page/i })
      .find((n) => n.classList.contains('lg:block'))!;
    fireEvent.click(wideNav.querySelector('a[href="#database"]')!);
    expect(Element.prototype.scrollIntoView).toHaveBeenCalledWith({
      behavior: 'smooth',
      block: 'start',
    });
    expect(location.hash).toBe('#database');
  });

});

describe('SectionNav — scroll-spy', () => {
  it('highlights the first item by default', () => {
    renderWithSections();
    const wideNav = screen
      .getAllByRole('navigation', { name: /on this page/i })
      .find((n) => n.classList.contains('lg:block'))!;
    const first = wideNav.querySelector('a[href="#architecture"]')!;
    expect(first.getAttribute('aria-current')).toBe('location');
  });

  it('updates active item when a different section intersects', () => {
    renderWithSections();
    act(() => {
      fireIntersection('api', true);
    });
    const wideNav = screen
      .getAllByRole('navigation', { name: /on this page/i })
      .find((n) => n.classList.contains('lg:block'))!;
    const api = wideNav.querySelector('a[href="#api"]')!;
    expect(api.getAttribute('aria-current')).toBe('location');
    const arch = wideNav.querySelector('a[href="#architecture"]')!;
    expect(arch.getAttribute('aria-current')).toBeNull();
  });

  it('replaces the hash (not pushes) when scroll-spy changes active section', () => {
    const pushSpy = vi.spyOn(history, 'pushState');
    const replaceSpy = vi.spyOn(history, 'replaceState');
    renderWithSections();
    replaceSpy.mockClear();
    pushSpy.mockClear();
    act(() => {
      fireIntersection('database', true);
    });
    expect(replaceSpy).toHaveBeenCalled();
    expect(pushSpy).not.toHaveBeenCalled();
    expect(location.hash).toBe('#database');
  });
});

describe('SectionNav — responsive variants', () => {
  it('renders the wide right-rail nav with lg-only visibility', () => {
    renderWithSections();
    const navs = screen.getAllByRole('navigation', { name: /on this page/i });
    const wide = navs.find((n) => n.classList.contains('hidden') && n.classList.contains('lg:block'));
    expect(wide).toBeTruthy();
  });

  it('renders the chip strip visible only on md (hidden on lg and below-md)', () => {
    renderWithSections();
    const navs = screen.getAllByRole('navigation', { name: /on this page/i });
    const strip = navs.find((n) =>
      n.classList.contains('md:flex') && n.classList.contains('lg:hidden')
    );
    expect(strip).toBeTruthy();
  });

  it('clicking an entry in the chip strip updates the hash', () => {
    renderWithSections();
    const navs = screen.getAllByRole('navigation', { name: /on this page/i });
    const strip = navs.find((n) => n.classList.contains('md:flex'))!;
    const apiLink = strip.querySelector('a[href="#api"]') as HTMLAnchorElement;
    fireEvent.click(apiLink);
    expect(location.hash).toBe('#api');
  });
});

describe('SectionNav — hash on mount', () => {
  let rafSpy: ReturnType<typeof vi.spyOn>;

  beforeEach(() => {
    rafSpy = vi.spyOn(window, 'requestAnimationFrame').mockImplementation((cb) => {
      cb(0);
      return 0;
    });
  });

  afterEach(() => {
    rafSpy.mockRestore();
  });

  it('scrolls to the hashed section on mount when it matches an item id', () => {
    history.replaceState(null, '', '/#database');
    renderWithSections();
    expect(Element.prototype.scrollIntoView).toHaveBeenCalledWith({
      behavior: 'auto',
      block: 'start',
    });
    const wideNav = screen
      .getAllByRole('navigation', { name: /on this page/i })
      .find((n) => n.classList.contains('lg:block'))!;
    const database = wideNav.querySelector('a[href="#database"]')!;
    expect(database.getAttribute('aria-current')).toBe('location');
  });

  it('does nothing when the hash does not match any item id', () => {
    history.replaceState(null, '', '/#unknown');
    renderWithSections();
    expect(Element.prototype.scrollIntoView).not.toHaveBeenCalled();
  });

  it('does nothing when there is no hash', () => {
    history.replaceState(null, '', '/');
    renderWithSections();
    expect(Element.prototype.scrollIntoView).not.toHaveBeenCalled();
  });
});
