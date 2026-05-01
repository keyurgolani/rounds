import type { ReactNode } from 'react';

// PWA-style page shell: the header (passed as the `header` slot) stays
// pinned while only the body scrolls. Use for any page that wants the
// shell — top nav + AppHeader — to stay put while content overflows.
export default function PageShell({
  header,
  children,
  bodyClassName,
}: {
  header: ReactNode;
  children: ReactNode;
  bodyClassName?: string;
}) {
  return (
    <div className="h-full flex flex-col min-h-0">
      {header}
      <div
        className={`flex-1 min-h-0 overflow-y-auto ${bodyClassName ?? ''}`}
      >
        {children}
      </div>
    </div>
  );
}
