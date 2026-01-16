import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import { 
  Instagram, MapPin, Users, Edit, LogOut, MessageSquare, Check, X, 
  ExternalLink, DollarSign, Image as ImageIcon, Loader2, Lock, Unlock
} from 'lucide-react';
import { Button } from '../../components/ui/button';
import { Badge } from '../../components/ui/badge';
import { Avatar, AvatarFallback, AvatarImage } from '../../components/ui/avatar';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../../components/ui/tabs';
import { creatorAPI, campaignsAPI } from '../../lib/api';
import { useAuth } from '../../lib/auth';
import { toast } from 'sonner';

const CreatorDashboard = () => {
  const navigate = useNavigate();
  const { user, logout } = useAuth();
  const [profile, setProfile] = useState(null);
  const [campaigns, setCampaigns] = useState([]);
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState(null);

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      const [profileRes, campaignsRes] = await Promise.all([
        creatorAPI.getProfile(),
        creatorAPI.getRequests()
      ]);
      setProfile(profileRes.data);
      setCampaigns(campaignsRes.data);
    } catch (error) {
      if (error.response?.status === 404) {
        navigate('/onboarding/creator');
      } else {
        toast.error("Failed to load profile");
      }
    } finally {
      setLoading(false);
    }
  };

  const handleCampaignAction = async (campaignId, newStatus) => {
    setActionLoading(campaignId);
    try {
      await campaignsAPI.updateStatus(campaignId, newStatus);
      setCampaigns(prev => prev.map(c => 
        c.id === campaignId ? { ...c, campaignStatus: newStatus } : c
      ));
      
      if (newStatus === 'accepted') {
        toast.success("Campaign accepted! Time to make magic ✨");
      } else if (newStatus === 'declined') {
        toast.success("Campaign declined");
      } else if (newStatus === 'delivered') {
        toast.success("Marked as delivered! Waiting for brand approval 🎉");
      }
    } catch (error) {
      toast.error("Failed to update campaign");
    } finally {
      setActionLoading(null);
    }
  };

  const handleLogout = () => {
    logout();
    navigate('/');
  };

  const formatPrice = (price) => {
    return new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR', maximumFractionDigits: 0 }).format(price);
  };

  const formatFollowers = (count) => {
    if (count >= 1000000) return `${(count / 1000000).toFixed(1)}M`;
    if (count >= 1000) return `${(count / 1000).toFixed(1)}K`;
    return count.toString();
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

  const proposedCampaigns = campaigns.filter(c => c.campaignStatus === 'proposed');
  const acceptedCampaigns = campaigns.filter(c => ['accepted', 'in_progress'].includes(c.campaignStatus));
  const completedCampaigns = campaigns.filter(c => ['delivered', 'completed'].includes(c.campaignStatus));
  const declinedCampaigns = campaigns.filter(c => ['declined', 'cancelled'].includes(c.campaignStatus));

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
          <div className="flex items-center gap-3">
            <Button
              variant="outline"
              className="rounded-full"
              onClick={() => navigate(`/profile/creator/${profile?.id}`)}
              data-testid="view-public-profile-btn"
            >
              <ExternalLink className="w-4 h-4 mr-2" />
              View Public Profile
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
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          {/* Profile Card */}
          <div className="lg:col-span-1">
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              className="card-orange p-6 sticky top-24"
            >
              <div className="text-center mb-6">
                <Avatar className="w-24 h-24 mx-auto mb-4 border-4 border-primary">
                  <AvatarImage src={profile?.profilePhotoUrl} />
                  <AvatarFallback className="bg-primary text-white text-2xl">
                    {profile?.name?.[0]}
                  </AvatarFallback>
                </Avatar>
                <h2 className="font-heading text-2xl font-bold mb-1">{profile?.name}</h2>
                <p className="text-muted-foreground text-sm mb-3">{profile?.bio}</p>
                
                <div className="flex items-center justify-center gap-4 text-sm text-muted-foreground mb-4">
                  {profile?.location && (
                    <div className="flex items-center gap-1">
                      <MapPin className="w-4 h-4" />
                      {profile.location}
                    </div>
                  )}
                  <div className="flex items-center gap-1">
                    <Users className="w-4 h-4" />
                    {formatFollowers(profile?.followersCount || 0)} followers
                  </div>
                </div>

                {/* Niches */}
                <div className="flex flex-wrap justify-center gap-2 mb-4">
                  {profile?.niches?.map(niche => (
                    <Badge key={niche} variant="secondary" className="bg-primary/10 text-primary">
                      {niche}
                    </Badge>
                  ))}
                </div>

                {profile?.isOpenToBarter && (
                  <Badge className="bg-accent text-accent-foreground">
                    🤝 Open to Barter
                  </Badge>
                )}
              </div>

              {/* Rates */}
              <div className="border-t border-orange-100 pt-4 mb-4">
                <h3 className="font-semibold text-sm text-muted-foreground mb-3">YOUR RATES</h3>
                <div className="grid grid-cols-2 gap-3">
                  <div className="bg-muted/50 p-3 rounded-xl">
                    <p className="text-xs text-muted-foreground">Reel</p>
                    <p className="font-bold text-primary">{formatPrice(profile?.rates?.reelPrice || 0)}</p>
                  </div>
                  <div className="bg-muted/50 p-3 rounded-xl">
                    <p className="text-xs text-muted-foreground">Story</p>
                    <p className="font-bold text-primary">{formatPrice(profile?.rates?.storyPrice || 0)}</p>
                  </div>
                  <div className="bg-muted/50 p-3 rounded-xl">
                    <p className="text-xs text-muted-foreground">Carousel</p>
                    <p className="font-bold text-primary">{formatPrice(profile?.rates?.carouselPrice || 0)}</p>
                  </div>
                  <div className="bg-muted/50 p-3 rounded-xl">
                    <p className="text-xs text-muted-foreground">Post</p>
                    <p className="font-bold text-primary">{formatPrice(profile?.rates?.postPrice || 0)}</p>
                  </div>
                </div>
              </div>

              {/* Actions */}
              <div className="space-y-2">
                {profile?.instagramUrl && (
                  <Button
                    variant="outline"
                    className="w-full rounded-full"
                    onClick={() => window.open(profile.instagramUrl, '_blank')}
                    data-testid="instagram-btn"
                  >
                    <Instagram className="w-4 h-4 mr-2" />
                    Go to Instagram
                  </Button>
                )}
                <Button
                  className="w-full btn-primary"
                  onClick={() => navigate('/onboarding/creator')}
                  data-testid="edit-profile-btn"
                >
                  <Edit className="w-4 h-4 mr-2" />
                  Edit Profile
                </Button>
              </div>
            </motion.div>
          </div>

          {/* Campaigns Section */}
          <div className="lg:col-span-2">
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.1 }}
            >
              <div className="flex items-center justify-between mb-6">
                <h2 className="font-heading text-2xl font-bold">Your Campaigns 🍊</h2>
                <Badge variant="secondary" className="text-lg px-4 py-1">
                  {proposedCampaigns.length} new
                </Badge>
              </div>

              {campaigns.length === 0 ? (
                <div className="card-orange p-12 text-center">
                  <span className="text-5xl block mb-4">🍊</span>
                  <h3 className="font-heading text-xl font-bold mb-2">No collabs yet…</h3>
                  <p className="text-muted-foreground">
                    But your Orange is fresh. The right brand is on its way 🍊✨
                  </p>
                </div>
              ) : (
                <Tabs defaultValue="proposed" className="w-full">
                  <TabsList className="mb-6 bg-muted/50 p-1 rounded-full">
                    <TabsTrigger value="proposed" className="rounded-full data-[state=active]:bg-white">
                      New ({proposedCampaigns.length})
                    </TabsTrigger>
                    <TabsTrigger value="active" className="rounded-full data-[state=active]:bg-white">
                      Active ({acceptedCampaigns.length})
                    </TabsTrigger>
                    <TabsTrigger value="completed" className="rounded-full data-[state=active]:bg-white">
                      Done ({completedCampaigns.length})
                    </TabsTrigger>
                    <TabsTrigger value="declined" className="rounded-full data-[state=active]:bg-white">
                      Declined ({declinedCampaigns.length})
                    </TabsTrigger>
                  </TabsList>

                  <TabsContent value="proposed" className="space-y-4">
                    {proposedCampaigns.length === 0 ? (
                      <p className="text-center text-muted-foreground py-8">No new proposals</p>
                    ) : (
                      proposedCampaigns.map(campaign => (
                        <CampaignCard 
                          key={campaign.id}
                          campaign={campaign}
                          onAccept={() => handleCampaignAction(campaign.id, 'accepted')}
                          onDecline={() => handleCampaignAction(campaign.id, 'declined')}
                          onChat={() => navigate(`/chat/${campaign.id}`)}
                          loading={actionLoading === campaign.id}
                          showActions
                        />
                      ))
                    )}
                  </TabsContent>

                  <TabsContent value="active" className="space-y-4">
                    {acceptedCampaigns.length === 0 ? (
                      <p className="text-center text-muted-foreground py-8">No active campaigns</p>
                    ) : (
                      acceptedCampaigns.map(campaign => (
                        <CampaignCard 
                          key={campaign.id}
                          campaign={campaign}
                          onChat={() => navigate(`/chat/${campaign.id}`)}
                          onDeliver={() => handleCampaignAction(campaign.id, 'delivered')}
                          loading={actionLoading === campaign.id}
                          showDeliverButton={campaign.escrowStatus === 'paid'}
                        />
                      ))
                    )}
                  </TabsContent>

                  <TabsContent value="completed" className="space-y-4">
                    {completedCampaigns.length === 0 ? (
                      <p className="text-center text-muted-foreground py-8">No completed campaigns</p>
                    ) : (
                      completedCampaigns.map(campaign => (
                        <CampaignCard 
                          key={campaign.id}
                          campaign={campaign}
                          onChat={() => navigate(`/chat/${campaign.id}`)}
                        />
                      ))
                    )}
                  </TabsContent>

                  <TabsContent value="declined" className="space-y-4">
                    {declinedCampaigns.length === 0 ? (
                      <p className="text-center text-muted-foreground py-8">No declined campaigns</p>
                    ) : (
                      declinedCampaigns.map(campaign => (
                        <CampaignCard 
                          key={campaign.id}
                          campaign={campaign}
                        />
                      ))
                    )}
                  </TabsContent>
                </Tabs>
              )}
            </motion.div>

            {/* Media Gallery Preview */}
            {profile?.mediaGallery?.length > 0 && (
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.2 }}
                className="mt-8"
              >
                <h3 className="font-heading text-xl font-bold mb-4 flex items-center gap-2">
                  <ImageIcon className="w-5 h-5" />
                  Your Gallery
                </h3>
                <div className="grid grid-cols-3 sm:grid-cols-4 md:grid-cols-5 gap-3">
                  {profile.mediaGallery.slice(0, 10).map((media, idx) => (
                    <div key={idx} className="aspect-square rounded-2xl overflow-hidden bg-muted">
                      {media.type === 'video' ? (
                        <video src={media.url} className="w-full h-full object-cover" />
                      ) : (
                        <img src={media.thumbnailUrl || media.url} alt="" className="w-full h-full object-cover" />
                      )}
                    </div>
                  ))}
                </div>
              </motion.div>
            )}
          </div>
        </div>
      </main>
    </div>
  );
};

const CampaignCard = ({ campaign, onAccept, onDecline, onChat, onDeliver, loading, showActions, showDeliverButton }) => {
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
    <div className="card-orange p-6" data-testid={`campaign-card-${campaign.id}`}>
      <div className="flex items-start gap-4">
        <Avatar className="w-12 h-12 border-2 border-orange-100">
          <AvatarFallback className="bg-primary/10 text-primary">
            {campaign.brandName?.[0]}
          </AvatarFallback>
        </Avatar>
        <div className="flex-1">
          <div className="flex items-center gap-2 mb-1 flex-wrap">
            <h4 className="font-semibold">{campaign.brandName || 'Brand'}</h4>
            <Badge className={statusColors[campaign.campaignStatus]}>
              {campaign.campaignStatus?.replace('_', ' ')}
            </Badge>
            <Badge className={escrowColors[campaign.escrowStatus]}>
              {campaign.escrowStatus === 'paid' ? '💰 Paid' : 
               campaign.escrowStatus === 'released' ? '✅ Released' : '⏳ Pending Payment'}
            </Badge>
          </div>
          <h3 className="font-heading text-lg font-bold mb-2">{campaign.title}</h3>
          <p className="text-muted-foreground text-sm mb-3">{campaign.brief}</p>
          
          <div className="flex flex-wrap gap-4 text-sm">
            {campaign.price > 0 && (
              <div className="flex items-center gap-1 text-primary font-semibold">
                <DollarSign className="w-4 h-4" />
                {formatPrice(campaign.price)}
              </div>
            )}
            {campaign.deliverables && (
              <div className="text-muted-foreground">
                📦 {campaign.deliverables}
              </div>
            )}
            {campaign.timeline && (
              <div className="text-muted-foreground">
                ⏰ {campaign.timeline}
              </div>
            )}
            {campaign.isBarter && (
              <Badge className="bg-accent/50 text-accent-foreground">🤝 Barter Deal</Badge>
            )}
          </div>
        </div>
      </div>

      <div className="flex items-center gap-3 mt-4 pt-4 border-t border-orange-100">
        {showActions && campaign.campaignStatus === 'proposed' && (
          <>
            <Button
              onClick={onAccept}
              disabled={loading}
              className="flex-1 bg-accent hover:bg-accent/90 text-accent-foreground rounded-full"
              data-testid={`accept-campaign-${campaign.id}`}
            >
              {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Check className="w-4 h-4 mr-2" />}
              Accept
            </Button>
            <Button
              onClick={onDecline}
              disabled={loading}
              variant="outline"
              className="flex-1 rounded-full"
              data-testid={`decline-campaign-${campaign.id}`}
            >
              <X className="w-4 h-4 mr-2" />
              Decline
            </Button>
          </>
        )}
        
        {showDeliverButton && campaign.campaignStatus !== 'delivered' && (
          <Button
            onClick={onDeliver}
            disabled={loading}
            className="bg-purple-500 hover:bg-purple-600 text-white rounded-full"
            data-testid={`deliver-campaign-${campaign.id}`}
          >
            {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : '📦 Mark Delivered'}
          </Button>
        )}
        
        {/* Chat available for all non-declined campaigns */}
        {!['declined', 'cancelled'].includes(campaign.campaignStatus) && onChat && (
          <Button
            onClick={onChat}
            className={campaign.escrowStatus === 'paid' ? "btn-primary flex-1" : "btn-secondary flex-1"}
            data-testid={`chat-campaign-${campaign.id}`}
          >
            <MessageSquare className="w-4 h-4 mr-2" />
            {campaign.escrowStatus === 'paid' ? 'Chat (Full Access)' : 'Chat'}
          </Button>
        )}
      </div>
      
      {/* Warning for unpaid escrow */}
      {campaign.campaignStatus === 'accepted' && campaign.escrowStatus === 'pending' && (
        <div className="mt-4 p-3 bg-orange-50 rounded-xl border border-orange-200">
          <p className="text-sm text-orange-800 flex items-center gap-2">
            <Lock className="w-4 h-4" />
            Waiting for brand to pay escrow. Instagram access will unlock after payment.
          </p>
        </div>
      )}
    </div>
  );
};

export default CreatorDashboard;
