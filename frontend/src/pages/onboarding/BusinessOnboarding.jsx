import { useState, useCallback, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import { useDropzone } from 'react-dropzone';
import { 
  ArrowLeft, ArrowRight, Check, Loader2, Upload, X, Instagram, Globe,
  MapPin, Building2, Image as ImageIcon, Plus, Trash2, Briefcase
} from 'lucide-react';
import { Button } from '../../components/ui/button';
import { Input } from '../../components/ui/input';
import { Label } from '../../components/ui/label';
import { Textarea } from '../../components/ui/textarea';
import { Progress } from '../../components/ui/progress';
import { Badge } from '../../components/ui/badge';
import { businessAPI, uploadAPI, instagramAPI, getErrorMessage } from '../../lib/api';
import { useAuth } from '../../lib/auth';
import { toast } from 'sonner';

const CATEGORIES = [
  'Fashion', 'Beauty', 'Tech', 'Food & Beverage', 'Health & Fitness',
  'Travel', 'Entertainment', 'Education', 'Finance', 'Home & Living',
  'Sports', 'Automotive', 'Gaming', 'E-commerce', 'Startup', 'Agency'
];

const NICHES = [
  'Fashion', 'Beauty', 'Tech', 'Food', 'Fitness', 'Travel', 'Lifestyle',
  'Gaming', 'Entertainment', 'Education', 'Finance', 'Parenting'
];

const OBJECTIVES = ['More walk-ins', 'Launch something new', 'Brand awareness', 'Online orders', 'Bookings and enquiries', 'Grow followers'];
const BUDGETS = [5000, 10000, 15000, 25000, 50000];
const VOICES = ['Warm', 'Playful', 'Premium', 'Bold', 'Minimal', 'Youthful', 'Traditional'];

const ChoiceChip = ({ selected, onClick, children }) => (
  <button type="button" onClick={onClick} aria-pressed={selected}
    className={`rounded-full px-3.5 py-1.5 text-sm transition-colors ${selected ? 'bg-ink text-white' : 'bg-white text-ink ring-1 ring-border hover:bg-stone'}`}>
    {children}
  </button>
);

const BusinessOnboarding = () => {
  const navigate = useNavigate();
  const { updateUser } = useAuth();
  const [step, setStep] = useState(1);
  const [loading, setLoading] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [verifyingInstagram, setVerifyingInstagram] = useState(false);
  const [instagramVerified, setInstagramVerified] = useState(false);

  const [formData, setFormData] = useState({
    brandName: '',
    category: '',
    bio: '',
    location: '',
    websiteUrl: '',
    instagramHandle: '',
    instagramUrl: '',
    profilePhotoUrl: '',
    mediaGallery: [],
    budgetRange: '',
    preferredNiches: [],
    isOpenToBarter: false,
    pastCollaborations: [],
    targetAudience: '',
    objectives: [],
    monthlyBudget: '',
    brandVoice: [],
    products: ''
  });
  const [isEditing, setIsEditing] = useState(false);

  const totalSteps = 5;
  const progress = (step / totalSteps) * 100;

  const toggleList = (field, value) => setFormData((prev) => ({ ...prev, [field]: prev[field].includes(value) ? prev[field].filter((x) => x !== value) : [...prev[field], value] }));

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

  // Toggle preferred niche
  const toggleNiche = (niche) => {
    setFormData(prev => ({
      ...prev,
      preferredNiches: prev.preferredNiches.includes(niche)
        ? prev.preferredNiches.filter(n => n !== niche)
        : [...prev.preferredNiches, niche]
    }));
  };

  // Past Collaborations helpers
  const addPastCollab = () => {
    setFormData(prev => ({
      ...prev,
      pastCollaborations: [
        ...prev.pastCollaborations,
        { campaignName: '', creatorNiche: '', platform: 'Instagram', description: '', mediaUrl: '', link: '' }
      ]
    }));
  };

  const updatePastCollab = (index, field, value) => {
    setFormData(prev => ({
      ...prev,
      pastCollaborations: prev.pastCollaborations.map((collab, i) =>
        i === index ? { ...collab, [field]: value } : collab
      )
    }));
  };

  const removePastCollab = (index) => {
    setFormData(prev => ({
      ...prev,
      pastCollaborations: prev.pastCollaborations.filter((_, i) => i !== index)
    }));
  };

  // Editing an existing profile: start from what is saved instead of a blank form.
  useEffect(() => {
    businessAPI.getProfile().then(({ data }) => {
      setIsEditing(true);
      setFormData((prev) => ({
        ...prev,
        brandName: data.brandName || '',
        category: data.industry || '',
        bio: data.bio || '',
        location: data.location || '',
        websiteUrl: data.websiteUrl || '',
        profilePhotoUrl: data.profilePhotoUrl || '',
        budgetRange: data.budgetRange || '',
        preferredNiches: data.preferredNiches || [],
        isOpenToBarter: !!data.barterEnabled,
        pastCollaborations: data.pastCollaborations || [],
        targetAudience: data.targetAudience || '',
        objectives: data.objectives || [],
        monthlyBudget: data.monthlyBudget ? String(data.monthlyBudget) : '',
        brandVoice: data.brandVoice || [],
        products: data.products || '',
      }));
    }).catch(() => {});
  }, []);

  useEffect(() => {
    instagramAPI.status().then(({ data }) => {
      if (!data.connected) return;
      updateField('instagramHandle', data.instagramUsername ? `@${data.instagramUsername.replace('@', '')}` : '');
      updateField('instagramUrl', data.instagramUsername ? `https://instagram.com/${data.instagramUsername.replace('@', '')}` : '');
      setInstagramVerified(true);
    }).catch(() => {});
  }, []);

  const connectInstagram = async () => {
    setVerifyingInstagram(true);
    try {
      const { data } = await instagramAPI.connect();
      window.location.assign(data.authorizationUrl);
    } catch (error) {
      toast.error(getErrorMessage(error, 'Instagram connection is not configured yet.'));
      setVerifyingInstagram(false);
    }
  };

  const handleSubmit = async () => {
    if (!formData.brandName) {
      toast.error("Brand name is required!");
      return;
    }

    setLoading(true);
    try {
      const profileData = {
        brandName: formData.brandName,
        industry: formData.category,
        bio: formData.bio,
        location: formData.location,
        budgetRange: formData.budgetRange,
        preferredNiches: formData.preferredNiches,
        isOpenToBarter: formData.isOpenToBarter,
        profilePhotoUrl: formData.profilePhotoUrl,
        pastCollaborations: formData.pastCollaborations.filter(c => c.campaignName),
        targetAudience: formData.targetAudience,
        objectives: formData.objectives,
        monthlyBudget: parseFloat(formData.monthlyBudget) || null,
        brandVoice: formData.brandVoice,
        products: formData.products,
        websiteUrl: formData.websiteUrl
      };
      await businessAPI.createProfile(profileData);
      updateUser({ hasCompletedOnboarding: true });
      toast.success(isEditing ? "Profile updated" : "Your brand profile is ready");
      navigate('/dashboard/business');
    } catch (error) {
      toast.error(getErrorMessage(error, "Failed to create profile"));
    } finally {
      setLoading(false);
    }
  };

  const canProceed = () => {
    switch (step) {
      case 1: return formData.brandName && formData.category;
      case 2: return formData.objectives.length > 0;
      case 3: return true; // Instagram can be connected later
      case 4: return true; // Past collabs optional
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
            <div className="mb-6">
              <h2 className="display text-3xl mb-2">Tell us about your business</h2>
              <p className="text-muted-foreground">A few basics so creators know who they're working with.</p>
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
          <motion.div initial={{ opacity: 0, x: 20 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0, x: -20 }} className="space-y-6">
            <div className="mb-6">
              <p className="eyebrow mb-2">Your goals</p>
              <h2 className="display text-3xl">What should Orange help you achieve?</h2>
              <p className="mt-2 text-muted-foreground">This is what the Growth Assistant plans around. You can change it any time.</p>
            </div>
            <div className="space-y-2">
              <Label>Goals</Label>
              <div className="flex flex-wrap gap-2">
                {OBJECTIVES.map((o) => (
                  <ChoiceChip key={o} selected={formData.objectives.includes(o)} onClick={() => toggleList('objectives', o)}>{o}</ChoiceChip>
                ))}
              </div>
            </div>
            <div className="space-y-2">
              <Label htmlFor="audience">Who are your customers?</Label>
              <Textarea id="audience" value={formData.targetAudience} onChange={(e) => updateField('targetAudience', e.target.value)} placeholder="College students and young professionals within 3 km, mostly 18 to 28" />
            </div>
            <div className="space-y-2">
              <Label htmlFor="products">What do you sell?</Label>
              <Input id="products" value={formData.products} onChange={(e) => updateField('products', e.target.value)} placeholder="Specialty coffee, cold brew, all-day breakfast" />
            </div>
            <div className="space-y-2">
              <Label>Monthly marketing budget</Label>
              <div className="flex flex-wrap gap-2">
                {BUDGETS.map((b) => (
                  <ChoiceChip key={b} selected={formData.monthlyBudget === String(b)} onClick={() => updateField('monthlyBudget', String(b))}>₹{b.toLocaleString('en-IN')}</ChoiceChip>
                ))}
                <Input type="number" inputMode="numeric" className="w-36" placeholder="Other ₹" value={BUDGETS.map(String).includes(formData.monthlyBudget) ? '' : formData.monthlyBudget} onChange={(e) => updateField('monthlyBudget', e.target.value)} />
              </div>
            </div>
            <div className="space-y-2">
              <Label>Brand personality</Label>
              <div className="flex flex-wrap gap-2">
                {VOICES.map((v) => (
                  <ChoiceChip key={v} selected={formData.brandVoice.includes(v)} onClick={() => toggleList('brandVoice', v)}>{v}</ChoiceChip>
                ))}
              </div>
            </div>
            <div className="space-y-2">
              <Label htmlFor="website">Website <span className="font-normal text-muted-foreground">(optional)</span></Label>
              <Input id="website" value={formData.websiteUrl} onChange={(e) => updateField('websiteUrl', e.target.value)} placeholder="https://" />
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
            <div className="mb-6">
              <h2 className="display text-3xl mb-2">Verify Your Instagram</h2>
              <p className="text-muted-foreground">Connect your brand's Instagram to get verified</p>
            </div>

            <div className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="instagram">Instagram account</Label>
                <p className="text-xs text-muted-foreground">Optional for now. Verified brands get more replies from creators, and you can connect later from your profile.</p>
                <div className="relative">
                  <Instagram className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
                  <Input
                    id="instagram"
                    placeholder="Connect your Instagram account"
                    value={formData.instagramHandle}
                    className="input-orange pl-10"
                    data-testid="business-instagram-input"
                    disabled
                  />
                </div>
              </div>

              {!instagramVerified ? (
                <Button
                  onClick={connectInstagram}
                  disabled={verifyingInstagram}
                  className="w-full btn-primary"
                  data-testid="verify-instagram-btn"
                >
                  {verifyingInstagram ? (
                    <><Loader2 className="w-4 h-4 mr-2 animate-spin" /> Connecting...</>
                  ) : (
                    <><Instagram className="w-4 h-4 mr-2" /> Connect Instagram</>
                  )}
                </Button>
              ) : (
                <div className="bg-green-50 border border-green-200 rounded-2xl p-4">
                  <div className="flex items-center gap-3">
                    <div className="w-10 h-10 bg-green-500 rounded-full flex items-center justify-center">
                      <Check className="w-5 h-5 text-white" />
                    </div>
                    <div>
                      <p className="font-semibold text-green-800">Instagram Verified! ✓</p>
                      <p className="text-sm text-green-600">Your brand is now verified</p>
                    </div>
                  </div>
                </div>
              )}

              <div className="bg-muted/50 rounded-xl p-4">
                <p className="text-xs text-muted-foreground">
                  💡 You’ll approve Orange in Instagram, then return here with your connected account.
                </p>
              </div>

              <div className="space-y-2">
                <Label htmlFor="website">Website URL (Optional)</Label>
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
            <div className="mb-6">
              <h2 className="display text-3xl mb-2">Past Collaborations</h2>
              <p className="text-muted-foreground">Share your influencer marketing history (optional)</p>
            </div>

            <div className="space-y-4">
              {formData.pastCollaborations.map((collab, index) => (
                <div key={index} className="card-orange p-4 space-y-3">
                  <div className="flex items-center justify-between">
                    <Badge variant="secondary">Collab #{index + 1}</Badge>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => removePastCollab(index)}
                      className="text-red-500 hover:text-red-700"
                    >
                      <Trash2 className="w-4 h-4" />
                    </Button>
                  </div>
                  
                  <Input
                    placeholder="Campaign Name (e.g., Summer Launch 2024)"
                    value={collab.campaignName}
                    onChange={(e) => updatePastCollab(index, 'campaignName', e.target.value)}
                    className="input-orange"
                  />
                  
                  <div className="grid grid-cols-2 gap-3">
                    <select
                      value={collab.creatorNiche}
                      onChange={(e) => updatePastCollab(index, 'creatorNiche', e.target.value)}
                      className="input-orange rounded-xl px-3 py-2"
                    >
                      <option value="">Creator Niche</option>
                      {NICHES.map(niche => (
                        <option key={niche} value={niche}>{niche}</option>
                      ))}
                    </select>
                    
                    <select
                      value={collab.platform}
                      onChange={(e) => updatePastCollab(index, 'platform', e.target.value)}
                      className="input-orange rounded-xl px-3 py-2"
                    >
                      <option value="Instagram">Instagram</option>
                      <option value="YouTube">YouTube</option>
                      <option value="TikTok">TikTok</option>
                      <option value="Twitter">Twitter</option>
                    </select>
                  </div>
                  
                  <Input
                    placeholder="Link to campaign (optional)"
                    value={collab.link}
                    onChange={(e) => updatePastCollab(index, 'link', e.target.value)}
                    className="input-orange"
                  />
                </div>
              ))}
              
              <Button
                type="button"
                variant="outline"
                onClick={addPastCollab}
                className="w-full rounded-xl border-dashed"
              >
                <Plus className="w-4 h-4 mr-2" />
                Add Past Collaboration
              </Button>
              
              {formData.pastCollaborations.length === 0 && (
                <div className="text-center py-6 text-muted-foreground">
                  <Briefcase className="w-12 h-12 mx-auto mb-3 opacity-30" />
                  <p>No past collaborations added yet</p>
                  <p className="text-sm">This helps creators trust your brand</p>
                </div>
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
            <div className="mb-6">
              <h2 className="display text-3xl mb-2">Brand Visuals</h2>
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
    <div className="min-h-screen gradient-hero py-10 px-4 sm:px-6">
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
        <div className="surface p-6 sm:p-8 shadow-card">
          <AnimatePresence mode="wait">
            {renderStep()}
          </AnimatePresence>

          {/* Navigation */}
          <div className="flex items-center justify-between mt-8 pt-6 border-t border-border">
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
                    Finish setup
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
