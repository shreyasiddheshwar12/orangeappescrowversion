import { useEffect, useState } from 'react';
import { Loader2, Send } from 'lucide-react';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from '../ui/dialog';
import { Button } from '../ui/button';
import { Input } from '../ui/input';
import { Label } from '../ui/label';
import { Textarea } from '../ui/textarea';
import { formatINR } from '../../lib/format';

const TYPES = [
  { value: 'paid', label: 'Paid', hint: 'Money held by Orange until content is approved' },
  { value: 'barter_product', label: 'Product barter', hint: 'Creator receives a product' },
  { value: 'barter_service', label: 'Service barter', hint: 'Creator receives a service or experience' },
];

/**
 * Collaboration request form. `target` = { id, type: 'creator' | 'brand', title, subtitle, suggestedBudget }.
 */
const RequestDialog = ({ open, onOpenChange, target, onSubmit, busy }) => {
  const [form, setForm] = useState({ campaignType: 'paid', deliverables: '', budget: '', productValue: '', timeline: '7 days', brief: '', barterDetails: '' });

  useEffect(() => {
    if (open) setForm({ campaignType: 'paid', deliverables: '', budget: target?.suggestedBudget ? String(target.suggestedBudget) : '', productValue: '', timeline: '7 days', brief: '', barterDetails: '' });
  }, [open, target]);

  const set = (k, v) => setForm((f) => ({ ...f, [k]: v }));
  const paid = form.campaignType === 'paid';
  const budget = Number(form.budget) || 0;
  const value = Number(form.productValue) || 0;
  const valid = form.deliverables.trim() && (paid ? budget > 0 : value > 0);

  const submit = async () => {
    const res = await onSubmit({
      receiverId: target.id,
      receiverType: target.type,
      campaignType: form.campaignType,
      deliverables: form.deliverables,
      budget: paid ? budget : 0,
      productValue: paid ? 0 : value,
      timeline: form.timeline,
      brief: form.brief,
      barterDetails: paid ? '' : form.barterDetails,
    });
    if (res) onOpenChange(false);
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-h-[90vh] overflow-y-auto sm:max-w-[520px]">
        <DialogHeader>
          <DialogTitle className="display text-2xl">Propose a collaboration</DialogTitle>
          <DialogDescription>{target?.title}{target?.subtitle ? ` · ${target.subtitle}` : ''}. They have 72 hours to respond.</DialogDescription>
        </DialogHeader>
        <div className="space-y-5 pt-2">
          <div className="grid grid-cols-3 gap-2" role="radiogroup">
            {TYPES.map((t) => (
              <button
                key={t.value}
                role="radio"
                aria-checked={form.campaignType === t.value}
                onClick={() => set('campaignType', t.value)}
                className={`rounded-lg border p-3 text-left transition-colors ${form.campaignType === t.value ? 'border-primary bg-orange-50 ring-1 ring-primary' : 'border-border bg-white hover:bg-stone'}`}
              >
                <p className="text-sm font-semibold">{t.label}</p>
                <p className="mt-0.5 text-[11px] leading-tight text-muted-foreground">{t.hint}</p>
              </button>
            ))}
          </div>
          <div className="space-y-1.5">
            <Label>Deliverables</Label>
            <Input value={form.deliverables} onChange={(e) => set('deliverables', e.target.value)} placeholder="1 reel and 2 stories" data-testid="deliverables-input" />
          </div>
          {paid ? (
            <div className="space-y-1.5">
              <Label>Budget (₹)</Label>
              <Input type="number" inputMode="numeric" value={form.budget} onChange={(e) => set('budget', e.target.value)} data-testid="budget-input" />
              {budget > 0 && <p className="num text-xs text-muted-foreground">Creator receives {formatINR(budget * 0.9)} after the 10% Orange commission.</p>}
            </div>
          ) : (
            <div className="grid gap-4 sm:grid-cols-2">
              <div className="space-y-1.5">
                <Label>Value of the offer (₹)</Label>
                <Input type="number" inputMode="numeric" value={form.productValue} onChange={(e) => set('productValue', e.target.value)} />
                {value > 0 && <p className="num text-xs text-muted-foreground">Orange fee {formatINR(value * 0.1)}, paid by the brand.</p>}
              </div>
              <div className="space-y-1.5">
                <Label>What's offered</Label>
                <Input value={form.barterDetails} onChange={(e) => set('barterDetails', e.target.value)} placeholder="Dinner for two" />
              </div>
            </div>
          )}
          <div className="space-y-1.5">
            <Label>Timeline</Label>
            <Input value={form.timeline} onChange={(e) => set('timeline', e.target.value)} placeholder="Post by Saturday" />
          </div>
          <div className="space-y-1.5">
            <Label>Brief <span className="font-normal text-muted-foreground">(optional)</span></Label>
            <Textarea value={form.brief} onChange={(e) => set('brief', e.target.value)} placeholder="What should the content show? Any must-haves?" />
          </div>
          <Button className="w-full" size="lg" onClick={submit} disabled={!valid || busy} data-testid="submit-request-btn">
            {busy ? <Loader2 className="animate-spin" /> : <Send />}Send request
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
};

export default RequestDialog;
