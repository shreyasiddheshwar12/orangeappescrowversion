import { useEffect, useState } from 'react';
import { Loader2, Receipt } from 'lucide-react';
import EmptyState from './EmptyState';
import { Pill } from './StatusPill';
import { ledgerAPI } from '../../lib/api';
import { formatINR, timeAgo } from '../../lib/format';

const LABEL = {
  funded: 'Paid into Orange', barter_fee: 'Barter fee', refund: 'Refund',
  payout_released: 'Payout released', payout_pending: 'Payout pending', commission: 'Orange commission',
};

/** Every money movement for this account, straight from the ledger. */
const PaymentsView = () => {
  const [rows, setRows] = useState(null);
  useEffect(() => { ledgerAPI.list().then((r) => setRows(r.data)).catch(() => setRows([])); }, []);
  if (!rows) return <div className="flex justify-center py-16"><Loader2 className="h-6 w-6 animate-spin text-primary" /></div>;
  if (!rows.length) return <EmptyState icon={Receipt} title="No payments yet" body="Payments show here once a collaboration is paid." />;
  const total = rows.filter((r) => r.direction === 'out').reduce((s, r) => s + r.amount, 0);
  return (
    <div className="space-y-4">
      <p className="text-sm text-ink-500">Total paid out: <span className="num font-semibold text-ink">{formatINR(total)}</span></p>
      <div className="surface divide-y divide-border">
        {rows.map((r) => (
          <div key={r.id} className="flex items-center gap-3 px-4 py-3 text-sm">
            <div className="min-w-0 flex-1">
              <p className="font-medium">{LABEL[r.type] || r.type}</p>
              <p className="text-xs text-muted-foreground">{r.counterpart} · {timeAgo(r.createdAt)}</p>
            </div>
            {r.simulated && <Pill tone="amber" dot={false}>Simulated</Pill>}
            <p className={`num w-28 text-right font-semibold ${r.direction === 'in' ? 'text-sage-700' : 'text-ink'}`}>{r.direction === 'in' ? '+' : '−'}{formatINR(r.amount)}</p>
          </div>
        ))}
      </div>
    </div>
  );
};

export default PaymentsView;
