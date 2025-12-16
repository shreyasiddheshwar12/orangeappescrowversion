import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import { 
  Instagram, MapPin, Users, ArrowLeft, Send, DollarSign, 
  ExternalLink, Loader2, Image as ImageIcon, Play
} from 'lucide-react';
import { Button } from '../../components/ui/button';
import { Badge } from '../../components/ui/badge';
import { Avatar, AvatarFallback, AvatarImage } from '../../components/ui/avatar';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '../../components/ui/dialog';
import { Input } from '../../components/ui/input';
import { Label } from '../../components/ui/label';
import { Textarea } from '../../components/ui/textarea';
import { marketplaceAPI, requestsAPI } from '../../lib/api';
import { useAuth } from '../../lib/auth';
import { toast } from 'sonner';

const CreatorProfile = () => {
  const { id } = useParams();
  const navigate = useNavigate();
  const { user } = useAuth();
  const [creator, setCreator] = useState(null);
  const [loading, setLoading] = useState(true);
  const [showRequestDialog, setShowRequestDialog] = useState(false);
  const [sendingRequest, setSendingRequest] = useState(false);
  const [selectedMedia, setSelectedMedia] = useState(null);
  
  const [requestForm, setRequestForm] = useState({
    title: '',
    brief: '',
    offerAmount: '',
    deliverables: '',
    timeline: ''
  });

  useEffect(() => {
    loadCreator();
  }, [id]);

  const loadCreator = async () => {
    try {
      const response = await marketplaceAPI.getCreatorById(id);
      setCreator(response.data);
    } catch (error) {
      toast.error("Creator not found");
      navigate(-1);
    } finally {
      setLoading(false);
    }
  };

  const handleSendRequest = async () => {
    if (!requestForm.title || !requestForm.brief) {
      toast.error("Please fill in title and brief");
      return;
    }

    setSendingRequest(true);
    try {
      await requestsAPI.create({
        creatorId: id,
        title: requestForm.title,
        brief: requestForm.brief,
        offerAmount: parseFloat(requestForm.offerAmount) || 0,
        deliverables: requestForm.deliverables,
        timeline: requestForm.timeline
      });
      toast.success("Request sent! Time to make magic together ✨");
      setShowRequestDialog(false);
      setRequestForm({ title: '', brief: '', offerAmount: '', deliverables: '', timeline: '' });
    } catch (error) {
      toast.error(error.response?.data?.detail || "Failed to send request");
    } finally {
      setSendingRequest(false);
    }
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
          <p className="text-muted-foreground">Loading profile...</p>
        </div>
      </div>
    );
  }

  const canSendRequest = user && user.role === 'business';

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
          {creator?.instagramUrl && (
            <Button
              variant="outline"
              className="rounded-full"
              onClick={() => window.open(creator.instagramUrl, '_blank')}
              data-testid="instagram-btn"
            >
              <Instagram className="w-4 h-4 mr-2" />
              Instagram
            </Button>
          )}
        </div>
      </header>

      <main className="max-w-5xl mx-auto px-6 py-8">
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          {/* Profile Info */}
          <div className="lg:col-span-1">
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              className="card-orange p-6 sticky top-24"
            >
              <div className="text-center mb-6">
                <Avatar className="w-32 h-32 mx-auto mb-4 border-4 border-primary">
                  <AvatarImage src={creator?.profilePhotoUrl} />
                  <AvatarFallback className="bg-primary text-white text-4xl">
                    {creator?.name?.[0]}
                  </AvatarFallback>
                </Avatar>
                <h1 className="font-heading text-2xl font-bold mb-2">{creator?.name}</h1>
                <p className="text-muted-foreground mb-4">{creator?.bio}</p>
                
                <div className="flex items-center justify-center gap-4 text-sm text-muted-foreground mb-4">
                  {creator?.location && (
                    <div className="flex items-center gap-1">
                      <MapPin className="w-4 h-4" />
                      {creator.location}
                    </div>
                  )}
                  <div className="flex items-center gap-1">
                    <Users className="w-4 h-4" />
                    {formatFollowers(creator?.followersCount || 0)}
                  </div>
                </div>

                {/* Niches */}
                <div className="flex flex-wrap justify-center gap-2 mb-4">
                  {creator?.niches?.map(niche => (
                    <Badge key={niche} variant="secondary" className="bg-primary/10 text-primary">
                      {niche}
                    </Badge>
                  ))}
                </div>

                {creator?.isOpenToBarter && (
                  <Badge className="bg-accent text-accent-foreground mb-4">
                    🤝 Open to Barter
                  </Badge>
                )}
              </div>

              {/* Rates */}
              <div className="border-t border-orange-100 pt-4 mb-6">
                <h3 className="font-semibold text-sm text-muted-foreground mb-3">RATES</h3>
                <div className="grid grid-cols-2 gap-3">
                  <div className="bg-muted/50 p-3 rounded-xl">
                    <p className="text-xs text-muted-foreground">Reel</p>
                    <p className="font-bold text-primary">{formatPrice(creator?.rates?.reelPrice || 0)}</p>
                  </div>
                  <div className="bg-muted/50 p-3 rounded-xl">
                    <p className="text-xs text-muted-foreground">Story</p>
                    <p className="font-bold text-primary">{formatPrice(creator?.rates?.storyPrice || 0)}</p>
                  </div>
                  <div className="bg-muted/50 p-3 rounded-xl">
                    <p className="text-xs text-muted-foreground">Post</p>
                    <p className="font-bold text-primary">{formatPrice(creator?.rates?.postPrice || 0)}</p>
                  </div>
                  <div className="bg-muted/50 p-3 rounded-xl">
                    <p className="text-xs text-muted-foreground">Bundle</p>
                    <p className="font-bold text-primary">{formatPrice(creator?.rates?.bundlePrice || 0)}</p>
                  </div>
                </div>
              </div>

              {/* Actions */}
              <div className="space-y-3">
                {creator?.instagramUrl && (
                  <Button
                    variant="outline"
                    className="w-full rounded-full"
                    onClick={() => window.open(creator.instagramUrl, '_blank')}
                  >
                    <Instagram className="w-4 h-4 mr-2" />
                    Go to Instagram
                  </Button>
                )}
                
                {canSendRequest && (
                  <Dialog open={showRequestDialog} onOpenChange={setShowRequestDialog}>
                    <DialogTrigger asChild>
                      <Button className="w-full btn-primary" data-testid="send-request-btn">
                        <Send className="w-4 h-4 mr-2" />
                        Send Collab Request
                      </Button>
                    </DialogTrigger>
                    <DialogContent className="sm:max-w-[500px]">
                      <DialogHeader>
                        <DialogTitle className="font-heading text-xl">
                          Send Request to {creator?.name} 🍊
                        </DialogTitle>
                      </DialogHeader>
                      <div className="space-y-4 pt-4">
                        <div className="space-y-2">
                          <Label>Campaign Title *</Label>
                          <Input
                            placeholder="Summer Collection 2024"
                            value={requestForm.title}
                            onChange={(e) => setRequestForm(prev => ({ ...prev, title: e.target.value }))}
                            className="input-orange"
                            data-testid="request-title-input"
                          />
                        </div>
                        <div className="space-y-2">
                          <Label>Brief *</Label>
                          <Textarea
                            placeholder="Tell them about your campaign, what you're looking for..."
                            value={requestForm.brief}
                            onChange={(e) => setRequestForm(prev => ({ ...prev, brief: e.target.value }))}
                            className="input-orange min-h-[100px]"
                            data-testid="request-brief-input"
                          />
                        </div>
                        <div className="grid grid-cols-2 gap-4">
                          <div className="space-y-2">
                            <Label>Offer Amount (₹)</Label>
                            <Input
                              type="number"
                              placeholder="15000"
                              value={requestForm.offerAmount}
                              onChange={(e) => setRequestForm(prev => ({ ...prev, offerAmount: e.target.value }))}
                              className="input-orange"
                              data-testid="request-amount-input"
                            />
                          </div>
                          <div className="space-y-2">
                            <Label>Timeline</Label>
                            <Input
                              placeholder="2 weeks"
                              value={requestForm.timeline}
                              onChange={(e) => setRequestForm(prev => ({ ...prev, timeline: e.target.value }))}
                              className="input-orange"
                              data-testid="request-timeline-input"
                            />
                          </div>
                        </div>
                        <div className="space-y-2">
                          <Label>Deliverables</Label>
                          <Input
                            placeholder="3 Reels, 5 Stories"
                            value={requestForm.deliverables}
                            onChange={(e) => setRequestForm(prev => ({ ...prev, deliverables: e.target.value }))}
                            className="input-orange"
                            data-testid="request-deliverables-input"
                          />
                        </div>
                        <Button
                          onClick={handleSendRequest}
                          disabled={sendingRequest}
                          className="w-full btn-primary"
                          data-testid="submit-request-btn"
                        >
                          {sendingRequest ? (
                            <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                          ) : (
                            <Send className="w-4 h-4 mr-2" />
                          )}
                          Send Request
                        </Button>
                      </div>
                    </DialogContent>
                  </Dialog>
                )}
                
                {!user && (
                  <Button
                    className="w-full btn-primary"
                    onClick={() => navigate('/signup?role=business')}
                  >
                    Sign up as Brand to Collaborate
                  </Button>
                )}
              </div>
            </motion.div>
          </div>

          {/* Media Gallery */}
          <div className="lg:col-span-2">
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.1 }}
            >
              <h2 className="font-heading text-2xl font-bold mb-6 flex items-center gap-2">
                <ImageIcon className="w-6 h-6" />
                Content Gallery
              </h2>

              {creator?.mediaGallery?.length > 0 ? (
                <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
                  {creator.mediaGallery.map((media, idx) => (
                    <motion.div
                      key={idx}
                      initial={{ opacity: 0, scale: 0.9 }}
                      animate={{ opacity: 1, scale: 1 }}
                      transition={{ delay: idx * 0.05 }}
                      className="aspect-square rounded-2xl overflow-hidden bg-muted cursor-pointer group relative"
                      onClick={() => setSelectedMedia(media)}
                    >
                      {media.type === 'video' ? (
                        <>
                          <img 
                            src={media.thumbnailUrl || media.url} 
                            alt="" 
                            className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300" 
                          />
                          <div className="absolute inset-0 flex items-center justify-center">
                            <div className="w-14 h-14 bg-black/50 rounded-full flex items-center justify-center">
                              <Play className="w-6 h-6 text-white fill-white" />
                            </div>
                          </div>
                        </>
                      ) : (
                        <img 
                          src={media.thumbnailUrl || media.url} 
                          alt="" 
                          className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300" 
                        />
                      )}
                    </motion.div>
                  ))}
                </div>
              ) : (
                <div className="card-orange p-12 text-center">
                  <ImageIcon className="w-12 h-12 mx-auto text-muted-foreground mb-4" />
                  <p className="text-muted-foreground">No media uploaded yet</p>
                </div>
              )}
            </motion.div>
          </div>
        </div>
      </main>

      {/* Media Lightbox */}
      {selectedMedia && (
        <div 
          className="fixed inset-0 bg-black/90 z-50 flex items-center justify-center p-4"
          onClick={() => setSelectedMedia(null)}
        >
          <Button
            variant="ghost"
            className="absolute top-4 right-4 text-white hover:bg-white/20 rounded-full"
            onClick={() => setSelectedMedia(null)}
          >
            ✕
          </Button>
          {selectedMedia.type === 'video' ? (
            <video 
              src={selectedMedia.url} 
              controls 
              autoPlay 
              className="max-w-full max-h-[90vh] rounded-lg"
              onClick={(e) => e.stopPropagation()}
            />
          ) : (
            <img 
              src={selectedMedia.url} 
              alt="" 
              className="max-w-full max-h-[90vh] rounded-lg object-contain"
              onClick={(e) => e.stopPropagation()}
            />
          )}
        </div>
      )}
    </div>
  );
};

export default CreatorProfile;
