import { useNavigate, Link } from 'react-router-dom';
import { ArrowRight, Sparkles, ShieldCheck, Search, FileText, BarChart3, Star, Repeat, QrCode, Check, MessageSquare, Brain } from 'lucide-react';
import Logo, { LogoMark } from '../components/orange/Logo';
import { Button } from '../components/ui/button';
import { useAuth } from '../lib/auth';

const STEPS = [
  ['Tell Orange your goal', 'In your own words: "More college students at my café this month, ₹15,000 budget."'],
  ['Get a plan you approve', 'A strategy, a budget split and a shortlist of local creators, each with the reason they were picked.'],
  ['Orange runs the collaboration', 'Briefs, requests, protected payment, deliverables and approvals in one workspace.'],
  ['See what actually worked', 'Every creator gets a coupon code, link and QR. You see redemptions per creator, not vanity metrics.'],
];

const AGENTS = [
  [Brain, 'Business Intelligence', 'Understands your business, audience and past campaigns.'],
  [FileText, 'Marketing Planner', 'Turns a goal and a budget into a plan with clear trade-offs.'],
  [Search, 'Creator Matching', 'Ranks creators on niche, area, price, reliability and history.'],
  [MessageSquare, 'Campaign Assistant', 'Writes briefs and outreach, then sets up tracking.'],
  [BarChart3, 'Performance Analyst', 'Reports results from real redemptions and suggests the next move.'],
];

const Preview = () => (
  <div className="relative mx-auto w-full max-w-[560px]">
    <div className="absolute -inset-6 -z-10 rounded-[28px] bg-gradient-to-br from-orange-100 via-peach to-plum-50 opacity-70 blur-2xl" />
    <div className="surface overflow-hidden shadow-float">
      <div className="flex items-center gap-2 border-b border-border bg-[#FFFCF8] px-4 py-2.5">
        <span className="h-2.5 w-2.5 rounded-full bg-[#E9E2D9]" /><span className="h-2.5 w-2.5 rounded-full bg-[#E9E2D9]" /><span className="h-2.5 w-2.5 rounded-full bg-[#E9E2D9]" />
        <span className="ml-2 text-xs text-muted-foreground">Growth Assistant · example</span>
      </div>
      <div className="space-y-4 p-5">
        <div className="ml-auto max-w-[85%] rounded-lg rounded-tr-sm bg-ink px-3.5 py-2.5 text-sm text-white">
          I run a café in Baner. ₹15,000 budget. I want more college students visiting this month.
        </div>
        <ol className="space-y-2.5">
          {[
            ['Business Intelligence', 'Read your profile and menu', 'done'],
            ['Marketing Planner', 'Split budget: 3 reels, 6 stories, ₹1,500 reserve', 'done'],
            ['Creator Matching', 'Ranked 12 food creators within 5 km', 'running'],
            ['Campaign Assistant', 'Draft brief and coupon codes', 'approval'],
          ].map(([agent, task, state]) => (
            <li key={agent} className="flex items-start gap-3">
              <span className={`mt-1 flex h-4 w-4 shrink-0 items-center justify-center rounded-full ${state === 'done' ? 'bg-sage-400 text-white' : state === 'running' ? 'bg-plum' : 'ring-1 ring-orange-300'}`}>
                {state === 'done' && <Check className="h-3 w-3" />}
                {state === 'running' && <span className="h-1.5 w-1.5 animate-pulse-dot rounded-full bg-white" />}
              </span>
              <div className="min-w-0 flex-1">
                <p className="text-xs font-semibold text-plum">{agent}</p>
                <p className="text-sm text-ink">{task}</p>
              </div>
              {state === 'approval' && <span className="rounded-full bg-orange-50 px-2 py-0.5 text-[11px] font-medium text-orange-800 ring-1 ring-orange-200">Needs approval</span>}
            </li>
          ))}
        </ol>
        <div className="grid grid-cols-3 gap-2 border-t border-border pt-4">
          {[['Food creator', 'Baner', '92'], ['Café reels', 'Aundh', '88'], ['Student life', 'Balewadi', '81']].map(([n, a, s]) => (
            <div key={n} className="rounded-lg border border-border bg-white p-2.5">
              <div className="mb-2 h-10 rounded bg-gradient-to-br from-orange-100 to-peach" />
              <p className="truncate text-xs font-semibold">{n}</p>
              <p className="text-[11px] text-muted-foreground">{a} · <span className="num font-semibold text-ink">{s}% match</span></p>
            </div>
          ))}
        </div>
      </div>
    </div>
  </div>
);

const Landing = () => {
  const navigate = useNavigate();
  const { user } = useAuth();
  const dashboard = user ? (user.role === 'creator' ? '/dashboard/creator' : '/dashboard/business') : null;

  return (
    <div className="min-h-screen bg-background text-ink">
      <header className="sticky top-0 z-40 border-b border-transparent bg-background/80 backdrop-blur">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-4 py-4 sm:px-6">
          <Logo />
          <nav className="hidden items-center gap-7 text-sm text-ink-500 md:flex">
            <a href="#how" className="hover:text-ink">How it works</a>
            <a href="#businesses" className="hover:text-ink">For businesses</a>
            <a href="#creators" className="hover:text-ink">For creators</a>
            <a href="#trust" className="hover:text-ink">Orange Trust</a>
          </nav>
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
        </div>
      </header>

      {/* Hero */}
      <section className="gradient-hero">
        <div className="mx-auto grid max-w-6xl items-center gap-14 px-4 pb-20 pt-12 sm:px-6 lg:grid-cols-[1.05fr_1fr] lg:pt-20">
          <div className="animate-fade-in">
            <p className="mb-5 inline-flex items-center gap-2 rounded-full bg-white px-3 py-1 text-xs font-medium text-plum ring-1 ring-plum-100">
              <Sparkles className="h-3.5 w-3.5" />Your AI-powered growth partner
            </p>
            <h1 className="display text-[44px] leading-[1.02] sm:text-[60px] lg:text-[68px]">
              Good marketing.<br /><em className="italic text-orange-700">Without</em> the agency chaos.
            </h1>
            <p className="mt-6 max-w-lg text-lg text-ink-500">
              Tell Orange what you want to achieve. We'll find the right creators, manage your campaigns and help your business grow.
            </p>
            <div className="mt-8 flex flex-col gap-3 sm:flex-row">
              <Button size="lg" onClick={() => navigate('/signup?role=business')} data-testid="hero-business-btn">Grow my business<ArrowRight /></Button>
              <Button size="lg" variant="outline" onClick={() => navigate('/signup?role=creator')} data-testid="hero-creator-btn">I'm a creator</Button>
            </div>
            <p className="mt-5 text-sm text-muted-foreground">Built for cafés, salons, gyms and local brands in Pune, Mumbai and Bangalore.</p>
          </div>
          <Preview />
        </div>
      </section>

      {/* How it works */}
      <section id="how" className="border-t border-border">
        <div className="mx-auto max-w-6xl px-4 py-20 sm:px-6">
          <p className="eyebrow">How it works</p>
          <h2 className="display mt-3 max-w-2xl text-4xl">You say what you want. Orange does the running around.</h2>
          <ol className="mt-12 grid gap-px overflow-hidden rounded-xl border border-border bg-border md:grid-cols-4">
            {STEPS.map(([title, body], i) => (
              <li key={title} className="bg-background p-6">
                <span className="num font-display text-3xl text-orange-600">0{i + 1}</span>
                <p className="mt-4 font-semibold">{title}</p>
                <p className="mt-2 text-sm text-ink-500">{body}</p>
              </li>
            ))}
          </ol>
        </div>
      </section>

      {/* Agents */}
      <section className="bg-ink text-white">
        <div className="mx-auto max-w-6xl px-4 py-20 sm:px-6">
          <div className="grid gap-12 lg:grid-cols-[1fr_1.4fr]">
            <div>
              <p className="text-[11px] font-semibold uppercase tracking-[0.08em] text-orange-300">The Orange team</p>
              <h2 className="display mt-3 text-4xl">Five specialists. One plan. You stay in charge.</h2>
              <p className="mt-4 text-white/70">Each specialist does real work on your data and shows every step. Nothing is sent, booked or paid without your approval.</p>
            </div>
            <ul className="grid gap-3 sm:grid-cols-2">
              {AGENTS.map(([Icon, name, body]) => (
                <li key={name} className="rounded-xl border border-white/10 bg-white/[0.04] p-5">
                  <Icon className="h-5 w-5 text-orange-300" />
                  <p className="mt-3 font-semibold">{name}</p>
                  <p className="mt-1 text-sm text-white/65">{body}</p>
                </li>
              ))}
            </ul>
          </div>
        </div>
      </section>

      {/* Businesses / Creators */}
      <section className="mx-auto grid max-w-6xl gap-6 px-4 py-20 sm:px-6 lg:grid-cols-2">
        <div id="businesses" className="surface p-8">
          <p className="eyebrow">For businesses</p>
          <h3 className="display mt-3 text-3xl">An agency's work, at a café's budget.</h3>
          <ul className="mt-6 space-y-3 text-[15px]">
            {['Local creators ranked for your area and audience', 'Clear budget plans before you spend a rupee', 'Pay only when content is approved', 'Coupon and QR tracking per creator', 'Rebook creators who worked in one click'].map((t) => (
              <li key={t} className="flex gap-3"><Check className="mt-0.5 h-4 w-4 shrink-0 text-orange-600" />{t}</li>
            ))}
          </ul>
          <Button className="mt-8" onClick={() => navigate('/signup?role=business')}>Start as a business<ArrowRight /></Button>
        </div>
        <div id="creators" className="surface bg-gradient-to-br from-white to-plum-50 p-8">
          <p className="eyebrow">For creators</p>
          <h3 className="display mt-3 text-3xl">Your brand deals, finally organised.</h3>
          <ul className="mt-6 space-y-3 text-[15px]">
            {['Paid and barter offers from local brands', 'Payment secured before you start shooting', 'Briefs, revisions and approvals in one place', 'A reputation that follows you: TrustScore and reviews', 'Earnings and payouts you can actually track'].map((t) => (
              <li key={t} className="flex gap-3"><Check className="mt-0.5 h-4 w-4 shrink-0 text-plum" />{t}</li>
            ))}
          </ul>
          <Button className="mt-8" variant="plum" onClick={() => navigate('/signup?role=creator')}>Join as a creator<ArrowRight /></Button>
        </div>
      </section>

      {/* Trust */}
      <section id="trust" className="border-y border-border bg-[#FFFCF8]">
        <div className="mx-auto max-w-6xl px-4 py-20 sm:px-6">
          <div className="max-w-2xl">
            <p className="eyebrow">Orange Trust</p>
            <h2 className="display mt-3 text-4xl">Both sides protected, every step recorded.</h2>
          </div>
          <div className="mt-10 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            {[
              [ShieldCheck, 'Protected payments', 'The brand pays upfront through our payment partner. The creator is paid when the content is approved.'],
              [QrCode, 'Honest attribution', 'Unique codes, links and QR per creator. Results come from real redemptions.'],
              [Star, 'Two-sided reputation', 'Creators and businesses both earn a TrustScore from completed work, with the maths shown.'],
              [Repeat, 'Repeat what works', 'Your creator history, invoices and agreements stay in one place.'],
            ].map(([Icon, title, body]) => (
              <div key={title} className="surface p-5">
                <Icon className="h-5 w-5 text-orange-700" />
                <p className="mt-4 font-semibold">{title}</p>
                <p className="mt-1.5 text-sm text-ink-500">{body}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* CTA */}
      <section className="mx-auto max-w-6xl px-4 py-24 text-center sm:px-6">
        <LogoMark size={44} className="mx-auto" />
        <h2 className="display mx-auto mt-6 max-w-2xl text-4xl sm:text-5xl">Your next twenty customers might be three reels away.</h2>
        <div className="mt-8 flex flex-col justify-center gap-3 sm:flex-row">
          <Button size="lg" onClick={() => navigate('/signup?role=business')}>Grow my business<ArrowRight /></Button>
          <Button size="lg" variant="outline" onClick={() => navigate('/signup?role=creator')}>I'm a creator</Button>
        </div>
      </section>

      <footer className="border-t border-border">
        <div className="mx-auto flex max-w-6xl flex-col gap-6 px-4 py-10 text-sm text-ink-500 sm:flex-row sm:items-center sm:justify-between sm:px-6">
          <div className="flex items-center gap-3"><Logo /><span className="hidden sm:inline">Your AI-powered growth partner.</span></div>
          <div className="flex flex-wrap gap-6">
            <a href="#how" className="hover:text-ink">How it works</a>
            <a href="#trust" className="hover:text-ink">Orange Trust</a>
            <Link to="/login" className="hover:text-ink">Log in</Link>
            <Link to="/signup" className="hover:text-ink">Sign up</Link>
          </div>
          <p>© {new Date().getFullYear()} Orange</p>
        </div>
      </footer>
    </div>
  );
};

export default Landing;
