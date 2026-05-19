import type { ReactNode } from 'react';

// PWA-style page shell: the header (passed as the `header` slot) stays
// pinned while only the body scrolls. Use for any page that wants the
// shell — top nav + AppHeader — to stay put while content overflows.
//
// Optional `footer` slot pins a row below the scrolling body — used
// by pages that want a docked action surface (e.g. the application
// detail's offer dock). The footer renders outside the scroll area
// so it stays at the viewport bottom regardless of content length.
export default function PageShell({
  header,
  children,
  footer,
  bodyClassName,
}: {
  header: ReactNode;
  children: ReactNode;
  footer?: ReactNode;
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
      {footer && <div className="flex-shrink-0">{footer}</div>}
    </div>
  );
}
