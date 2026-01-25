import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import { 
  MapPin, Edit, LogOut, MessageSquare, Check, X, ExternalLink, 
  Loader2, Clock, CheckCircle, AlertCircle, Link as LinkIcon, Star, Eye, EyeOff, Send
} from 'lucide-react';
import { Button } from '../../components/ui/button';
import { Badge } from '../../components/ui/badge';
import { Avatar, AvatarFallback, AvatarImage } from '../../components/ui/avatar';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../../components/ui/tabs';
import { Input } from '../../components/ui/input';
import { Label } from '../../components/ui/label';
import { Textarea } from '../../components/ui/textarea';
import { Switch } from '../../components/ui/switch';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../../components/ui/select';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '../../components/ui/dialog';
import { creatorAPI, campaignAPI, marketplaceAPI, getErrorMessage } from '../../lib/api';
import { useAuth } from '../../lib/auth';
import { toast } from 'sonner';

// Campaign status display config
const STATUS_CONFIG = {
  requested: { label: 'New Request', color: 'bg-yellow-100 text-yellow-800', icon: Clock },
  accepted: { label: 'Accepted - Waiting Payment', color: 'bg-blue-100 text-blue-800', icon: Clock },
  paid: { label: 'Paid - Submit Link', color: 'bg-purple-100 text-purple-800', icon: LinkIcon },
  in_progress: { label: 'In Progress', color: 'bg-purple-100 text-purple-800', icon: Clock },
  link_submitted: { label: 'Link Under Review', color: 'bg-orange-100 text-orange-800', icon: Clock },
  link_verified: { label: 'Verified - Awaiting Completion', color: 'bg-green-100 text-green-800', icon: CheckCircle },
  completed: { label: 'Completed', color: 'bg-green-500 text-white', icon: CheckCircle },
  disputed: { label: 'Disputed', color: 'bg-red-100 text-red-800', icon: AlertCircle },
  cancelled: { label: 'Cancelled', color: 'bg-gray-100 text-gray-800', icon: X },
};

const CreatorDashboard = () => {
  const navigate = useNavigate();
  const { logout } = useAuth();
  const [profile, setProfile] = useState(null);
  const [incomingCampaigns, setIncomingCampaigns] = useState([]);
  const [outgoingCampaigns, setOutgoingCampaigns] = useState([]);
  const [brands, setBrands] = useState([]);
  const [loading, setLoading] = useState(true);
  const [loadingBrands, setLoadingBrands] = useState(false);
  const [actionLoading, setActionLoading] = useState(false);
  const [activeTab, setActiveTab] = useState('requests');
  
  // Modals
  const [showCampaignModal, setShowCampaignModal] = useState(false);
  const [selectedCampaign, setSelectedCampaign] = useState(null);
  const [showRequestModal, setShowRequestModal] = useState(false);
  const [selectedBrand, setSelectedBrand] = useState(null);
  const [contentLink, setContentLink] = useState('');
  const [ratingForm, setRatingForm] = useState({ rating: 5, feedback: '' });
  
  // Request form for sending to brands
  const [requestForm, setRequestForm] = useState({
    campaignType: 'paid',
    deliverables: '',
    budget: 0,
    productValue: 0,
    timeline: '',
    brief: '',
    barterDetails: ''
  });

  useEffect(() => {
    loadData();
  }, []);

  useEffect(() => {
    if (activeTab === 'brands') {
      loadBrands();
    }
  }, [activeTab]);

  const loadData = async () => {
    try {
      const [profileRes, incomingRes, outgoingRes] = await Promise.all([
        creatorAPI.getProfile(),
        campaignAPI.getIncoming(),
        campaignAPI.getOutgoing()
      ]);
      setProfile(profileRes.data);
      setIncomingCampaigns(incomingRes.data);
      setOutgoingCampaigns(outgoingRes.data);
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

  const loadBrands = async () => {
    setLoadingBrands(true);
    try {
      const response = await marketplaceAPI.discoverBrands();
      setBrands(response.data);
    } catch (error) {
      toast.error("Failed to load brands");
    } finally {
      setLoadingBrands(false);
    }
  };

  const handleBrandClick = (brand) => {
    setSelectedBrand(brand);
    setRequestForm({
      campaignType: 'paid',
      deliverables: '',
      budget: profile?.reelPrice || 10000,
      productValue: 0,
      timeline: '7 days',
      brief: '',
      barterDetails: ''
    });
    setShowRequestModal(true);
  };

  const handleSendRequest = async () => {
    if (!selectedBrand || !requestForm.deliverables) {
      toast.error("Please fill in deliverables");
      return;
    }
    
    setActionLoading(true);
    try {
      await campaignAPI.create({
        receiverId: selectedBrand.id,
        receiverType: 'brand',
        campaignType: requestForm.campaignType,
        deliverables: requestForm.deliverables,
        budget: requestForm.campaignType === 'paid' ? requestForm.budget : 0,
        productValue: requestForm.campaignType !== 'paid' ? requestForm.productValue : 0,
        timeline: requestForm.timeline,
        brief: requestForm.brief,
        barterDetails: requestForm.barterDetails
      });
      
      toast.success("Collaboration request sent! 🍊");
      setShowRequestModal(false);
      
      // Refresh outgoing campaigns
      const res = await campaignAPI.getOutgoing();
      setOutgoingCampaigns(res.data);
    } catch (error) {
      toast.error(getErrorMessage(error, "Failed to send request"));
    } finally {
      setActionLoading(false);
    }
  };

  const handleAcceptRequest = async (campaign) => {
    setActionLoading(true);
    try {
      await campaignAPI.respond(campaign.id, 'accept');
      toast.success("Request accepted! 🎉 Waiting for brand to pay.");
      
      const res = await campaignAPI.getIncoming();
      setIncomingCampaigns(res.data);
      setShowCampaignModal(false);
    } catch (error) {
      toast.error(getErrorMessage(error, "Failed to accept"));
    } finally {
      setActionLoading(false);
    }
  };

  const handleRejectRequest = async (campaign) => {
    setActionLoading(true);
    try {
      await campaignAPI.respond(campaign.id, 'reject');
      toast.success("Request declined.");
      
      const res = await campaignAPI.getIncoming();
      setIncomingCampaigns(res.data);
      setShowCampaignModal(false);
    } catch (error) {
      toast.error(getErrorMessage(error, "Failed to reject"));
    } finally {
      setActionLoading(false);
    }
  };

  const handleSubmitLink = async (campaign) => {
    if (!contentLink) {
      toast.error("Please enter the reel/story link");
      return;
    }
    
    setActionLoading(true);
    try {
      await campaignAPI.submitLink(campaign.id, contentLink);
      toast.success("Link submitted! Waiting for brand to verify.");
      
      const [inRes, outRes] = await Promise.all([
        campaignAPI.getIncoming(),
        campaignAPI.getOutgoing()
      ]);
      setIncomingCampaigns(inRes.data);
      setOutgoingCampaigns(outRes.data);
      setContentLink('');
      setShowCampaignModal(false);
    } catch (error) {
      toast.error(getErrorMessage(error, "Failed to submit link"));
    } finally {
      setActionLoading(false);
    }
  };

  const handleSubmitRating = async (campaign) => {
    if (!ratingForm.feedback || ratingForm.feedback.length < 10) {
      toast.error("Please provide feedback (min 10 characters)");
      return;
    }
    
    setActionLoading(true);
    try {
      await campaignAPI.rate(campaign.id, ratingForm.rating, ratingForm.feedback);
      toast.success("Rating submitted!");
      
      const [inRes, outRes] = await Promise.all([
        campaignAPI.getIncoming(),
        campaignAPI.getOutgoing()
      ]);
      setIncomingCampaigns(inRes.data);
      setOutgoingCampaigns(outRes.data);
      setShowCampaignModal(false);
    } catch (error) {
      toast.error(getErrorMessage(error, "Failed to submit rating"));
    } finally {
      setActionLoading(false);
    }
  };

  const handleToggleVisibility = async () => {
    setActionLoading(true);
    try {
      const newVisibility = !profile.isVisible;
      await creatorAPI.toggleVisibility(newVisibility);
      setProfile(prev => ({ ...prev, isVisible: newVisibility }));
      toast.success(newVisibility ? "Profile is now visible to brands!" : "Profile hidden from marketplace.");
    } catch (error) {
      toast.error(getErrorMessage(error, "Failed to update visibility"));
    } finally {
      setActionLoading(false);
    }
  };

  const formatPrice = (price) => {
    return new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR', maximumFractionDigits: 0 }).format(price);
  };

  // Separate campaigns by status
  const pendingRequests = incomingCampaigns.filter(c => c.status === 'requested');
  const activeIncoming = incomingCampaigns.filter(c => ['accepted', 'paid', 'in_progress', 'link_submitted', 'link_verified'].includes(c.status));
  const activeOutgoing = outgoingCampaigns.filter(c => ['requested', 'accepted', 'paid', 'in_progress', 'link_submitted', 'link_verified'].includes(c.status));
  const completedCampaigns = [...incomingCampaigns, ...outgoingCampaigns].filter(c => c.status === 'completed');

  if (loading) {
    return (
      <div className="min-h-screen gradient-hero flex items-center justify-center">
        <div className="text-center">
          <Loader2 className="w-10 h-10 mx-auto text-primary animate-spin mb-4" />
          <p className="text-muted-foreground">Loading... 🍊</p>
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
          
          <div className="flex items-center gap-4">
            {/* Visibility Toggle */}
            <div className="flex items-center gap-2 bg-accent/20 px-4 py-2 rounded-full">
              {profile?.isVisible ? (
                <Eye className="w-4 h-4 text-green-600" />
              ) : (
                <EyeOff className="w-4 h-4 text-red-600" />
              )}
              <span className="font-semibold text-sm">
                {profile?.isVisible ? 'Visible' : 'Hidden'}
              </span>
              <Switch
                checked={profile?.isVisible}
                onCheckedChange={handleToggleVisibility}
                disabled={actionLoading}
              />
            </div>
            
            <Button
              variant="outline"
              className="rounded-full"
              onClick={() => navigate(`/profile/creator/${profile?.id}`)}
              data-testid="view-public-profile-btn"
            >
              <ExternalLink className="w-4 h-4 mr-2" />
              View Profile
            </Button>
            <Button
              variant="ghost"
              className="rounded-full text-muted-foreground"
              onClick={() => { logout(); navigate('/'); }}
              data-testid="logout-btn"
            >
              <LogOut className="w-4 h-4 mr-2" />
              Logout
            </Button>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-6 py-8">
        {/* Profile Card */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="card-orange p-6 mb-8"
        >
          <div className="flex items-center gap-6">
            <Avatar className="w-20 h-20 border-4 border-primary">
              <AvatarImage src={profile?.profilePhotoUrl} />
              <AvatarFallback className="bg-primary text-white text-2xl">
                {profile?.name?.[0]}
              </AvatarFallback>
            </Avatar>
            <div className="flex-1">
              <div className="flex items-center gap-3 mb-2">
                <h2 className="font-heading text-2xl font-bold">{profile?.name}</h2>
                {profile?.instagramVerified && (
                  <Badge className="bg-green-100 text-green-800">✓ Verified</Badge>
                )}
                {profile?.rating && (
                  <Badge variant="secondary">⭐ {profile.rating.toFixed(1)}</Badge>
                )}
              </div>
              <p className="text-muted-foreground mb-3">{profile?.bio}</p>
              <div className="flex flex-wrap gap-2">
                <Badge>{profile?.niche}</Badge>
                {profile?.location && (
                  <Badge variant="outline">
                    <MapPin className="w-3 h-3 mr-1" />
                    {profile.location}
                  </Badge>
                )}
                <Badge variant="outline">{profile?.totalCollabs || 0} Collabs</Badge>
              </div>
            </div>
            <div className="text-right">
              <div className="mb-2">
                <p className="text-sm text-muted-foreground">Your Rates</p>
                <p className="font-bold">Reel: {formatPrice(profile?.reelPrice || 0)}</p>
                <p className="font-bold">Story: {formatPrice(profile?.storyPrice || 0)}</p>
              </div>
              <Button
                onClick={() => navigate('/onboarding/creator')}
                variant="outline"
                className="rounded-full"
                data-testid="edit-profile-btn"
              >
                <Edit className="w-4 h-4 mr-2" />
                Edit Profile
              </Button>
            </div>
          </div>
        </motion.div>

        {/* Tabs */}
        <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full">
          <TabsList className="mb-6 bg-muted/50 p-1 rounded-full flex-wrap">
            <TabsTrigger value="requests" className="rounded-full data-[state=active]:bg-white px-4">
              📥 Incoming ({pendingRequests.length})
            </TabsTrigger>
            <TabsTrigger value="active" className="rounded-full data-[state=active]:bg-white px-4">
              🔄 Active ({activeIncoming.length + activeOutgoing.length})
            </TabsTrigger>
            <TabsTrigger value="sent" className="rounded-full data-[state=active]:bg-white px-4">
              📤 Sent ({outgoingCampaigns.length})
            </TabsTrigger>
            <TabsTrigger value="completed" className="rounded-full data-[state=active]:bg-white px-4">
              ✅ Completed ({completedCampaigns.length})
            </TabsTrigger>
            <TabsTrigger value="brands" className="rounded-full data-[state=active]:bg-white px-4">
              🏢 Find Brands
            </TabsTrigger>
          </TabsList>

          {/* Incoming Requests Tab */}
          <TabsContent value="requests">
            <div className="mb-6">
              <h2 className="font-heading text-2xl font-bold">Collaboration Requests</h2>
              <p className="text-muted-foreground">New requests from brands</p>
            </div>

            {pendingRequests.length === 0 ? (
              <div className="card-orange p-12 text-center">
                <span className="text-5xl block mb-4">📥</span>
                <h3 className="font-heading text-xl font-bold mb-2">No new requests</h3>
                <p className="text-muted-foreground">New collaboration requests will appear here</p>
              </div>
            ) : (
              <div className="space-y-4">
                {pendingRequests.map(campaign => (
                  <CampaignCard 
                    key={campaign.id} 
                    campaign={campaign}
                    isIncoming={true}
                    onClick={() => { setSelectedCampaign(campaign); setShowCampaignModal(true); }}
                  />
                ))}
              </div>
            )}
          </TabsContent>

          {/* Active Campaigns Tab */}
          <TabsContent value="active">
            <div className="mb-6">
              <h2 className="font-heading text-2xl font-bold">Active Campaigns</h2>
              <p className="text-muted-foreground">Ongoing collaborations</p>
            </div>

            {(activeIncoming.length + activeOutgoing.length) === 0 ? (
              <div className="card-orange p-12 text-center">
                <span className="text-5xl block mb-4">🔄</span>
                <h3 className="font-heading text-xl font-bold mb-2">No active campaigns</h3>
                <p className="text-muted-foreground">Accept requests or reach out to brands!</p>
              </div>
            ) : (
              <div className="space-y-4">
                {activeIncoming.map(campaign => (
                  <CampaignCard 
                    key={campaign.id} 
                    campaign={campaign}
                    isIncoming={true}
                    onClick={() => { setSelectedCampaign(campaign); setShowCampaignModal(true); }}
                  />
                ))}
                {activeOutgoing.map(campaign => (
                  <CampaignCard 
                    key={campaign.id} 
                    campaign={campaign}
                    isIncoming={false}
                    onClick={() => { setSelectedCampaign(campaign); setShowCampaignModal(true); }}
                  />
                ))}
              </div>
            )}
          </TabsContent>

          {/* Sent Requests Tab */}
          <TabsContent value="sent">
            <div className="mb-6">
              <h2 className="font-heading text-2xl font-bold">Sent Requests</h2>
              <p className="text-muted-foreground">Requests you've sent to brands</p>
            </div>

            {outgoingCampaigns.length === 0 ? (
              <div className="card-orange p-12 text-center">
                <span className="text-5xl block mb-4">📤</span>
                <h3 className="font-heading text-xl font-bold mb-2">No sent requests</h3>
                <p className="text-muted-foreground">Go to "Find Brands" to send collaboration requests!</p>
              </div>
            ) : (
              <div className="space-y-4">
                {outgoingCampaigns.map(campaign => (
                  <CampaignCard 
                    key={campaign.id} 
                    campaign={campaign}
                    isIncoming={false}
                    onClick={() => { setSelectedCampaign(campaign); setShowCampaignModal(true); }}
                  />
                ))}
              </div>
            )}
          </TabsContent>

          {/* Completed Campaigns Tab */}
          <TabsContent value="completed">
            <div className="mb-6">
              <h2 className="font-heading text-2xl font-bold">Completed</h2>
              <p className="text-muted-foreground">Past collaborations</p>
            </div>

            {completedCampaigns.length === 0 ? (
              <div className="card-orange p-12 text-center">
                <span className="text-5xl block mb-4">✅</span>
                <h3 className="font-heading text-xl font-bold mb-2">No completed campaigns yet</h3>
                <p className="text-muted-foreground">Completed collaborations will appear here</p>
              </div>
            ) : (
              <div className="space-y-4">
                {completedCampaigns.map(campaign => (
                  <CampaignCard 
                    key={campaign.id} 
                    campaign={campaign}
                    isIncoming={incomingCampaigns.some(c => c.id === campaign.id)}
                    onClick={() => { setSelectedCampaign(campaign); setShowCampaignModal(true); }}
                  />
                ))}
              </div>
            )}
          </TabsContent>

          {/* Browse Brands Tab */}
          <TabsContent value="brands">
            <div className="mb-6">
              <h2 className="font-heading text-2xl font-bold">Find Brands 🏢</h2>
              <p className="text-muted-foreground">Click on a brand to send a collaboration request</p>
            </div>

            {loadingBrands ? (
              <div className="text-center py-12">
                <Loader2 className="w-10 h-10 mx-auto text-primary animate-spin mb-4" />
                <p className="text-muted-foreground">Loading brands...</p>
              </div>
            ) : brands.length === 0 ? (
              <div className="card-orange p-12 text-center">
                <span className="text-5xl block mb-4">🏢</span>
                <h3 className="font-heading text-xl font-bold mb-2">No brands found</h3>
                <p className="text-muted-foreground">Check back later for new brands</p>
              </div>
            ) : (
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
                {brands.map((brand, idx) => (
                  <BrandCard 
                    key={brand.id} 
                    brand={brand} 
                    index={idx}
                    onClick={() => handleBrandClick(brand)}
                  />
                ))}
              </div>
            )}
          </TabsContent>
        </Tabs>
      </main>

      {/* Campaign Details Modal */}
      <Dialog open={showCampaignModal} onOpenChange={setShowCampaignModal}>
        <DialogContent className="sm:max-w-[500px]">
          <DialogHeader>
            <DialogTitle className="font-heading text-xl">Campaign Details</DialogTitle>
          </DialogHeader>
          
          {selectedCampaign && (
            <div className="space-y-4 pt-4">
              <div className="bg-muted/50 rounded-xl p-4">
                <div className="flex items-center justify-between mb-3">
                  <div>
                    <p className="font-semibold">
                      {incomingCampaigns.some(c => c.id === selectedCampaign.id) 
                        ? selectedCampaign.senderName 
                        : selectedCampaign.receiverName}
                    </p>
                    <p className="text-sm text-muted-foreground capitalize">{selectedCampaign.campaignType.replace('_', ' ')}</p>
                  </div>
                  <Badge className={STATUS_CONFIG[selectedCampaign.status]?.color}>
                    {STATUS_CONFIG[selectedCampaign.status]?.label}
                  </Badge>
                </div>
                <p className="text-sm"><strong>Deliverables:</strong> {selectedCampaign.deliverables}</p>
                {selectedCampaign.campaignType === 'paid' && (
                  <>
                    <p className="text-sm"><strong>Budget:</strong> {formatPrice(selectedCampaign.budget)}</p>
                    <p className="text-sm text-green-600"><strong>Your Payout:</strong> {formatPrice(selectedCampaign.creatorPayout)}</p>
                  </>
                )}
                {selectedCampaign.campaignType !== 'paid' && (
                  <>
                    <p className="text-sm"><strong>Product Value:</strong> {formatPrice(selectedCampaign.productValue)}</p>
                    {selectedCampaign.barterDetails && (
                      <p className="text-sm"><strong>Product/Service:</strong> {selectedCampaign.barterDetails}</p>
                    )}
                  </>
                )}
                {selectedCampaign.timeline && (
                  <p className="text-sm"><strong>Timeline:</strong> {selectedCampaign.timeline}</p>
                )}
                {selectedCampaign.brief && (
                  <p className="text-sm"><strong>Brief:</strong> {selectedCampaign.brief}</p>
                )}
              </div>

              {/* Identity Info */}
              {selectedCampaign.identityUnlocked && (
                <div className="bg-green-50 rounded-xl p-4">
                  <p className="font-semibold text-green-800 mb-2">🔓 Identity Unlocked</p>
                  <p className="text-sm">
                    Instagram: <strong>
                      {incomingCampaigns.some(c => c.id === selectedCampaign.id) 
                        ? selectedCampaign.senderInstagram 
                        : selectedCampaign.receiverInstagram || 'N/A'}
                    </strong>
                  </p>
                </div>
              )}

              {/* Action Buttons based on status */}
              <div className="space-y-3">
                {selectedCampaign.status === 'requested' && incomingCampaigns.some(c => c.id === selectedCampaign.id) && (
                  <div className="flex gap-3">
                    <Button onClick={() => handleAcceptRequest(selectedCampaign)} className="flex-1 btn-primary" disabled={actionLoading}>
                      {actionLoading ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : <Check className="w-4 h-4 mr-2" />}
                      Accept
                    </Button>
                    <Button onClick={() => handleRejectRequest(selectedCampaign)} variant="outline" className="flex-1 rounded-full" disabled={actionLoading}>
                      <X className="w-4 h-4 mr-2" />
                      Decline
                    </Button>
                  </div>
                )}

                {selectedCampaign.status === 'requested' && outgoingCampaigns.some(c => c.id === selectedCampaign.id) && (
                  <div className="bg-yellow-50 rounded-xl p-4 text-center">
                    <Clock className="w-8 h-8 mx-auto text-yellow-500 mb-2" />
                    <p className="text-yellow-800">Waiting for brand to respond...</p>
                  </div>
                )}

                {selectedCampaign.status === 'accepted' && (
                  <div className="bg-blue-50 rounded-xl p-4 text-center">
                    <Clock className="w-8 h-8 mx-auto text-blue-500 mb-2" />
                    <p className="text-blue-800">
                      {incomingCampaigns.some(c => c.id === selectedCampaign.id) 
                        ? "Waiting for brand to complete payment..."
                        : "Waiting for brand to accept and pay..."}
                    </p>
                  </div>
                )}

                {(selectedCampaign.status === 'paid' || selectedCampaign.status === 'in_progress') && (
                  <div className="space-y-3">
                    <Label>Submit Reel/Story Link</Label>
                    <Input
                      placeholder="https://instagram.com/reel/..."
                      value={contentLink}
                      onChange={(e) => setContentLink(e.target.value)}
                      className="input-orange"
                    />
                    <Button onClick={() => handleSubmitLink(selectedCampaign)} className="w-full btn-primary" disabled={actionLoading}>
                      {actionLoading ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : <LinkIcon className="w-4 h-4 mr-2" />}
                      Submit Link
                    </Button>
                  </div>
                )}

                {selectedCampaign.status === 'link_submitted' && (
                  <div className="bg-orange-50 rounded-xl p-4 text-center">
                    <Clock className="w-8 h-8 mx-auto text-orange-500 mb-2" />
                    <p className="text-orange-800">Waiting for brand to verify your link...</p>
                    <p className="text-sm text-muted-foreground mt-1">{selectedCampaign.contentLink}</p>
                  </div>
                )}

                {selectedCampaign.status === 'link_verified' && (
                  <div className="bg-green-50 rounded-xl p-4 text-center">
                    <CheckCircle className="w-8 h-8 mx-auto text-green-500 mb-2" />
                    <p className="text-green-800">Link verified! Waiting for brand to mark complete...</p>
                  </div>
                )}

                {selectedCampaign.status === 'completed' && (
                  <div className="space-y-3">
                    <div className="bg-green-50 rounded-xl p-4 text-center">
                      <CheckCircle className="w-8 h-8 mx-auto text-green-500 mb-2" />
                      <p className="text-green-800 font-semibold">Campaign Completed! 🎉</p>
                      {selectedCampaign.campaignType === 'paid' && (
                        <p className="text-sm">Payout: {formatPrice(selectedCampaign.creatorPayout)}</p>
                      )}
                    </div>
                    
                    <Label>Rate this brand</Label>
                    <div className="flex gap-1">
                      {[1, 2, 3, 4, 5].map(star => (
                        <button
                          key={star}
                          onClick={() => setRatingForm(prev => ({ ...prev, rating: star }))}
                          className={`p-1 ${ratingForm.rating >= star ? 'text-yellow-500' : 'text-gray-300'}`}
                        >
                          <Star className="w-6 h-6 fill-current" />
                        </button>
                      ))}
                    </div>
                    <Textarea
                      placeholder="Share your feedback (min 10 characters)"
                      value={ratingForm.feedback}
                      onChange={(e) => setRatingForm(prev => ({ ...prev, feedback: e.target.value }))}
                      className="input-orange"
                    />
                    <Button onClick={() => handleSubmitRating(selectedCampaign)} className="w-full btn-primary" disabled={actionLoading}>
                      {actionLoading ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : <Star className="w-4 h-4 mr-2" />}
                      Submit Rating
                    </Button>
                  </div>
                )}

                {selectedCampaign.chatEnabled && (
                  <Button variant="outline" onClick={() => navigate(`/chat/${selectedCampaign.id}`)} className="w-full rounded-full">
                    <MessageSquare className="w-4 h-4 mr-2" />
                    Open Chat
                  </Button>
                )}
              </div>
            </div>
          )}
        </DialogContent>
      </Dialog>

      {/* Send Request to Brand Modal */}
      <Dialog open={showRequestModal} onOpenChange={setShowRequestModal}>
        <DialogContent className="sm:max-w-[500px]">
          <DialogHeader>
            <DialogTitle className="font-heading text-xl flex items-center gap-2">
              <Send className="w-5 h-5 text-primary" />
              Send Collaboration Request
            </DialogTitle>
          </DialogHeader>
          
          {selectedBrand && (
            <div className="space-y-4 pt-4">
              <div className="bg-muted/50 rounded-xl p-4">
                <div className="flex items-center gap-3">
                  <div className="w-12 h-12 rounded-full bg-primary/20 flex items-center justify-center text-xl">
                    🏢
                  </div>
                  <div>
                    <p className="font-semibold">{selectedBrand.industry} Brand</p>
                    <p className="text-sm text-muted-foreground">{selectedBrand.location}</p>
                  </div>
                </div>
                <div className="mt-3 flex gap-2 text-sm">
                  <Badge variant="secondary">{selectedBrand.budgetRange}</Badge>
                  {selectedBrand.barterEnabled && <Badge>🤝 Barter</Badge>}
                </div>
              </div>

              <div className="space-y-2">
                <Label>Collaboration Type</Label>
                <Select value={requestForm.campaignType} onValueChange={(value) => setRequestForm(prev => ({ ...prev, campaignType: value }))}>
                  <SelectTrigger className="rounded-xl">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="paid">💰 Paid Collaboration</SelectItem>
                    <SelectItem value="barter_product">📦 Barter - Product</SelectItem>
                    <SelectItem value="barter_service">🎁 Barter - Service</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              <div className="space-y-2">
                <Label>What you'll deliver *</Label>
                <Textarea
                  placeholder="e.g., I will create 2 reels and 3 stories featuring your product"
                  value={requestForm.deliverables}
                  onChange={(e) => setRequestForm(prev => ({ ...prev, deliverables: e.target.value }))}
                  className="input-orange"
                />
              </div>

              {requestForm.campaignType === 'paid' && (
                <div className="space-y-2">
                  <Label>Your Rate (₹)</Label>
                  <Input
                    type="number"
                    value={requestForm.budget}
                    onChange={(e) => setRequestForm(prev => ({ ...prev, budget: Number(e.target.value) }))}
                    className="input-orange"
                  />
                  <p className="text-xs text-muted-foreground">
                    You'll receive 90% after completion. 10% platform fee.
                  </p>
                </div>
              )}

              {requestForm.campaignType !== 'paid' && (
                <>
                  <div className="space-y-2">
                    <Label>Expected Product/Service Value (₹)</Label>
                    <Input
                      type="number"
                      value={requestForm.productValue}
                      onChange={(e) => setRequestForm(prev => ({ ...prev, productValue: Number(e.target.value) }))}
                      className="input-orange"
                    />
                  </div>
                  <div className="space-y-2">
                    <Label>What product/service do you want?</Label>
                    <Textarea
                      placeholder="Describe what you'd like in exchange"
                      value={requestForm.barterDetails}
                      onChange={(e) => setRequestForm(prev => ({ ...prev, barterDetails: e.target.value }))}
                      className="input-orange"
                    />
                  </div>
                </>
              )}

              <div className="space-y-2">
                <Label>Timeline</Label>
                <Input
                  placeholder="e.g., 7 days"
                  value={requestForm.timeline}
                  onChange={(e) => setRequestForm(prev => ({ ...prev, timeline: e.target.value }))}
                  className="input-orange"
                />
              </div>

              <div className="space-y-2">
                <Label>Additional Notes (Optional)</Label>
                <Textarea
                  placeholder="Any additional information..."
                  value={requestForm.brief}
                  onChange={(e) => setRequestForm(prev => ({ ...prev, brief: e.target.value }))}
                  className="input-orange"
                />
              </div>

              <Button onClick={handleSendRequest} className="w-full btn-primary" disabled={actionLoading}>
                {actionLoading ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : <Send className="w-4 h-4 mr-2" />}
                Send Request
              </Button>
            </div>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
};

// Campaign Card Component
const CampaignCard = ({ campaign, isIncoming, onClick }) => {
  const StatusIcon = STATUS_CONFIG[campaign.status]?.icon || Clock;
  
  const formatPrice = (price) => {
    return new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR', maximumFractionDigits: 0 }).format(price);
  };

  const otherParty = isIncoming ? campaign.senderName : campaign.receiverName;

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      className="card-orange p-4 cursor-pointer hover:shadow-lg transition-shadow"
      onClick={onClick}
      data-testid={`campaign-card-${campaign.id}`}
    >
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <div className="w-12 h-12 rounded-full bg-primary/20 flex items-center justify-center">
            <StatusIcon className="w-6 h-6 text-primary" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h3 className="font-semibold">{otherParty}</h3>
              <Badge variant="outline" className="text-xs">
                {isIncoming ? '📥 Incoming' : '📤 Sent'}
              </Badge>
            </div>
            <p className="text-sm text-muted-foreground capitalize">
              {campaign.campaignType.replace('_', ' ')} • {campaign.deliverables}
            </p>
          </div>
        </div>
        <div className="text-right">
          <Badge className={STATUS_CONFIG[campaign.status]?.color}>
            {STATUS_CONFIG[campaign.status]?.label}
          </Badge>
          <p className="text-sm text-muted-foreground mt-1">
            {campaign.campaignType === 'paid' ? formatPrice(campaign.creatorPayout || campaign.budget) : formatPrice(campaign.productValue)}
          </p>
        </div>
      </div>
      
      {campaign.identityUnlocked && (
        <div className="mt-3 pt-3 border-t border-orange-100 text-sm text-green-600">
          🔓 Instagram: {isIncoming ? campaign.senderInstagram : campaign.receiverInstagram || 'Available'}
        </div>
      )}
    </motion.div>
  );
};

// Brand Card Component (Clickable - to send request)
const BrandCard = ({ brand, index, onClick }) => {
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: index * 0.05 }}
      className="card-orange p-6 cursor-pointer hover:shadow-lg transition-shadow group"
      onClick={onClick}
      data-testid={`brand-card-${brand.id}`}
    >
      <div className="w-16 h-16 rounded-full bg-primary/20 flex items-center justify-center text-3xl mb-4 group-hover:bg-primary/30 transition-colors">
        🏢
      </div>
      <h3 className="font-heading font-bold text-lg mb-1">{brand.industry} Brand</h3>
      <p className="text-sm text-muted-foreground mb-3">{brand.location}</p>
      <div className="flex flex-wrap gap-2 mb-4">
        <Badge variant="secondary">{brand.budgetRange}</Badge>
        {brand.barterEnabled && <Badge>🤝 Barter</Badge>}
      </div>
      <Button variant="outline" className="w-full rounded-full group-hover:bg-primary group-hover:text-white transition-colors">
        <Send className="w-4 h-4 mr-2" />
        Send Request
      </Button>
    </motion.div>
  );
};

export default CreatorDashboard;
