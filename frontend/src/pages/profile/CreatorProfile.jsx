import { useState, useEffect, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { Instagram, MapPin, Users, ArrowLeft, Send, Loader2, Lock, Unlock, Star, Play, Languages } from 'lucide-react';
import { Button } from '../../components/ui/button';
import { Badge } from '../../components/ui/badge';
import { Avatar, AvatarFallback, AvatarImage } from '../../components/ui/avatar';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from '../../components/ui/dialog';
import { Input } from '../../components/ui/input';
import { Label } from '../../components/ui/label';
import { Textarea } from '../../components/ui/textarea';
import { Switch } from '../../components/ui/switch';
import { marketplaceAPI, campaignAPI, getErrorMessage } from '../../lib/api';
import { useAuth } from '../../lib/auth';
import { toast } from 'sonner';
import TrustScore from '../../components/orange/TrustScore';

const formatPrice = (price) => new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR', maximumFractionDigits: 0 }).format(price || 0);
const formatCount = (n) => (n >= 1000000 ? `${(n / 1000000).toFixed(1)}M` : n >= 1000 ? `${(n / 1000).toFixed(1)}K` : String(n));
const emptyForm = { brief: '', deliverables: '', budget: '', timeline: '', isBarter: false, barterDetails: '', productValue: '' };

const CreatorProfile = () => {
  const { id } = useParams();
  const navigate = useNavigate();
  const { user } = useAuth();
  const [creator, setCreator] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [dialogOpen, setDialogOpen] = useState(false);
  const [sending, setSending] = useState(false);
  const [form, setForm] = useState(emptyForm);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const res = await marketplaceAPI.getCreator(id);
      setCreator(res.data);
      setError('');
    } catch (e) {
      setError(getErrorMessage(e, 'Creator not found'));
    } finally {
      setLoading(false);
    }
  }, [id]);

  useEffect(() => { load(); }, [load]);

  const update = (field, value) => setForm((prev) => ({ ...prev, [field]: value }));

  const sendRequest = async () => {
    if (!form.deliverables.trim()) return toast.error('Add the deliverables you want');
    const budget = parseFloat(form.budget) || 0;
    const productValue = parseFloat(form.productValue) || 0;
    if (!form.isBarter && budget <= 0) return toast.error('Add a budget greater than zero');
    if (form.isBarter && productValue <= 0) return toast.error('Add the value of the product or service');
    setSending(true);
    try {
      await campaignAPI.create({
        receiverId: id,
        receiverType: 'creator',
        campaignType: form.isBarter ? 'barter_product' : 'paid',
        deliverables: form.deliverables,
        budget: form.isBarter ? 0 : budget,
        productValue: form.isBarter ? productValue : 0,
        timeline: form.timeline,
        brief: form.brief,
        barterDetails: form.isBarter ? form.barterDetails : '',
      });
      toast.success('Request sent. You can track it on your dashboard.');
      setDialogOpen(false);
      setForm(emptyForm);
    } catch (e) {
      toast.error(getErrorMessage(e, 'Failed to send request'));
    } finally {
      setSending(false);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center">
        <Loader2 className="w-8 h-8 text-primary animate-spin" />
      </div>
    );
  }

  if (error || !creator) {
    return (
      <div className="min-h-screen bg-background flex flex-col items-center justify-center gap-4 p-6 text-center">
        <p className="text-lg font-semibold">{error || 'Creator not found'}</p>
        <Button variant="outline" onClick={() => navigate(-1)}><ArrowLeft className="w-4 h-4 mr-2" />Go back</Button>
      </div>
    );
  }

  const canRequest = user?.role === 'business' && !creator.isOwner;
  const prices = [
    ['Reel', creator.reelPrice], ['Story', creator.storyPrice], ['Post', creator.postPrice],
    ['Carousel', creator.carouselPrice], ['Bundle', creator.bundlePrice],
  ].filter(([, v]) => v > 0);

  return (
    <div className="min-h-screen bg-background">
      <header className="border-b bg-white/70 backdrop-blur-sm sticky top-0 z-40">
        <div className="max-w-5xl mx-auto px-4 sm:px-6 py-3 flex items-center justify-between">
          <Button variant="ghost" onClick={() => navigate(-1)} data-testid="back-btn"><ArrowLeft className="w-4 h-4 mr-2" />Back</Button>
          <Badge variant="outline" className="gap-1" data-testid="identity-badge">
            {creator.identityUnlocked ? <><Unlock className="w-3 h-3" />Identity visible</> : <><Lock className="w-3 h-3" />Identity unlocks after payment</>}
          </Badge>
        </div>
      </header>

      <main className="max-w-5xl mx-auto px-4 sm:px-6 py-8 space-y-8">
        <section className="bg-card border rounded-xl p-6 flex flex-col sm:flex-row gap-6">
          <Avatar className="w-24 h-24">
            {creator.profilePhotoUrl && <AvatarImage src={creator.profilePhotoUrl} alt="" />}
            <AvatarFallback className="text-2xl">{(creator.name || 'C').charAt(0)}</AvatarFallback>
          </Avatar>
          <div className="flex-1 space-y-3">
            <div>
              <h1 className="text-3xl font-heading font-bold" data-testid="creator-name">{creator.name}</h1>
              <div className="flex flex-wrap gap-x-4 gap-y-1 text-sm text-muted-foreground mt-1">
                {creator.location && <span className="flex items-center gap-1"><MapPin className="w-4 h-4" />{creator.location}</span>}
                {creator.language && <span className="flex items-center gap-1"><Languages className="w-4 h-4" />{creator.language}</span>}
                {creator.instagramUsername && <span className="flex items-center gap-1"><Instagram className="w-4 h-4" />@{creator.instagramUsername.replace(/^@/, '')}</span>}
              </div>
            </div>
            {creator.bio && <p className="text-foreground/80">{creator.bio}</p>}
            <div className="flex flex-wrap gap-2">
              {(creator.niches?.length ? creator.niches : [creator.niche]).filter(Boolean).map((n) => <Badge key={n} variant="secondary">{n}</Badge>)}
              {creator.instagramVerified && <Badge variant="outline">Instagram connected</Badge>}
              {creator.barterEnabled && <Badge variant="outline">Open to barter</Badge>}
            </div>
          </div>
          {canRequest && (
            <div className="sm:self-center">
              <Button onClick={() => setDialogOpen(true)} data-testid="send-request-btn"><Send className="w-4 h-4 mr-2" />Send request</Button>
            </div>
          )}
        </section>

        <TrustScore kind="creator" profileId={creator.id} />

        <section className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <Stat label="Followers" value={creator.followersCount ? formatCount(creator.followersCount) : 'Not shared'} icon={Users} />
          <Stat label="Engagement" value={creator.engagementMeasured ? `${creator.engagementRate}%` : 'Not measured yet'} />
          <Stat label="Rating" value={creator.rating ? `${creator.rating.toFixed(1)} / 5` : 'No ratings yet'} icon={Star} />
          <Stat label="Completed on Orange" value={String(creator.totalCollabs || 0)} />
        </section>

        <section className="space-y-3">
          <h2 className="text-xl font-heading font-semibold">Rates</h2>
          {prices.length ? (
            <div className="grid grid-cols-2 sm:grid-cols-5 gap-3">
              {prices.map(([label, value]) => (
                <div key={label} className="border rounded-lg p-3 bg-card">
                  <p className="text-xs text-muted-foreground">{label}</p>
                  <p className="font-semibold">{formatPrice(value)}</p>
                </div>
              ))}
            </div>
          ) : <p className="text-muted-foreground text-sm">This creator hasn't added rates yet.</p>}
        </section>

        <section className="space-y-3">
          <h2 className="text-xl font-heading font-semibold">Portfolio</h2>
          {creator.mediaGallery?.length ? (
            <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
              {creator.mediaGallery.map((m, i) => (
                <div key={m.id || i} className="relative aspect-[4/5] rounded-lg overflow-hidden bg-muted">
                  {m.type === 'video'
                    ? <><video src={m.url} className="w-full h-full object-cover" muted /><Play className="absolute inset-0 m-auto w-10 h-10 text-white drop-shadow" /></>
                    : <img src={m.thumbnailUrl || m.url} alt="" className="w-full h-full object-cover" />}
                </div>
              ))}
            </div>
          ) : <p className="text-muted-foreground text-sm">No portfolio items yet.</p>}
        </section>

        <section className="space-y-3">
          <h2 className="text-xl font-heading font-semibold">Reviews from brands</h2>
          {creator.ratings?.length ? creator.ratings.map((r, i) => (
            <div key={i} className="border rounded-lg p-4 bg-card">
              <p className="font-medium">{'★'.repeat(r.rating)}{'☆'.repeat(5 - r.rating)}</p>
              <p className="text-sm text-foreground/80 mt-1">{r.feedback}</p>
            </div>
          )) : <p className="text-muted-foreground text-sm">No reviews yet.</p>}
        </section>
      </main>

      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <DialogContent className="sm:max-w-[520px]">
          <DialogHeader>
            <DialogTitle>Send a collaboration request</DialogTitle>
            <DialogDescription>The creator has 72 hours to accept. You pay only after they accept.</DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <Label htmlFor="barter">Barter instead of paid</Label>
              <Switch id="barter" checked={form.isBarter} onCheckedChange={(v) => update('isBarter', v)} />
            </div>
            <div className="space-y-1"><Label>Deliverables</Label><Input value={form.deliverables} onChange={(e) => update('deliverables', e.target.value)} placeholder="1 reel + 2 stories" data-testid="deliverables-input" /></div>
            {form.isBarter ? (
              <>
                <div className="space-y-1"><Label>Product or service value (₹)</Label><Input type="number" value={form.productValue} onChange={(e) => update('productValue', e.target.value)} /></div>
                <div className="space-y-1"><Label>What you'll offer</Label><Input value={form.barterDetails} onChange={(e) => update('barterDetails', e.target.value)} placeholder="Meal for two" /></div>
              </>
            ) : (
              <div className="space-y-1"><Label>Budget (₹)</Label><Input type="number" value={form.budget} onChange={(e) => update('budget', e.target.value)} placeholder={creator.reelPrice ? String(creator.reelPrice) : '5000'} data-testid="budget-input" /></div>
            )}
            <div className="space-y-1"><Label>Timeline</Label><Input value={form.timeline} onChange={(e) => update('timeline', e.target.value)} placeholder="Post by 30 Nov" /></div>
            <div className="space-y-1"><Label>Brief</Label><Textarea value={form.brief} onChange={(e) => update('brief', e.target.value)} placeholder="What should the content show?" /></div>
            <Button className="w-full" onClick={sendRequest} disabled={sending} data-testid="submit-request-btn">
              {sending ? <Loader2 className="w-4 h-4 animate-spin" /> : 'Send request'}
            </Button>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
};

const Stat = ({ label, value, icon: Icon }) => (
  <div className="border rounded-xl p-4 bg-card">
    <p className="text-xs text-muted-foreground flex items-center gap-1">{Icon && <Icon className="w-3 h-3" />}{label}</p>
    <p className="text-lg font-semibold mt-1">{value}</p>
  </div>
);

export default CreatorProfile;
