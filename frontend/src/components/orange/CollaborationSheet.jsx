import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Check, X, Loader2, MessageSquare, ExternalLink, Star, Flag, Instagram, ShieldCheck } from 'lucide-react';
import { Sheet, SheetContent, SheetHeader, SheetTitle, SheetDescription } from '../ui/sheet';
import { Button } from '../ui/button';
import { Input } from '../ui/input';
import { Textarea } from '../ui/textarea';
import StatusPill from './StatusPill';
import TrackingCard from './TrackingCard';
import { STATUS_META, LIFECYCLE, TYPE_LABEL, counterpartName, counterpartInstagram, nextStep } from '../../lib/collaborations';
import { formatINR } from '../../lib/format';

const Row = ({ label, children }) => (
  <div className="flex items-start justify-between gap-4 py-2 text-sm">
    <span className="text-muted-foreground">{label}</span>
    <span className="num text-right font-medium text-ink">{children}</span>
  </div>
);

const Lifecycle = ({ status }) => {
  const step = STATUS_META[status]?.step ?? -1;
  if (step < 0) return null;
  return (
    <ol className="flex items-center gap-1" aria-label="Progress">
      {LIFECYCLE.map((label, i) => (
        <li key={label} className="flex flex-1 flex-col gap-1.5">
          <span className={`h-1 rounded-full ${i <= step ? 'bg-primary' : 'bg-stone'}`} />
          <span className={`text-[10px] ${i === step ? 'font-semibold text-ink' : 'text-muted-foreground'}`}>{label}</span>
        </li>
      ))}
    </ol>
  );
};

const TRACKABLE = ['accepted', 'payment_pending', 'paid', 'in_progress', 'link_submitted', 'link_verified', 'completed'];

const CollaborationSheet = ({ collab, role, open, onOpenChange, actions, busy }) => {
  const navigate = useNavigate();
  const [link, setLink] = useState('');
  const [shipping, setShipping] = useState('');
  const [rating, setRating] = useState(5);
  const [feedback, setFeedback] = useState('');
  const [reporting, setReporting] = useState(false);
  const [reason, setReason] = useState('');

  useEffect(() => { setLink(''); setShipping(''); setFeedback(''); setRating(5); setReporting(false); setReason(''); }, [collab?.id]);

  if (!collab) return null;
  const step = nextStep(collab, role, { incoming: collab._incoming });
  const isBusy = (key) => busy === `${key}:${collab.id}`;
  const handle = counterpartInstagram(collab, role);
  const after = async (promise) => { const res = await promise; if (res) onOpenChange(false); };

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent className="w-full overflow-y-auto bg-background sm:max-w-[480px]">
        <SheetHeader className="space-y-3 text-left">
          <div className="flex items-center gap-2">
            <StatusPill status={collab.status} />
            <span className="text-xs text-muted-foreground">{TYPE_LABEL[collab.campaignType]} · {collab._incoming ? 'Received' : 'Sent'}</span>
          </div>
          <SheetTitle className="display text-2xl">{counterpartName(collab, role)}</SheetTitle>
          <SheetDescription>{collab.deliverables}</SheetDescription>
        </SheetHeader>

        <div className="mt-6 space-y-6">
          <Lifecycle status={collab.status} />

          {/* Next step */}
          <div className={`rounded-lg border p-4 ${step.who === 'you' ? 'border-orange-200 bg-orange-50' : 'border-border bg-white'}`} data-testid="next-step">
            <p className="eyebrow mb-1">{step.who === 'you' ? 'Your next step' : 'Next step'}</p>
            <p className="font-medium text-ink">{step.label}</p>

            {step.action === 'respond' && (
              <div className="mt-3 flex gap-2">
                <Button className="flex-1" onClick={() => after(actions.accept(collab))} disabled={!!busy} data-testid="accept-btn">
                  {isBusy('accept') ? <Loader2 className="animate-spin" /> : <Check />}Accept
                </Button>
                <Button variant="outline" className="flex-1" onClick={() => after(actions.decline(collab))} disabled={!!busy} data-testid="decline-btn"><X />Decline</Button>
              </div>
            )}
            {step.action === 'pay' && (
              <>
                <Button className="mt-3 w-full" onClick={() => after(actions.pay(collab))} disabled={!!busy} data-testid="pay-btn">
                  {isBusy('pay') ? <Loader2 className="animate-spin" /> : <ShieldCheck />}{step.label}
                </Button>
                <p className="mt-2 text-xs text-muted-foreground">
                  {collab.campaignType === 'paid'
                    ? 'Your payment is held by Orange and released to the creator only after you approve the content.'
                    : 'This is the Orange barter fee. You provide the product or service directly.'}
                </p>
              </>
            )}
            {step.action === 'ship' && (
              <div className="mt-3 space-y-2">
                <Input value={shipping} onChange={(e) => setShipping(e.target.value)} placeholder="Courier and tracking number, or pickup details" />
                <Button className="w-full" disabled={!shipping.trim() || !!busy} onClick={() => actions.ship(collab, shipping)}>
                  {isBusy('ship') && <Loader2 className="animate-spin" />}Save shipping details
                </Button>
              </div>
            )}
            {step.action === 'receive' && (
              <Button className="mt-3 w-full" disabled={!!busy} onClick={() => actions.receive(collab)}>
                {isBusy('receive') && <Loader2 className="animate-spin" />}I received it
              </Button>
            )}
            {step.action === 'submit' && (
              <div className="mt-3 space-y-2">
                <Input value={link} onChange={(e) => setLink(e.target.value)} placeholder="https://www.instagram.com/reel/…" data-testid="content-link-input" />
                <Button className="w-full" disabled={!/^https?:\/\//.test(link) || !!busy} onClick={() => after(actions.submit(collab, link))} data-testid="submit-link-btn">
                  {isBusy('submit') && <Loader2 className="animate-spin" />}Submit for review
                </Button>
              </div>
            )}
            {step.action === 'verify' && (
              <div className="mt-3 space-y-2">
                <a href={collab.contentLink} target="_blank" rel="noopener noreferrer" className="flex items-center gap-1.5 break-all text-sm font-medium text-orange-800 underline-offset-2 hover:underline">
                  <ExternalLink className="h-4 w-4 shrink-0" />{collab.contentLink}
                </a>
                <Button className="w-full" disabled={!!busy} onClick={() => after(actions.verify(collab))} data-testid="verify-btn">
                  {isBusy('verify') ? <Loader2 className="animate-spin" /> : <Check />}Approve content
                </Button>
              </div>
            )}
            {step.action === 'complete' && (
              <Button className="mt-3 w-full" disabled={!!busy} onClick={() => after(actions.complete(collab))} data-testid="complete-btn">
                {isBusy('complete') && <Loader2 className="animate-spin" />}{step.label}
              </Button>
            )}
            {step.action === 'rate' && (
              <div className="mt-3 space-y-2">
                <div className="flex gap-1" role="radiogroup" aria-label="Rating">
                  {[1, 2, 3, 4, 5].map((s) => (
                    <button key={s} onClick={() => setRating(s)} aria-label={`${s} stars`} className={rating >= s ? 'text-primary' : 'text-ink-300'}>
                      <Star className="h-6 w-6 fill-current" />
                    </button>
                  ))}
                </div>
                <Textarea value={feedback} onChange={(e) => setFeedback(e.target.value)} placeholder="How did it go? At least 10 characters." />
                <Button className="w-full" disabled={feedback.trim().length < 10 || !!busy} onClick={() => after(actions.rate(collab, rating, feedback))}>
                  {isBusy('rate') && <Loader2 className="animate-spin" />}Submit rating
                </Button>
              </div>
            )}
          </div>

          {TRACKABLE.includes(collab.status) && <TrackingCard campaignId={collab.id} isBrand={role === 'business'} />}

          {/* Money */}
          <div className="surface px-4 py-2">
            {collab.campaignType === 'paid' ? (
              <>
                <Row label="Budget">{formatINR(collab.budget)}</Row>
                <Row label="Orange commission (10%)">{formatINR(collab.platformCommission)}</Row>
                <Row label="Creator receives">{formatINR(collab.creatorPayout)}</Row>
                <Row label="Payment">{collab.status === 'completed' ? 'Released' : collab.paymentStatus === 'paid' ? 'Held by Orange' : 'Not paid yet'}</Row>
                {collab.payoutStatus && <Row label="Payout">{collab.payoutStatus === 'released' ? 'Released' : 'Pending creator payout setup'}</Row>}
              </>
            ) : (
              <>
                <Row label="Product or service value">{formatINR(collab.productValue)}</Row>
                <Row label="Orange barter fee">{formatINR(collab.barterFee)}</Row>
                <Row label="Fee">{collab.paymentStatus === 'paid' ? 'Paid' : 'Not paid yet'}</Row>
              </>
            )}
          </div>

          {/* Details */}
          <div className="space-y-3 text-sm">
            {collab.timeline && <div><p className="eyebrow mb-1">Timeline</p><p>{collab.timeline}</p></div>}
            {collab.brief && <div><p className="eyebrow mb-1">Brief</p><p className="whitespace-pre-line">{collab.brief}</p></div>}
            {collab.barterDetails && <div><p className="eyebrow mb-1">Barter offer</p><p>{collab.barterDetails}</p></div>}
            {collab.shippingDetails && <div><p className="eyebrow mb-1">Shipping</p><p>{collab.shippingDetails}{collab.productReceived ? ' · Received' : ''}</p></div>}
            {collab.contentLink && step.action !== 'verify' && (
              <div><p className="eyebrow mb-1">Content</p>
                <a href={collab.contentLink} target="_blank" rel="noopener noreferrer" className="break-all font-medium text-orange-800 hover:underline">{collab.contentLink}</a>
              </div>
            )}
            {collab.identityUnlocked && handle && (
              <div className="flex items-center gap-2 rounded-md bg-sage-50 px-3 py-2 text-sage-700"><Instagram className="h-4 w-4" />{handle}</div>
            )}
          </div>

          <div className="flex flex-col gap-2">
            {collab.chatEnabled && (
              <Button variant="outline" onClick={() => navigate(`/chat/${collab.id}`)} data-testid="open-chat-btn"><MessageSquare />Open conversation</Button>
            )}
            {!['completed', 'cancelled', 'disputed', 'requested'].includes(collab.status) && (
              reporting ? (
                <div className="space-y-2 rounded-lg border border-border bg-white p-3">
                  <Textarea value={reason} onChange={(e) => setReason(e.target.value)} placeholder="What went wrong?" />
                  <div className="flex gap-2">
                    <Button variant="destructive" className="flex-1" disabled={reason.trim().length < 5 || !!busy} onClick={() => after(actions.report(collab, reason))}>Report issue</Button>
                    <Button variant="ghost" onClick={() => setReporting(false)}>Cancel</Button>
                  </div>
                </div>
              ) : (
                <button onClick={() => setReporting(true)} className="flex items-center justify-center gap-1.5 py-2 text-xs text-muted-foreground hover:text-brick-700"><Flag className="h-3.5 w-3.5" />Report a problem</button>
              )
            )}
          </div>
        </div>
      </SheetContent>
    </Sheet>
  );
};

export default CollaborationSheet;
