import { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import { MapPin } from 'lucide-react';
import { LogoMark } from '../components/orange/Logo';
import { trackingAPI } from '../lib/api';

/** Public page a customer lands on from a creator's link or QR. */
const Offer = () => {
  const { slug } = useParams();
  const [o, setO] = useState(null);
  const [missing, setMissing] = useState(false);
  useEffect(() => { trackingAPI.offer(slug).then((r) => setO(r.data)).catch(() => setMissing(true)); }, [slug]);

  return (
    <div className="flex min-h-screen items-center justify-center bg-background px-4">
      <div className="w-full max-w-sm text-center">
        {missing ? (
          <p className="text-ink-500">This offer link isn't valid.</p>
        ) : !o ? null : (
          <div className="surface p-8 shadow-float">
            <p className="eyebrow">Your offer at</p>
            <h1 className="display mt-2 text-3xl">{o.brandName}</h1>
            {o.location && <p className="mt-1 inline-flex items-center gap-1 text-sm text-muted-foreground"><MapPin className="h-3.5 w-3.5" />{o.location}</p>}
            {o.offer && <p className="mt-5 text-lg text-ink">{o.offer}</p>}
            <div className="mt-6 rounded-xl border-2 border-dashed border-orange-300 bg-orange-50 px-4 py-5">
              <p className="text-xs text-orange-800">Show this code at the counter</p>
              <p className="mt-1 font-mono text-3xl font-semibold tracking-widest text-ink" data-testid="offer-code">{o.couponCode}</p>
            </div>
            {o.websiteUrl && <a href={o.websiteUrl} className="mt-5 inline-block text-sm font-medium text-orange-800 hover:underline" rel="noopener noreferrer">Visit {o.brandName}</a>}
          </div>
        )}
        <p className="mt-6 flex items-center justify-center gap-1.5 text-xs text-muted-foreground"><LogoMark size={14} />Powered by Orange</p>
      </div>
    </div>
  );
};

export default Offer;
