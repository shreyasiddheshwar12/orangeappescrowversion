import { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { motion } from 'framer-motion';
import { Eye, EyeOff, ArrowLeft, Loader2 } from 'lucide-react';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { useAuth } from '../lib/auth';
import { toast } from 'sonner';

const Login = () => {
  const navigate = useNavigate();
  const { login } = useAuth();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);

    try {
      const user = await login(email, password);
      toast.success("Welcome back! 🍊");
      
      // Redirect based on role and onboarding status
      if (!user.hasCompletedOnboarding) {
        navigate(user.role === 'creator' ? '/onboarding/creator' : '/onboarding/business');
      } else {
        navigate(user.role === 'creator' ? '/dashboard/creator' : '/dashboard/business');
      }
    } catch (error) {
      toast.error(error.response?.data?.detail || "Invalid email or password");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen gradient-hero flex items-center justify-center p-6">
      {/* Decorative blobs */}
      <div className="absolute top-20 left-10 w-72 h-72 bg-primary/10 rounded-full blur-3xl" />
      <div className="absolute bottom-20 right-10 w-96 h-96 bg-accent/10 rounded-full blur-3xl" />

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

        {/* Login Card */}
        <div className="card-orange p-8">
          <div className="text-center mb-8">
            <div className="w-16 h-16 bg-primary rounded-full flex items-center justify-center mx-auto mb-4">
              <span className="text-3xl">🍊</span>
            </div>
            <h1 className="font-heading text-3xl font-bold mb-2">Welcome back!</h1>
            <p className="text-muted-foreground">Log in to your Orange account</p>
          </div>

          <form onSubmit={handleSubmit} className="space-y-6">
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
                data-testid="login-email-input"
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="password">Password</Label>
              <div className="relative">
                <Input
                  id="password"
                  type={showPassword ? 'text' : 'password'}
                  placeholder="Enter your password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="input-orange pr-10"
                  required
                  data-testid="login-password-input"
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
              disabled={loading}
              data-testid="login-submit-btn"
            >
              {loading ? (
                <>
                  <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                  Logging in...
                </>
              ) : (
                'Log in 🍊'
              )}
            </Button>
          </form>

          <div className="mt-6 text-center">
            <p className="text-muted-foreground">
              Don't have an account?{' '}
              <Link to="/signup" className="text-primary font-semibold hover:underline" data-testid="signup-link">
                Sign up
              </Link>
            </p>
          </div>

          {/* Demo Accounts */}
          <div className="mt-8 pt-6 border-t border-orange-100">
            <p className="text-sm text-muted-foreground text-center mb-4">
              Try demo accounts:
            </p>
            <div className="grid grid-cols-2 gap-3 text-xs">
              <div className="bg-muted/50 p-3 rounded-xl">
                <p className="font-semibold text-foreground">Creator</p>
                <p className="text-muted-foreground">creator1@orange.com</p>
                <p className="text-muted-foreground">password123</p>
              </div>
              <div className="bg-muted/50 p-3 rounded-xl">
                <p className="font-semibold text-foreground">Brand</p>
                <p className="text-muted-foreground">business1@orange.com</p>
                <p className="text-muted-foreground">password123</p>
              </div>
            </div>
          </div>
        </div>
      </motion.div>
    </div>
  );
};

export default Login;
