import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import { 
  Instagram, Globe, MapPin, Edit, LogOut, MessageSquare, Send, Unlock, CreditCard,
  ExternalLink, Search, Filter, X, Users, DollarSign, Loader2, Lock, Eye, Sparkles
} from 'lucide-react';
import { Button } from '../../components/ui/button';
import { Badge } from '../../components/ui/badge';
import { Avatar, AvatarFallback, AvatarImage } from '../../components/ui/avatar';
import { Input } from '../../components/ui/input';
import { Label } from '../../components/ui/label';
import { Slider } from '../../components/ui/slider';
import { Switch } from '../../components/ui/switch';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../../components/ui/select';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../../components/ui/tabs';
import { Sheet, SheetContent, SheetHeader, SheetTitle, SheetTrigger } from '../../components/ui/sheet';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '../../components/ui/dialog';
import { businessAPI, marketplaceAPI, campaignsAPI, paymentsAPI, requestsAPI, getErrorMessage } from '../../lib/api';
import { useAuth } from '../../lib/auth';
import { toast } from 'sonner';

const NICHES = [
  'All', 'Fashion', 'Beauty', 'Fitness', 'Tech', 'Gaming', 'Food', 
  'Travel', 'Lifestyle', 'Comedy', 'Education', 'Music', 'Art',
  'Sports', 'Health', 'Finance'
];

const BusinessDashboard = () => {
  const navigate = useNavigate();
  const { logout } = useAuth();
  const [profile, setProfile] = useState(null);
  const [creators, setCreators] = useState([]);
  const [sentCampaigns, setSentCampaigns] = useState([]);
  const [unlockCredits, setUnlockCredits] = useState({ availableCredits: 0 });
  const [loading, setLoading] = useState(true);
  const [creatorsLoading, setCreatorsLoading] = useState(false);
  const [showUnlockModal, setShowUnlockModal] = useState(false);
  const [selectedCreator, setSelectedCreator] = useState(null);
  const [buyingCredits, setBuyingCredits] = useState(false);
  
  // Filters
  const [filters, setFilters] = useState({
    niche: '',
    minFollowers: 0,
    maxFollowers: 1000000,
    location: '',
    openToBarter: false
  });
  const [showFilters, setShowFilters] = useState(false);

  useEffect(() => {
    loadProfile();
    loadCreators();
    loadSentCampaigns();
  }, []);

  const loadProfile = async () => {
    try {
      const [profileRes, creditsRes] = await Promise.all([
        businessAPI.getProfile(),
        businessAPI.getUnlockCredits()
      ]);
      setProfile(profileRes.data);
      setUnlockCredits(creditsRes.data);
    } catch (error) {
      if (error.response?.status === 404) {
        navigate('/onboarding/business');
      }
    }
  };

  const loadCreators = async (customFilters = filters) => {
    setCreatorsLoading(true);
    try {
      const params = {};
      if (customFilters.niche && customFilters.niche !== 'All') params.niche = customFilters.niche;
      if (customFilters.minFollowers > 0) params.minFollowers = customFilters.minFollowers;
      if (customFilters.maxFollowers < 1000000) params.maxFollowers = customFilters.maxFollowers;
      if (customFilters.location) params.location = customFilters.location;
      if (customFilters.openToBarter) params.openToBarter = true;
      
      const response = await marketplaceAPI.discoverCreators(params);
      setCreators(response.data);
    } catch (error) {
      toast.error("Failed to load creators");
    } finally {
      setCreatorsLoading(false);
      setLoading(false);
    }
  };

  const loadSentCampaigns = async () => {
    try {
      const response = await campaignsAPI.getSent();
      setSentCampaigns(response.data);
    } catch (error) {
      console.error("Failed to load sent campaigns");
    }
  };

  const applyFilters = () => {
    loadCreators(filters);
    setShowFilters(false);
  };

  const resetFilters = () => {
    const defaultFilters = {
      niche: '',
      minFollowers: 0,
      maxFollowers: 1000000,
      location: '',
      openToBarter: false
    };
    setFilters(defaultFilters);
    loadCreators(defaultFilters);
  };

  const handleCreatorClick = (creator) => {
    if (creator.isUnlocked) {
      navigate(`/profile/creator/${creator.id}`);
    } else {
      setSelectedCreator(creator);
      setShowUnlockModal(true);
    }
  };

  const handleUnlockCreator = async () => {
    if (!selectedCreator) return;
    
    if (unlockCredits.availableCredits <= 0) {
      toast.error("No unlock credits! Purchase a pack first.");
      return;
    }

    try {
      await marketplaceAPI.unlockCreator(selectedCreator.id);
      toast.success("Creator unlocked! 🔓");
      setShowUnlockModal(false);
      
      // Refresh credits and creators
      const creditsRes = await businessAPI.getUnlockCredits();
      setUnlockCredits(creditsRes.data);
      loadCreators();
      
      // Navigate to unlocked profile
      navigate(`/profile/creator/${selectedCreator.id}`);
    } catch (error) {
      toast.error(error.response?.data?.detail || "Failed to unlock creator");
    }
  };

  const handleBuyCredits = async () => {
    setBuyingCredits(true);
    try {
      const orderRes = await paymentsAPI.createUnlockOrder();
      const { orderId, amount, keyId, testMode } = orderRes.data;
      
      // For test mode without valid keys, use demo credits
      if (!keyId || keyId === 'rzp_test_demo' || testMode) {
        // Use demo credits for testing
        await paymentsAPI.addDemoCredits();
        toast.success("Demo credits added! 5 credits for testing 🎉");
        const creditsRes = await paymentsAPI.getCredits();
        setUnlockCredits(creditsRes.data);
        setBuyingCredits(false);
        return;
      }

      const options = {
        key: keyId,
        amount: amount,
        currency: "INR",
        name: "Orange",
        description: "5 Creator Unlock Credits",
        order_id: orderId,
        handler: async (response) => {
          try {
            await paymentsAPI.verifyUnlockPayment({
              razorpay_order_id: response.razorpay_order_id,
              razorpay_payment_id: response.razorpay_payment_id,
              razorpay_signature: response.razorpay_signature
            });
            toast.success("Payment successful! 5 credits added 🎉");
            const creditsRes = await paymentsAPI.getCredits();
            setUnlockCredits(creditsRes.data);
          } catch (err) {
            toast.error("Payment verification failed");
          }
        },
        prefill: {
          email: profile?.email || ""
        },
        theme: {
          color: "#FF6B00"
        }
      };

      const razorpay = new window.Razorpay(options);
      razorpay.open();
    } catch (error) {
      // Fallback to demo credits
      try {
        await paymentsAPI.addDemoCredits();
        toast.success("Demo credits added! 5 credits for testing 🎉");
        const creditsRes = await paymentsAPI.getCredits();
        setUnlockCredits(creditsRes.data);
      } catch (demoError) {
        toast.error("Failed to add credits");
      }
    } finally {
      setBuyingCredits(false);
    }
  };

  const handleLogout = () => {
    logout();
    navigate('/');
  };

  const formatFollowers = (count) => {
    if (count >= 1000000) return `${(count / 1000000).toFixed(1)}M`;
    if (count >= 1000) return `${(count / 1000).toFixed(1)}K`;
    return count.toString();
  };

  const formatPrice = (price) => {
    return new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR', maximumFractionDigits: 0 }).format(price);
  };

  if (loading) {
    return (
      <div className="min-h-screen gradient-hero flex items-center justify-center">
        <div className="text-center">
          <Loader2 className="w-10 h-10 mx-auto text-primary animate-spin mb-4" />
          <p className="text-muted-foreground">Juicing the data... 🧃</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <header className="border-b border-orange-100 bg-white/50 backdrop-blur-sm sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-primary rounded-full flex items-center justify-center">
              <span className="text-white text-xl">🍊</span>
            </div>
            <span className="font-heading font-bold text-xl">Orange</span>
          </div>
          
          {/* Unlock Credits Badge */}
          <div className="flex items-center gap-4">
            <div className="flex items-center gap-2 bg-accent/20 px-4 py-2 rounded-full">
              <Unlock className="w-4 h-4 text-primary" />
              <span className="font-semibold">{unlockCredits.availableCredits} Credits</span>
              <Button 
                size="sm" 
                className="ml-2 bg-primary hover:bg-primary/90 rounded-full h-7 px-3"
                onClick={handleBuyCredits}
                disabled={buyingCredits}
                data-testid="buy-credits-btn"
              >
                {buyingCredits ? <Loader2 className="w-3 h-3 animate-spin" /> : '+'}
              </Button>
            </div>
            
            <Button
              variant="outline"
              className="rounded-full"
              onClick={() => navigate(`/profile/business/${profile?.id}`)}
              data-testid="view-public-profile-btn"
            >
              <ExternalLink className="w-4 h-4 mr-2" />
              View Profile
            </Button>
            <Button
              variant="ghost"
              className="rounded-full text-muted-foreground"
              onClick={handleLogout}
              data-testid="logout-btn"
            >
              <LogOut className="w-4 h-4 mr-2" />
              Logout
            </Button>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-6 py-8">
        {/* Brand Card */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="card-orange p-6 mb-8"
        >
          <div className="flex items-center gap-6">
            <Avatar className="w-20 h-20 border-4 border-primary">
              <AvatarImage src={profile?.profilePhotoUrl} />
              <AvatarFallback className="bg-primary text-white text-2xl">
                {profile?.brandName?.[0]}
              </AvatarFallback>
            </Avatar>
            <div className="flex-1">
              <div className="flex items-center gap-3 mb-2">
                <h2 className="font-heading text-2xl font-bold">{profile?.brandName}</h2>
                <Badge className="bg-accent text-accent-foreground">{profile?.category}</Badge>
              </div>
              <p className="text-muted-foreground mb-3">{profile?.bio}</p>
              <div className="flex items-center gap-4 text-sm text-muted-foreground">
                {profile?.location && (
                  <div className="flex items-center gap-1">
                    <MapPin className="w-4 h-4" />
                    {profile.location}
                  </div>
                )}
              </div>
            </div>
            <Button
              onClick={() => navigate('/onboarding/business')}
              variant="outline"
              className="rounded-full"
              data-testid="edit-profile-btn"
            >
              <Edit className="w-4 h-4 mr-2" />
              Edit Profile
            </Button>
          </div>
        </motion.div>

        {/* Credits Info Banner */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
          className="bg-gradient-to-r from-primary/10 to-accent/10 rounded-3xl p-6 mb-8"
        >
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <div className="w-14 h-14 bg-primary rounded-2xl flex items-center justify-center">
                <CreditCard className="w-7 h-7 text-white" />
              </div>
              <div>
                <h3 className="font-heading font-bold text-lg">Unlock Creators</h3>
                <p className="text-muted-foreground text-sm">
                  ₹200 = 5 credits • 1 credit = 1 creator unlock • Valid for 7 days
                </p>
              </div>
            </div>
            <Button onClick={handleBuyCredits} className="btn-primary" disabled={buyingCredits}>
              {buyingCredits ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : <Sparkles className="w-4 h-4 mr-2" />}
              Buy Unlock Pack - ₹200
            </Button>
          </div>
        </motion.div>

        {/* Tabs */}
        <Tabs defaultValue="marketplace" className="w-full">
          <TabsList className="mb-6 bg-muted/50 p-1 rounded-full">
            <TabsTrigger value="marketplace" className="rounded-full data-[state=active]:bg-white px-6">
              🍊 Creator Marketplace
            </TabsTrigger>
            <TabsTrigger value="campaigns" className="rounded-full data-[state=active]:bg-white px-6">
              📤 My Campaigns ({sentCampaigns.length})
            </TabsTrigger>
          </TabsList>

          <TabsContent value="marketplace">
            {/* Marketplace Header */}
            <div className="flex items-center justify-between mb-6">
              <div>
                <h2 className="font-heading text-2xl font-bold">Squeeze the perfect creator 🍊</h2>
                <p className="text-muted-foreground">{creators.length} creators found</p>
              </div>
              
              <Sheet open={showFilters} onOpenChange={setShowFilters}>
                <SheetTrigger asChild>
                  <Button variant="outline" className="rounded-full" data-testid="open-filters-btn">
                    <Filter className="w-4 h-4 mr-2" />
                    Filters
                  </Button>
                </SheetTrigger>
                <SheetContent className="w-[400px]">
                  <SheetHeader>
                    <SheetTitle className="font-heading">Filter Creators 🎯</SheetTitle>
                  </SheetHeader>
                  
                  <div className="space-y-6 mt-6">
                    <div className="space-y-2">
                      <Label>Niche</Label>
                      <Select value={filters.niche} onValueChange={(value) => setFilters(prev => ({ ...prev, niche: value }))}>
                        <SelectTrigger className="rounded-xl">
                          <SelectValue placeholder="All niches" />
                        </SelectTrigger>
                        <SelectContent>
                          {NICHES.map(niche => (
                            <SelectItem key={niche} value={niche}>{niche}</SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    </div>

                    <div className="space-y-4">
                      <Label>Followers Range</Label>
                      <Slider
                        value={[filters.minFollowers, filters.maxFollowers]}
                        onValueChange={([min, max]) => setFilters(prev => ({ ...prev, minFollowers: min, maxFollowers: max }))}
                        min={0}
                        max={1000000}
                        step={1000}
                      />
                      <div className="flex justify-between text-sm text-muted-foreground">
                        <span>{formatFollowers(filters.minFollowers)}</span>
                        <span>{formatFollowers(filters.maxFollowers)}</span>
                      </div>
                    </div>

                    <div className="space-y-2">
                      <Label>Location</Label>
                      <Input
                        placeholder="Mumbai, Delhi..."
                        value={filters.location}
                        onChange={(e) => setFilters(prev => ({ ...prev, location: e.target.value }))}
                        className="input-orange"
                      />
                    </div>

                    <div className="flex items-center justify-between p-4 bg-muted/50 rounded-xl">
                      <div>
                        <p className="font-semibold">Open to Barter Only</p>
                        <p className="text-sm text-muted-foreground">Filter barter-friendly creators</p>
                      </div>
                      <Switch
                        checked={filters.openToBarter}
                        onCheckedChange={(checked) => setFilters(prev => ({ ...prev, openToBarter: checked }))}
                      />
                    </div>

                    <div className="flex gap-3 pt-4">
                      <Button variant="outline" className="flex-1 rounded-full" onClick={resetFilters}>
                        Reset
                      </Button>
                      <Button className="flex-1 btn-primary" onClick={applyFilters}>
                        Apply Filters
                      </Button>
                    </div>
                  </div>
                </SheetContent>
              </Sheet>
            </div>

            {/* Creators Grid */}
            {creatorsLoading ? (
              <div className="text-center py-12">
                <Loader2 className="w-10 h-10 mx-auto text-primary animate-spin mb-4" />
                <p className="text-muted-foreground">Finding amazing creators...</p>
              </div>
            ) : creators.length === 0 ? (
              <div className="card-orange p-12 text-center">
                <span className="text-5xl block mb-4">🔍</span>
                <h3 className="font-heading text-xl font-bold mb-2">No creators found</h3>
                <p className="text-muted-foreground mb-4">Try adjusting your filters</p>
                <Button onClick={resetFilters} variant="outline" className="rounded-full">
                  Reset Filters
                </Button>
              </div>
            ) : (
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
                {creators.map((creator, idx) => (
                  <CreatorDiscoveryCard 
                    key={creator.id} 
                    creator={creator} 
                    index={idx}
                    onClick={() => handleCreatorClick(creator)}
                  />
                ))}
              </div>
            )}
          </TabsContent>

          <TabsContent value="campaigns">
            <div className="mb-6">
              <h2 className="font-heading text-2xl font-bold">Your Campaigns</h2>
              <p className="text-muted-foreground">Track your collaboration campaigns</p>
            </div>

            {sentCampaigns.length === 0 ? (
              <div className="card-orange p-12 text-center">
                <span className="text-5xl block mb-4">📤</span>
                <h3 className="font-heading text-xl font-bold mb-2">No campaigns yet</h3>
                <p className="text-muted-foreground">Unlock creators and send your first campaign!</p>
              </div>
            ) : (
              <div className="space-y-4">
                {sentCampaigns.map(campaign => (
                  <CampaignCard 
                    key={campaign.id} 
                    campaign={campaign}
                    onChat={() => navigate(`/chat/${campaign.id}`)}
                    onViewCreator={() => navigate(`/profile/creator/${campaign.creatorId}`)}
                  />
                ))}
              </div>
            )}
          </TabsContent>
        </Tabs>
      </main>

      {/* Unlock Modal */}
      <Dialog open={showUnlockModal} onOpenChange={setShowUnlockModal}>
        <DialogContent className="sm:max-w-[450px]">
          <DialogHeader>
            <DialogTitle className="font-heading text-xl flex items-center gap-2">
              <Lock className="w-5 h-5 text-primary" />
              Unlock Creator Profile
            </DialogTitle>
          </DialogHeader>
          
          {selectedCreator && (
            <div className="space-y-6 pt-4">
              <div className="text-center">
                <div className="w-20 h-20 mx-auto mb-4 rounded-full bg-gradient-to-br from-primary/20 to-accent/20 flex items-center justify-center text-4xl">
                  {selectedCreator.niches?.[0]?.[0] || '🍊'}
                </div>
                <h3 className="font-heading text-xl font-bold">Creator Profile</h3>
                <p className="text-muted-foreground">{selectedCreator.location}</p>
                <div className="flex justify-center gap-2 mt-2">
                  {selectedCreator.niches?.slice(0, 2).map(niche => (
                    <Badge key={niche} variant="secondary">{niche}</Badge>
                  ))}
                </div>
              </div>

              <div className="bg-muted/50 rounded-2xl p-4 space-y-2">
                <p className="font-semibold text-sm">What you'll unlock:</p>
                <ul className="text-sm text-muted-foreground space-y-1">
                  <li>✓ Full profile & bio</li>
                  <li>✓ Exact engagement rate</li>
                  <li>✓ Complete rate card</li>
                  <li>✓ Full media gallery</li>
                  <li>✓ In-app chat access</li>
                </ul>
                <p className="text-xs text-muted-foreground pt-2 border-t">
                  Instagram access unlocks after campaign payment
                </p>
              </div>

              <div className="flex items-center justify-between p-4 bg-primary/5 rounded-2xl">
                <div>
                  <p className="font-semibold">Your Credits</p>
                  <p className="text-2xl font-bold text-primary">{unlockCredits.availableCredits}</p>
                </div>
                <div className="text-right">
                  <p className="font-semibold">Cost</p>
                  <p className="text-2xl font-bold">1 Credit</p>
                </div>
              </div>

              {unlockCredits.availableCredits > 0 ? (
                <Button onClick={handleUnlockCreator} className="w-full btn-primary">
                  <Unlock className="w-4 h-4 mr-2" />
                  Unlock Creator Profile
                </Button>
              ) : (
                <div className="space-y-3">
                  <p className="text-center text-destructive font-semibold">No credits available!</p>
                  <Button onClick={handleBuyCredits} className="w-full btn-primary" disabled={buyingCredits}>
                    {buyingCredits ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : <CreditCard className="w-4 h-4 mr-2" />}
                    Buy 5 Credits - ₹200
                  </Button>
                </div>
              )}
            </div>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
};

// Discovery Card (Layer 1 - Gated)
const CreatorDiscoveryCard = ({ creator, index, onClick }) => {
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: index * 0.05 }}
      className="card-orange overflow-hidden cursor-pointer group"
      onClick={onClick}
      data-testid={`creator-card-${creator.id}`}
    >
      <div className="aspect-[3/4] relative">
        {/* Blurred/Placeholder Background */}
        <div className="w-full h-full bg-gradient-to-br from-primary/30 to-accent/30 flex items-center justify-center">
          {creator.previewContent?.[0] ? (
            <img 
              src={creator.previewContent[0]} 
              alt=""
              className={`w-full h-full object-cover ${!creator.isUnlocked ? 'blur-sm' : ''} group-hover:scale-105 transition-transform duration-300`}
            />
          ) : (
            <span className="text-6xl">{creator.niches?.[0]?.[0] || '🍊'}</span>
          )}
        </div>
        
        {/* Lock Overlay for non-unlocked */}
        {!creator.isUnlocked && (
          <div className="absolute inset-0 bg-black/20 flex items-center justify-center">
            <div className="bg-white/90 backdrop-blur-sm rounded-full p-3">
              <Lock className="w-6 h-6 text-primary" />
            </div>
          </div>
        )}
        
        {/* Gradient overlay */}
        <div className="absolute inset-0 bg-gradient-to-t from-black/70 via-transparent to-transparent" />
        
        {/* Badges */}
        <div className="absolute top-3 left-3 flex flex-wrap gap-2">
          {creator.niches?.slice(0, 2).map(niche => (
            <Badge key={niche} className="bg-white/90 text-foreground text-xs">
              {niche}
            </Badge>
          ))}
        </div>
        
        {creator.isOpenToBarter && (
          <div className="absolute top-3 right-3">
            <Badge className="bg-accent text-accent-foreground">🤝 Barter</Badge>
          </div>
        )}

        {creator.isUnlocked && (
          <div className="absolute top-3 right-3">
            <Badge className="bg-green-500 text-white">
              <Unlock className="w-3 h-3 mr-1" />
              Unlocked
            </Badge>
          </div>
        )}

        {/* Info */}
        <div className="absolute bottom-0 left-0 right-0 p-4 text-white">
          <h3 className="font-heading font-bold text-lg mb-1">
            {creator.isUnlocked ? 'View Profile' : 'Creator'}
          </h3>
          <div className="flex items-center gap-3 text-sm opacity-90">
            <div className="flex items-center gap-1">
              <Users className="w-4 h-4" />
              {creator.followersDisplay}
            </div>
            {creator.location && (
              <div className="flex items-center gap-1">
                <MapPin className="w-4 h-4" />
                {creator.location}
              </div>
            )}
          </div>
          <div className="mt-2 flex items-center gap-3 text-xs opacity-80">
            <span>📊 {creator.engagementRateDisplay}</span>
            <span>💰 {creator.rateRange}</span>
          </div>
        </div>
      </div>
    </motion.div>
  );
};

// Campaign Card
const CampaignCard = ({ campaign, onChat, onViewCreator }) => {
  const formatPrice = (price) => {
    return new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR', maximumFractionDigits: 0 }).format(price);
  };

  const statusColors = {
    proposed: 'bg-blue-100 text-blue-800',
    accepted: 'bg-green-100 text-green-800',
    declined: 'bg-red-100 text-red-800',
    in_progress: 'bg-yellow-100 text-yellow-800',
    delivered: 'bg-purple-100 text-purple-800',
    completed: 'bg-green-100 text-green-800',
    cancelled: 'bg-gray-100 text-gray-800'
  };

  const escrowColors = {
    pending: 'bg-orange-100 text-orange-800',
    paid: 'bg-green-100 text-green-800',
    released: 'bg-blue-100 text-blue-800'
  };

  return (
    <div className="card-orange p-6" data-testid={`campaign-${campaign.id}`}>
      <div className="flex items-start gap-4">
        <Avatar className="w-14 h-14 border-2 border-orange-100 cursor-pointer" onClick={onViewCreator}>
          <AvatarFallback className="bg-primary/10 text-primary">
            {campaign.creatorName?.[0]}
          </AvatarFallback>
        </Avatar>
        <div className="flex-1">
          <div className="flex items-center gap-2 mb-1 flex-wrap">
            <h4 className="font-semibold cursor-pointer hover:text-primary" onClick={onViewCreator}>
              {campaign.creatorName || 'Creator'}
            </h4>
            <Badge className={statusColors[campaign.campaignStatus]}>
              {campaign.campaignStatus?.replace('_', ' ')}
            </Badge>
            <Badge className={escrowColors[campaign.escrowStatus]}>
              Escrow: {campaign.escrowStatus}
            </Badge>
          </div>
          <h3 className="font-heading text-lg font-bold mb-2">{campaign.title}</h3>
          <p className="text-muted-foreground text-sm mb-3 line-clamp-2">{campaign.brief}</p>
          
          <div className="flex flex-wrap gap-4 text-sm">
            <div className="flex items-center gap-1 text-primary font-semibold">
              <DollarSign className="w-4 h-4" />
              {formatPrice(campaign.price)}
            </div>
            {campaign.deliverables && (
              <div className="text-muted-foreground">📦 {campaign.deliverables}</div>
            )}
            {campaign.instagramHandle && (
              <a href={campaign.instagramUrl} target="_blank" rel="noopener noreferrer" 
                 className="flex items-center gap-1 text-primary hover:underline">
                <Instagram className="w-4 h-4" />
                {campaign.instagramHandle}
              </a>
            )}
          </div>
        </div>
        
        {campaign.campaignStatus !== 'declined' && campaign.campaignStatus !== 'cancelled' && (
          <Button onClick={onChat} className="btn-primary" data-testid={`chat-btn-${campaign.id}`}>
            <MessageSquare className="w-4 h-4 mr-2" />
            Chat
          </Button>
        )}
      </div>
    </div>
  );
};

export default BusinessDashboard;
