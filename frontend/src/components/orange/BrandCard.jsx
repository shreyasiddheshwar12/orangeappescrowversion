import { MapPin, Star } from 'lucide-react';
import { Button } from '../ui/button';

const BrandCard = ({ brand, onView, onPropose }) => (
  <article className="surface flex flex-col p-4 transition-shadow duration-200 hover:shadow-lift" data-testid={`brand-card-${brand.id}`}>
    <div className="flex items-start justify-between gap-3">
      <div>
        <p className="font-display text-lg leading-tight text-ink">{brand.industry || 'Local'} brand</p>
        {brand.location && <p className="mt-1 flex items-center gap-1 text-xs text-muted-foreground"><MapPin className="h-3.5 w-3.5" />{brand.location}</p>}
      </div>
      {brand.rating && <span className="num flex items-center gap-1 text-xs font-semibold"><Star className="h-3.5 w-3.5 fill-primary text-primary" />{brand.rating.toFixed(1)}</span>}
    </div>
    {brand.deliverables && <p className="mt-3 line-clamp-2 text-sm text-ink-700">Looking for: {brand.deliverables}</p>}
    <div className="mt-3 flex flex-wrap gap-1.5">
      {brand.budgetRange && <span className="rounded-full bg-stone px-2 py-0.5 text-[11px] text-ink-700">{brand.budgetRange}</span>}
      {brand.paidCollabsEnabled && <span className="rounded-full bg-sage-50 px-2 py-0.5 text-[11px] text-sage-700">Paid</span>}
      {brand.barterEnabled && <span className="rounded-full bg-plum-50 px-2 py-0.5 text-[11px] text-plum-700">Barter</span>}
      {(brand.preferredNiches || []).slice(0, 3).map((n) => <span key={n} className="rounded-full bg-orange-50 px-2 py-0.5 text-[11px] text-orange-800">{n}</span>)}
    </div>
    <div className="mt-4 flex gap-2">
      {onView && <Button variant="outline" size="sm" className="flex-1" onClick={() => onView(brand)}>View</Button>}
      {onPropose && <Button size="sm" className="flex-1" onClick={() => onPropose(brand)}>Pitch</Button>}
    </div>
  </article>
);

export default BrandCard;
