import { useState } from 'react';
import { motion } from 'framer-motion';
import type { TradeoffVisual } from './types';

interface TradeoffSliderProps {
  visual: TradeoffVisual;
  className?: string;
}

export function TradeoffSlider({ visual, className = '' }: TradeoffSliderProps) {
  const [pos, setPos] = useState(0); // 0..100
  const activeIdx = pos < 50 ? 0 : 1;
  const active = visual.options[activeIdx];

  return (
    <div className={`card p-4 ${className}`}>
      <h3 className="text-sm font-medium text-gray-900 mb-3">{visual.title}</h3>
      <div className="flex items-center justify-between text-xs font-mono text-gray-500 mb-1">
        <span className={activeIdx === 0 ? 'text-accent-blue font-semibold' : ''}>
          {visual.options[0].label}
        </span>
        <span className={activeIdx === 1 ? 'text-accent-purple font-semibold' : ''}>
          {visual.options[1].label}
        </span>
      </div>
      <input
        type="range"
        min={0}
        max={100}
        value={pos}
        onChange={(e) => setPos(Number(e.target.value))}
        className="w-full accent-gray-900"
        aria-label={visual.title}
      />
      <motion.div
        key={active.label}
        initial={{ opacity: 0, y: 6 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.2 }}
        className="mt-4"
      >
        <p className="text-sm text-gray-700 font-medium">{active.description}</p>
        <div className="grid grid-cols-2 gap-3 mt-3">
          <div>
            <span className="text-xs uppercase tracking-wider text-green-600 font-medium">
              Pros
            </span>
            <ul className="mt-1 space-y-0.5">
              {(active.pros ?? []).map((p) => (
                <li key={p} className="text-xs text-gray-600 flex gap-1.5">
                  <span className="text-green-500">+</span>
                  <span>{p}</span>
                </li>
              ))}
            </ul>
          </div>
          <div>
            <span className="text-xs uppercase tracking-wider text-red-600 font-medium">
              Cons
            </span>
            <ul className="mt-1 space-y-0.5">
              {(active.cons ?? []).map((c) => (
                <li key={c} className="text-xs text-gray-600 flex gap-1.5">
                  <span className="text-red-500">−</span>
                  <span>{c}</span>
                </li>
              ))}
            </ul>
          </div>
        </div>
      </motion.div>
      {visual.recommendation && (
        <div className="mt-4 pt-3 border-t border-gray-50">
          <span className="text-xs font-medium text-gray-500 uppercase">
            Recommendation:
          </span>
          <span className="text-sm text-gray-700 ml-1">{visual.recommendation}</span>
        </div>
      )}
    </div>
  );
}
