import { useCallback, useEffect, useMemo, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { Heart, Receipt, Home, Search, Layers, Loader2, Inbox, Users, Wallet, Sparkles, ArrowRight, Pencil, SlidersHorizontal } from 'lucide-react';
import AppShell from '../../components/orange/AppShell';
import PageHeader from '../../components/orange/PageHeader';
import StatTile from '../../components/orange/StatTile';
import Section from '../../components/orange/Section';
import EmptyState from '../../components/orange/EmptyState';
import CollaborationRow from '../../components/orange/CollaborationRow';
import CollaborationSheet from '../../components/orange/CollaborationSheet';
import CreatorCard from '../../components/orange/CreatorCard';
import RequestDialog from '../../components/orange/RequestDialog';
import GrowthAssistant from '../../components/orange/GrowthAssistant';
import MyCreators from '../../components/orange/MyCreators';
import PaymentsView from '../../components/orange/PaymentsView';
import RedeemCard from '../../components/orange/RedeemCard';
import { Button } from '../../components/ui/button';
import { Input } from '../../components/ui/input';
import { Switch } from '../../components/ui/switch';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../../components/ui/select';
import { businessAPI, marketplaceAPI, crmAPI } from '../../lib/api';
import useCollaborations from '../../hooks/useCollaborations';
import { ACTIVE_STATES, IN_FLIGHT_STATES, nextStep } from '../../lib/collaborations';
import { formatINR, greeting } from '../../lib/format';

const NICHES = ['All', 'Food', 'Lifestyle', 'Fashion', 'Beauty', 'Fitness', 'Travel', 'Tech', 'Gaming', 'Comedy', 'Education', 'Music', 'Art', 'Sports', 'Health', 'Finance'];
const VIEWS = ['home', 'growth', 'discover', 'campaigns', 'creators', 'payments'];

const BusinessDashboard = () => {
  const navigate = useNavigate();
  const [params, setParams] = useSearchParams();
  const view = VIEWS.includes(params.get('view')) ? params.get('view') : 'home';
  const setView = (v) => setParams(v === 'home' ? {} : { view: v });

  const [profile, setProfile] = useState(null);
  const [profileLoading, setProfileLoading] = useState(true);
  const [creators, setCreators] = useState([]);
  const [creatorsLoading, setCreatorsLoading] = useState(false);
  const [filters, setFilters] = useState({ niche: 'All', location: '', barterOnly: false });
  const [proposeTo, setProposeTo] = useState(null);
  const [openCollab, setOpenCollab] = useState(null);
  const [campaignFilter, setCampaignFilter] = useState('active');
  const [savedIds, setSavedIds] = useState(new Set());

  useEffect(() => {
    crmAPI.list().then((res) => setSavedIds(new Set(res.data.filter((c) => c.saved).map((c) => c.creatorId)))).catch(() => {});
  }, []);

  const toggleSave = async (creator) => {
    const on = savedIds.has(creator.id);
    setSavedIds((prev) => { const next = new Set(prev); if (on) next.delete(creator.id); else next.add(creator.id); return next; });
    await (on ? crmAPI.unsave(creator.id) : crmAPI.save(creator.id)).catch(() => {});
  };

  const { all, loading, busy, actions, refresh } = useCollaborations();

  useEffect(() => {
    businessAPI.getProfile()
      .then((res) => setProfile(res.data))
      .catch((e) => { if (e.response?.status === 404) navigate('/onboarding/business'); })
      .finally(() => setProfileLoading(false));
  }, [navigate]);

  const loadCreators = useCallback(async (f) => {
    setCreatorsLoading(true);
    try {
      const q = {};
      if (f.niche && f.niche !== 'All') q.niche = f.niche;
      if (f.location.trim()) q.location = f.location.trim();
      if (f.barterOnly) q.barterOnly = true;
      const res = await marketplaceAPI.discoverCreators(q);
      setCreators(res.data);
    } catch {
      setCreators([]);
    } finally {
      setCreatorsLoading(false);
    }
  }, []);

  const [initialFilters] = useState(filters);
  useEffect(() => { loadCreators(initialFilters); }, [loadCreators, initialFilters]);

  // Keep the open sheet in sync with refreshed data.
  const current = openCollab ? all.find((c) => c.id === openCollab.id) || openCollab : null;

  const stats = useMemo(() => {
    const paid = all.filter((c) => c.campaignType === 'paid');
    return {
      active: all.filter((c) => ACTIVE_STATES.includes(c.status)).length,
      held: paid.filter((c) => IN_FLIGHT_STATES.includes(c.status)).reduce((s, c) => s + (c.escrowAmount || 0), 0),
      spent: all.filter((c) => c.status === 'completed').reduce((s, c) => s + (c.campaignType === 'paid' ? c.escrowAmount || 0 : c.barterFee || 0), 0),
      creators: new Set(all.filter((c) => c.status === 'completed').map((c) => (c.senderType === 'business' ? c.receiverId : c.senderId))).size,
    };
  }, [all]);

  const attention = useMemo(() => all.filter((c) => nextStep(c, 'business', { incoming: c._incoming }).who === 'you' && c.status !== 'completed'), [all]);
  const pendingIncoming = all.filter((c) => c._incoming && c.status === 'requested').length;

  const filteredCampaigns = all.filter((c) => {
    if (campaignFilter === 'active') return ACTIVE_STATES.includes(c.status);
    if (campaignFilter === 'completed') return c.status === 'completed';
    return true;
  });

  const nav = [
    { key: 'home', label: 'Home', icon: Home, badge: attention.length },
    { key: 'growth', label: 'Growth Assistant', icon: Sparkles },
    { key: 'discover', label: 'Find creators', icon: Search },
    { key: 'campaigns', label: 'Collaborations', icon: Layers, badge: pendingIncoming },
    { key: 'creators', label: 'My creators', icon: Heart },
    { key: 'payments', label: 'Payments', icon: Receipt },
  ];

  if (profileLoading) {
    return <div className="flex min-h-screen items-center justify-center bg-background"><Loader2 className="h-6 w-6 animate-spin text-primary" /></div>;
  }

  const propose = (creator) => setProposeTo({ id: creator.id, type: 'creator', title: `${creator.niche || 'Local'} creator`, subtitle: creator.location, suggestedBudget: creator.reelPrice || '' });
  const viewCreator = (creator) => navigate(`/profile/creator/${creator.id}`);
  const firstName = profile?.brandName || 'there';

  return (
    <AppShell
      items={nav}
      active={view}
      onSelect={setView}
      displayName={profile?.brandName}
      subtitle={[profile?.industry, profile?.location].filter(Boolean).join(' · ')}
      photoUrl={profile?.profilePhotoUrl}
      profileHref={profile ? `/profile/business/${profile.id}` : null}
    >
      {view === 'home' && (
        <div className="space-y-10 animate-fade-in">
          <PageHeader
            eyebrow={greeting()}
            title={<>Let's grow <em className="font-display italic text-orange-700">{firstName}</em>.</>}
            description={attention.length ? `${attention.length} ${attention.length === 1 ? 'thing needs' : 'things need'} your attention.` : 'Nothing is waiting on you right now.'}
            actions={<>
              <Button variant="outline" onClick={() => navigate('/onboarding/business')} data-testid="edit-profile-btn"><Pencil />Edit profile</Button>
              <Button onClick={() => setView('discover')}><Search />Find creators</Button>
            </>}
          />

          <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
            <StatTile label="Active" value={stats.active} hint="Collaborations in progress" icon={Layers} />
            <StatTile label="Held by Orange" value={formatINR(stats.held)} hint="Released after you approve" icon={Wallet} />
            <StatTile label="Spent" value={formatINR(stats.spent)} hint="On completed collaborations" />
            <StatTile label="Creators" value={stats.creators} hint="You've completed work with" icon={Users} />
          </div>

          <div className="relative overflow-hidden rounded-xl border border-plum-100 bg-gradient-to-br from-plum-50 via-white to-orange-50 p-5 sm:p-6">
            <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
              <div className="flex items-start gap-3">
                <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-plum text-white"><Sparkles className="h-5 w-5" /></div>
                <div>
                  <p className="font-display text-xl text-ink">Tell Orange what you want to achieve</p>
                  <p className="mt-1 max-w-xl text-sm text-ink-500">Describe your goal and budget. Orange plans the campaign and shortlists creators for you to approve.</p>
                </div>
              </div>
              <Button variant="plum" onClick={() => setView('growth')} data-testid="open-growth">Plan a campaign<ArrowRight /></Button>
            </div>
          </div>

          <RedeemCard />

          <Section title="Needs your attention" description="Payments, content to review and requests to answer">
            {loading ? <SkeletonRows /> : attention.length ? (
              <div className="surface overflow-hidden">{attention.map((c) => <CollaborationRow key={c.id} collab={c} role="business" onOpen={setOpenCollab} />)}</div>
            ) : (
              <EmptyState compact icon={Inbox} title="You're all caught up" body="When a creator accepts, submits content or sends you a request, it shows up here." />
            )}
          </Section>

          <Section title="Creators to explore" description="Verified creators on Orange" action={<Button variant="ghost" size="sm" onClick={() => setView('discover')}>See all<ArrowRight /></Button>}>
            {creatorsLoading ? <SkeletonCards /> : creators.length ? (
              <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
                {[...creators].sort((a, b) => (b.rating || 0) - (a.rating || 0)).slice(0, 3).map((c) => <CreatorCard key={c.id} creator={c} onView={viewCreator} onPropose={propose} saved={savedIds.has(c.id)} onToggleSave={toggleSave} />)}
              </div>
            ) : <EmptyState compact icon={Users} title="No verified creators yet" body="Creators appear here once they connect Instagram." />}
          </Section>

          {all.length > 0 && (
            <Section title="Recent activity" action={<Button variant="ghost" size="sm" onClick={() => setView('campaigns')}>All collaborations<ArrowRight /></Button>}>
              <div className="surface overflow-hidden">{all.slice(0, 5).map((c) => <CollaborationRow key={c.id} collab={c} role="business" onOpen={setOpenCollab} />)}</div>
            </Section>
          )}
        </div>
      )}

      {view === 'growth' && (
        <div className="space-y-8 animate-fade-in">
          <PageHeader eyebrow="Growth Assistant" title="Plan a campaign" description="Five specialists read your business, plan the campaign and shortlist creators. You approve before anything is sent." />
          <GrowthAssistant onOpenCollaborations={() => setView('campaigns')} />
        </div>
      )}

      {view === 'creators' && (
        <div className="space-y-8 animate-fade-in">
          <PageHeader eyebrow="CRM" title="My creators" description="Creators you saved or worked with. Rebook the ones that worked in one click." />
          <MyCreators onRepeated={refresh} onFind={() => setView('discover')} />
        </div>
      )}

      {view === 'payments' && (
        <div className="space-y-8 animate-fade-in">
          <PageHeader eyebrow="Orange Trust" title="Payments" description="Every payment, fee and refund on your account." />
          <PaymentsView />
        </div>
      )}

      {view === 'discover' && (
        <div className="space-y-8 animate-fade-in">
          <PageHeader eyebrow="Marketplace" title="Find creators" description="Names and handles unlock once a collaboration is paid. Rates, location and reviews are visible now." />
          <div className="surface flex flex-col gap-3 p-3 sm:flex-row sm:items-center">
            <div className="flex items-center gap-2 px-1 text-sm text-muted-foreground"><SlidersHorizontal className="h-4 w-4" />Filters</div>
            <Select value={filters.niche} onValueChange={(v) => setFilters((f) => ({ ...f, niche: v }))}>
              <SelectTrigger className="sm:w-44" data-testid="niche-filter"><SelectValue placeholder="Niche" /></SelectTrigger>
              <SelectContent>{NICHES.map((n) => <SelectItem key={n} value={n}>{n === 'All' ? 'All niches' : n}</SelectItem>)}</SelectContent>
            </Select>
            <Input className="sm:w-56" placeholder="Area or city, e.g. Baner" value={filters.location} onChange={(e) => setFilters((f) => ({ ...f, location: e.target.value }))} onKeyDown={(e) => e.key === 'Enter' && loadCreators(filters)} data-testid="location-filter" />
            <label className="flex items-center gap-2 px-1 text-sm"><Switch checked={filters.barterOnly} onCheckedChange={(v) => setFilters((f) => ({ ...f, barterOnly: v }))} />Barter only</label>
            <div className="flex gap-2 sm:ml-auto">
              <Button variant="ghost" onClick={() => { const f = { niche: 'All', location: '', barterOnly: false }; setFilters(f); loadCreators(f); }}>Reset</Button>
              <Button onClick={() => loadCreators(filters)} data-testid="apply-filters-btn">Apply</Button>
            </div>
          </div>
          {creatorsLoading ? <SkeletonCards count={6} /> : creators.length ? (
            <>
              <p className="text-sm text-muted-foreground">{creators.length} {creators.length === 1 ? 'creator' : 'creators'}</p>
              <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
                {creators.map((c) => <CreatorCard key={c.id} creator={c} onView={viewCreator} onPropose={propose} saved={savedIds.has(c.id)} onToggleSave={toggleSave} />)}
              </div>
            </>
          ) : <EmptyState icon={Search} title="No creators match" body="Try another niche or a wider area." />}
        </div>
      )}

      {view === 'campaigns' && (
        <div className="space-y-6 animate-fade-in">
          <PageHeader eyebrow="Workspace" title="Collaborations" description="Every request, payment and deliverable in one place." />
          <div className="flex gap-1 rounded-lg bg-stone p-1 text-sm sm:w-fit" role="tablist">
            {[['active', 'Active'], ['completed', 'Completed'], ['all', 'All']].map(([k, label]) => (
              <button key={k} role="tab" aria-selected={campaignFilter === k} onClick={() => setCampaignFilter(k)}
                className={`flex-1 rounded-md px-4 py-1.5 sm:flex-none ${campaignFilter === k ? 'bg-white font-semibold text-ink shadow-card' : 'text-ink-500'}`}>{label}</button>
            ))}
          </div>
          {loading ? <SkeletonRows /> : filteredCampaigns.length ? (
            <div className="surface overflow-hidden">{filteredCampaigns.map((c) => <CollaborationRow key={c.id} collab={c} role="business" onOpen={setOpenCollab} />)}</div>
          ) : (
            <EmptyState icon={Layers} title={campaignFilter === 'completed' ? 'Nothing completed yet' : 'No collaborations yet'} body="Propose a collaboration to a creator to get started." action={<Button onClick={() => setView('discover')}>Find creators</Button>} />
          )}
        </div>
      )}

      <RequestDialog open={!!proposeTo} onOpenChange={(o) => !o && setProposeTo(null)} target={proposeTo} onSubmit={actions.create} busy={busy === 'create'} />
      <CollaborationSheet collab={current} role="business" open={!!openCollab} onOpenChange={(o) => !o && setOpenCollab(null)} actions={actions} busy={busy} />
    </AppShell>
  );
};

export const SkeletonRows = ({ count = 3 }) => (
  <div className="surface divide-y divide-border overflow-hidden">
    {Array.from({ length: count }).map((_, i) => (
      <div key={i} className="flex items-center gap-4 px-5 py-4">
        <div className="h-9 w-9 animate-pulse rounded-full bg-stone" />
        <div className="flex-1 space-y-2"><div className="h-3 w-40 animate-pulse rounded bg-stone" /><div className="h-3 w-64 animate-pulse rounded bg-stone" /></div>
      </div>
    ))}
  </div>
);

export const SkeletonCards = ({ count = 3 }) => (
  <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
    {Array.from({ length: count }).map((_, i) => <div key={i} className="surface h-64 animate-pulse bg-stone/50" />)}
  </div>
);

export default BusinessDashboard;
