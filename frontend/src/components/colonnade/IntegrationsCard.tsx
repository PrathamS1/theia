/* The Figma export positioned every row absolutely (`left-[48px] top-[6px]
 * absolute`), which cannot survive a fluid column. Same visual -- a raised
 * logo tile overlapping a white pill -- rebuilt as flex so it reflows.
 *
 * Every measurement comes from three variables defined on `.colonnade` in
 * tailwind.css: --row-pad (the card's padding, equal on all four sides),
 * --row-gap (between rows) and --logo (the tile, solved so that three rows
 * and two gaps fill the card's content box exactly). Nothing here is sized by
 * inference -- see the note in that file for why the earlier
 * `aspect-square h-full w-auto` did not produce a square. */
const INTEGRATIONS = [
  { src: '/img/logo-gmail-128.webp', name: 'Gmail', label: 'Connects with your org email' },
  { src: '/img/logo-slack-128.webp', name: 'Slack', label: 'Connects with your org Slack' },
  { src: '/img/logo-hubspot-128.webp', name: 'HubSpot', label: 'Connects with your HubSpot' },
];

export function IntegrationsCard() {
  return (
    <div className="h-full w-full z-2 rounded-card bg-sand p-[var(--row-pad)]">
      <ul role="list" className="flex  flex-col   gap-[var(--row-gap)] ">
        {INTEGRATIONS.map((item) => (
          <li key={item.name} className=" flex min-h-0 flex-1 items-center -translate-x-6 ">
            <img
              src={item.src}
              alt=""
              width={64}
              height={64}
              loading="lazy"
              decoding="async"
              className=" shrink-0 object-contain z-4"
            />

            {/* Slid under the tile so the two whites read as one shape with a
              * raised corner, and `pl` re-centres the label against the
              * *visible* pill rather than its true box. */}
            <span
              className="-ml-4 z-3 flex h-[calc(var(--logo)*0.84)] flex-1 items-center justify-center
                whitespace-nowrap rounded-[0.85rem] bg-white pl-[1.3rem] pr-3 text-center
                text-muted [font-size:clamp(0.6875rem,0.95vw,0.8125rem)]"
            >
              {item.label}
            </span>
          </li>
        ))}
      </ul>
    </div>
  );
}
