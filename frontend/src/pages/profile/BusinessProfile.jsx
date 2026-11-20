import { useState, useEffect, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { Instagram, MapPin, ArrowLeft, Loader2, Lock, Unlock, Star, Building2 } from 'lucide-react';
import { Button } from '../../components/ui/button';
import { Badge } from '../../components/ui/badge';
import { Avatar, AvatarFallback, AvatarImage } from '../../components/ui/avatar';
import { marketplaceAPI, getErrorMessage } from '../../lib/api';
import TrustScore from '../../components/orange/TrustScore';

const BusinessProfile = () => {
  const { id } = useParams();
  const navigate = useNavigate();
  const [brand, setBrand] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const res = await marketplaceAPI.getBrand(id);
      setBrand(res.data);
      setError('');
    } catch (e) {
      setError(getErrorMessage(e, 'Brand not found'));
    } finally {
      setLoading(false);
    }
  }, [id]);

  useEffect(() => { load(); }, [load]);

  if (loading) {
    return <div className="min-h-screen bg-background flex items-center justify-center"><Loader2 className="w-8 h-8 text-primary animate-spin" /></div>;
  }
  if (error || !brand) {
    return (
      <div className="min-h-screen bg-background flex flex-col items-center justify-center gap-4 p-6 text-center">
        <p className="text-lg font-semibold">{error || 'Brand not found'}</p>
        <Button variant="outline" onClick={() => navigate(-1)}><ArrowLeft className="w-4 h-4 mr-2" />Go back</Button>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-background">
      <header className="border-b bg-white/70 backdrop-blur-sm sticky top-0 z-40">
        <div className="max-w-5xl mx-auto px-4 sm:px-6 py-3 flex items-center justify-between">
          <Button variant="ghost" onClick={() => navigate(-1)} data-testid="back-btn"><ArrowLeft className="w-4 h-4 mr-2" />Back</Button>
          <Badge variant="outline" className="gap-1">
            {brand.identityUnlocked ? <><Unlock className="w-3 h-3" />Identity visible</> : <><Lock className="w-3 h-3" />Identity unlocks after collaboration</>}
          </Badge>
        </div>
      </header>

      <main className="max-w-5xl mx-auto px-4 sm:px-6 py-8 space-y-8">
        <section className="bg-card border rounded-xl p-6 flex flex-col sm:flex-row gap-6">
          <Avatar className="w-24 h-24">
            {brand.profilePhotoUrl && <AvatarImage src={brand.profilePhotoUrl} alt="" />}
            <AvatarFallback><Building2 className="w-8 h-8" /></AvatarFallback>
          </Avatar>
          <div className="flex-1 space-y-3">
            <h1 className="text-3xl font-heading font-bold" data-testid="brand-name">{brand.brandName}</h1>
            <div className="flex flex-wrap gap-x-4 gap-y-1 text-sm text-muted-foreground">
              {brand.industry && <span>{brand.industry}</span>}
              {brand.location && <span className="flex items-center gap-1"><MapPin className="w-4 h-4" />{brand.location}</span>}
              {brand.instagramUsername && <span className="flex items-center gap-1"><Instagram className="w-4 h-4" />@{brand.instagramUsername.replace(/^@/, '')}</span>}
            </div>
            {brand.bio && <p className="text-foreground/80">{brand.bio}</p>}
            <div className="flex flex-wrap gap-2">
              {brand.preferredNiches?.map((n) => <Badge key={n} variant="secondary">{n}</Badge>)}
              {brand.paidCollabsEnabled && <Badge variant="outline">Paid collaborations</Badge>}
              {brand.barterEnabled && <Badge variant="outline">Open to barter</Badge>}
            </div>
          </div>
        </section>

        <TrustScore kind="brand" profileId={brand.id} />

        <section className="grid grid-cols-2 md:grid-cols-3 gap-4">
          <Stat label="Rating from creators" value={brand.rating ? `${brand.rating.toFixed(1)} / 5` : 'No ratings yet'} />
          <Stat label="Completed on Orange" value={String(brand.completedCollabs || 0)} />
          <Stat label="Typical budget" value={brand.budgetRange || 'Not shared'} />
        </section>

        {(brand.deliverables || brand.brandRequirements) && (
          <section className="grid md:grid-cols-2 gap-4">
            {brand.deliverables && <Block title="Usually looks for" text={brand.deliverables} />}
            {brand.brandRequirements && <Block title="Requirements" text={brand.brandRequirements} />}
          </section>
        )}

        {brand.pastCollaborations?.length > 0 && (
          <section className="space-y-3">
            <h2 className="text-xl font-heading font-semibold">Past collaborations</h2>
            {brand.pastCollaborations.map((c, i) => (
              <div key={i} className="border rounded-lg p-4 bg-card">
                <p className="font-medium">{c.campaignName}</p>
                {c.result && <p className="text-sm text-muted-foreground">{c.result}</p>}
              </div>
            ))}
          </section>
        )}

        <section className="space-y-3">
          <h2 className="text-xl font-heading font-semibold">Reviews from creators</h2>
          {brand.ratings?.length ? brand.ratings.map((r, i) => (
            <div key={i} className="border rounded-lg p-4 bg-card">
              <p className="font-medium flex items-center gap-1"><Star className="w-4 h-4" />{r.rating} / 5</p>
              <p className="text-sm text-foreground/80 mt-1">{r.feedback}</p>
            </div>
          )) : <p className="text-muted-foreground text-sm">No reviews yet.</p>}
        </section>
      </main>
    </div>
  );
};

const Stat = ({ label, value }) => (
  <div className="border rounded-xl p-4 bg-card">
    <p className="text-xs text-muted-foreground">{label}</p>
    <p className="text-lg font-semibold mt-1">{value}</p>
  </div>
);
const Block = ({ title, text }) => (
  <div className="border rounded-xl p-4 bg-card">
    <p className="text-xs text-muted-foreground mb-1">{title}</p>
    <p className="text-sm whitespace-pre-line">{text}</p>
  </div>
);

export default BusinessProfile;
