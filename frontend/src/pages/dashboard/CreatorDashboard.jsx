import { useEffect, useMemo, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { Home, Compass, Layers, Wallet, Loader2, Inbox, Star, Eye, EyeOff, Pencil, ArrowRight, Check, Store } from 'lucide-react';
import AppShell from '../../components/orange/AppShell';
import PageHeader from '../../components/orange/PageHeader';
import StatTile from '../../components/orange/StatTile';
import Section from '../../components/orange/Section';
import EmptyState from '../../components/orange/EmptyState';
import CollaborationRow from '../../components/orange/CollaborationRow';
import CollaborationSheet from '../../components/orange/CollaborationSheet';
import BrandCard from '../../components/orange/BrandCard';
import RequestDialog from '../../components/orange/RequestDialog';
import { Button } from '../../components/ui/button';
import { Switch } from '../../components/ui/switch';
import { creatorAPI, marketplaceAPI, getErrorMessage } from '../../lib/api';
import useCollaborations from '../../hooks/useCollaborations';
import { ACTIVE_STATES, IN_FLIGHT_STATES, nextStep } from '../../lib/collaborations';
import { formatINR, greeting } from '../../lib/format';
import { SkeletonRows, SkeletonCards } from './BusinessDashboard';
import { toast } from 'sonner';

const VIEWS = ['home', 'opportunities', 'collaborations', 'earnings'];

const completionChecks = (p) => [
  ['Name and bio', !!(p?.name && p?.bio)],
  ['Location', !!p?.location],
  ['Niches', (p?.niches || []).length > 0],
  ['Rates', (p?.reelPrice || 0) + (p?.storyPrice || 0) + (p?.postPrice || 0) > 0],
  ['Profile photo', !!p?.profilePhotoUrl],
  ['Portfolio', (p?.mediaGallery || []).length > 0],
  ['Instagram connected', !!p?.instagramVerified],
];

const CreatorDashboard = () => {
  const navigate = useNavigate();
  const [params, setParams] = useSearchParams();
  const view = VIEWS.includes(params.get('view')) ? params.get('view') : 'home';
  const setView = (v) => setParams(v === 'home' ? {} : { view: v });

  const [profile, setProfile] = useState(null);
  const [profileLoading, setProfileLoading] = useState(true);
  const [brands, setBrands] = useState([]);
  const [brandsLoading, setBrandsLoading] = useState(true);
  const [pitchTo, setPitchTo] = useState(null);
  const [openCollab, setOpenCollab] = useState(null);
  const [toggling, setToggling] = useState(false);

  const { all, loading, busy, actions } = useCollaborations();

  useEffect(() => {
    creatorAPI.getProfile()
      .then((res) => setProfile(res.data))
      .catch((e) => { if (e.response?.status === 404) navigate('/onboarding/creator'); })
      .finally(() => setProfileLoading(false));
    marketplaceAPI.discoverBrands({}).then((res) => setBrands(res.data)).catch(() => setBrands([])).finally(() => setBrandsLoading(false));
  }, [navigate]);

  const current = openCollab ? all.find((c) => c.id === openCollab.id) || openCollab : null;
  const attention = useMemo(() => all.filter((c) => nextStep(c, 'creator', { incoming: c._incoming }).who === 'you' && c.status !== 'completed'), [all]);
  const requests = all.filter((c) => c._incoming && c.status === 'requested');

  const earnings = useMemo(() => {
    const paid = all.filter((c) => c.campaignType === 'paid');
    const done = paid.filter((c) => c.status === 'completed');
    return {
      released: done.filter((c) => c.payoutStatus === 'released').reduce((s, c) => s + (c.creatorPayout || 0), 0),
      pendingPayout: done.filter((c) => c.payoutStatus !== 'released').reduce((s, c) => s + (c.creatorPayout || 0), 0),
      inProgress: paid.filter((c) => IN_FLIGHT_STATES.includes(c.status)).reduce((s, c) => s + (c.creatorPayout || 0), 0),
      completed: all.filter((c) => c.status === 'completed').length,
      rows: done,
    };
  }, [all]);

  const checks = completionChecks(profile);
  const completion = Math.round((checks.filter(([, ok]) => ok).length / checks.length) * 100);

  const toggleVisibility = async () => {
    setToggling(true);
    try {
      const next = !profile.isVisible;
      await creatorAPI.toggleVisibility(next);
      setProfile((p) => ({ ...p, isVisible: next }));
      toast.success(next ? 'You are visible to brands' : 'You are hidden from the marketplace');
    } catch (e) {
      toast.error(getErrorMessage(e, 'Could not update visibility'));
    } finally {
      setToggling(false);
    }
  };

  if (profileLoading) {
    return <div className="flex min-h-screen items-center justify-center bg-background"><Loader2 className="h-6 w-6 animate-spin text-primary" /></div>;
  }

  const nav = [
    { key: 'home', label: 'Home', icon: Home, badge: attention.length },
    { key: 'opportunities', label: 'Opportunities', icon: Compass },
    { key: 'collaborations', label: 'Collaborations', icon: Layers, badge: requests.length },
    { key: 'earnings', label: 'Earnings', icon: Wallet },
  ];
  const pitch = (brand) => setPitchTo({ id: brand.id, type: 'brand', title: `${brand.industry || 'Local'} brand`, subtitle: brand.location, suggestedBudget: profile?.reelPrice || '' });
  const firstName = (profile?.name || '').split(' ')[0] || 'there';

  return (
    <AppShell
      items={nav}
      active={view}
      onSelect={setView}
      displayName={profile?.name}
      subtitle={[profile?.niche, profile?.location].filter(Boolean).join(' · ')}
      photoUrl={profile?.profilePhotoUrl}
      profileHref={profile ? `/profile/creator/${profile.id}` : null}
    >
      {view === 'home' && (
        <div className="space-y-10 animate-fade-in">
          <PageHeader
            eyebrow={greeting()}
            title={<>Hey <em className="font-display italic text-orange-700">{firstName}</em>, here's your studio.</>}
            description={attention.length ? `${attention.length} ${attention.length === 1 ? 'thing needs' : 'things need'} you.` : 'Nothing is waiting on you right now.'}
            actions={<Button variant="outline" onClick={() => navigate('/onboarding/creator')} data-testid="edit-profile-btn"><Pencil />Edit profile</Button>}
          />

          <div className="grid gap-3 lg:grid-cols-3">
            <div className="surface p-5 lg:col-span-2">
              <div className="flex items-center justify-between">
                <p className="eyebrow">Profile strength</p>
                <span className="num text-sm font-semibold">{completion}%</span>
              </div>
              <div className="mt-3 h-1.5 overflow-hidden rounded-full bg-stone"><div className="h-full rounded-full bg-primary transition-all" style={{ width: `${completion}%` }} /></div>
              <ul className="mt-4 grid grid-cols-2 gap-x-4 gap-y-2 text-sm sm:grid-cols-3">
                {checks.map(([label, ok]) => (
                  <li key={label} className={`flex items-center gap-2 ${ok ? 'text-ink' : 'text-muted-foreground'}`}>
                    <span className={`flex h-4 w-4 items-center justify-center rounded-full ${ok ? 'bg-sage-400 text-white' : 'ring-1 ring-border'}`}>{ok && <Check className="h-3 w-3" />}</span>{label}
                  </li>
                ))}
              </ul>
            </div>
            <div className="surface flex flex-col justify-between p-5">
              <div>
                <p className="eyebrow">Marketplace visibility</p>
                <p className="mt-2 font-display text-xl">{profile?.isVisible === false ? 'Hidden' : 'Visible to brands'}</p>
                <p className="mt-1 text-sm text-muted-foreground">{profile?.instagramVerified ? 'Brands can find you in discovery.' : 'Connect Instagram to appear in discovery.'}</p>
              </div>
              <label className="mt-4 flex items-center justify-between text-sm">
                <span className="flex items-center gap-2">{profile?.isVisible === false ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}Show my profile</span>
                <Switch checked={profile?.isVisible !== false} disabled={toggling} onCheckedChange={toggleVisibility} data-testid="visibility-toggle" />
              </label>
            </div>
          </div>

          <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
            <StatTile label="Earned" value={formatINR(earnings.released)} hint="Paid out to you" icon={Wallet} />
            <StatTile label="On the way" value={formatINR(earnings.inProgress + earnings.pendingPayout)} hint="Held for active and completed work" />
            <StatTile label="Completed" value={earnings.completed} hint="Collaborations on Orange" />
            <StatTile label="Rating" value={profile?.rating ? profile.rating.toFixed(1) : 'New'} hint={profile?.rating ? 'Average from brands' : 'Shown after your first review'} icon={Star} />
          </div>

          <Section title="Needs you" description="Requests to answer and content to deliver">
            {loading ? <SkeletonRows /> : attention.length ? (
              <div className="surface overflow-hidden">{attention.map((c) => <CollaborationRow key={c.id} collab={c} role="creator" onOpen={setOpenCollab} />)}</div>
            ) : <EmptyState compact icon={Inbox} title="All clear" body="New requests and deliverables will show up here." />}
          </Section>

          <Section title="Brands on Orange" action={<Button variant="ghost" size="sm" onClick={() => setView('opportunities')}>See all<ArrowRight /></Button>}>
            {brandsLoading ? <SkeletonCards /> : brands.length ? (
              <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">{brands.slice(0, 3).map((b) => <BrandCard key={b.id} brand={b} onView={(x) => navigate(`/profile/business/${x.id}`)} onPropose={pitch} />)}</div>
            ) : <EmptyState compact icon={Store} title="No brands listed yet" body="Brands appear here once they verify their account." />}
          </Section>
        </div>
      )}

      {view === 'opportunities' && (
        <div className="space-y-8 animate-fade-in">
          <PageHeader eyebrow="Marketplace" title="Opportunities" description="Brands open to collaborations. Pitch one and they'll see your rates and portfolio." />
          {brandsLoading ? <SkeletonCards count={6} /> : brands.length ? (
            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">{brands.map((b) => <BrandCard key={b.id} brand={b} onView={(x) => navigate(`/profile/business/${x.id}`)} onPropose={pitch} />)}</div>
          ) : <EmptyState icon={Compass} title="No brands yet" body="Check back soon." />}
        </div>
      )}

      {view === 'collaborations' && (
        <div className="space-y-6 animate-fade-in">
          <PageHeader eyebrow="Workspace" title="Collaborations" description="Requests, deliverables and completed work." />
          {loading ? <SkeletonRows /> : all.length ? (
            <>
              {requests.length > 0 && (
                <Section title={`New requests · ${requests.length}`}>
                  <div className="surface overflow-hidden">{requests.map((c) => <CollaborationRow key={c.id} collab={c} role="creator" onOpen={setOpenCollab} />)}</div>
                </Section>
              )}
              <Section title="Active">
                {all.filter((c) => ACTIVE_STATES.includes(c.status) && !(c._incoming && c.status === 'requested')).length ? (
                  <div className="surface overflow-hidden">
                    {all.filter((c) => ACTIVE_STATES.includes(c.status) && !(c._incoming && c.status === 'requested')).map((c) => <CollaborationRow key={c.id} collab={c} role="creator" onOpen={setOpenCollab} />)}
                  </div>
                ) : <EmptyState compact icon={Layers} title="Nothing active" />}
              </Section>
              <Section title="Completed">
                {all.filter((c) => c.status === 'completed').length ? (
                  <div className="surface overflow-hidden">{all.filter((c) => c.status === 'completed').map((c) => <CollaborationRow key={c.id} collab={c} role="creator" onOpen={setOpenCollab} />)}</div>
                ) : <EmptyState compact icon={Star} title="No completed collaborations yet" />}
              </Section>
            </>
          ) : <EmptyState icon={Layers} title="No collaborations yet" body="Pitch a brand or wait for a request." action={<Button onClick={() => setView('opportunities')}>See opportunities</Button>} />}
        </div>
      )}

      {view === 'earnings' && (
        <div className="space-y-8 animate-fade-in">
          <PageHeader eyebrow="Money" title="Earnings" description="Payments are held by Orange while you work and released when the brand approves." />
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
            <StatTile label="Released" value={formatINR(earnings.released)} hint="Sent to your account" accent />
            <StatTile label="Awaiting payout" value={formatINR(earnings.pendingPayout)} hint="Completed, payout account not set up yet" />
            <StatTile label="In progress" value={formatINR(earnings.inProgress)} hint="Held for active collaborations" />
          </div>
          {earnings.rows.length ? (
            <div className="surface overflow-hidden">
              <table className="w-full text-sm">
                <thead className="bg-[#FFFCF8] text-left text-xs text-muted-foreground"><tr><th className="px-5 py-3 font-medium">Collaboration</th><th className="px-5 py-3 font-medium">Completed</th><th className="px-5 py-3 text-right font-medium">You receive</th><th className="px-5 py-3 text-right font-medium">Payout</th></tr></thead>
                <tbody>
                  {earnings.rows.map((c) => (
                    <tr key={c.id} className="border-t border-border">
                      <td className="px-5 py-3"><p className="font-medium">{c.senderType === 'creator' ? c.receiverName : c.senderName}</p><p className="text-xs text-muted-foreground">{c.deliverables}</p></td>
                      <td className="px-5 py-3 text-muted-foreground">{new Date(c.updatedAt).toLocaleDateString('en-IN', { day: 'numeric', month: 'short' })}</td>
                      <td className="num px-5 py-3 text-right font-semibold">{formatINR(c.creatorPayout)}</td>
                      <td className="px-5 py-3 text-right">{c.payoutStatus === 'released' ? <span className="text-sage-700">Released</span> : <span className="text-amber-700">Pending</span>}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : <EmptyState icon={Wallet} title="No earnings yet" body="Completed paid collaborations will be listed here." />}
        </div>
      )}

      <RequestDialog open={!!pitchTo} onOpenChange={(o) => !o && setPitchTo(null)} target={pitchTo} onSubmit={actions.create} busy={busy === 'create'} />
      <CollaborationSheet collab={current} role="creator" open={!!openCollab} onOpenChange={(o) => !o && setOpenCollab(null)} actions={actions} busy={busy} />
    </AppShell>
  );
};

export default CreatorDashboard;
