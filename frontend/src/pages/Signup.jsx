import { useState, useEffect } from 'react';
import { useNavigate, Link, useSearchParams } from 'react-router-dom';
import { motion } from 'framer-motion';
import { Eye, EyeOff, ArrowLeft, Loader2, Check } from 'lucide-react';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { useAuth } from '../lib/auth';
import { toast } from 'sonner';

const Signup = () => {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const { signup } = useAuth();
  
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [role, setRole] = useState(searchParams.get('role') || '');
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    const roleParam = searchParams.get('role');
    if (roleParam && ['creator', 'business'].includes(roleParam)) {
      setRole(roleParam);
    }
  }, [searchParams]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    if (!role) {
      toast.error("Please select your role");
      return;
    }

    if (password.length < 6) {
      toast.error("Password must be at least 6 characters");
      return;
    }

    setLoading(true);

    try {
      await signup(email, password, role);
      toast.success("Account created! Let's set up your profile ✨");
      navigate(role === 'creator' ? '/onboarding/creator' : '/onboarding/business');
    } catch (error) {
      toast.error(error.response?.data?.detail || "Failed to create account");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen gradient-hero flex items-center justify-center p-6">
      {/* Decorative blobs */}
      <div className="absolute top-20 right-10 w-72 h-72 bg-primary/10 rounded-full blur-3xl" />
      <div className="absolute bottom-20 left-10 w-96 h-96 bg-accent/10 rounded-full blur-3xl" />

      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }}
        className="relative z-10 w-full max-w-md"
      >
        {/* Back Button */}
        <Button
          variant="ghost"
          className="mb-6 rounded-full"
          onClick={() => navigate('/')}
          data-testid="back-btn"
        >
          <ArrowLeft className="w-4 h-4 mr-2" />
          Back to home
        </Button>

        {/* Signup Card */}
        <div className="card-orange p-8">
          <div className="text-center mb-8">
            <div className="w-16 h-16 bg-primary rounded-full flex items-center justify-center mx-auto mb-4">
              <span className="text-3xl">🍊</span>
            </div>
            <h1 className="font-heading text-3xl font-bold mb-2">Join Orange!</h1>
            <p className="text-muted-foreground">Create your account and start vibing</p>
          </div>

          <form onSubmit={handleSubmit} className="space-y-6">
            {/* Role Selection */}
            <div className="space-y-3">
              <Label>Who are you?</Label>
              <div className="grid grid-cols-2 gap-3">
                <button
                  type="button"
                  onClick={() => setRole('creator')}
                  className={`p-4 rounded-2xl border-2 transition-all text-left ${
                    role === 'creator' 
                      ? 'border-primary bg-primary/5' 
                      : 'border-orange-100 hover:border-orange-200'
                  }`}
                  data-testid="role-creator-btn"
                >
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-2xl">🎨</span>
                    {role === 'creator' && <Check className="w-5 h-5 text-primary" />}
                  </div>
                  <p className="font-semibold">Creator</p>
                  <p className="text-xs text-muted-foreground">I create content</p>
                </button>
                <button
                  type="button"
                  onClick={() => setRole('business')}
                  className={`p-4 rounded-2xl border-2 transition-all text-left ${
                    role === 'business' 
                      ? 'border-primary bg-primary/5' 
                      : 'border-orange-100 hover:border-orange-200'
                  }`}
                  data-testid="role-business-btn"
                >
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-2xl">💼</span>
                    {role === 'business' && <Check className="w-5 h-5 text-primary" />}
                  </div>
                  <p className="font-semibold">Brand</p>
                  <p className="text-xs text-muted-foreground">I need creators</p>
                </button>
              </div>
            </div>

            <div className="space-y-2">
              <Label htmlFor="email">Email</Label>
              <Input
                id="email"
                type="email"
                placeholder="you@example.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="input-orange"
                required
                data-testid="signup-email-input"
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="password">Password</Label>
              <div className="relative">
                <Input
                  id="password"
                  type={showPassword ? 'text' : 'password'}
                  placeholder="Min. 6 characters"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="input-orange pr-10"
                  required
                  data-testid="signup-password-input"
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
                >
                  {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                </button>
              </div>
            </div>

            <Button
              type="submit"
              className="btn-primary w-full"
              disabled={loading || !role}
              data-testid="signup-submit-btn"
            >
              {loading ? (
                <>
                  <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                  Creating account...
                </>
              ) : (
                'Create Account 🍊'
              )}
            </Button>
          </form>

          <div className="mt-6 text-center">
            <p className="text-muted-foreground">
              Already have an account?{' '}
              <Link to="/login" className="text-primary font-semibold hover:underline" data-testid="login-link">
                Log in
              </Link>
            </p>
          </div>
        </div>
      </motion.div>
    </div>
  );
};

export default Signup;
