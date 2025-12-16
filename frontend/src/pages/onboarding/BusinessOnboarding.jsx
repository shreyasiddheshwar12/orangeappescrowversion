import { useState, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import { useDropzone } from 'react-dropzone';
import { 
  ArrowLeft, ArrowRight, Check, Loader2, Upload, X, Instagram, Globe,
  MapPin, Building2, Image as ImageIcon
} from 'lucide-react';
import { Button } from '../../components/ui/button';
import { Input } from '../../components/ui/input';
import { Label } from '../../components/ui/label';
import { Textarea } from '../../components/ui/textarea';
import { Progress } from '../../components/ui/progress';
import { businessAPI, uploadAPI } from '../../lib/api';
import { useAuth } from '../../lib/auth';
import { toast } from 'sonner';

const CATEGORIES = [
  'Fashion', 'Beauty', 'Tech', 'Food & Beverage', 'Health & Fitness',
  'Travel', 'Entertainment', 'Education', 'Finance', 'Home & Living',
  'Sports', 'Automotive', 'Gaming', 'E-commerce', 'Startup', 'Agency'
];

const BusinessOnboarding = () => {
  const navigate = useNavigate();
  const { updateUser } = useAuth();
  const [step, setStep] = useState(1);
  const [loading, setLoading] = useState(false);
  const [uploading, setUploading] = useState(false);

  const [formData, setFormData] = useState({
    brandName: '',
    category: '',
    bio: '',
    location: '',
    websiteUrl: '',
    instagramHandle: '',
    instagramUrl: '',
    profilePhotoUrl: '',
    mediaGallery: []
  });

  const totalSteps = 3;
  const progress = (step / totalSteps) * 100;

  const updateField = (field, value) => {
    setFormData(prev => ({ ...prev, [field]: value }));
  };

  // Profile photo upload
  const onDropProfile = useCallback(async (acceptedFiles) => {
    const file = acceptedFiles[0];
    if (!file) return;

    setUploading(true);
    try {
      const response = await uploadAPI.uploadFile(file);
      updateField('profilePhotoUrl', response.data.url);
      toast.success("Brand logo uploaded! 🎨");
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
    if (!formData.brandName) {
      toast.error("Brand name is required!");
      return;
    }

    setLoading(true);
    try {
      await businessAPI.createProfile(formData);
      updateUser({ hasCompletedOnboarding: true });
      toast.success("Brand profile ready! Let's find your next favorite creator 🤝");
      navigate('/dashboard/business');
    } catch (error) {
      toast.error(error.response?.data?.detail || "Failed to create profile");
    } finally {
      setLoading(false);
    }
  };

  const canProceed = () => {
    switch (step) {
      case 1: return formData.brandName && formData.category;
      case 2: return true;
      case 3: return true;
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
              <span className="text-5xl mb-4 block">🤝</span>
              <h2 className="font-heading text-2xl font-bold mb-2">Let's find your next favorite creator collab</h2>
              <p className="text-muted-foreground">Good brands advertise. Great brands collaborate.</p>
            </div>

            <div className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="brandName">Brand Name *</Label>
                <div className="relative">
                  <Building2 className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
                  <Input
                    id="brandName"
                    placeholder="Your brand name"
                    value={formData.brandName}
                    onChange={(e) => updateField('brandName', e.target.value)}
                    className="input-orange pl-10"
                    data-testid="business-name-input"
                  />
                </div>
              </div>

              <div className="space-y-2">
                <Label>Category *</Label>
                <div className="grid grid-cols-3 gap-2">
                  {CATEGORIES.map(cat => (
                    <button
                      key={cat}
                      type="button"
                      onClick={() => updateField('category', cat)}
                      className={`p-3 rounded-xl text-sm font-medium transition-all ${
                        formData.category === cat
                          ? 'bg-primary text-white'
                          : 'bg-muted hover:bg-muted/80'
                      }`}
                      data-testid={`category-${cat.toLowerCase().replace(/\s+/g, '-')}`}
                    >
                      {cat}
                    </button>
                  ))}
                </div>
              </div>

              <div className="space-y-2">
                <Label htmlFor="bio">About Your Brand</Label>
                <Textarea
                  id="bio"
                  placeholder="What makes your brand special?"
                  value={formData.bio}
                  onChange={(e) => updateField('bio', e.target.value)}
                  className="input-orange min-h-[100px]"
                  data-testid="business-bio-input"
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
                    data-testid="business-location-input"
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
              <span className="text-5xl mb-4 block">🌐</span>
              <h2 className="font-heading text-2xl font-bold mb-2">Social & Web Presence</h2>
              <p className="text-muted-foreground">Help creators find and verify your brand</p>
            </div>

            <div className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="website">Website URL</Label>
                <div className="relative">
                  <Globe className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
                  <Input
                    id="website"
                    placeholder="https://yourbrand.com"
                    value={formData.websiteUrl}
                    onChange={(e) => updateField('websiteUrl', e.target.value)}
                    className="input-orange pl-10"
                    data-testid="business-website-input"
                  />
                </div>
              </div>

              <div className="space-y-2">
                <Label htmlFor="instagram">Instagram Handle</Label>
                <div className="relative">
                  <Instagram className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
                  <Input
                    id="instagram"
                    placeholder="@yourbrand"
                    value={formData.instagramHandle}
                    onChange={(e) => {
                      const handle = e.target.value;
                      updateField('instagramHandle', handle);
                      updateField('instagramUrl', handle ? `https://instagram.com/${handle.replace('@', '')}` : '');
                    }}
                    className="input-orange pl-10"
                    data-testid="business-instagram-input"
                  />
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
              <span className="text-5xl mb-4 block">📸</span>
              <h2 className="font-heading text-2xl font-bold mb-2">Brand Visuals</h2>
              <p className="text-muted-foreground">Upload your logo & brand images</p>
            </div>

            {/* Logo Upload */}
            <div className="space-y-3">
              <Label>Brand Logo</Label>
              <div
                {...getProfileRootProps()}
                className={`border-2 border-dashed rounded-3xl p-8 text-center cursor-pointer transition-all ${
                  uploading ? 'border-primary bg-primary/5' : 'border-orange-200 hover:border-primary hover:bg-primary/5'
                }`}
                data-testid="business-logo-dropzone"
              >
                <input {...getProfileInputProps()} />
                {formData.profilePhotoUrl ? (
                  <div className="relative inline-block">
                    <img
                      src={formData.profilePhotoUrl}
                      alt="Logo"
                      className="w-24 h-24 rounded-2xl object-cover mx-auto border-2 border-primary"
                    />
                    <div className="absolute -bottom-2 -right-2 w-6 h-6 bg-accent rounded-full flex items-center justify-center">
                      <Check className="w-4 h-4 text-accent-foreground" />
                    </div>
                  </div>
                ) : uploading ? (
                  <Loader2 className="w-10 h-10 mx-auto text-primary animate-spin" />
                ) : (
                  <>
                    <Upload className="w-10 h-10 mx-auto text-muted-foreground mb-3" />
                    <p className="font-medium">Upload brand logo</p>
                    <p className="text-sm text-muted-foreground">Click or drag to upload</p>
                  </>
                )}
              </div>
            </div>

            {/* Media Gallery */}
            <div className="space-y-3">
              <Label>Brand Media (Optional)</Label>
              <div
                {...getMediaRootProps()}
                className={`border-2 border-dashed rounded-3xl p-6 text-center cursor-pointer transition-all ${
                  uploading ? 'border-primary bg-primary/5' : 'border-orange-200 hover:border-primary hover:bg-primary/5'
                }`}
                data-testid="business-media-dropzone"
              >
                <input {...getMediaInputProps()} />
                {uploading ? (
                  <div className="flex items-center justify-center gap-3">
                    <Loader2 className="w-5 h-5 text-primary animate-spin" />
                    <span>Uploading...</span>
                  </div>
                ) : (
                  <>
                    <ImageIcon className="w-8 h-8 mx-auto text-muted-foreground mb-2" />
                    <p className="font-medium text-sm">Add product/campaign images</p>
                  </>
                )}
              </div>
            </div>

            {formData.mediaGallery.length > 0 && (
              <div className="grid grid-cols-4 gap-2">
                {formData.mediaGallery.map(media => (
                  <div key={media.id} className="relative group aspect-square rounded-xl overflow-hidden">
                    {media.type === 'video' ? (
                      <video src={media.url} className="w-full h-full object-cover" />
                    ) : (
                      <img src={media.thumbnailUrl || media.url} alt="" className="w-full h-full object-cover" />
                    )}
                    <button
                      onClick={() => removeMedia(media.id)}
                      className="absolute top-1 right-1 w-6 h-6 bg-black/50 rounded-full flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity"
                    >
                      <X className="w-3 h-3 text-white" />
                    </button>
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
                    Find Creators 🍊
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

export default BusinessOnboarding;
