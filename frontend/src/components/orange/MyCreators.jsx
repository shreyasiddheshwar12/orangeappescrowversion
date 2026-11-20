import { useEffect, useState } from 'react';
import { Heart, Repeat, Loader2, Users } from 'lucide-react';
import { toast } from 'sonner';
import { Button } from '../ui/button';
import EmptyState from './EmptyState';
import { crmAPI, getErrorMessage } from '../../lib/api';
import { formatINR, timeAgo } from '../../lib/format';

/** Saved creators and everyone the business has worked with, with one-click rebooking. */
const MyCreators = ({ onRepeated, onFind }) => {
  const [rows, setRows] = useState(null);
  const [busy, setBusy] = useState(null);

  const load = () => crmAPI.list().then((r) => setRows(r.data)).catch(() => setRows([]));
  useEffect(() => { load(); }, []);

  const repeat = async (row) => {
    setBusy(row.creatorId);
    try {
      await crmAPI.repeat(row.lastCompletedId);
      toast.success(`New request sent to ${row.name} with the same terms`);
      onRepeated?.();
      load();
    } catch (e) {
      toast.error(getErrorMessage(e, 'Could not repeat'));
    } finally {
      setBusy(null);
    }
  };

  const unsave = async (row) => {
    await crmAPI.unsave(row.creatorId).catch(() => {});
    load();
  };

  if (!rows) return <div className="flex justify-center py-16"><Loader2 className="h-6 w-6 animate-spin text-primary" /></div>;
  if (!rows.length) {
    return <EmptyState icon={Users} title="No creators yet" body="Save creators with the heart while browsing, or complete a collaboration, and they'll show up here." action={<Button onClick={onFind}>Find creators</Button>} />;
  }

  return (
    <div className="surface divide-y divide-border">
      {rows.map((r) => (
        <div key={r.creatorId} className="flex flex-col gap-3 p-4 sm:flex-row sm:items-center" data-testid={`my-creator-${r.creatorId}`}>
          <div className="min-w-0 flex-1">
            <p className="flex items-center gap-2 font-semibold">
              {r.name}
              {r.saved && <button onClick={() => unsave(r)} aria-label="Remove from saved"><Heart className="h-4 w-4 fill-orange-600 text-orange-600" /></button>}
            </p>
            <p className="text-sm text-muted-foreground">{[r.instagramUsername, r.niche, r.location].filter(Boolean).join(' · ')}</p>
          </div>
          <dl className="grid grid-cols-4 gap-4 text-sm sm:w-[420px]">
            <div><dt className="text-xs text-muted-foreground">Completed</dt><dd className="num font-semibold">{r.completed}</dd></div>
            <div><dt className="text-xs text-muted-foreground">Your rating</dt><dd className="num font-semibold">{r.yourRating ? `${r.yourRating}/5` : '–'}</dd></div>
            <div><dt className="text-xs text-muted-foreground">Redeemed</dt><dd className="num font-semibold">{r.redemptions}</dd></div>
            <div><dt className="text-xs text-muted-foreground">Reel</dt><dd className="num font-semibold">{r.reelPrice ? formatINR(r.reelPrice) : '–'}</dd></div>
          </dl>
          <div className="flex items-center gap-2 sm:w-44 sm:justify-end">
            {r.lastCompletedId ? (
              <Button size="sm" onClick={() => repeat(r)} disabled={busy === r.creatorId} data-testid={`repeat-${r.creatorId}`}>
                {busy === r.creatorId ? <Loader2 className="animate-spin" /> : <Repeat />}Repeat campaign
              </Button>
            ) : (
              <span className="text-xs text-muted-foreground">{r.lastActivity ? `Active ${timeAgo(r.lastActivity)}` : 'Saved'}</span>
            )}
          </div>
        </div>
      ))}
    </div>
  );
};

export default MyCreators;
