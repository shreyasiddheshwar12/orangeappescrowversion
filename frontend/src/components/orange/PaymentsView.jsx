import { useEffect, useState } from 'react';
import { Loader2, Receipt } from 'lucide-react';
import EmptyState from './EmptyState';
import { Pill } from './StatusPill';
import { ledgerAPI } from '../../lib/api';
import { useAuth } from '../../lib/auth';
import { formatINR, timeAgo } from '../../lib/format';

const LABEL = {
  funded: 'Paid into Orange', barter_fee: 'Barter fee', refund: 'Refund',
  payout_released: 'Payout released', payout_pending: 'Payout pending', commission: 'Orange commission',
};

/** Every money movement for this account, straight from the ledger. */
const PaymentsView = () => {
  const { user } = useAuth();
  const [rows, setRows] = useState(null);
  useEffect(() => { ledgerAPI.list().then((r) => setRows(r.data)).catch(() => setRows([])); }, []);
  if (!rows) return <div className="flex justify-center py-16"><Loader2 className="h-6 w-6 animate-spin text-primary" /></div>;
  if (!rows.length) return <EmptyState icon={Receipt} title="No payments yet" body="Payments show here once a collaboration is paid." />;
  const sum = (dir) => rows.filter((r) => r.direction === dir).reduce((s, r) => s + r.amount, 0);
  const isCreator = user?.role === 'creator';
  const total = isCreator ? sum('in') - sum('out') : sum('out') - sum('in');
  return (
    <div className="space-y-4">
      {rows.some((r) => r.simulated) && <p className="text-xs text-muted-foreground">Payments are simulated while Orange is in testing. No real money moves.</p>}
      <p className="text-sm text-ink-500">{isCreator ? 'Total earned' : 'Total paid'}: <span className="num font-semibold text-ink">{formatINR(total)}</span></p>
      <div className="surface divide-y divide-border">
        {rows.map((r) => (
          <div key={r.id} className="flex items-center gap-3 px-4 py-3 text-sm">
            <div className="min-w-0 flex-1">
              <p className="font-medium">{r.direction === 'none' ? `Released to ${r.counterpart}` : (LABEL[r.type] || r.type)}</p>
              <p className="text-xs text-muted-foreground">{r.direction === 'none' ? 'After their Orange fee' : r.counterpart} · {timeAgo(r.createdAt)}</p>
            </div>
            {r.simulated && <span className="hidden sm:inline-flex"><Pill tone="amber" dot={false}>Simulated</Pill></span>}
            <p className={`num shrink-0 text-right sm:w-28 font-semibold ${r.direction === 'in' ? 'text-sage-700' : r.direction === 'none' ? 'text-muted-foreground' : 'text-ink'}`}>{r.direction === 'in' ? '+' : r.direction === 'out' ? '−' : ''}{formatINR(r.amount)}</p>
          </div>
        ))}
      </div>
    </div>
  );
};

export default PaymentsView;
