import { STATUS_META } from '../../lib/collaborations';

const TONES = {
  orange: 'bg-orange-50 text-orange-800 ring-orange-200',
  amber: 'bg-amber-50 text-amber-700 ring-amber-100',
  plum: 'bg-plum-50 text-plum-700 ring-plum-100',
  sage: 'bg-sage-50 text-sage-700 ring-sage-100',
  brick: 'bg-brick-50 text-brick-700 ring-brick-100',
  neutral: 'bg-stone text-ink-500 ring-border',
};

export const Pill = ({ tone = 'neutral', children, dot = true, className = '' }) => (
  <span className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-xs font-medium ring-1 ring-inset ${TONES[tone] || TONES.neutral} ${className}`}>
    {dot && <span className="h-1.5 w-1.5 rounded-full bg-current opacity-70" />}
    {children}
  </span>
);

const StatusPill = ({ status, className = '' }) => {
  const meta = STATUS_META[status] || { label: status, tone: 'neutral' };
  return <Pill tone={meta.tone} className={className}>{meta.label}</Pill>;
};

export default StatusPill;
