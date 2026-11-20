const EmptyState = ({ icon: Icon, title, body, action, compact = false }) => (
  <div className={`surface flex flex-col items-center text-center ${compact ? 'p-6' : 'px-6 py-12'}`}>
    {Icon && (
      <div className="mb-4 flex h-11 w-11 items-center justify-center rounded-full bg-orange-50 text-orange-700 ring-1 ring-orange-100">
        <Icon className="h-5 w-5" />
      </div>
    )}
    <p className="font-display text-xl text-ink">{title}</p>
    {body && <p className="mt-1.5 max-w-sm text-sm text-muted-foreground">{body}</p>}
    {action && <div className="mt-5">{action}</div>}
  </div>
);

export default EmptyState;
