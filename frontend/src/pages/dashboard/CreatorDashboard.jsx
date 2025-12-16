import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import { 
  Instagram, MapPin, Users, Edit, LogOut, MessageSquare, Check, X, 
  ExternalLink, DollarSign, Image as ImageIcon, Loader2
} from 'lucide-react';
import { Button } from '../../components/ui/button';
import { Badge } from '../../components/ui/badge';
import { Avatar, AvatarFallback, AvatarImage } from '../../components/ui/avatar';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../../components/ui/tabs';
import { creatorAPI, requestsAPI } from '../../lib/api';
import { useAuth } from '../../lib/auth';
import { toast } from 'sonner';

const CreatorDashboard = () => {
  const navigate = useNavigate();
  const { user, logout } = useAuth();
  const [profile, setProfile] = useState(null);
  const [requests, setRequests] = useState([]);
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState(null);

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      const [profileRes, requestsRes] = await Promise.all([
        creatorAPI.getProfile(),
        creatorAPI.getRequests()
      ]);
      setProfile(profileRes.data);
      setRequests(requestsRes.data);
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

  const handleRequestAction = async (requestId, newStatus) => {
    setActionLoading(requestId);
    try {
      await requestsAPI.updateStatus(requestId, newStatus);
      // Force UI update with new status
      setRequests(prev => prev.map(r => 
        r.id === requestId ? { ...r, status: newStatus } : r
      ));
      toast.success(newStatus === 'accepted' ? "Request accepted! Time to make magic ✨" : "Request declined");
    } catch (error) {
      toast.error("Failed to update request");
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

  const pendingRequests = requests.filter(r => r.status === 'pending');
  const acceptedRequests = requests.filter(r => r.status === 'accepted');
  const declinedRequests = requests.filter(r => r.status === 'declined');

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

                {/* Barter Badge */}
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
                    <p className="text-xs text-muted-foreground">Post</p>
                    <p className="font-bold text-primary">{formatPrice(profile?.rates?.postPrice || 0)}</p>
                  </div>
                  <div className="bg-muted/50 p-3 rounded-xl">
                    <p className="text-xs text-muted-foreground">Bundle</p>
                    <p className="font-bold text-primary">{formatPrice(profile?.rates?.bundlePrice || 0)}</p>
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

          {/* Requests Section */}
          <div className="lg:col-span-2">
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.1 }}
            >
              <div className="flex items-center justify-between mb-6">
                <h2 className="font-heading text-2xl font-bold">Collab Requests 🍊</h2>
                <Badge variant="secondary" className="text-lg px-4 py-1">
                  {pendingRequests.length} new
                </Badge>
              </div>

              {requests.length === 0 ? (
                <div className="card-orange p-12 text-center">
                  <span className="text-5xl block mb-4">🍊</span>
                  <h3 className="font-heading text-xl font-bold mb-2">No collabs yet…</h3>
                  <p className="text-muted-foreground">
                    But your Orange is fresh. The right brand is on its way 🍊✨
                  </p>
                </div>
              ) : (
                <Tabs defaultValue="pending" className="w-full">
                  <TabsList className="mb-6 bg-muted/50 p-1 rounded-full">
                    <TabsTrigger value="pending" className="rounded-full data-[state=active]:bg-white">
                      Pending ({pendingRequests.length})
                    </TabsTrigger>
                    <TabsTrigger value="accepted" className="rounded-full data-[state=active]:bg-white">
                      Accepted ({acceptedRequests.length})
                    </TabsTrigger>
                    <TabsTrigger value="declined" className="rounded-full data-[state=active]:bg-white">
                      Declined ({declinedRequests.length})
                    </TabsTrigger>
                  </TabsList>

                  <TabsContent value="pending" className="space-y-4">
                    {pendingRequests.length === 0 ? (
                      <p className="text-center text-muted-foreground py-8">No pending requests</p>
                    ) : (
                      pendingRequests.map(request => (
                        <RequestCard 
                          key={request.id}
                          request={request}
                          onAccept={() => handleRequestAction(request.id, 'accepted')}
                          onDecline={() => handleRequestAction(request.id, 'declined')}
                          onChat={() => navigate(`/chat/${request.id}`)}
                          loading={actionLoading === request.id}
                          showActions
                        />
                      ))
                    )}
                  </TabsContent>

                  <TabsContent value="accepted" className="space-y-4">
                    {acceptedRequests.length === 0 ? (
                      <p className="text-center text-muted-foreground py-8">No accepted requests yet</p>
                    ) : (
                      acceptedRequests.map(request => (
                        <RequestCard 
                          key={request.id}
                          request={request}
                          onChat={() => navigate(`/chat/${request.id}`)}
                        />
                      ))
                    )}
                  </TabsContent>

                  <TabsContent value="declined" className="space-y-4">
                    {declinedRequests.length === 0 ? (
                      <p className="text-center text-muted-foreground py-8">No declined requests</p>
                    ) : (
                      declinedRequests.map(request => (
                        <RequestCard 
                          key={request.id}
                          request={request}
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

const RequestCard = ({ request, onAccept, onDecline, onChat, loading, showActions }) => {
  const formatPrice = (price) => {
    return new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR', maximumFractionDigits: 0 }).format(price);
  };

  const statusColors = {
    pending: 'bg-yellow-100 text-yellow-800',
    accepted: 'bg-green-100 text-green-800',
    declined: 'bg-red-100 text-red-800'
  };

  return (
    <div className="card-orange p-6" data-testid={`request-card-${request.id}`}>
      <div className="flex items-start gap-4">
        <Avatar className="w-12 h-12 border-2 border-orange-100">
          <AvatarImage src={request.businessPhoto} />
          <AvatarFallback className="bg-primary/10 text-primary">
            {request.businessName?.[0]}
          </AvatarFallback>
        </Avatar>
        <div className="flex-1">
          <div className="flex items-center gap-2 mb-1">
            <h4 className="font-semibold">{request.businessName || 'Brand'}</h4>
            <Badge className={statusColors[request.status]}>
              {request.status}
            </Badge>
          </div>
          <h3 className="font-heading text-lg font-bold mb-2">{request.title}</h3>
          <p className="text-muted-foreground text-sm mb-3">{request.brief}</p>
          
          <div className="flex flex-wrap gap-4 text-sm">
            {request.offerAmount > 0 && (
              <div className="flex items-center gap-1 text-primary font-semibold">
                <DollarSign className="w-4 h-4" />
                {formatPrice(request.offerAmount)}
              </div>
            )}
            {request.deliverables && (
              <div className="text-muted-foreground">
                📦 {request.deliverables}
              </div>
            )}
            {request.timeline && (
              <div className="text-muted-foreground">
                ⏰ {request.timeline}
              </div>
            )}
          </div>
        </div>
      </div>

      <div className="flex items-center gap-3 mt-4 pt-4 border-t border-orange-100">
        {showActions && request.status === 'pending' && (
          <>
            <Button
              onClick={onAccept}
              disabled={loading}
              className="flex-1 bg-accent hover:bg-accent/90 text-accent-foreground rounded-full"
              data-testid={`accept-request-${request.id}`}
            >
              {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Check className="w-4 h-4 mr-2" />}
              Accept
            </Button>
            <Button
              onClick={onDecline}
              disabled={loading}
              variant="outline"
              className="flex-1 rounded-full"
              data-testid={`decline-request-${request.id}`}
            >
              <X className="w-4 h-4 mr-2" />
              Decline
            </Button>
          </>
        )}
        {/* Chat available for both pending and accepted requests */}
        {(request.status === 'pending' || request.status === 'accepted') && onChat && (
          <Button
            onClick={onChat}
            className={request.status === 'accepted' ? "btn-primary flex-1" : "btn-secondary flex-1"}
            data-testid={`chat-request-${request.id}`}
          >
            <MessageSquare className="w-4 h-4 mr-2" />
            {request.status === 'pending' ? 'Message Brand' : 'Open Chat'}
          </Button>
        )}
      </div>
    </div>
  );
};

export default CreatorDashboard;
