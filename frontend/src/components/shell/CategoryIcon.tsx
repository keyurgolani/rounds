import {
  BookOpen,
  CalendarClock,
  Compass,
  KeyRound,
  Lightbulb,
  LifeBuoy,
  MessageCircle,
  Puzzle,
  Scale,
  Swords,
  Target,
  Users,
  Wind,
  type LucideIcon,
  type LucideProps,
} from 'lucide-react';

// Kebab-case Lucide icon names we accept from seed data. Kept explicit so
// the bundle stays small and missing names are caught at review time.
const ICON_MAP: Record<string, LucideIcon> = {
  'book-open': BookOpen,
  'calendar-clock': CalendarClock,
  compass: Compass,
  'key-round': KeyRound,
  lightbulb: Lightbulb,
  'life-buoy': LifeBuoy,
  'message-circle': MessageCircle,
  puzzle: Puzzle,
  scale: Scale,
  swords: Swords,
  target: Target,
  users: Users,
  wind: Wind,
};

interface CategoryIconProps extends Omit<LucideProps, 'name'> {
  name: string | undefined | null;
}

export function CategoryIcon({ name, ...props }: CategoryIconProps) {
  if (!name) return null;
  const Icon = ICON_MAP[name];
  if (!Icon) return null;
  return <Icon {...props} />;
}
