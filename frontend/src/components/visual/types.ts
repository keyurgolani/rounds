export interface ArchitectureNode {
  id: string;
  label: string;
  type?: 'client' | 'server' | 'cache' | 'database' | 'queue' | 'lb' | 'service';
  description?: string;
}

export interface ArchitectureEdge {
  id?: string;
  source: string;
  target: string;
  label?: string;
  animated?: boolean;
}

export interface ArchitectureDiagramData {
  nodes: ArchitectureNode[];
  edges: ArchitectureEdge[];
}

export interface TradeoffOption {
  label: string;
  description: string;
  icon?: string;
  pros?: string[];
  cons?: string[];
  metrics?: { name: string; value: number; max: number }[];
}

export interface TradeoffVisual {
  title: string;
  options: [TradeoffOption, TradeoffOption];
  recommendation?: string;
}

export interface SeniorTopicSection {
  heading: string;
  body: string;
}

export interface SeniorTopicSource {
  label: string;
  url: string;
}

export interface SeniorTopic {
  id: string;
  title: string;
  summary: string;
  sections: SeniorTopicSection[];
  diagram?: string;
  sources: SeniorTopicSource[];
}
