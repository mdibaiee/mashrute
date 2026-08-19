import events from '../data/events.json';
import people from '../data/people.json';
import groups from '../data/groups.json';

// Built from the data rather than by crawling the output, so nothing is missed:
// most of these pages are only reachable through a long chronology or a
// directory that filters client-side, which is exactly the case a sitemap is
// for. Priorities are relative, and say what this site is actually about — the
// records, not the index pages that list them.
export function GET({ site }) {
  const base = import.meta.env.BASE_URL.replace(/\/$/, '');
  const origin = String(site).replace(/\/$/, '');
  // Persian at the root, English under /en/. Each entry declares both, so the
  // two are read as translations of one page rather than as duplicates.
  const url = (path, locale) => `${origin}${base}${locale === 'en' ? '/en' : ''}${path}`;

  const pages = [
    { path: '/', priority: '1.0', changefreq: 'weekly' },
    { path: '/people/', priority: '0.8', changefreq: 'weekly' },
    { path: '/groups/', priority: '0.8', changefreq: 'weekly' },
    { path: '/notes/', priority: '0.4', changefreq: 'yearly' },
    ...events.map((e) => ({ path: `/events/${e.id}/`, priority: '0.7', changefreq: 'monthly' })),
    // Modern scholars Afary cites are listed but are not the subject here.
    ...people.map((p) => ({
      path: `/people/${p.id}/`,
      priority: p.is_historical_actor ? '0.7' : '0.3',
      changefreq: 'monthly',
    })),
    ...groups.map((g) => ({ path: `/groups/${g.id}/`, priority: '0.6', changefreq: 'monthly' })),
  ];

  const entries = pages.flatMap((pg) =>
    ['fa', 'en'].map((locale) => ({ ...pg, loc: url(pg.path, locale) })));

  const body = `<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"
        xmlns:xhtml="http://www.w3.org/1999/xhtml">
${entries.map((e) => `  <url>
    <loc>${e.loc}</loc>
    <xhtml:link rel="alternate" hreflang="fa" href="${url(e.path, 'fa')}" />
    <xhtml:link rel="alternate" hreflang="en" href="${url(e.path, 'en')}" />
    <xhtml:link rel="alternate" hreflang="x-default" href="${url(e.path, 'fa')}" />
    <changefreq>${e.changefreq}</changefreq>
    <priority>${e.priority}</priority>
  </url>`).join('\n')}
</urlset>
`;
  return new Response(body, { headers: { 'Content-Type': 'application/xml; charset=utf-8' } });
}
