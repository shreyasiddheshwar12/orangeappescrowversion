import { useEffect, useState } from 'react';
import { ShieldCheck } from 'lucide-react';
import { trustAPI } from '../../lib/api';

const LABELS = {
  onTime: 'On-time delivery', rating: 'Reviews', completion: 'Completion', response: 'Responds to requests', repeat: 'Repeat brands',
  payment: 'Pays reliably', turnaround: 'Approves quickly',
};

/** TrustScore with its maths shown. `kind` is 'creator' or 'brand'. */
const TrustScore = ({ kind, profileId }) => {
  const [t, setT] = useState(null);
  useEffect(() => {
    (kind === 'creator' ? trustAPI.creator(profileId) : trustAPI.brand(profileId)).then((r) => setT(r.data)).catch(() => {});
  }, [kind, profileId]);
  if (!t) return null;
  return (
    <section className="surface p-5" data-testid="trust-score">
      <div className="flex items-center gap-4">
        <div className="flex h-16 w-16 shrink-0 flex-col items-center justify-center rounded-full bg-sage-50 ring-1 ring-sage-100">
          {t.isNew ? <span className="text-sm font-semibold text-sage-700">New</span> : <span className="num font-display text-2xl text-sage-700">{t.score}</span>}
        </div>
        <div>
          <p className="flex items-center gap-1.5 font-semibold"><ShieldCheck className="h-4 w-4 text-sage-600" />TrustScore</p>
          <p className="text-sm text-muted-foreground">
            {t.isNew ? `Shown after 3 completed collaborations (${t.completed} so far).` : `From ${t.completed} completed collaborations on Orange.`}
          </p>
        </div>
      </div>
      <ul className="mt-4 space-y-1.5 border-t border-border pt-3 text-sm">
        {t.factors.map((f) => (
          <li key={f.factor} className="flex gap-3">
            <span className="w-40 shrink-0 text-ink">{LABELS[f.factor] || f.factor}</span>
            <span className="flex-1 text-ink-500">{f.detail}</span>
            <span className="num w-12 shrink-0 text-right text-muted-foreground">{f.value === null ? '–' : `${Math.round(f.value * f.weight)}/${f.weight}`}</span>
          </li>
        ))}
      </ul>
    </section>
  );
};

export default TrustScore;
