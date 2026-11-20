import { LogOut, ExternalLink } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import Logo from './Logo';
import { useAuth } from '../../lib/auth';
import { initials } from '../../lib/format';

/**
 * Workspace layout for both dashboards: sidebar on desktop, top bar plus a
 * scrollable tab row on mobile. `items` = [{ key, label, icon, badge }].
 */
const AppShell = ({ items, active, onSelect, displayName, subtitle, photoUrl, profileHref, children }) => {
  const navigate = useNavigate();
  const { logout } = useAuth();
  const signOut = () => { logout(); navigate('/'); };

  return (
    <div className="min-h-screen bg-background">
      {/* Desktop sidebar */}
      <aside className="fixed inset-y-0 left-0 z-30 hidden w-[248px] flex-col border-r border-border bg-[#FFFCF8] lg:flex">
        <div className="px-5 pt-6 pb-8"><Logo to="/" /></div>
        <nav className="flex-1 space-y-0.5 px-3" aria-label="Workspace">
          {items.map((item) => {
            const Icon = item.icon;
            const isActive = item.key === active;
            return (
              <button
                key={item.key}
                onClick={() => onSelect(item.key)}
                data-testid={`nav-${item.key}`}
                aria-current={isActive ? 'page' : undefined}
                className={`group flex w-full items-center gap-3 rounded-md px-3 py-2 text-left text-sm transition-colors ${
                  isActive ? 'bg-white text-ink shadow-card ring-1 ring-border font-semibold' : 'text-ink-500 hover:bg-stone hover:text-ink'
                }`}
              >
                <span className={`flex h-6 w-6 items-center justify-center rounded ${isActive ? 'text-orange-700' : 'text-ink-300 group-hover:text-ink-500'}`}>
                  <Icon className="h-[18px] w-[18px]" />
                </span>
                <span className="flex-1">{item.label}</span>
                {item.badge > 0 && (
                  <span className="num rounded-full bg-primary px-1.5 text-[11px] font-semibold leading-5 text-ink">{item.badge}</span>
                )}
              </button>
            );
          })}
        </nav>
        <div className="m-3 rounded-lg border border-border bg-white p-3">
          <div className="flex items-center gap-3">
            {photoUrl
              ? <img src={photoUrl} alt="" className="h-9 w-9 rounded-full object-cover" />
              : <div className="flex h-9 w-9 items-center justify-center rounded-full bg-peach text-sm font-semibold text-orange-800">{initials(displayName)}</div>}
            <div className="min-w-0 flex-1">
              <p className="truncate text-sm font-semibold text-ink">{displayName || 'Your workspace'}</p>
              <p className="truncate text-xs text-muted-foreground">{subtitle}</p>
            </div>
          </div>
          <div className="mt-3 flex gap-1">
            {profileHref && (
              <button onClick={() => navigate(profileHref)} className="flex flex-1 items-center justify-center gap-1.5 rounded-md py-1.5 text-xs font-medium text-ink-500 hover:bg-stone hover:text-ink" data-testid="view-public-profile-btn">
                <ExternalLink className="h-3.5 w-3.5" />Profile
              </button>
            )}
            <button onClick={signOut} className="flex flex-1 items-center justify-center gap-1.5 rounded-md py-1.5 text-xs font-medium text-ink-500 hover:bg-stone hover:text-ink" data-testid="logout-btn">
              <LogOut className="h-3.5 w-3.5" />Log out
            </button>
          </div>
        </div>
      </aside>

      {/* Mobile top bar */}
      <header className="sticky top-0 z-30 border-b border-border bg-background/90 backdrop-blur lg:hidden">
        <div className="flex items-center justify-between px-4 py-3">
          <Logo to="/" size={24} />
          <div className="flex items-center gap-1">
            {profileHref && (
              <button onClick={() => navigate(profileHref)} className="rounded-md p-2 text-ink-500 hover:bg-stone" aria-label="View profile"><ExternalLink className="h-4 w-4" /></button>
            )}
            <button onClick={signOut} className="rounded-md p-2 text-ink-500 hover:bg-stone" aria-label="Log out"><LogOut className="h-4 w-4" /></button>
          </div>
        </div>
        <nav className="scrollbar-hide flex gap-1 overflow-x-auto px-3 pb-2" aria-label="Workspace">
          {items.map((item) => (
            <button
              key={item.key}
              onClick={() => onSelect(item.key)}
              className={`shrink-0 rounded-full px-3 py-1.5 text-sm ${item.key === active ? 'bg-ink text-white' : 'text-ink-500 hover:bg-stone'}`}
            >
              {item.label}{item.badge > 0 ? ` · ${item.badge}` : ''}
            </button>
          ))}
        </nav>
      </header>

      <main className="lg:pl-[248px]">
        <div className="mx-auto max-w-[1180px] px-4 py-6 sm:px-6 lg:px-10 lg:py-10">{children}</div>
      </main>
    </div>
  );
};

export default AppShell;
