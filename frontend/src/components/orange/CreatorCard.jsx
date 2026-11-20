import { MapPin, Star, Users } from 'lucide-react';
import { Button } from '../ui/button';
import { formatINR, formatCount } from '../../lib/format';

const NICHE_TINT = {
  Food: 'from-orange-100 to-peach', Fashion: 'from-plum-100 to-plum-50', Beauty: 'from-[#F6DCDC] to-[#FBEFEF]',
  Fitness: 'from-sage-100 to-sage-50', Travel: 'from-[#DCE7EE] to-[#EEF3F6]', Lifestyle: 'from-amber-100 to-amber-50',
};

const CreatorCard = ({ creator, onView, onPropose, children }) => {
  const tint = NICHE_TINT[creator.niche] || 'from-stone to-ivory';
  return (
    <article className="surface group flex flex-col overflow-hidden transition-shadow duration-200 hover:shadow-lift" data-testid={`creator-card-${creator.id}`}>
      <div className={`relative h-16 bg-gradient-to-br sm:h-24 ${tint}`}>
        <span className="absolute left-4 top-4 rounded-full bg-white/80 px-2.5 py-0.5 text-xs font-medium text-ink backdrop-blur">{creator.niche || 'Creator'}</span>
        {creator.matchScore != null && (
          <span className="num absolute right-4 top-4 rounded-full bg-ink px-2.5 py-0.5 text-xs font-semibold text-white">{creator.matchScore}% match</span>
        )}
      </div>
      <div className="flex flex-1 flex-col p-4">
        <p className="font-display text-lg leading-tight text-ink">{creator.name || `${creator.niche || 'Local'} creator`}</p>
        <div className="mt-1 flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-muted-foreground">
          {creator.location && <span className="flex items-center gap-1"><MapPin className="h-3.5 w-3.5" />{creator.location}</span>}
          {creator.language && <span>{creator.language}</span>}
        </div>
        <dl className="mt-4 grid grid-cols-3 gap-2 text-xs">
          <div><dt className="text-muted-foreground">Reel</dt><dd className="num mt-0.5 font-semibold text-ink">{creator.reelPrice ? formatINR(creator.reelPrice) : '—'}</dd></div>
          <div><dt className="text-muted-foreground flex items-center gap-1"><Users className="h-3 w-3" />Followers</dt><dd className="num mt-0.5 font-semibold text-ink">{creator.followersCount ? formatCount(creator.followersCount) : '—'}</dd></div>
          <div><dt className="text-muted-foreground flex items-center gap-1"><Star className="h-3 w-3" />Rating</dt><dd className="num mt-0.5 font-semibold text-ink">{creator.rating ? creator.rating.toFixed(1) : 'New'}</dd></div>
        </dl>
        <p className="mt-2 text-[11px] text-muted-foreground">
          {creator.engagementMeasured ? `${creator.engagementRate}% engagement` : 'Engagement not measured yet'}
          {creator.barterEnabled ? ' · open to barter' : ''}
        </p>
        {children}
        <div className="mt-4 flex gap-2 pt-1">
          {onView && <Button variant="outline" size="sm" className="flex-1" onClick={() => onView(creator)}>View profile</Button>}
          {onPropose && <Button size="sm" className="flex-1" onClick={() => onPropose(creator)} data-testid={`propose-${creator.id}`}>Propose</Button>}
        </div>
      </div>
    </article>
  );
};

export default CreatorCard;
