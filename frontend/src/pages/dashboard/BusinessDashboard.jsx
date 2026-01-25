import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import { 
  MapPin, Edit, LogOut, MessageSquare, Send, ExternalLink, 
  Search, Filter, X, Loader2, Eye, CheckCircle, Clock, AlertCircle,
  Link as LinkIcon, Star
} from 'lucide-react';
import { Button } from '../../components/ui/button';
import { Badge } from '../../components/ui/badge';
import { Avatar, AvatarFallback, AvatarImage } from '../../components/ui/avatar';
import { Input } from '../../components/ui/input';
import { Label } from '../../components/ui/label';
import { Textarea } from '../../components/ui/textarea';
import { Switch } from '../../components/ui/switch';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../../components/ui/select';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../../components/ui/tabs';
import { Sheet, SheetContent, SheetHeader, SheetTitle, SheetTrigger } from '../../components/ui/sheet';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '../../components/ui/dialog';
import { businessAPI, marketplaceAPI, campaignAPI, getErrorMessage } from '../../lib/api';
import { useAuth } from '../../lib/auth';
import { toast } from 'sonner';

const NICHES = ['All', 'Fashion', 'Beauty', 'Fitness', 'Tech', 'Gaming', 'Food', 'Travel', 'Lifestyle', 'Comedy', 'Education', 'Music', 'Art', 'Sports', 'Health', 'Finance'];

// Campaign status display config
const STATUS_CONFIG = {
  requested: { label: 'Pending', color: 'bg-yellow-100 text-yellow-800', icon: Clock },
  accepted: { label: 'Accepted - Pay Now', color: 'bg-blue-100 text-blue-800', icon: Send },
  paid: { label: 'In Progress', color: 'bg-purple-100 text-purple-800', icon: Clock },
  in_progress: { label: 'In Progress', color: 'bg-purple-100 text-purple-800', icon: Clock },
  link_submitted: { label: 'Link Submitted - Verify', color: 'bg-orange-100 text-orange-800', icon: LinkIcon },
  link_verified: { label: 'Verified - Complete', color: 'bg-green-100 text-green-800', icon: CheckCircle },
  completed: { label: 'Completed', color: 'bg-green-500 text-white', icon: CheckCircle },
  disputed: { label: 'Disputed', color: 'bg-red-100 text-red-800', icon: AlertCircle },
  cancelled: { label: 'Cancelled', color: 'bg-gray-100 text-gray-800', icon: X },
};

const BusinessDashboard = () => {
  const navigate = useNavigate();
  const { logout } = useAuth();
  const [profile, setProfile] = useState(null);
  const [creators, setCreators] = useState([]);
  const [outgoingCampaigns, setOutgoingCampaigns] = useState([]);
  const [incomingCampaigns, setIncomingCampaigns] = useState([]);
  const [loading, setLoading] = useState(true);
  const [creatorsLoading, setCreatorsLoading] = useState(false);
  
  // Modals
  const [showRequestModal, setShowRequestModal] = useState(false);
  const [selectedCreator, setSelectedCreator] = useState(null);
  const [showCampaignModal, setShowCampaignModal] = useState(false);
  const [selectedCampaign, setSelectedCampaign] = useState(null);
  const [actionLoading, setActionLoading] = useState(false);
  
  // Request form
  const [requestForm, setRequestForm] = useState({
    campaignType: 'paid',
    deliverables: '',
    budget: 0,
    productValue: 0,
    timeline: '',
    brief: '',
    barterDetails: ''
  });
  
  // Filters
  const [filters, setFilters] = useState({ niche: '', barterOnly: false });
  const [showFilters, setShowFilters] = useState(false);

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      const [profileRes, outgoingRes, incomingRes] = await Promise.all([
        businessAPI.getProfile(),
        campaignAPI.getOutgoing(),
        campaignAPI.getIncoming()
      ]);
      setProfile(profileRes.data);
      setOutgoingCampaigns(outgoingRes.data);
      setIncomingCampaigns(incomingRes.data);
      await loadCreators();
    } catch (error) {
      if (error.response?.status === 404) {
        navigate('/onboarding/business');
      }
    } finally {
      setLoading(false);
    }
  };

  const loadCreators = async (customFilters = filters) => {
    setCreatorsLoading(true);
    try {
      const params = {};
      if (customFilters.niche && customFilters.niche !== 'All') params.niche = customFilters.niche;
      if (customFilters.barterOnly) params.barterOnly = true;
      
      const response = await marketplaceAPI.discoverCreators(params);
      setCreators(response.data);
    } catch (error) {
      toast.error("Failed to load creators");
    } finally {
      setCreatorsLoading(false);
    }
  };

  const handleCreatorClick = (creator) => {
    setSelectedCreator(creator);
    setRequestForm({
      campaignType: 'paid',
      deliverables: '',
      budget: creator.reelPrice || 0,
      productValue: 0,
      timeline: '7 days',
      brief: '',
      barterDetails: ''
    });
    setShowRequestModal(true);
  };

  const handleSendRequest = async () => {
    if (!selectedCreator || !requestForm.deliverables) {
      toast.error("Please fill in deliverables");
      return;
    }
    
    setActionLoading(true);
    try {
      await campaignAPI.create({
        receiverId: selectedCreator.id,
        receiverType: 'creator',
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
      
      // Refresh campaigns
      const [outRes, inRes] = await Promise.all([
        campaignAPI.getOutgoing(),
        campaignAPI.getIncoming()
      ]);
      setOutgoingCampaigns(outRes.data);
      setIncomingCampaigns(inRes.data);
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
      toast.success("Request accepted! Creator will be notified to proceed.");
      
      // Refresh campaigns
      const [outRes, inRes] = await Promise.all([
        campaignAPI.getOutgoing(),
        campaignAPI.getIncoming()
      ]);
      setOutgoingCampaigns(outRes.data);
      setIncomingCampaigns(inRes.data);
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
      
      // Refresh campaigns
      const [outRes, inRes] = await Promise.all([
        campaignAPI.getOutgoing(),
        campaignAPI.getIncoming()
      ]);
      setOutgoingCampaigns(outRes.data);
      setIncomingCampaigns(inRes.data);
      setShowCampaignModal(false);
    } catch (error) {
      toast.error(getErrorMessage(error, "Failed to reject"));
    } finally {
      setActionLoading(false);
    }
  };

  const handlePayCampaign = async (campaign) => {
    setActionLoading(true);
    try {
      const res = await campaignAPI.pay(campaign.id);
      toast.success(res.data.message || "Payment successful!");
      
      if (res.data.identityUnlocked) {
        toast.success(`Instagram: ${res.data.receiverInstagram}`);
      }
      
      // Refresh campaigns
      const campaignsRes = await campaignAPI.getOutgoing();
      setCampaigns(campaignsRes.data);
      setShowCampaignModal(false);
    } catch (error) {
      toast.error(getErrorMessage(error, "Payment failed"));
    } finally {
      setActionLoading(false);
    }
  };

  const handleVerifyLink = async (campaign) => {
    setActionLoading(true);
    try {
      const res = await campaignAPI.verifyLink(campaign.id);
      toast.success(res.data.message || "Link verified!");
      
      if (res.data.identityUnlocked) {
        toast.success(`Instagram: ${res.data.receiverInstagram}`);
      }
      
      // Refresh campaigns
      const campaignsRes = await campaignAPI.getOutgoing();
      setCampaigns(campaignsRes.data);
      setShowCampaignModal(false);
    } catch (error) {
      toast.error(getErrorMessage(error, "Verification failed"));
    } finally {
      setActionLoading(false);
    }
  };

  const handleCompleteCampaign = async (campaign) => {
    setActionLoading(true);
    try {
      const res = await campaignAPI.complete(campaign.id);
      toast.success(res.data.message || "Campaign completed!");
      
      // Refresh campaigns
      const campaignsRes = await campaignAPI.getOutgoing();
      setCampaigns(campaignsRes.data);
      setShowCampaignModal(false);
    } catch (error) {
      toast.error(getErrorMessage(error, "Failed to complete"));
    } finally {
      setActionLoading(false);
    }
  };

  const [ratingForm, setRatingForm] = useState({ rating: 5, feedback: '' });
  
  const handleSubmitRating = async (campaign) => {
    if (!ratingForm.feedback || ratingForm.feedback.length < 10) {
      toast.error("Please provide feedback (min 10 characters)");
      return;
    }
    
    setActionLoading(true);
    try {
      await campaignAPI.rate(campaign.id, ratingForm.rating, ratingForm.feedback);
      toast.success("Rating submitted!");
      
      // Refresh campaigns
      const campaignsRes = await campaignAPI.getOutgoing();
      setCampaigns(campaignsRes.data);
      setShowCampaignModal(false);
    } catch (error) {
      toast.error(getErrorMessage(error, "Failed to submit rating"));
    } finally {
      setActionLoading(false);
    }
  };

  const formatPrice = (price) => {
    return new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR', maximumFractionDigits: 0 }).format(price);
  };

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
                <Badge className="bg-accent text-accent-foreground">{profile?.industry}</Badge>
              </div>
              <p className="text-muted-foreground mb-3">{profile?.bio}</p>
              {profile?.location && (
                <div className="flex items-center gap-1 text-sm text-muted-foreground">
                  <MapPin className="w-4 h-4" />
                  {profile.location}
                </div>
              )}
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

        {/* Tabs */}
        <Tabs defaultValue="marketplace" className="w-full">
          <TabsList className="mb-6 bg-muted/50 p-1 rounded-full">
            <TabsTrigger value="marketplace" className="rounded-full data-[state=active]:bg-white px-6">
              🍊 Creator Marketplace
            </TabsTrigger>
            <TabsTrigger value="campaigns" className="rounded-full data-[state=active]:bg-white px-6">
              📤 My Campaigns ({campaigns.length})
            </TabsTrigger>
          </TabsList>

          <TabsContent value="marketplace">
            {/* Marketplace Header */}
            <div className="flex items-center justify-between mb-6">
              <div>
                <h2 className="font-heading text-2xl font-bold">Find your perfect creator 🍊</h2>
                <p className="text-muted-foreground">{creators.length} creators available</p>
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

                    <div className="flex items-center justify-between p-4 bg-muted/50 rounded-xl">
                      <div>
                        <p className="font-semibold">Barter Only</p>
                        <p className="text-sm text-muted-foreground">Filter barter-friendly creators</p>
                      </div>
                      <Switch
                        checked={filters.barterOnly}
                        onCheckedChange={(checked) => setFilters(prev => ({ ...prev, barterOnly: checked }))}
                      />
                    </div>

                    <div className="flex gap-3 pt-4">
                      <Button variant="outline" className="flex-1 rounded-full" onClick={() => { setFilters({ niche: '', barterOnly: false }); loadCreators({ niche: '', barterOnly: false }); }}>
                        Reset
                      </Button>
                      <Button className="flex-1 btn-primary" onClick={() => { loadCreators(filters); setShowFilters(false); }}>
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
                <p className="text-muted-foreground">Finding creators...</p>
              </div>
            ) : creators.length === 0 ? (
              <div className="card-orange p-12 text-center">
                <span className="text-5xl block mb-4">🔍</span>
                <h3 className="font-heading text-xl font-bold mb-2">No creators found</h3>
                <p className="text-muted-foreground mb-4">Try adjusting your filters</p>
              </div>
            ) : (
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
                {creators.map((creator, idx) => (
                  <CreatorCard 
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
              <p className="text-muted-foreground">Track your collaboration requests</p>
            </div>

            {campaigns.length === 0 ? (
              <div className="card-orange p-12 text-center">
                <span className="text-5xl block mb-4">📤</span>
                <h3 className="font-heading text-xl font-bold mb-2">No campaigns yet</h3>
                <p className="text-muted-foreground">Click on a creator to send a collaboration request!</p>
              </div>
            ) : (
              <div className="space-y-4">
                {campaigns.map(campaign => (
                  <CampaignCard 
                    key={campaign.id} 
                    campaign={campaign}
                    onClick={() => { setSelectedCampaign(campaign); setShowCampaignModal(true); }}
                  />
                ))}
              </div>
            )}
          </TabsContent>
        </Tabs>
      </main>

      {/* Send Request Modal */}
      <Dialog open={showRequestModal} onOpenChange={setShowRequestModal}>
        <DialogContent className="sm:max-w-[500px]">
          <DialogHeader>
            <DialogTitle className="font-heading text-xl flex items-center gap-2">
              <Send className="w-5 h-5 text-primary" />
              Send Collaboration Request
            </DialogTitle>
          </DialogHeader>
          
          {selectedCreator && (
            <div className="space-y-4 pt-4">
              <div className="bg-muted/50 rounded-xl p-4">
                <div className="flex items-center gap-3">
                  <div className="w-12 h-12 rounded-full bg-primary/20 flex items-center justify-center text-xl">
                    {selectedCreator.niche?.[0] || '🍊'}
                  </div>
                  <div>
                    <p className="font-semibold">{selectedCreator.niche} Creator</p>
                    <p className="text-sm text-muted-foreground">{selectedCreator.location}</p>
                  </div>
                </div>
                <div className="mt-3 flex gap-2 text-sm">
                  <Badge variant="secondary">Reel: {formatPrice(selectedCreator.reelPrice)}</Badge>
                  <Badge variant="secondary">Story: {formatPrice(selectedCreator.storyPrice)}</Badge>
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
                <Label>Deliverables *</Label>
                <Textarea
                  placeholder="e.g., 1 Reel + 2 Stories featuring our product"
                  value={requestForm.deliverables}
                  onChange={(e) => setRequestForm(prev => ({ ...prev, deliverables: e.target.value }))}
                  className="input-orange"
                />
              </div>

              {requestForm.campaignType === 'paid' && (
                <div className="space-y-2">
                  <Label>Budget (₹)</Label>
                  <Input
                    type="number"
                    value={requestForm.budget}
                    onChange={(e) => setRequestForm(prev => ({ ...prev, budget: Number(e.target.value) }))}
                    className="input-orange"
                  />
                  <p className="text-xs text-muted-foreground">
                    Full amount goes to escrow. 10% platform fee on completion.
                  </p>
                </div>
              )}

              {requestForm.campaignType !== 'paid' && (
                <>
                  <div className="space-y-2">
                    <Label>Product/Service Value (₹)</Label>
                    <Input
                      type="number"
                      value={requestForm.productValue}
                      onChange={(e) => setRequestForm(prev => ({ ...prev, productValue: Number(e.target.value) }))}
                      className="input-orange"
                    />
                    <p className="text-xs text-muted-foreground">
                      10% barter fee: {formatPrice(requestForm.productValue * 0.1)}
                    </p>
                  </div>
                  <div className="space-y-2">
                    <Label>Product/Service Description</Label>
                    <Textarea
                      placeholder="Describe the product or service you're offering"
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
                <Label>Brief (Optional)</Label>
                <Textarea
                  placeholder="Any additional requirements..."
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
                    <p className="font-semibold">{selectedCampaign.receiverName}</p>
                    <p className="text-sm text-muted-foreground capitalize">{selectedCampaign.campaignType.replace('_', ' ')}</p>
                  </div>
                  <Badge className={STATUS_CONFIG[selectedCampaign.status]?.color}>
                    {STATUS_CONFIG[selectedCampaign.status]?.label}
                  </Badge>
                </div>
                <p className="text-sm"><strong>Deliverables:</strong> {selectedCampaign.deliverables}</p>
                {selectedCampaign.campaignType === 'paid' && (
                  <p className="text-sm"><strong>Budget:</strong> {formatPrice(selectedCampaign.budget)}</p>
                )}
                {selectedCampaign.campaignType !== 'paid' && (
                  <>
                    <p className="text-sm"><strong>Product Value:</strong> {formatPrice(selectedCampaign.productValue)}</p>
                    <p className="text-sm"><strong>Barter Fee:</strong> {formatPrice(selectedCampaign.barterFee)}</p>
                  </>
                )}
              </div>

              {/* Identity Info */}
              {selectedCampaign.identityUnlocked && (
                <div className="bg-green-50 rounded-xl p-4">
                  <p className="font-semibold text-green-800 mb-2">🔓 Identity Unlocked</p>
                  <p className="text-sm">Instagram: <strong>{selectedCampaign.receiverInstagram || 'N/A'}</strong></p>
                </div>
              )}

              {/* Content Link */}
              {selectedCampaign.contentLink && (
                <div className="bg-blue-50 rounded-xl p-4">
                  <p className="font-semibold text-blue-800 mb-2">📎 Submitted Link</p>
                  <a href={selectedCampaign.contentLink} target="_blank" rel="noopener noreferrer" className="text-sm text-blue-600 underline break-all">
                    {selectedCampaign.contentLink}
                  </a>
                </div>
              )}

              {/* Action Buttons based on status */}
              <div className="space-y-3">
                {selectedCampaign.status === 'accepted' && (
                  <Button onClick={() => handlePayCampaign(selectedCampaign)} className="w-full btn-primary" disabled={actionLoading}>
                    {actionLoading ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : null}
                    Pay {selectedCampaign.campaignType === 'paid' ? formatPrice(selectedCampaign.escrowAmount || selectedCampaign.budget) : formatPrice(selectedCampaign.barterFee)} to Proceed
                  </Button>
                )}

                {selectedCampaign.status === 'link_submitted' && (
                  <Button onClick={() => handleVerifyLink(selectedCampaign)} className="w-full btn-primary" disabled={actionLoading}>
                    {actionLoading ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : <CheckCircle className="w-4 h-4 mr-2" />}
                    Verify Link
                  </Button>
                )}

                {selectedCampaign.status === 'link_verified' && (
                  <Button onClick={() => handleCompleteCampaign(selectedCampaign)} className="w-full btn-primary" disabled={actionLoading}>
                    {actionLoading ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : <CheckCircle className="w-4 h-4 mr-2" />}
                    Mark as Complete
                  </Button>
                )}

                {selectedCampaign.status === 'completed' && (
                  <div className="space-y-3">
                    <Label>Rate this collaboration</Label>
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
    </div>
  );
};

// Creator Card Component (Anonymous - No Name/Instagram shown)
const CreatorCard = ({ creator, index, onClick }) => {
  const formatPrice = (price) => {
    return new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR', maximumFractionDigits: 0 }).format(price);
  };

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
        <div className="w-full h-full bg-gradient-to-br from-primary/30 to-accent/30 flex items-center justify-center">
          <span className="text-6xl">{creator.niche?.[0] || '🍊'}</span>
        </div>
        
        {/* Orange Watermark Overlay */}
        <div className="absolute inset-0 flex items-center justify-center opacity-20">
          <span className="text-8xl rotate-[-15deg]">🍊</span>
        </div>
        
        <div className="absolute inset-0 bg-gradient-to-t from-black/70 via-transparent to-transparent" />
        
        {/* Badges */}
        <div className="absolute top-3 left-3 flex flex-wrap gap-2">
          <Badge className="bg-white/90 text-foreground text-xs">
            {creator.niche}
          </Badge>
        </div>
        
        {creator.barterEnabled && (
          <div className="absolute top-3 right-3">
            <Badge className="bg-accent text-accent-foreground">🤝 Barter</Badge>
          </div>
        )}

        {/* Info */}
        <div className="absolute bottom-0 left-0 right-0 p-4 text-white">
          <h3 className="font-heading font-bold text-lg mb-1">
            {creator.niche} Creator
          </h3>
          <div className="flex items-center gap-3 text-sm opacity-90">
            <span>{creator.engagementRate}% ER</span>
            <span>•</span>
            <span>{creator.location}</span>
          </div>
          <div className="mt-2 flex gap-2">
            <Badge variant="secondary" className="bg-white/20 text-white text-xs">
              Reel: {formatPrice(creator.reelPrice)}
            </Badge>
          </div>
        </div>
      </div>
    </motion.div>
  );
};

// Campaign Card Component
const CampaignCard = ({ campaign, onClick }) => {
  const StatusIcon = STATUS_CONFIG[campaign.status]?.icon || Clock;
  
  const formatPrice = (price) => {
    return new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR', maximumFractionDigits: 0 }).format(price);
  };

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
            <h3 className="font-semibold">{campaign.receiverName}</h3>
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
            {campaign.campaignType === 'paid' ? formatPrice(campaign.budget) : formatPrice(campaign.productValue)}
          </p>
        </div>
      </div>
      
      {campaign.identityUnlocked && (
        <div className="mt-3 pt-3 border-t border-orange-100 text-sm text-green-600">
          🔓 Instagram: {campaign.receiverInstagram || 'Available'}
        </div>
      )}
    </motion.div>
  );
};

export default BusinessDashboard;
