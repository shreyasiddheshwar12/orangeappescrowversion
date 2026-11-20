const Section = ({ title, description, action, children, className = '' }) => (
  <section className={className}>
    <div className="mb-3 flex items-end justify-between gap-4">
      <div>
        <h2 className="font-sans text-[15px] font-semibold text-ink">{title}</h2>
        {description && <p className="text-sm text-muted-foreground">{description}</p>}
      </div>
      {action}
    </div>
    {children}
  </section>
);

export default Section;
