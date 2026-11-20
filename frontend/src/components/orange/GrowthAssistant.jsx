import { useCallback, useEffect, useRef, useState } from 'react';
import { ArrowRight, Check, ChevronDown, ChevronUp, Loader2, Sparkles, X, AlertCircle } from 'lucide-react';
import { toast } from 'sonner';
import { Button } from '../ui/button';
import { Input } from '../ui/input';
import { Textarea } from '../ui/textarea';
import { Pill } from './StatusPill';
import { growthAPI, getErrorMessage } from '../../lib/api';
import { formatINR, formatCount, timeAgo } from '../../lib/format';

const LIVE = ['running', 'launching'];
const FACTOR_LABEL = { niche: 'Niche', location: 'Area', price: 'Price', trust: 'Track record', engagement: 'Engagement', language: 'Language', availability: 'Availability' };

const EngineTag = ({ engine }) => engine ? (
  <span className={`rounded px-1.5 py-0.5 text-[10px] font-semibold uppercase tracking-wide ${engine === 'claude' ? 'bg-plum-50 text-plum-700' : 'bg-stone text-ink-500'}`}>
    {engine === 'claude' ? 'AI' : 'Rules'}
  </span>
) : null;

const StepDot = ({ status }) => {
  if (status === 'done') return <span className="flex h-5 w-5 items-center justify-center rounded-full bg-sage-400 text-white"><Check className="h-3 w-3" /></span>;
  if (status === 'running') return <span className="flex h-5 w-5 items-center justify-center rounded-full bg-plum"><span className="h-1.5 w-1.5 animate-pulse-dot rounded-full bg-white" /></span>;
  if (status === 'failed') return <span className="flex h-5 w-5 items-center justify-center rounded-full bg-brick-500 text-white"><X className="h-3 w-3" /></span>;
  return <span className="h-5 w-5 rounded-full ring-1 ring-inset ring-border bg-white" />;
};

/** The agent timeline: one row per step, live while the run works. */
const Timeline = ({ steps, awaiting }) => (
  <ol className="relative space-y-4">
    {steps.map((s, i) => (
      <li key={s.id} className="relative flex gap-3">
        {(i < steps.length - 1 || awaiting) && <span className="absolute left-[9px] top-6 h-[calc(100%-4px)] w-px bg-border" />}
        <StepDot status={s.status} />
        <div className="min-w-0 flex-1 pb-1">
          <div className="flex items-center gap-2">
            <p className="text-xs font-semibold text-plum">{s.agentName}</p>
            <EngineTag engine={s.engine} />
          </div>
          <p className={`text-sm ${s.status === 'pending' || s.status === 'skipped' ? 'text-muted-foreground' : 'text-ink'}`}>
            {s.status === 'failed' ? s.error : s.summary || s.title}
          </p>
        </div>
      </li>
    ))}
    {awaiting && (
      <li className="relative flex gap-3">
        <span className="h-5 w-5 rounded-full bg-orange-50 ring-1 ring-inset ring-orange-300" />
        <p className="text-sm font-medium text-orange-800">Waiting for you to approve the plan</p>
      </li>
    )}
  </ol>
);

const MatchCard = ({ c, selected, onToggle }) => {
  const [open, setOpen] = useState(false);
  return (
    <div className={`rounded-xl border bg-white p-4 transition-shadow ${selected ? 'border-primary ring-2 ring-primary/30' : 'border-border'}`}>
      <div className="flex items-start gap-3">
        <button
          onClick={onToggle}
          aria-pressed={selected}
          aria-label={selected ? `Remove ${c.name}` : `Choose ${c.name}`}
          className={`mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded border ${selected ? 'border-primary bg-primary text-ink' : 'border-ink-200 bg-white'}`}
        >
          {selected && <Check className="h-3.5 w-3.5" />}
        </button>
        <div className="min-w-0 flex-1">
          <div className="flex items-start justify-between gap-3">
            <div className="min-w-0">
              <p className="truncate font-semibold">{c.name}</p>
              <p className="truncate text-sm text-muted-foreground">{c.instagramUsername || 'Handle not set'} · {c.location || 'Location not set'}</p>
            </div>
            <div className="text-right">
              <p className="num font-display text-2xl leading-none text-orange-700">{c.score}%</p>
              <p className="text-[11px] text-muted-foreground">match</p>
            </div>
          </div>
          <p className="mt-2 text-sm text-ink-500">
            {c.niche} · Reel {c.reelPrice ? formatINR(c.reelPrice) : 'price not set'}
            {c.followersCount ? ` · ${formatCount(c.followersCount)} followers` : ''}
          </p>
          <button onClick={() => setOpen((o) => !o)} className="mt-2 inline-flex items-center gap-1 text-xs font-medium text-ink-500 hover:text-ink">
            Why this creator {open ? <ChevronUp className="h-3.5 w-3.5" /> : <ChevronDown className="h-3.5 w-3.5" />}
          </button>
          {open && (
            <ul className="mt-2 space-y-1.5 border-t border-border pt-2">
              {c.breakdown.map((b) => (
                <li key={b.factor} className="flex gap-2 text-xs">
                  <span className="w-24 shrink-0 font-medium text-ink">{FACTOR_LABEL[b.factor]}</span>
                  <span className="flex-1 text-ink-500">{b.reason}</span>
                  <span className="num w-10 shrink-0 text-right text-muted-foreground">{b.points === null ? '–' : `${b.points}/${b.weight}`}</span>
                </li>
              ))}
              <li className="pt-1 text-[11px] text-muted-foreground">Score is based on {c.coverage} of 100 points we have data for. Missing data never counts against a creator.</li>
            </ul>
          )}
        </div>
      </div>
    </div>
  );
};

const PlanCard = ({ plan, business }) => (
  <div className="surface p-5">
    <p className="eyebrow">The plan</p>
    <h3 className="mt-1 font-display text-2xl">{plan.campaignName}</h3>
    <p className="mt-1 text-sm text-ink-500">{plan.objective}</p>
    <dl className="mt-4 grid grid-cols-2 gap-3 text-sm sm:grid-cols-4">
      <div><dt className="text-muted-foreground">Creators</dt><dd className="num font-semibold">{plan.creatorCount}</dd></div>
      <div><dt className="text-muted-foreground">{plan.campaignType === 'paid' ? 'Each' : 'Product value'}</dt><dd className="num font-semibold">{formatINR(plan.budgetPerCreator)}</dd></div>
      <div><dt className="text-muted-foreground">Content</dt><dd className="font-semibold">{plan.deliverables}</dd></div>
      <div><dt className="text-muted-foreground">When</dt><dd className="font-semibold">{plan.timeline}</dd></div>
    </dl>
    {plan.contentIdeas?.length > 0 && (
      <ul className="mt-4 space-y-1 text-sm">
        {plan.contentIdeas.map((idea) => <li key={idea} className="flex gap-2"><Sparkles className="mt-0.5 h-3.5 w-3.5 shrink-0 text-plum" />{idea}</li>)}
      </ul>
    )}
    {business?.gaps?.length > 0 && (
      <p className="mt-4 rounded-md bg-stone px-3 py-2 text-xs text-ink-500">{business.gaps.join(' ')}</p>
    )}
  </div>
);

const GrowthAssistant = ({ onOpenCollaborations }) => {
  const [runs, setRuns] = useState([]);
  const [run, setRun] = useState(null);
  const [loading, setLoading] = useState(true);
  const [goal, setGoal] = useState('');
  const [budget, setBudget] = useState('');
  const [starting, setStarting] = useState(false);
  const [selected, setSelected] = useState([]);
  const [sending, setSending] = useState(false);
  const preselectedFor = useRef(null);

  const loadRun = useCallback(async (id) => {
    const res = await growthAPI.getRun(id);
    setRun(res.data);
    return res.data;
  }, []);

  useEffect(() => {
    growthAPI.listRuns()
      .then(async (res) => {
        setRuns(res.data);
        const latest = res.data[0];
        if (latest && ['running', 'launching', 'awaiting_approval'].includes(latest.status)) await loadRun(latest.id);
      })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [loadRun]);

  // Poll while agents are working.
  useEffect(() => {
    if (!run || !LIVE.includes(run.status)) return undefined;
    const t = setInterval(() => { loadRun(run.id).catch(() => {}); }, 1500);
    return () => clearInterval(t);
  }, [run, loadRun]);

  // Preselect the plan's number of top matches once, when the shortlist arrives.
  useEffect(() => {
    if (run?.status === 'awaiting_approval' && preselectedFor.current !== run.id) {
      const plan = run.outputs?.marketing_planner;
      const creators = run.outputs?.creator_matching?.creators || [];
      setSelected(creators.slice(0, plan?.creatorCount || 3).map((c) => c.creatorId));
      preselectedFor.current = run.id;
    }
  }, [run]);

  const start = async (e) => {
    e.preventDefault();
    setStarting(true);
    try {
      const res = await growthAPI.startRun({ goal, budget: budget ? Number(budget) : undefined });
      setRun(res.data);
      setRuns((r) => [res.data, ...r]);
    } catch (err) {
      toast.error(getErrorMessage(err, 'Could not start the assistant'));
    } finally {
      setStarting(false);
    }
  };

  const approve = async () => {
    setSending(true);
    try {
      const res = await growthAPI.approve(run.id, { creatorIds: selected });
      setRun(res.data);
    } catch (err) {
      toast.error(getErrorMessage(err, 'Could not send requests'));
    } finally {
      setSending(false);
    }
  };

  const dismiss = async () => {
    await growthAPI.dismiss(run.id).catch(() => {});
    setRun(null);
  };

  const reset = () => { setRun(null); setGoal(''); setBudget(''); };

  if (loading) return <div className="flex justify-center py-20"><Loader2 className="h-6 w-6 animate-spin text-primary" /></div>;

  // Composer
  if (!run) {
    return (
      <div className="mx-auto max-w-2xl space-y-8">
        <form onSubmit={start} className="surface space-y-4 p-6">
          <div className="flex items-center gap-3">
            <span className="flex h-9 w-9 items-center justify-center rounded-full bg-plum text-white"><Sparkles className="h-4 w-4" /></span>
            <h2 className="font-display text-2xl">What do you want to achieve?</h2>
          </div>
          <Textarea
            value={goal}
            onChange={(e) => setGoal(e.target.value)}
            placeholder="More college students visiting my café this month"
            rows={3}
            data-testid="growth-goal"
          />
          <div className="flex flex-col gap-3 sm:flex-row sm:items-end">
            <label className="flex-1 text-sm">
              <span className="mb-1.5 block text-muted-foreground">Budget (optional)</span>
              <Input type="number" min="0" inputMode="numeric" value={budget} onChange={(e) => setBudget(e.target.value)} placeholder="15000" />
            </label>
            <Button type="submit" size="lg" disabled={starting || goal.trim().length < 5} data-testid="growth-start">
              {starting ? <Loader2 className="animate-spin" /> : <Sparkles />}Make a plan
            </Button>
          </div>
          <p className="text-xs text-muted-foreground">Nothing is sent to creators until you approve.</p>
        </form>

        {runs.length > 0 && (
          <div>
            <p className="eyebrow mb-2">Earlier plans</p>
            <ul className="surface divide-y divide-border">
              {runs.slice(0, 5).map((r) => (
                <li key={r.id}>
                  <button onClick={() => loadRun(r.id)} className="flex w-full items-center justify-between gap-3 px-4 py-3 text-left hover:bg-stone/50">
                    <span className="truncate text-sm">{r.goal}</span>
                    <span className="flex shrink-0 items-center gap-2 text-xs text-muted-foreground">
                      <Pill tone={r.status === 'completed' ? 'sage' : r.status === 'failed' ? 'brick' : 'neutral'}>{r.status.replace('_', ' ')}</Pill>
                      {timeAgo(r.createdAt)}
                    </span>
                  </button>
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>
    );
  }

  const plan = run.approval?.plan || run.outputs?.marketing_planner;
  const creators = run.outputs?.creator_matching?.creators || [];
  const launch = run.outputs?.campaign_assistant;
  const awaiting = run.status === 'awaiting_approval';

  return (
    <div className="grid gap-6 lg:grid-cols-[320px_1fr]">
      <aside className="space-y-4">
        <div className="surface p-5">
          <p className="eyebrow">Your goal</p>
          <p className="mt-1 text-sm">{run.goal}</p>
          <div className="mt-5 hairline pt-5">
            <Timeline steps={run.steps || []} awaiting={awaiting} />
          </div>
        </div>
        {!LIVE.includes(run.status) && <Button variant="outline" className="w-full" onClick={reset}>New plan</Button>}
      </aside>

      <section className="space-y-5">
        {LIVE.includes(run.status) && !plan && (
          <div className="surface flex items-center gap-3 p-6 text-sm text-ink-500"><Loader2 className="h-4 w-4 animate-spin text-plum" />Working on your plan…</div>
        )}

        {run.status === 'failed' && (
          <div className="flex items-start gap-3 rounded-xl border border-brick-100 bg-brick-50 p-4 text-sm text-brick-700">
            <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />
            <div>{run.error || 'The assistant stopped.'} <button className="font-semibold underline" onClick={reset}>Try again</button></div>
          </div>
        )}

        {plan && <PlanCard plan={plan} business={run.outputs?.business_intelligence} />}

        {awaiting && (
          <div className="space-y-3">
            <div className="flex items-end justify-between gap-3">
              <div>
                <h3 className="font-display text-xl">Pick your creators</h3>
                <p className="text-sm text-muted-foreground">We picked the top {Math.min(plan?.creatorCount || 3, creators.length)}. Change it if you like.</p>
              </div>
            </div>
            {creators.length === 0 ? (
              <p className="surface p-5 text-sm text-ink-500">No creators on Orange match this plan yet. Try a different goal or a larger budget.</p>
            ) : (
              <div className="grid items-start gap-3 xl:grid-cols-2">
                {creators.map((c) => (
                  <MatchCard
                    key={c.creatorId}
                    c={c}
                    selected={selected.includes(c.creatorId)}
                    onToggle={() => setSelected((s) => (s.includes(c.creatorId) ? s.filter((x) => x !== c.creatorId) : s.length >= 6 ? s : [...s, c.creatorId]))}
                  />
                ))}
              </div>
            )}
            <div className="sticky bottom-0 z-10 flex flex-col gap-2 border-t border-border bg-background py-3 sm:flex-row sm:justify-end">
              <Button variant="ghost" onClick={dismiss}>Dismiss</Button>
              <Button size="lg" onClick={approve} disabled={!selected.length || sending} data-testid="growth-approve">
                {sending ? <Loader2 className="animate-spin" /> : <Check />}Send requests to {selected.length} creator{selected.length === 1 ? '' : 's'}
              </Button>
            </div>
          </div>
        )}

        {run.status === 'completed' && launch && (
          <div className="surface p-5">
            <p className="font-display text-xl">Requests sent</p>
            <ul className="mt-3 space-y-1 text-sm">
              {launch.sent.map((s) => <li key={s.campaignId} className="flex items-center gap-2"><Check className="h-4 w-4 text-sage-600" />{s.name}</li>)}
              {launch.failed.map((f) => <li key={f.creatorId} className="flex items-center gap-2 text-brick-700"><X className="h-4 w-4" />{f.name}: {f.reason}</li>)}
            </ul>
            <p className="mt-3 text-sm text-ink-500">You'll pay each creator once they accept. Orange holds the money until you approve their content.</p>
            <Button className="mt-4" onClick={onOpenCollaborations}>View collaborations<ArrowRight /></Button>
          </div>
        )}
      </section>
    </div>
  );
};

export default GrowthAssistant;
