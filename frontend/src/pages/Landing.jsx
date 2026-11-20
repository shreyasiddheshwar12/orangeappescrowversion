import { useNavigate, Link } from 'react-router-dom';
import { ArrowRight } from 'lucide-react';
import Logo from '../components/orange/Logo';
import { Button } from '../components/ui/button';
import { useAuth } from '../lib/auth';

const STEPS = [
  ['Tell us your goal', 'What you want and what you can spend.'],
  ['Pick your creators', 'We suggest local creators who fit.'],
  ['Pay when it is done', 'Your money is held until the content is approved.'],
];

const Landing = () => {
  const navigate = useNavigate();
  const { user } = useAuth();
  const dashboard = user ? (user.role === 'creator' ? '/dashboard/creator' : '/dashboard/business') : null;

  return (
    <div className="flex min-h-screen flex-col bg-background text-ink">
      <header className="mx-auto flex w-full max-w-5xl items-center justify-between px-4 py-5 sm:px-6">
        <Logo />
        <div className="flex items-center gap-2">
          {dashboard ? (
            <Button onClick={() => navigate(dashboard)}>Open workspace<ArrowRight /></Button>
          ) : (
            <>
              <Button variant="ghost" onClick={() => navigate('/login')} data-testid="login-btn">Log in</Button>
              <Button onClick={() => navigate('/signup?role=business')} data-testid="signup-btn">Get started</Button>
            </>
          )}
        </div>
      </header>

      <main className="flex-1">
        <section className="mx-auto max-w-3xl px-4 pb-20 pt-16 text-center sm:px-6 sm:pt-28">
          <h1 className="display text-[44px] leading-[1.05] sm:text-[64px]">
            Good marketing.<br /><em className="italic text-orange-700">Without</em> the agency chaos.
          </h1>
          <p className="mx-auto mt-6 max-w-md text-lg text-ink-500">
            Orange finds the right local creators for your business and handles the rest.
          </p>
          <div className="mt-9 flex flex-col justify-center gap-3 sm:flex-row">
            <Button size="lg" onClick={() => navigate('/signup?role=business')} data-testid="hero-business-btn">Grow my business<ArrowRight /></Button>
            <Button size="lg" variant="outline" onClick={() => navigate('/signup?role=creator')} data-testid="hero-creator-btn">I'm a creator</Button>
          </div>
        </section>

        <section className="mx-auto max-w-4xl px-4 pb-24 sm:px-6">
          <ol className="grid gap-4 sm:grid-cols-3">
            {STEPS.map(([title, body], i) => (
              <li key={title} className="surface p-6">
                <span className="num font-display text-2xl text-orange-600">{i + 1}</span>
                <p className="mt-3 font-semibold">{title}</p>
                <p className="mt-1 text-sm text-ink-500">{body}</p>
              </li>
            ))}
          </ol>
        </section>
      </main>

      <footer className="border-t border-border">
        <div className="mx-auto flex max-w-5xl items-center justify-between px-4 py-6 text-sm text-ink-500 sm:px-6">
          <p>© {new Date().getFullYear()} Orange</p>
          <div className="flex gap-5">
            <Link to="/login" className="hover:text-ink">Log in</Link>
            <Link to="/signup" className="hover:text-ink">Sign up</Link>
          </div>
        </div>
      </footer>
    </div>
  );
};

export default Landing;
