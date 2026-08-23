import { useEffect } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { Loader2 } from 'lucide-react';
import { instagramAPI } from '../lib/api';
import { useAuth } from '../lib/auth';
import { toast } from 'sonner';

const InstagramCallback = () => {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const { user } = useAuth();

  useEffect(() => {
    const finish = async () => {
      if (searchParams.get('instagram') === 'error') {
        toast.error(searchParams.get('reason') || 'Instagram connection failed.');
        navigate(user?.role === 'creator' ? '/onboarding/creator' : '/onboarding/business', { replace: true });
        return;
      }

      try {
        const { data } = await instagramAPI.status();
        if (!data.connected) throw new Error('Instagram connection was not completed.');
        const username = data.instagramUsername ? `@${data.instagramUsername.replace('@', '')}` : 'Instagram';
        toast.success(`Connected ${username} to Orange!`);
      } catch (error) {
        toast.error(error.message || 'Instagram connection failed.');
      } finally {
        navigate(user?.role === 'creator' ? '/onboarding/creator' : '/onboarding/business', { replace: true });
      }
    };

    if (user) finish();
  }, [navigate, searchParams, user]);

  return (
    <div className="min-h-screen gradient-hero flex items-center justify-center">
      <div className="text-center">
        <Loader2 className="w-10 h-10 animate-spin text-primary mx-auto mb-4" />
        <p className="text-muted-foreground">Finishing your Instagram connection...</p>
      </div>
    </div>
  );
};

export default InstagramCallback;
