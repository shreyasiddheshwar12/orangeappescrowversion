const StatTile = ({ label, value, hint, icon: Icon, accent = false }) => (
  <div className={`surface p-4 sm:p-5 ${accent ? 'bg-gradient-to-br from-white to-orange-50' : ''}`}>
    <div className="flex items-center justify-between">
      <p className="eyebrow">{label}</p>
      {Icon && <Icon className="h-4 w-4 text-ink-300" />}
    </div>
    <p className="num mt-3 font-display text-[28px] leading-none text-ink">{value}</p>
    {hint && <p className="mt-2 text-xs text-muted-foreground">{hint}</p>}
  </div>
);

export default StatTile;
