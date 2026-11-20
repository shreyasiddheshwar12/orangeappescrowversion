import { Link } from 'react-router-dom';

// Orange mark: a tangerine disc with its segment lines and a small sage leaf.
export const LogoMark = ({ size = 28, className = '' }) => (
  <svg width={size} height={size} viewBox="0 0 32 32" className={className} aria-hidden="true">
    <circle cx="16" cy="17.5" r="12.5" fill="#FF7138" />
    <g stroke="#FFF9F3" strokeWidth="1.3" strokeLinecap="round" opacity="0.85">
      <path d="M16 17.5 L16 8.5" />
      <path d="M16 17.5 L23.8 13" />
      <path d="M16 17.5 L23.8 22" />
      <path d="M16 17.5 L16 26.5" />
      <path d="M16 17.5 L8.2 22" />
      <path d="M16 17.5 L8.2 13" />
    </g>
    <path d="M17 5.2 C19.5 1.8 24 2 25.5 3.2 C23.6 6 20.4 6.6 17 5.2 Z" fill="#7E9673" />
  </svg>
);

const Logo = ({ to = '/', size = 28, className = '', tone = 'ink' }) => (
  <Link to={to} className={`inline-flex items-center gap-2 ${className}`} aria-label="Orange home">
    <LogoMark size={size} />
    <span className={`font-display text-[22px] leading-none font-semibold tracking-tight ${tone === 'light' ? 'text-white' : 'text-ink'}`}>orange</span>
  </Link>
);

export default Logo;
