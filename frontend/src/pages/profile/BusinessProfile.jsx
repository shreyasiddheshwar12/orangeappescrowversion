import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import { 
  Instagram, Globe, MapPin, ArrowLeft, Loader2, 
  Image as ImageIcon, Play, ExternalLink
} from 'lucide-react';
import { Button } from '../../components/ui/button';
import { Badge } from '../../components/ui/badge';
import { Avatar, AvatarFallback, AvatarImage } from '../../components/ui/avatar';
import { marketplaceAPI } from '../../lib/api';
import { toast } from 'sonner';

const BusinessProfile = () => {
  const { id } = useParams();
  const navigate = useNavigate();
  const [business, setBusiness] = useState(null);
  const [loading, setLoading] = useState(true);
  const [selectedMedia, setSelectedMedia] = useState(null);

  useEffect(() => {
    loadBusiness();
  }, [id]);

  const loadBusiness = async () => {
    try {
      const response = await marketplaceAPI.getBusinessById(id);
      setBusiness(response.data);
    } catch (error) {
      toast.error("Business not found");
      navigate(-1);
    } finally {
      setLoading(false);
    }
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
          <div className="flex gap-2">
            {business?.websiteUrl && (
              <Button
                variant="outline"
                className="rounded-full"
                onClick={() => window.open(business.websiteUrl, '_blank')}
                data-testid="website-btn"
              >
                <Globe className="w-4 h-4 mr-2" />
                Website
              </Button>
            )}
            {business?.instagramUrl && (
              <Button
                variant="outline"
                className="rounded-full"
                onClick={() => window.open(business.instagramUrl, '_blank')}
                data-testid="instagram-btn"
              >
                <Instagram className="w-4 h-4 mr-2" />
                Instagram
              </Button>
            )}
          </div>
        </div>
      </header>

      <main className="max-w-5xl mx-auto px-6 py-8">
        {/* Brand Hero */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="card-orange p-8 mb-8"
        >
          <div className="flex items-start gap-6">
            <Avatar className="w-24 h-24 border-4 border-primary">
              <AvatarImage src={business?.profilePhotoUrl} />
              <AvatarFallback className="bg-primary text-white text-3xl">
                {business?.brandName?.[0]}
              </AvatarFallback>
            </Avatar>
            <div className="flex-1">
              <div className="flex items-center gap-3 mb-2">
                <h1 className="font-heading text-3xl font-bold">{business?.brandName}</h1>
                <Badge className="bg-accent text-accent-foreground">{business?.category}</Badge>
              </div>
              <p className="text-muted-foreground text-lg mb-4">{business?.bio}</p>
              <div className="flex items-center gap-6 text-muted-foreground">
                {business?.location && (
                  <div className="flex items-center gap-2">
                    <MapPin className="w-5 h-5" />
                    {business.location}
                  </div>
                )}
                {business?.websiteUrl && (
                  <a 
                    href={business.websiteUrl} 
                    target="_blank" 
                    rel="noopener noreferrer"
                    className="flex items-center gap-2 hover:text-primary transition-colors"
                  >
                    <Globe className="w-5 h-5" />
                    Visit Website
                    <ExternalLink className="w-4 h-4" />
                  </a>
                )}
                {business?.instagramHandle && (
                  <a 
                    href={business.instagramUrl} 
                    target="_blank" 
                    rel="noopener noreferrer"
                    className="flex items-center gap-2 hover:text-primary transition-colors"
                  >
                    <Instagram className="w-5 h-5" />
                    {business.instagramHandle}
                  </a>
                )}
              </div>
            </div>
          </div>
        </motion.div>

        {/* Media Gallery */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
        >
          <h2 className="font-heading text-2xl font-bold mb-6 flex items-center gap-2">
            <ImageIcon className="w-6 h-6" />
            Brand Gallery
          </h2>

          {business?.mediaGallery?.length > 0 ? (
            <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
              {business.mediaGallery.map((media, idx) => (
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
                        <div className="w-12 h-12 bg-black/50 rounded-full flex items-center justify-center">
                          <Play className="w-5 h-5 text-white fill-white" />
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

export default BusinessProfile;
