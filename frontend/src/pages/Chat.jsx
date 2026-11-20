import { useState, useEffect, useRef, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { ArrowLeft, Send, Loader2, Lock, Paperclip, X, ExternalLink, ShieldAlert, Instagram, FileText } from 'lucide-react';
import { Button } from '../components/ui/button';
import StatusPill from '../components/orange/StatusPill';
import { campaignAPI, messagesAPI, uploadAPI, getErrorMessage } from '../lib/api';
import { useAuth } from '../lib/auth';
import { STATUS_META, LIFECYCLE, TYPE_LABEL, counterpartName, counterpartInstagram, nextStep, amountFor } from '../lib/collaborations';
import { formatINR, initials } from '../lib/format';
import { toast } from 'sonner';

const POLL_MS = 5000;

const dayLabel = (iso) => {
  const d = new Date(iso);
  const today = new Date();
  const yesterday = new Date(); yesterday.setDate(today.getDate() - 1);
  if (d.toDateString() === today.toDateString()) return 'Today';
  if (d.toDateString() === yesterday.toDateString()) return 'Yesterday';
  return d.toLocaleDateString('en-IN', { day: 'numeric', month: 'short' });
};
const timeLabel = (iso) => new Date(iso).toLocaleTimeString('en-IN', { hour: 'numeric', minute: '2-digit' });

const AttachmentView = ({ a, mine }) => {
  if (a.type === 'image') return <a href={a.url} target="_blank" rel="noopener noreferrer"><img src={a.url} alt={a.name || ''} className="max-h-60 rounded-md object-cover" /></a>;
  if (a.type === 'video') return <video src={a.url} controls className="max-h-60 rounded-md" />;
  return (
    <a href={a.url} target="_blank" rel="noopener noreferrer" className={`flex items-center gap-2 text-sm underline-offset-2 hover:underline ${mine ? 'text-white' : 'text-ink'}`}>
      <FileText className="h-4 w-4" />{a.name || 'Attachment'}
    </a>
  );
};

const Chat = () => {
  const { requestId } = useParams();
  const navigate = useNavigate();
  const { user } = useAuth();
  const [campaign, setCampaign] = useState(null);
  const [messages, setMessages] = useState([]);
  const [text, setText] = useState('');
  const [pending, setPending] = useState([]);
  const [uploading, setUploading] = useState(false);
  const [loading, setLoading] = useState(true);
  const [sending, setSending] = useState(false);
  const endRef = useRef(null);
  const fileRef = useRef(null);

  const loadMessages = useCallback(async () => {
    try {
      const res = await messagesAPI.getMessages(requestId);
      setMessages(res.data);
    } catch { /* polling: ignore transient errors */ }
  }, [requestId]);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const res = await campaignAPI.getById(requestId);
        if (cancelled) return;
        setCampaign(res.data);
        if (res.data.chatEnabled) await loadMessages();
      } catch (e) {
        toast.error(getErrorMessage(e, 'Could not open this conversation'));
        navigate(-1);
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => { cancelled = true; };
  }, [requestId, loadMessages, navigate]);

  // Poll only once chat is enabled; the effect re-runs when that changes.
  useEffect(() => {
    if (!campaign?.chatEnabled) return undefined;
    const id = setInterval(loadMessages, POLL_MS);
    return () => clearInterval(id);
  }, [campaign?.chatEnabled, loadMessages]);

  useEffect(() => { endRef.current?.scrollIntoView({ behavior: 'smooth' }); }, [messages.length]);

  const onFiles = async (files) => {
    if (!files?.length) return;
    setUploading(true);
    try {
      const uploaded = await Promise.all([...files].slice(0, 5 - pending.length).map((f) => uploadAPI.uploadFile(f)));
      setPending((p) => [...p, ...uploaded.map((r) => ({ url: r.data.url, type: r.data.type, name: r.data.filename, size: r.data.size }))]);
    } catch (e) {
      toast.error(getErrorMessage(e, 'Upload failed'));
    } finally {
      setUploading(false);
      if (fileRef.current) fileRef.current.value = '';
    }
  };

  const send = async (e) => {
    e.preventDefault();
    if (!text.trim() && !pending.length) return;
    setSending(true);
    try {
      const res = await messagesAPI.sendMessage(requestId, text, pending);
      setMessages((m) => [...m, res.data]);
      setText('');
      setPending([]);
      if (res.data.flagged) toast.warning('Contact details sent. Payments made outside Orange are not protected.');
    } catch (err) {
      toast.error(getErrorMessage(err, 'Message not sent'));
    } finally {
      setSending(false);
    }
  };

  if (loading) return <div className="flex min-h-screen items-center justify-center bg-background"><Loader2 className="h-6 w-6 animate-spin text-primary" /></div>;
  if (!campaign) return null;

  const role = user?.role;
  const step = nextStep(campaign, role, { incoming: campaign.receiverType === (role === 'business' ? 'brand' : 'creator') });
  const name = counterpartName(campaign, role);
  const handle = counterpartInstagram(campaign, role);
  const stepIndex = STATUS_META[campaign.status]?.step ?? -1;
  const dashboard = role === 'creator' ? '/dashboard/creator?view=collaborations' : '/dashboard/business?view=campaigns';

  let lastDay = '';

  return (
    <div className="flex h-screen flex-col bg-background">
      <header className="flex items-center gap-3 border-b border-border bg-white/80 px-4 py-3 backdrop-blur sm:px-6">
        <Button variant="ghost" size="icon" onClick={() => navigate(-1)} aria-label="Back" data-testid="back-btn"><ArrowLeft /></Button>
        <div className="flex h-9 w-9 items-center justify-center rounded-full bg-peach text-sm font-semibold text-orange-800">{initials(name)}</div>
        <div className="min-w-0 flex-1">
          <p className="truncate font-semibold text-ink">{name}</p>
          <p className="truncate text-xs text-muted-foreground">{TYPE_LABEL[campaign.campaignType]} · {campaign.deliverables}</p>
        </div>
        <StatusPill status={campaign.status} />
      </header>

      <div className="flex min-h-0 flex-1">
        {/* Conversation */}
        <section className="flex min-w-0 flex-1 flex-col">
          <div className="flex-1 overflow-y-auto px-4 py-6 sm:px-8">
            {!campaign.chatEnabled ? (
              <div className="mx-auto mt-16 max-w-sm text-center">
                <Lock className="mx-auto h-6 w-6 text-ink-300" />
                <p className="mt-3 font-display text-xl">Chat opens after payment</p>
                <p className="mt-1 text-sm text-muted-foreground">Once the brand pays, both sides can talk here and share files.</p>
              </div>
            ) : messages.length === 0 ? (
              <div className="mx-auto mt-16 max-w-sm text-center">
                <p className="font-display text-xl">Say hello</p>
                <p className="mt-1 text-sm text-muted-foreground">Agree on the shoot date, share references and keep everything in one place.</p>
              </div>
            ) : (
              <ol className="mx-auto max-w-2xl space-y-2">
                {messages.map((m) => {
                  const mine = m.senderId === user?.id;
                  const day = dayLabel(m.createdAt);
                  const showDay = day !== lastDay; lastDay = day;
                  return (
                    <li key={m.id}>
                      {showDay && <p className="my-4 text-center text-[11px] font-medium uppercase tracking-wider text-muted-foreground">{day}</p>}
                      <div className={`flex ${mine ? 'justify-end' : 'justify-start'}`}>
                        <div className={`max-w-[78%] rounded-xl px-3.5 py-2 ${m.blocked ? 'bg-brick-50 text-brick-700 ring-1 ring-brick-100' : mine ? 'rounded-br-sm bg-ink text-white' : 'rounded-bl-sm bg-white text-ink ring-1 ring-border'}`}>
                          {m.blocked && <ShieldAlert className="mb-1 h-4 w-4" />}
                          {(m.attachments || []).length > 0 && <div className="mb-1.5 space-y-1.5">{m.attachments.map((a, i) => <AttachmentView key={i} a={a} mine={mine} />)}</div>}
                          {m.content && <p className="whitespace-pre-wrap text-[15px] leading-relaxed">{m.content}</p>}
                          <p className={`mt-0.5 text-right text-[10px] ${mine ? 'text-white/60' : 'text-muted-foreground'}`}>{timeLabel(m.createdAt)}</p>
                        </div>
                      </div>
                      {m.flagged && (
                        <p className={`mt-1 flex items-center gap-1 text-[11px] text-amber-700 ${mine ? 'justify-end' : 'justify-start'}`}>
                          <ShieldAlert className="h-3 w-3" />Contact details shared. Deals and payments outside Orange aren't protected.
                        </p>
                      )}
                    </li>
                  );
                })}
                <div ref={endRef} />
              </ol>
            )}
          </div>

          {campaign.chatEnabled && (
            <form onSubmit={send} className="border-t border-border bg-white px-4 py-3 sm:px-8">
              {pending.length > 0 && (
                <div className="mx-auto mb-2 flex max-w-2xl flex-wrap gap-2">
                  {pending.map((a, i) => (
                    <span key={a.url} className="flex items-center gap-1.5 rounded-full bg-stone px-2.5 py-1 text-xs">
                      <Paperclip className="h-3 w-3" />{a.name || a.type}
                      <button type="button" aria-label="Remove attachment" onClick={() => setPending((p) => p.filter((_, j) => j !== i))}><X className="h-3 w-3" /></button>
                    </span>
                  ))}
                </div>
              )}
              <div className="mx-auto flex max-w-2xl items-end gap-2">
                <input ref={fileRef} type="file" accept="image/*,video/*" multiple className="hidden" onChange={(e) => onFiles(e.target.files)} />
                <Button type="button" variant="ghost" size="icon" onClick={() => fileRef.current?.click()} disabled={uploading || pending.length >= 5} aria-label="Attach files">
                  {uploading ? <Loader2 className="animate-spin" /> : <Paperclip />}
                </Button>
                <textarea
                  value={text}
                  onChange={(e) => setText(e.target.value)}
                  onKeyDown={(e) => { if (e.key === 'Enter' && !e.shiftKey) send(e); }}
                  rows={1}
                  placeholder="Write a message"
                  className="max-h-40 min-h-[40px] flex-1 resize-none rounded-md border border-input bg-white px-3 py-2 text-[15px] focus:border-primary focus:outline-none focus:ring-2 focus:ring-ring/40"
                  data-testid="message-input"
                />
                <Button type="submit" size="icon" disabled={sending || (!text.trim() && !pending.length)} aria-label="Send" data-testid="send-btn">
                  {sending ? <Loader2 className="animate-spin" /> : <Send />}
                </Button>
              </div>
            </form>
          )}
        </section>

        {/* Campaign context */}
        <aside className="hidden w-[320px] shrink-0 overflow-y-auto border-l border-border bg-[#FFFCF8] p-5 lg:block">
          <p className="eyebrow">Collaboration</p>
          {stepIndex >= 0 && (
            <ol className="mt-3 space-y-2">
              {LIFECYCLE.map((label, i) => (
                <li key={label} className="flex items-center gap-2 text-sm">
                  <span className={`h-2 w-2 rounded-full ${i < stepIndex ? 'bg-sage-400' : i === stepIndex ? 'bg-primary ring-4 ring-orange-100' : 'bg-stone ring-1 ring-border'}`} />
                  <span className={i === stepIndex ? 'font-semibold text-ink' : i < stepIndex ? 'text-ink-500' : 'text-muted-foreground'}>{label}</span>
                </li>
              ))}
            </ol>
          )}
          <div className={`mt-5 rounded-lg border p-3 text-sm ${step.who === 'you' ? 'border-orange-200 bg-orange-50' : 'border-border bg-white'}`}>
            <p className="eyebrow mb-1">{step.who === 'you' ? 'Your next step' : 'Next step'}</p>
            <p className="font-medium">{step.label}</p>
            {step.action && step.action !== 'rate' && (
              <Button size="sm" className="mt-3 w-full" onClick={() => navigate(dashboard)}>Open in workspace</Button>
            )}
          </div>
          <dl className="mt-5 space-y-3 text-sm">
            <div><dt className="eyebrow">Value</dt><dd className="num mt-1 font-semibold">{formatINR(amountFor(campaign))}{campaign.campaignType === 'paid' ? ' held by Orange' : ' barter fee'}</dd></div>
            <div><dt className="eyebrow">Deliverables</dt><dd className="mt-1">{campaign.deliverables}</dd></div>
            {campaign.timeline && <div><dt className="eyebrow">Timeline</dt><dd className="mt-1">{campaign.timeline}</dd></div>}
            {campaign.brief && <div><dt className="eyebrow">Brief</dt><dd className="mt-1 whitespace-pre-line">{campaign.brief}</dd></div>}
            {campaign.contentLink && (
              <div><dt className="eyebrow">Submitted content</dt>
                <dd className="mt-1"><a href={campaign.contentLink} target="_blank" rel="noopener noreferrer" className="flex items-center gap-1 break-all font-medium text-orange-800 hover:underline"><ExternalLink className="h-3.5 w-3.5 shrink-0" />{campaign.contentLink}</a></dd>
              </div>
            )}
            {campaign.identityUnlocked && handle && (
              <div><dt className="eyebrow">Instagram</dt><dd className="mt-1 flex items-center gap-1.5"><Instagram className="h-3.5 w-3.5" />{handle}</dd></div>
            )}
          </dl>
          <p className="mt-6 text-xs text-muted-foreground">Keep payments and agreements on Orange so both sides stay protected.</p>
        </aside>
      </div>
    </div>
  );
};

export default Chat;
