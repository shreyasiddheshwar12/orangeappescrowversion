import { useEffect, useState } from 'react';
import { Copy, QrCode, MousePointerClick, Ticket } from 'lucide-react';
import { toast } from 'sonner';
import { Button } from '../ui/button';
import { Input } from '../ui/input';
import { trackingAPI, getErrorMessage } from '../../lib/api';

const copy = (text) => navigator.clipboard?.writeText(text).then(() => toast.success('Copied'), () => {});

/** Coupon code, tracking link and QR for one collaboration, with real click and redemption counts. */
const TrackingCard = ({ campaignId, isBrand }) => {
  const [t, setT] = useState(null);
  const [offer, setOffer] = useState('');
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    let alive = true;
    trackingAPI.get(campaignId).then((res) => { if (alive) { setT(res.data); setOffer(res.data.offer || ''); } }).catch(() => {});
    return () => { alive = false; };
  }, [campaignId]);

  if (!t) return null;

  const saveOffer = async () => {
    setSaving(true);
    try { setT((await trackingAPI.setOffer(campaignId, offer)).data); toast.success('Offer saved'); }
    catch (e) { toast.error(getErrorMessage(e, 'Could not save')); }
    finally { setSaving(false); }
  };

  return (
    <div className="surface space-y-4 p-4" data-testid="tracking-card">
      <div className="flex items-start gap-4">
        <img src={t.qrUrl} alt="QR code for the tracking link" className="h-24 w-24 shrink-0 rounded-md border border-border bg-white p-1" />
        <div className="min-w-0 flex-1 space-y-2">
          <p className="eyebrow">Coupon code</p>
          <button onClick={() => copy(t.couponCode)} className="flex items-center gap-2 font-mono text-xl font-semibold tracking-wider text-ink hover:text-orange-700" data-testid="coupon-code">
            {t.couponCode}<Copy className="h-4 w-4" />
          </button>
          <button onClick={() => copy(t.url)} className="flex max-w-full items-center gap-1.5 truncate text-xs text-ink-500 hover:text-ink">
            <QrCode className="h-3.5 w-3.5 shrink-0" /><span className="truncate">{t.url}</span>
          </button>
        </div>
      </div>
      <div className="grid grid-cols-2 gap-2 text-sm">
        <div className="rounded-md bg-stone px-3 py-2"><MousePointerClick className="mb-1 h-4 w-4 text-ink-500" /><span className="num font-semibold">{t.clicks}</span> link {t.clicks === 1 ? 'visit' : 'visits'}</div>
        <div className="rounded-md bg-stone px-3 py-2"><Ticket className="mb-1 h-4 w-4 text-ink-500" /><span className="num font-semibold">{t.redemptions}</span> {t.redemptions === 1 ? 'code' : 'codes'} redeemed</div>
      </div>
      {isBrand ? (
        <div className="flex gap-2">
          <Input value={offer} onChange={(e) => setOffer(e.target.value)} placeholder="Offer for customers, e.g. 10% off any cold brew" maxLength={140} />
          <Button variant="outline" onClick={saveOffer} disabled={saving || offer === (t.offer || '')}>Save</Button>
        </div>
      ) : (
        <p className="text-xs text-ink-500">{t.offer ? `Offer: ${t.offer}. ` : ''}Share the code or link in your content. Every redemption counts towards your results.</p>
      )}
    </div>
  );
};

export default TrackingCard;
