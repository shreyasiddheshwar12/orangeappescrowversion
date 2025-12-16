import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import { 
  Instagram, Globe, MapPin, Edit, LogOut, MessageSquare, Send,
  ExternalLink, Search, Filter, X, Users, DollarSign, Loader2
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
import { businessAPI, marketplaceAPI, requestsAPI } from '../../lib/api';
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
  const [sentRequests, setSentRequests] = useState([]);
  const [loading, setLoading] = useState(true);
  const [creatorsLoading, setCreatorsLoading] = useState(false);
  
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
    loadSentRequests();
  }, []);

  const loadProfile = async () => {
    try {
      const response = await businessAPI.getProfile();
      setProfile(response.data);
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
      
      const response = await marketplaceAPI.getCreators(params);
      setCreators(response.data);
    } catch (error) {
      toast.error("Failed to load creators");
    } finally {
      setCreatorsLoading(false);
      setLoading(false);
    }
  };

  const loadSentRequests = async () => {
    try {
      const response = await requestsAPI.getSent();
      setSentRequests(response.data);
    } catch (error) {
      console.error("Failed to load sent requests");
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
          <div className="flex items-center gap-3">
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
                {profile?.websiteUrl && (
                  <a href={profile.websiteUrl} target="_blank" rel="noopener noreferrer" 
                     className="flex items-center gap-1 hover:text-primary transition-colors">
                    <Globe className="w-4 h-4" />
                    Website
                  </a>
                )}
                {profile?.instagramUrl && (
                  <a href={profile.instagramUrl} target="_blank" rel="noopener noreferrer"
                     className="flex items-center gap-1 hover:text-primary transition-colors">
                    <Instagram className="w-4 h-4" />
                    Instagram
                  </a>
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

        {/* Tabs */}
        <Tabs defaultValue="marketplace" className="w-full">
          <TabsList className="mb-6 bg-muted/50 p-1 rounded-full">
            <TabsTrigger value="marketplace" className="rounded-full data-[state=active]:bg-white px-6">
              🍊 Creator Marketplace
            </TabsTrigger>
            <TabsTrigger value="requests" className="rounded-full data-[state=active]:bg-white px-6">
              📤 Sent Requests ({sentRequests.length})
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
                    {(filters.niche || filters.location || filters.openToBarter || filters.minFollowers > 0 || filters.maxFollowers < 1000000) && (
                      <Badge className="ml-2 bg-primary text-white">Active</Badge>
                    )}
                  </Button>
                </SheetTrigger>
                <SheetContent className="w-[400px]">
                  <SheetHeader>
                    <SheetTitle className="font-heading">Filter Creators 🎯</SheetTitle>
                  </SheetHeader>
                  
                  <div className="space-y-6 mt-6">
                    {/* Niche Filter */}
                    <div className="space-y-2">
                      <Label>Niche</Label>
                      <Select value={filters.niche} onValueChange={(value) => setFilters(prev => ({ ...prev, niche: value }))}>
                        <SelectTrigger className="rounded-xl" data-testid="filter-niche-select">
                          <SelectValue placeholder="All niches" />
                        </SelectTrigger>
                        <SelectContent>
                          {NICHES.map(niche => (
                            <SelectItem key={niche} value={niche}>{niche}</SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    </div>

                    {/* Followers Range */}
                    <div className="space-y-4">
                      <Label>Followers Range</Label>
                      <div className="px-2">
                        <Slider
                          value={[filters.minFollowers, filters.maxFollowers]}
                          onValueChange={([min, max]) => setFilters(prev => ({ ...prev, minFollowers: min, maxFollowers: max }))}
                          min={0}
                          max={1000000}
                          step={1000}
                          className="w-full"
                          data-testid="filter-followers-slider"
                        />
                      </div>
                      <div className="flex justify-between text-sm text-muted-foreground">
                        <span>{formatFollowers(filters.minFollowers)}</span>
                        <span>{formatFollowers(filters.maxFollowers)}</span>
                      </div>
                    </div>

                    {/* Location */}
                    <div className="space-y-2">
                      <Label>Location</Label>
                      <Input
                        placeholder="Mumbai, Delhi..."
                        value={filters.location}
                        onChange={(e) => setFilters(prev => ({ ...prev, location: e.target.value }))}
                        className="input-orange"
                        data-testid="filter-location-input"
                      />
                    </div>

                    {/* Barter Toggle */}
                    <div className="flex items-center justify-between p-4 bg-muted/50 rounded-xl">
                      <div>
                        <p className="font-semibold">Open to Barter Only</p>
                        <p className="text-sm text-muted-foreground">Filter creators who accept products</p>
                      </div>
                      <Switch
                        checked={filters.openToBarter}
                        onCheckedChange={(checked) => setFilters(prev => ({ ...prev, openToBarter: checked }))}
                        data-testid="filter-barter-switch"
                      />
                    </div>

                    {/* Actions */}
                    <div className="flex gap-3 pt-4">
                      <Button variant="outline" className="flex-1 rounded-full" onClick={resetFilters} data-testid="reset-filters-btn">
                        Reset
                      </Button>
                      <Button className="flex-1 btn-primary" onClick={applyFilters} data-testid="apply-filters-btn">
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
                  <CreatorCard 
                    key={creator.id} 
                    creator={creator} 
                    index={idx}
                    onClick={() => navigate(`/profile/creator/${creator.id}`)}
                  />
                ))}
              </div>
            )}
          </TabsContent>

          <TabsContent value="requests">
            <div className="mb-6">
              <h2 className="font-heading text-2xl font-bold">Your Sent Requests</h2>
              <p className="text-muted-foreground">Track your collaboration requests</p>
            </div>

            {sentRequests.length === 0 ? (
              <div className="card-orange p-12 text-center">
                <span className="text-5xl block mb-4">📤</span>
                <h3 className="font-heading text-xl font-bold mb-2">No requests sent yet</h3>
                <p className="text-muted-foreground">Browse the marketplace and send your first collab request!</p>
              </div>
            ) : (
              <div className="space-y-4">
                {sentRequests.map(request => (
                  <SentRequestCard 
                    key={request.id} 
                    request={request}
                    onChat={() => navigate(`/chat/${request.id}`)}
                    onViewCreator={() => navigate(`/profile/creator/${request.creatorId}`)}
                  />
                ))}
              </div>
            )}
          </TabsContent>
        </Tabs>
      </main>
    </div>
  );
};

const CreatorCard = ({ creator, index, onClick }) => {
  const formatFollowers = (count) => {
    if (count >= 1000000) return `${(count / 1000000).toFixed(1)}M`;
    if (count >= 1000) return `${(count / 1000).toFixed(1)}K`;
    return count.toString();
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
        {creator.profilePhotoUrl ? (
          <img 
            src={creator.profilePhotoUrl} 
            alt={creator.name}
            className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300"
          />
        ) : (
          <div className="w-full h-full bg-gradient-to-br from-primary/20 to-accent/20 flex items-center justify-center">
            <span className="text-6xl">{creator.name?.[0]}</span>
          </div>
        )}
        
        {/* Overlay */}
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

        {/* Info */}
        <div className="absolute bottom-0 left-0 right-0 p-4 text-white">
          <h3 className="font-heading font-bold text-lg mb-1">{creator.name}</h3>
          <div className="flex items-center gap-3 text-sm opacity-90">
            <div className="flex items-center gap-1">
              <Users className="w-4 h-4" />
              {formatFollowers(creator.followersCount || 0)}
            </div>
            {creator.location && (
              <div className="flex items-center gap-1">
                <MapPin className="w-4 h-4" />
                {creator.location}
              </div>
            )}
          </div>
        </div>
      </div>
    </motion.div>
  );
};

const SentRequestCard = ({ request, onChat, onViewCreator }) => {
  const formatPrice = (price) => {
    return new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR', maximumFractionDigits: 0 }).format(price);
  };

  const statusColors = {
    pending: 'bg-yellow-100 text-yellow-800',
    accepted: 'bg-green-100 text-green-800',
    declined: 'bg-red-100 text-red-800'
  };

  return (
    <div className="card-orange p-6" data-testid={`sent-request-${request.id}`}>
      <div className="flex items-start gap-4">
        <Avatar 
          className="w-14 h-14 border-2 border-orange-100 cursor-pointer" 
          onClick={onViewCreator}
        >
          <AvatarImage src={request.creatorPhoto} />
          <AvatarFallback className="bg-primary/10 text-primary">
            {request.creatorName?.[0]}
          </AvatarFallback>
        </Avatar>
        <div className="flex-1">
          <div className="flex items-center gap-2 mb-1">
            <h4 className="font-semibold cursor-pointer hover:text-primary transition-colors" onClick={onViewCreator}>
              {request.creatorName || 'Creator'}
            </h4>
            <Badge className={statusColors[request.status]}>
              {request.status}
            </Badge>
          </div>
          <h3 className="font-heading text-lg font-bold mb-2">{request.title}</h3>
          <p className="text-muted-foreground text-sm mb-3 line-clamp-2">{request.brief}</p>
          
          <div className="flex flex-wrap gap-4 text-sm">
            {request.offerAmount > 0 && (
              <div className="flex items-center gap-1 text-primary font-semibold">
                <DollarSign className="w-4 h-4" />
                {formatPrice(request.offerAmount)}
              </div>
            )}
            {request.deliverables && (
              <div className="text-muted-foreground">📦 {request.deliverables}</div>
            )}
          </div>
        </div>
        
        {/* Chat available for pending and accepted requests */}
        {request.status !== 'declined' && (
          <Button 
            onClick={onChat} 
            className={request.status === 'accepted' ? "btn-primary" : "btn-secondary"}
            data-testid={`chat-btn-${request.id}`}
          >
            <MessageSquare className="w-4 h-4 mr-2" />
            {request.status === 'pending' ? 'Message Creator' : 'Chat'}
          </Button>
        )}
      </div>
    </div>
  );
};

export default BusinessDashboard;
