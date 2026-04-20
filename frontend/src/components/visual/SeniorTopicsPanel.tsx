import { Accordion } from './Accordion';
import { MermaidRenderer } from './MermaidRenderer';
import type { SeniorTopic } from './types';

interface SeniorTopicsPanelProps {
  topics: SeniorTopic[];
  className?: string;
}

function TopicBody({ topic }: { topic: SeniorTopic }) {
  return (
    <div className="space-y-4">
      {topic.sections.map((s, i) => (
        <div key={i}>
          <h4 className="text-xs font-medium text-gray-500 uppercase tracking-wider mb-1">
            {s.heading}
          </h4>
          <p className="text-sm text-gray-700 leading-relaxed whitespace-pre-line">
            {s.body}
          </p>
        </div>
      ))}
      {topic.diagram && (
        <div className="card p-3 overflow-hidden">
          <MermaidRenderer chart={topic.diagram} />
        </div>
      )}
      {topic.sources.length > 0 && (
        <div className="pt-3 border-t border-gray-50">
          <span className="text-xs font-medium text-gray-500 uppercase tracking-wider">
            Sources
          </span>
          <div className="flex flex-wrap gap-1.5 mt-1.5">
            {topic.sources.map((src) => (
              <a
                key={src.url}
                href={src.url}
                target="_blank"
                rel="noopener noreferrer"
                className="pill bg-gray-50 text-gray-600 hover:bg-gray-100 transition-colors"
              >
                {src.label}
              </a>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

export function SeniorTopicsPanel({ topics, className = '' }: SeniorTopicsPanelProps) {
  const items = topics.map((t) => ({
    id: t.id,
    title: t.title,
    summary: t.summary,
    children: <TopicBody topic={t} />,
  }));
  return <Accordion items={items} className={className} />;
}
