import { ReactNode, useState } from 'react';
import { motion } from 'framer-motion';

export interface AccordionItemSpec {
  id: string;
  title: string;
  summary?: string;
  children: ReactNode;
}

interface AccordionProps {
  items: AccordionItemSpec[];
  defaultOpenId?: string;
  className?: string;
}

export function Accordion({
  items,
  defaultOpenId,
  className = '',
}: AccordionProps) {
  const initialOpen = defaultOpenId ?? items[0]?.id ?? null;
  const [openId, setOpenId] = useState<string | null>(initialOpen);

  const toggle = (id: string) => {
    setOpenId((current) => (current === id ? null : id));
  };

  return (
    <div className={`space-y-2 ${className}`}>
      {items.map((item) => {
        const isOpen = item.id === openId;
        return (
          <div key={item.id} className="card overflow-hidden">
            <button
              type="button"
              onClick={() => toggle(item.id)}
              aria-expanded={isOpen}
              className="w-full text-left px-4 py-3 flex items-start justify-between gap-3 hover:bg-gray-50 transition-colors"
            >
              <div className="min-w-0">
                <div className="text-sm font-medium text-gray-900">{item.title}</div>
                {item.summary && (
                  <div className="text-xs text-gray-500 mt-0.5">{item.summary}</div>
                )}
              </div>
              <span
                className={`flex-shrink-0 text-gray-400 text-xs mt-1 transition-transform ${
                  isOpen ? 'rotate-180' : ''
                }`}
                aria-hidden
              >
                ▾
              </span>
            </button>
            {isOpen && (
              <motion.div
                key="body"
                initial={{ height: 0, opacity: 0 }}
                animate={{ height: 'auto', opacity: 1 }}
                transition={{ duration: 0.2, ease: 'easeOut' }}
                className="overflow-hidden"
              >
                <div className="px-4 pb-4 pt-1 border-t border-gray-50">
                  {item.children}
                </div>
              </motion.div>
            )}
          </div>
        );
      })}
    </div>
  );
}
