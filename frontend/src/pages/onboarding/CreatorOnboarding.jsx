import { useState, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import { useDropzone } from 'react-dropzone';
import { 
  ArrowLeft, ArrowRight, Check, Loader2, Upload, X, Instagram,
  MapPin, Users, DollarSign, Image as ImageIcon
} from 'lucide-react';
import { Button } from '../../components/ui/button';
import { Input } from '../../components/ui/input';
import { Label } from '../../components/ui/label';
import { Textarea } from '../../components/ui/textarea';
import { Switch } from '../../components/ui/switch';
import { Badge } from '../../components/ui/badge';
import { Progress } from '../../components/ui/progress';
import { creatorAPI, uploadAPI } from '../../lib/api';
import { useAuth } from '../../lib/auth';
import { toast } from 'sonner';

const NICHES = [
  'Fashion', 'Beauty', 'Fitness', 'Tech', 'Gaming', 'Food', 
  'Travel', 'Lifestyle', 'Comedy', 'Education', 'Music', 'Art',
  'Sports', 'Health', 'Finance', 'Parenting', 'Photography', 'Dance'
];

const CreatorOnboarding = () => {
  const navigate = useNavigate();
  const { updateUser } = useAuth();
  const [step, setStep] = useState(1);
  const [loading, setLoading] = useState(false);
  const [uploading, setUploading] = useState(false);

  // Form data
  const [formData, setFormData] = useState({
    name: '',
    bio: '',
    location: '',
    instagramHandle: '',
    instagramUrl: '',
    followersCount: '',
    niches: [],
    isOpenToBarter: false,
    rates: {
      reelPrice: '',
      storyPrice: '',
      postPrice: '',
      bundlePrice: ''
    },
    profilePhotoUrl: '',
    mediaGallery: []
  });

  const totalSteps = 5;
  const progress = (step / totalSteps) * 100;

  const updateField = (field, value) => {
    setFormData(prev => ({ ...prev, [field]: value }));
  };

  const updateRates = (field, value) => {
    setFormData(prev => ({
      ...prev,
      rates: { ...prev.rates, [field]: value }
    }));
  };

  const toggleNiche = (niche) => {
    setFormData(prev => ({
      ...prev,
      niches: prev.niches.includes(niche)
        ? prev.niches.filter(n => n !== niche)
        : [...prev.niches, niche]
    }));
  };

  // Profile photo upload
  const onDropProfile = useCallback(async (acceptedFiles) => {
    const file = acceptedFiles[0];
    if (!file) return;

    setUploading(true);
    try {
      const response = await uploadAPI.uploadFile(file);
      updateField('profilePhotoUrl', response.data.url);
      toast.success("Looking good! 📸");
    } catch (error) {
      toast.error("Upload failed. Try again?");
    } finally {
      setUploading(false);
    }
  }, []);

  const { getRootProps: getProfileRootProps, getInputProps: getProfileInputProps } = useDropzone({
    onDrop: onDropProfile,
    accept: { 'image/*': ['.jpeg', '.jpg', '.png', '.webp'] },
    maxFiles: 1
  });

  // Media gallery upload
  const onDropMedia = useCallback(async (acceptedFiles) => {
    setUploading(true);
    try {
      const uploadPromises = acceptedFiles.map(file => uploadAPI.uploadFile(file));
      const responses = await Promise.all(uploadPromises);
      
      const newMedia = responses.map(res => ({
        id: Math.random().toString(36).substr(2, 9),
        type: res.data.type,
        url: res.data.url,
        thumbnailUrl: res.data.thumbnailUrl
      }));

      setFormData(prev => ({
        ...prev,
        mediaGallery: [...prev.mediaGallery, ...newMedia]
      }));
      toast.success(`${acceptedFiles.length} files uploaded! ✨`);
    } catch (error) {
      toast.error("Some uploads failed");
    } finally {
      setUploading(false);
    }
  }, []);

  const { getRootProps: getMediaRootProps, getInputProps: getMediaInputProps } = useDropzone({
    onDrop: onDropMedia,
    accept: { 
      'image/*': ['.jpeg', '.jpg', '.png', '.webp'],
      'video/*': ['.mp4', '.mov', '.webm']
    },
    maxFiles: 10
  });

  const removeMedia = (id) => {
    setFormData(prev => ({
      ...prev,
      mediaGallery: prev.mediaGallery.filter(m => m.id !== id)
    }));
  };

  const handleSubmit = async () => {
    if (!formData.name) {
      toast.error("Name is required!");
      return;
    }

    setLoading(true);
    try {
      const profileData = {
        ...formData,
        followersCount: parseInt(formData.followersCount) || 0,
        rates: {
          reelPrice: parseFloat(formData.rates.reelPrice) || 0,
          storyPrice: parseFloat(formData.rates.storyPrice) || 0,
          postPrice: parseFloat(formData.rates.postPrice) || 0,
          bundlePrice: parseFloat(formData.rates.bundlePrice) || 0
        }
      };

      await creatorAPI.createProfile(profileData);
      updateUser({ hasCompletedOnboarding: true });
      toast.success("Profile created – you look extra juicy now! 🍊");
      navigate('/dashboard/creator');
    } catch (error) {
      toast.error(error.response?.data?.detail || "Failed to create profile");
    } finally {
      setLoading(false);
    }
  };

  const canProceed = () => {
    switch (step) {
      case 1: return formData.name && formData.bio;
      case 2: return true;
      case 3: return true;
      case 4: return true;
      case 5: return true;
      default: return false;
    }
  };

  const renderStep = () => {
    switch (step) {
      case 1:
        return (
          <motion.div
            initial={{ opacity: 0, x: 20 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: -20 }}
            className="space-y-6"
          >
            <div className="text-center mb-8">
              <span className="text-5xl mb-4 block">✨</span>
              <h2 className="font-heading text-2xl font-bold mb-2">Let's make your Orange profile irresistible</h2>
              <p className="text-muted-foreground">Tell brands why your content hits different 💅</p>
            </div>

            <div className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="name">Your Name *</Label>
                <Input
                  id="name"
                  placeholder="What should brands call you?"
                  value={formData.name}
                  onChange={(e) => updateField('name', e.target.value)}
                  className="input-orange"
                  data-testid="creator-name-input"
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="bio">Bio *</Label>
                <Textarea
                  id="bio"
                  placeholder="Tell your story in a few lines... What makes you, you?"
                  value={formData.bio}
                  onChange={(e) => updateField('bio', e.target.value)}
                  className="input-orange min-h-[120px]"
                  data-testid="creator-bio-input"
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="location">Location</Label>
                <div className="relative">
                  <MapPin className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
                  <Input
                    id="location"
                    placeholder="Mumbai, Delhi, Bangalore..."
                    value={formData.location}
                    onChange={(e) => updateField('location', e.target.value)}
                    className="input-orange pl-10"
                    data-testid="creator-location-input"
                  />
                </div>
              </div>
            </div>
          </motion.div>
        );

      case 2:
        return (
          <motion.div
            initial={{ opacity: 0, x: 20 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: -20 }}
            className="space-y-6"
          >
            <div className="text-center mb-8">
              <span className="text-5xl mb-4 block">📱</span>
              <h2 className="font-heading text-2xl font-bold mb-2">Your Social Presence</h2>
              <p className="text-muted-foreground">Connect your Instagram & show off those followers</p>
            </div>

            <div className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="instagram">Instagram Handle</Label>
                <div className="relative">
                  <Instagram className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
                  <Input
                    id="instagram"
                    placeholder="@yourusername"
                    value={formData.instagramHandle}
                    onChange={(e) => {
                      const handle = e.target.value;
                      updateField('instagramHandle', handle);
                      updateField('instagramUrl', handle ? `https://instagram.com/${handle.replace('@', '')}` : '');
                    }}
                    className="input-orange pl-10"
                    data-testid="creator-instagram-input"
                  />
                </div>
              </div>

              <div className="space-y-2">
                <Label htmlFor="followers">Followers Count</Label>
                <div className="relative">
                  <Users className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
                  <Input
                    id="followers"
                    type="number"
                    placeholder="50000"
                    value={formData.followersCount}
                    onChange={(e) => updateField('followersCount', e.target.value)}
                    className="input-orange pl-10"
                    data-testid="creator-followers-input"
                  />
                </div>
              </div>

              <div className="space-y-3">
                <Label>Your Niches (select all that apply)</Label>
                <div className="flex flex-wrap gap-2">
                  {NICHES.map(niche => (
                    <Badge
                      key={niche}
                      variant={formData.niches.includes(niche) ? "default" : "outline"}
                      className={`cursor-pointer transition-all ${
                        formData.niches.includes(niche) 
                          ? 'bg-primary text-white' 
                          : 'hover:bg-primary/10'
                      }`}
                      onClick={() => toggleNiche(niche)}
                      data-testid={`niche-${niche.toLowerCase()}`}
                    >
                      {niche}
                    </Badge>
                  ))}
                </div>
              </div>
            </div>
          </motion.div>
        );

      case 3:
        return (
          <motion.div
            initial={{ opacity: 0, x: 20 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: -20 }}
            className="space-y-6"
          >
            <div className="text-center mb-8">
              <span className="text-5xl mb-4 block">💰</span>
              <h2 className="font-heading text-2xl font-bold mb-2">Set Your Rates</h2>
              <p className="text-muted-foreground">Know your worth, king/queen 👑</p>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="reelPrice">Reel Price (₹)</Label>
                <div className="relative">
                  <DollarSign className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
                  <Input
                    id="reelPrice"
                    type="number"
                    placeholder="10000"
                    value={formData.rates.reelPrice}
                    onChange={(e) => updateRates('reelPrice', e.target.value)}
                    className="input-orange pl-10"
                    data-testid="rate-reel-input"
                  />
                </div>
              </div>

              <div className="space-y-2">
                <Label htmlFor="storyPrice">Story Price (₹)</Label>
                <div className="relative">
                  <DollarSign className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
                  <Input
                    id="storyPrice"
                    type="number"
                    placeholder="3000"
                    value={formData.rates.storyPrice}
                    onChange={(e) => updateRates('storyPrice', e.target.value)}
                    className="input-orange pl-10"
                    data-testid="rate-story-input"
                  />
                </div>
              </div>

              <div className="space-y-2">
                <Label htmlFor="postPrice">Post Price (₹)</Label>
                <div className="relative">
                  <DollarSign className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
                  <Input
                    id="postPrice"
                    type="number"
                    placeholder="8000"
                    value={formData.rates.postPrice}
                    onChange={(e) => updateRates('postPrice', e.target.value)}
                    className="input-orange pl-10"
                    data-testid="rate-post-input"
                  />
                </div>
              </div>

              <div className="space-y-2">
                <Label htmlFor="bundlePrice">Bundle Price (₹)</Label>
                <div className="relative">
                  <DollarSign className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
                  <Input
                    id="bundlePrice"
                    type="number"
                    placeholder="20000"
                    value={formData.rates.bundlePrice}
                    onChange={(e) => updateRates('bundlePrice', e.target.value)}
                    className="input-orange pl-10"
                    data-testid="rate-bundle-input"
                  />
                </div>
              </div>
            </div>

            <div className="flex items-center justify-between p-4 bg-accent/20 rounded-2xl">
              <div>
                <p className="font-semibold">Open to Barter? 🤝</p>
                <p className="text-sm text-muted-foreground">Accept products instead of payment</p>
              </div>
              <Switch
                checked={formData.isOpenToBarter}
                onCheckedChange={(checked) => updateField('isOpenToBarter', checked)}
                data-testid="barter-switch"
              />
            </div>
          </motion.div>
        );

      case 4:
        return (
          <motion.div
            initial={{ opacity: 0, x: 20 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: -20 }}
            className="space-y-6"
          >
            <div className="text-center mb-8">
              <span className="text-5xl mb-4 block">📸</span>
              <h2 className="font-heading text-2xl font-bold mb-2">Profile Photo</h2>
              <p className="text-muted-foreground">First impressions matter – make it count!</p>
            </div>

            <div
              {...getProfileRootProps()}
              className={`border-2 border-dashed rounded-3xl p-12 text-center cursor-pointer transition-all ${
                uploading ? 'border-primary bg-primary/5' : 'border-orange-200 hover:border-primary hover:bg-primary/5'
              }`}
              data-testid="profile-photo-dropzone"
            >
              <input {...getProfileInputProps()} />
              {formData.profilePhotoUrl ? (
                <div className="relative inline-block">
                  <img
                    src={formData.profilePhotoUrl}
                    alt="Profile"
                    className="w-32 h-32 rounded-full object-cover mx-auto border-4 border-primary"
                  />
                  <div className="absolute -bottom-2 -right-2 w-8 h-8 bg-accent rounded-full flex items-center justify-center">
                    <Check className="w-5 h-5 text-accent-foreground" />
                  </div>
                </div>
              ) : uploading ? (
                <Loader2 className="w-12 h-12 mx-auto text-primary animate-spin" />
              ) : (
                <>
                  <Upload className="w-12 h-12 mx-auto text-muted-foreground mb-4" />
                  <p className="font-medium">Drop your photo here</p>
                  <p className="text-sm text-muted-foreground">or click to browse</p>
                </>
              )}
            </div>
          </motion.div>
        );

      case 5:
        return (
          <motion.div
            initial={{ opacity: 0, x: 20 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: -20 }}
            className="space-y-6"
          >
            <div className="text-center mb-8">
              <span className="text-5xl mb-4 block">🖼️</span>
              <h2 className="font-heading text-2xl font-bold mb-2">Media Gallery</h2>
              <p className="text-muted-foreground">Show off your best work!</p>
            </div>

            <div
              {...getMediaRootProps()}
              className={`border-2 border-dashed rounded-3xl p-8 text-center cursor-pointer transition-all ${
                uploading ? 'border-primary bg-primary/5' : 'border-orange-200 hover:border-primary hover:bg-primary/5'
              }`}
              data-testid="media-gallery-dropzone"
            >
              <input {...getMediaInputProps()} />
              {uploading ? (
                <div className="flex items-center justify-center gap-3">
                  <Loader2 className="w-6 h-6 text-primary animate-spin" />
                  <span>Uploading...</span>
                </div>
              ) : (
                <>
                  <ImageIcon className="w-10 h-10 mx-auto text-muted-foreground mb-3" />
                  <p className="font-medium">Drop images or videos here</p>
                  <p className="text-sm text-muted-foreground">Up to 10 files</p>
                </>
              )}
            </div>

            {formData.mediaGallery.length > 0 && (
              <div className="grid grid-cols-3 gap-3">
                {formData.mediaGallery.map(media => (
                  <div key={media.id} className="relative group aspect-square rounded-2xl overflow-hidden">
                    {media.type === 'video' ? (
                      <video src={media.url} className="w-full h-full object-cover" />
                    ) : (
                      <img src={media.thumbnailUrl || media.url} alt="" className="w-full h-full object-cover" />
                    )}
                    <button
                      onClick={() => removeMedia(media.id)}
                      className="absolute top-2 right-2 w-8 h-8 bg-black/50 rounded-full flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity"
                    >
                      <X className="w-4 h-4 text-white" />
                    </button>
                    {media.type === 'video' && (
                      <div className="absolute bottom-2 left-2 bg-black/50 px-2 py-1 rounded text-xs text-white">
                        Video
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}
          </motion.div>
        );

      default:
        return null;
    }
  };

  return (
    <div className="min-h-screen gradient-hero py-12 px-6">
      <div className="max-w-lg mx-auto">
        {/* Progress */}
        <div className="mb-8">
          <div className="flex items-center justify-between mb-3">
            <span className="text-sm font-medium text-muted-foreground">Step {step} of {totalSteps}</span>
            <span className="text-sm font-medium text-primary">{Math.round(progress)}%</span>
          </div>
          <Progress value={progress} className="h-2" />
        </div>

        {/* Card */}
        <div className="card-orange p-8">
          <AnimatePresence mode="wait">
            {renderStep()}
          </AnimatePresence>

          {/* Navigation */}
          <div className="flex items-center justify-between mt-8 pt-6 border-t border-orange-100">
            {step > 1 ? (
              <Button
                variant="ghost"
                onClick={() => setStep(step - 1)}
                className="rounded-full"
                data-testid="prev-step-btn"
              >
                <ArrowLeft className="w-4 h-4 mr-2" />
                Back
              </Button>
            ) : (
              <div />
            )}

            {step < totalSteps ? (
              <Button
                onClick={() => setStep(step + 1)}
                disabled={!canProceed()}
                className="btn-primary"
                data-testid="next-step-btn"
              >
                Continue
                <ArrowRight className="w-4 h-4 ml-2" />
              </Button>
            ) : (
              <Button
                onClick={handleSubmit}
                disabled={loading}
                className="btn-primary"
                data-testid="complete-onboarding-btn"
              >
                {loading ? (
                  <>
                    <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                    Creating...
                  </>
                ) : (
                  <>
                    Complete Profile 🍊
                    <Check className="w-4 h-4 ml-2" />
                  </>
                )}
              </Button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default CreatorOnboarding;
