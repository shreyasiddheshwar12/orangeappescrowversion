import { useState } from 'react';
import { Ticket, Loader2, Check } from 'lucide-react';
import { toast } from 'sonner';
import { Button } from '../ui/button';
import { Input } from '../ui/input';
import { trackingAPI, getErrorMessage } from '../../lib/api';

/** Counter tool: enter the code a customer shows to record a redemption. */
const RedeemCard = () => {
  const [code, setCode] = useState('');
  const [amount, setAmount] = useState('');
  const [busy, setBusy] = useState(false);
  const [last, setLast] = useState(null);

  const submit = async (e) => {
    e.preventDefault();
    setBusy(true);
    try {
      const res = await trackingAPI.redeem(code, amount ? Number(amount) : undefined);
      setLast(res.data);
      setCode(''); setAmount('');
    } catch (err) {
      toast.error(getErrorMessage(err, 'Code not found'));
    } finally {
      setBusy(false);
    }
  };

  return (
    <form onSubmit={submit} className="surface p-5" data-testid="redeem-card">
      <p className="flex items-center gap-2 font-semibold"><Ticket className="h-4 w-4 text-orange-700" />Redeem a customer's code</p>
      <div className="mt-3 flex flex-col gap-2 sm:flex-row">
        <Input value={code} onChange={(e) => setCode(e.target.value.toUpperCase())} placeholder="SNEHA-4F2K" className="font-mono sm:flex-1" data-testid="redeem-code" />
        <Input type="number" min="0" value={amount} onChange={(e) => setAmount(e.target.value)} placeholder="Bill ₹ (optional)" className="sm:w-40" />
        <Button type="submit" disabled={busy || code.trim().length < 3} data-testid="redeem-submit">{busy ? <Loader2 className="animate-spin" /> : <Check />}Redeem</Button>
      </div>
      {last && <p className="mt-3 text-sm text-sage-700">Recorded for {last.creatorName}. That code has now been redeemed {last.redemptions} time{last.redemptions === 1 ? '' : 's'}.</p>}
    </form>
  );
};

export default RedeemCard;
