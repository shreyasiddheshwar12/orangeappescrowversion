import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import { 
  Instagram, Globe, MapPin, ArrowLeft, Loader2, Lock, Unlock,
  Image as ImageIcon, Play, ExternalLink, DollarSign, MessageSquare,
  Building2, Briefcase, CreditCard
} from 'lucide-react';
import { Button } from '../../components/ui/button';
import { Badge } from '../../components/ui/badge';
import { Avatar, AvatarFallback, AvatarImage } from '../../components/ui/avatar';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from '../../components/ui/dialog';
import { marketplaceAPI, paymentsAPI, requestsAPI, getErrorMessage } from '../../lib/api';
import { useAuth } from '../../lib/auth';
import { toast } from 'sonner';

const BusinessProfile = () => {
  const { id } = useParams();
  const navigate = useNavigate();
  const { user } = useAuth();
  const [brand, setBrand] = useState(null);
  const [loading, setLoading] = useState(true);
  const [accessLevel, setAccessLevel] = useState('discovery'); // discovery, unlocked, full
  const [unlockCredits, setUnlockCredits] = useState({ availableCredits: 0, totalCredits: 0 });
  const [showUnlockModal, setShowUnlockModal] = useState(false);
  const [unlocking, setUnlocking] = useState(false);
  const [buyingCredits, setBuyingCredits] = useState(false);

  useEffect(() => {
    loadBrand();
    if (user?.role === 'creator') {
      loadCredits();
    }
  }, [id, user]);

  const loadBrand = async () => {
    try {
      // Try to get unlocked brand profile
      const response = await marketplaceAPI.getUnlockedBrand(id);
      setBrand(response.data);
      setAccessLevel('unlocked');
    } catch (e) {
      if (e.response?.status === 403) {
        // Not unlocked yet - show unlock modal
        setShowUnlockModal(true);
        // Try to get discovery data
        try {
          const discoverRes = await marketplaceAPI.discoverBrands({});
          const discoveryBrand = discoverRes.data.find(b => b.id === id);
          if (discoveryBrand) {
            setBrand(discoveryBrand);
            setAccessLevel('discovery');
          } else {
            toast.error("Brand not found");
            navigate(-1);
          }
        } catch (discoverErr) {
          toast.error("Brand not found");
          navigate(-1);
        }
      } else {
        toast.error("Brand not found");
        navigate(-1);
      }
    } finally {
      setLoading(false);
    }
  };

  const loadCredits = async () => {
    try {
      const response = await paymentsAPI.getCredits();
      setUnlockCredits(response.data);
    } catch (e) {
      console.error("Failed to load credits", e);
    }
  };

  const handleUnlockBrand = async () => {
    if (unlockCredits.availableCredits < 1) {
      toast.error("You need at least 1 credit to unlock this brand");
      return;
    }
    
    setUnlocking(true);
    try {
      await marketplaceAPI.unlockBrand(id);
      toast.success("Brand unlocked! 🔓");
      setShowUnlockModal(false);
      // Reload the brand with unlocked data
      const response = await marketplaceAPI.getUnlockedBrand(id);
      setBrand(response.data);
      setAccessLevel('unlocked');
      // Update credits
      loadCredits();
    } catch (error) {
      toast.error(getErrorMessage(error, "Failed to unlock brand"));
    } finally {
      setUnlocking(false);
    }
  };

  const handleBuyCredits = async () => {
    setBuyingCredits(true);
    try {
      // Use demo credits for test mode
      await paymentsAPI.addDemoCredits();
      toast.success("Demo credits added! 5 credits for testing 🎉");
      loadCredits();
    } catch (error) {
      toast.error("Failed to add credits");
    } finally {
      setBuyingCredits(false);
    }
  };

  const canSendRequest = user && user.role === 'creator' && accessLevel !== 'discovery';
  const canSeeInstagram = accessLevel === 'full' && brand?.instagramUsername;

  const displayName = brand?.brandName || 'Brand Profile';

  if (loading) {
    return (
      <div className="min-h-screen gradient-hero flex items-center justify-center">
        <div className="text-center">
          <Loader2 className="w-10 h-10 mx-auto text-primary animate-spin mb-4" />
          <p className="text-muted-foreground">Loading profile...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <header className="border-b border-orange-100 bg-white/50 backdrop-blur-sm sticky top-0 z-50">
        <div className="max-w-5xl mx-auto px-6 py-4 flex items-center justify-between">
          <Button variant="ghost" className="rounded-full" onClick={() => navigate(-1)} data-testid="back-btn">
            <ArrowLeft className="w-4 h-4 mr-2" />
            Back
          </Button>
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 bg-primary rounded-full flex items-center justify-center">
              <span className="text-white">🍊</span>
            </div>
            <span className="font-heading font-bold">Orange</span>
          </div>
          
          {/* Access Level Badge */}
          <Badge className={accessLevel === 'full' ? 'bg-green-500 text-white' : accessLevel === 'unlocked' ? 'bg-primary text-white' : 'bg-muted'}>
            {accessLevel === 'full' ? (
              <><Unlock className="w-3 h-3 mr-1" /> Full Access</>
            ) : accessLevel === 'unlocked' ? (
              <><Unlock className="w-3 h-3 mr-1" /> Context Unlocked</>
            ) : (
              <><Lock className="w-3 h-3 mr-1" /> Locked</>
            )}
          </Badge>
        </div>
      </header>

      <main className="max-w-5xl mx-auto px-6 py-8">
        {/* Brand Hero */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="card-orange p-8 mb-8"
        >
          <div className="flex flex-col md:flex-row items-start gap-6">
            <div className="w-24 h-24 bg-gradient-to-br from-primary/20 to-accent/20 rounded-2xl flex items-center justify-center shrink-0">
              <Building2 className="w-12 h-12 text-primary" />
            </div>
            
            <div className="flex-1">
              <div className="text-center md:text-left">
                <h1 className="font-heading text-2xl font-bold mb-2">{displayName}</h1>
                {accessLevel !== 'discovery' && brand?.bio && (
                  <p className="text-muted-foreground mb-4">{brand.bio}</p>
                )}
                
                <div className="flex items-center justify-center md:justify-start gap-4 text-sm text-muted-foreground mb-4">
                  {brand?.location && (
                    <div className="flex items-center gap-1">
                      <MapPin className="w-4 h-4" />
                      {brand.location}
                    </div>
                  )}
                  {brand?.industry && (
                    <Badge variant="secondary">{brand.industry}</Badge>
                  )}
                </div>

                {/* Stats */}
                <div className="grid grid-cols-2 gap-4 mb-4">
                  <div className="bg-muted/50 p-3 rounded-xl text-center">
                    <DollarSign className="w-5 h-5 mx-auto text-primary mb-1" />
                    <p className="text-xs text-muted-foreground">Budget Range</p>
                    <p className="font-bold text-primary">{brand?.budgetRange || 'Varies'}</p>
                  </div>
                  <div className="bg-muted/50 p-3 rounded-xl text-center">
                    <Briefcase className="w-5 h-5 mx-auto text-primary mb-1" />
                    <p className="text-xs text-muted-foreground">Past Collabs</p>
                    <p className="font-bold text-primary">{brand?.pastCollabCount || brand?.pastCollabsDisplay || '0'}</p>
                  </div>
                </div>

                {/* Preferred Niches */}
                {brand?.preferredNiches?.length > 0 && (
                  <div className="mb-4">
                    <p className="text-xs text-muted-foreground mb-2">LOOKING FOR</p>
                    <div className="flex flex-wrap gap-2">
                      {brand.preferredNiches.map(niche => (
                        <Badge key={niche} variant="outline">{niche}</Badge>
                      ))}
                    </div>
                  </div>
                )}

                {brand?.isOpenToBarter && (
                  <Badge className="bg-accent text-accent-foreground">
                    🤝 Open to Barter
                  </Badge>
                )}
              </div>
            </div>
          </div>
        </motion.div>

        {/* Past Collaborations Section (only if unlocked and has collabs) */}
        {accessLevel === 'unlocked' && brand?.pastCollaborations?.length > 0 && (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.05 }}
            className="card-orange p-6 mb-8"
          >
            <h3 className="font-heading text-lg font-bold mb-4 flex items-center gap-2">
              <Briefcase className="w-5 h-5 text-primary" />
              Past Collaborations ({brand.pastCollaborations.length})
            </h3>
            <div className="grid gap-3">
              {brand.pastCollaborations.map((collab, index) => (
                <div key={index} className="bg-muted/50 p-4 rounded-xl">
                  <div className="flex items-start justify-between">
                    <div>
                      <p className="font-semibold">{collab.campaignName}</p>
                      <div className="flex items-center gap-2 mt-1 text-sm text-muted-foreground">
                        {collab.creatorNiche && <Badge variant="outline" className="text-xs">{collab.creatorNiche}</Badge>}
                        {collab.platform && <span>on {collab.platform}</span>}
                      </div>
                    </div>
                    {collab.link && (
                      <a href={collab.link} target="_blank" rel="noopener noreferrer" className="text-primary hover:underline text-sm">
                        View →
                      </a>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </motion.div>
        )}

        {/* Instagram Access Section (only if full access) */}
        {accessLevel === 'unlocked' && (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.1 }}
            className="card-orange p-6 mb-8 border-2 border-dashed border-orange-200"
          >
            <div className="flex items-center gap-4">
              <div className="w-12 h-12 bg-orange-100 rounded-full flex items-center justify-center">
                <Instagram className="w-6 h-6 text-primary" />
              </div>
              <div className="flex-1">
                <h3 className="font-semibold">Instagram Access Locked</h3>
                <p className="text-sm text-muted-foreground">
                  Instagram handle unlocks after brand accepts your collaboration request
                </p>
              </div>
              <Lock className="w-5 h-5 text-muted-foreground" />
            </div>
          </motion.div>
        )}

        {/* CTA Section */}
        {canSendRequest && (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.2 }}
            className="card-orange p-6"
          >
            <h3 className="font-heading text-lg font-bold mb-4">Interested in collaborating?</h3>
            <Button 
              className="btn-primary w-full"
              onClick={() => toast.info("Request flow coming soon!")}
              data-testid="send-request-btn"
            >
              <MessageSquare className="w-4 h-4 mr-2" />
              Send Collaboration Request
            </Button>
          </motion.div>
        )}
      </main>

      {/* Unlock Modal */}
      <Dialog open={showUnlockModal} onOpenChange={setShowUnlockModal}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <Lock className="w-5 h-5 text-primary" />
              Unlock Brand Profile
            </DialogTitle>
            <DialogDescription>
              Spend 1 credit to unlock full profile details
            </DialogDescription>
          </DialogHeader>
          
          <div className="space-y-4">
            {/* Brand Preview */}
            <div className="flex items-center gap-4 p-4 bg-muted/50 rounded-xl">
              <div className="w-16 h-16 bg-gradient-to-br from-primary/20 to-accent/20 rounded-2xl flex items-center justify-center">
                <Building2 className="w-8 h-8 text-primary" />
              </div>
              <div>
                <h3 className="font-heading font-bold">Brand Profile</h3>
                <p className="text-sm text-muted-foreground">{brand?.industry}</p>
                {brand?.location && (
                  <p className="text-xs text-muted-foreground">{brand.location}</p>
                )}
              </div>
            </div>

            {/* What you'll unlock */}
            <div className="space-y-2">
              <p className="font-semibold text-sm">What you'll unlock:</p>
              <ul className="text-sm text-muted-foreground space-y-1">
                <li className="flex items-center gap-2">
                  <Unlock className="w-4 h-4 text-green-500" /> Full brand bio & details
                </li>
                <li className="flex items-center gap-2">
                  <Unlock className="w-4 h-4 text-green-500" /> Budget range
                </li>
                <li className="flex items-center gap-2">
                  <Unlock className="w-4 h-4 text-green-500" /> Past collaboration history
                </li>
                <li className="flex items-center gap-2">
                  <Unlock className="w-4 h-4 text-green-500" /> Send collaboration requests
                </li>
              </ul>
              <p className="text-xs text-orange-600 mt-2">
                Note: Instagram access unlocks after your collaboration request is accepted
              </p>
            </div>

            {/* Credits Display */}
            <div className="flex items-center justify-between p-3 bg-primary/10 rounded-xl">
              <div className="flex items-center gap-2">
                <CreditCard className="w-5 h-5 text-primary" />
                <span className="font-semibold">Your Credits:</span>
              </div>
              <span className="font-bold text-primary">{unlockCredits.availableCredits}</span>
            </div>

            {/* Action Buttons */}
            {unlockCredits.availableCredits > 0 ? (
              <Button 
                onClick={handleUnlockBrand} 
                className="w-full btn-primary"
                disabled={unlocking}
                data-testid="unlock-brand-btn"
              >
                {unlocking ? (
                  <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                ) : (
                  <Unlock className="w-4 h-4 mr-2" />
                )}
                Unlock Brand Profile (1 Credit)
              </Button>
            ) : (
              <div className="space-y-3">
                <p className="text-center text-sm text-muted-foreground">
                  You need credits to unlock profiles
                </p>
                <Button 
                  onClick={handleBuyCredits}
                  className="w-full btn-primary"
                  disabled={buyingCredits}
                  data-testid="buy-credits-btn"
                >
                  {buyingCredits ? (
                    <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                  ) : (
                    <CreditCard className="w-4 h-4 mr-2" />
                  )}
                  Get Demo Credits (Test Mode)
                </Button>
              </div>
            )}

            <Button 
              variant="outline" 
              onClick={() => {
                setShowUnlockModal(false);
                navigate(-1);
              }}
              className="w-full"
            >
              Go Back
            </Button>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default BusinessProfile;
