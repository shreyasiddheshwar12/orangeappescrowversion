const PageHeader = ({ eyebrow, title, description, actions, className = '' }) => (
  <div className={`flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between ${className}`}>
    <div className="min-w-0">
      {eyebrow && <p className="eyebrow mb-2">{eyebrow}</p>}
      <h1 className="display text-[28px] sm:text-[34px] leading-[1.1] text-ink">{title}</h1>
      {description && <p className="mt-2 max-w-2xl text-[15px] text-muted-foreground">{description}</p>}
    </div>
    {actions && <div className="flex shrink-0 flex-wrap gap-2">{actions}</div>}
  </div>
);

export default PageHeader;
