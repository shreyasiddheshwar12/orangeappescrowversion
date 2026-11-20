import { ArrowUpRight, ArrowDownLeft } from 'lucide-react';
import StatusPill from './StatusPill';
import { counterpartName, nextStep, TYPE_LABEL, amountFor } from '../../lib/collaborations';
import { formatINR, timeAgo } from '../../lib/format';

const CollaborationRow = ({ collab, role, onOpen }) => {
  const step = nextStep(collab, role, { incoming: collab._incoming });
  const yourMove = step.who === 'you';
  return (
    <button
      onClick={() => onOpen(collab)}
      data-testid={`collab-row-${collab.id}`}
      className="group flex w-full items-center gap-4 border-b border-border px-4 py-3.5 text-left transition-colors last:border-b-0 hover:bg-[#FFFCF8] sm:px-5"
    >
      <div className={`flex h-9 w-9 shrink-0 items-center justify-center rounded-full ${collab._incoming ? 'bg-plum-50 text-plum-700' : 'bg-orange-50 text-orange-700'}`}>
        {collab._incoming ? <ArrowDownLeft className="h-4 w-4" /> : <ArrowUpRight className="h-4 w-4" />}
      </div>
      <div className="min-w-0 flex-1">
        <div className="flex flex-wrap items-center gap-x-2 gap-y-1">
          <p className="truncate font-semibold text-ink">{counterpartName(collab, role)}</p>
          <span className="text-xs text-muted-foreground">{TYPE_LABEL[collab.campaignType]}</span>
        </div>
        <p className="truncate text-sm text-muted-foreground">{collab.deliverables}</p>
      </div>
      <div className="hidden w-48 text-sm md:block">
        <p className={yourMove ? 'font-medium text-orange-800' : 'text-muted-foreground'}>{step.label}</p>
      </div>
      <div className="hidden w-24 text-right sm:block">
        <p className="num text-sm font-semibold text-ink">{formatINR(amountFor(collab))}</p>
        <p className="text-xs text-muted-foreground">{timeAgo(collab.updatedAt)}</p>
      </div>
      <StatusPill status={collab.status} />
    </button>
  );
};

export default CollaborationRow;
