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
  const url = (path) => `${origin}${base}${path}`;

  const entries = [
    { loc: url('/'), priority: '1.0', changefreq: 'weekly' },
    { loc: url('/people/'), priority: '0.8', changefreq: 'weekly' },
    { loc: url('/groups/'), priority: '0.8', changefreq: 'weekly' },
    { loc: url('/notes/'), priority: '0.4', changefreq: 'yearly' },
    ...events.map((e) => ({ loc: url(`/events/${e.id}/`), priority: '0.7', changefreq: 'monthly' })),
    // Modern scholars Afary cites are listed but are not the subject here.
    ...people.map((p) => ({
      loc: url(`/people/${p.id}/`),
      priority: p.is_historical_actor ? '0.7' : '0.3',
      changefreq: 'monthly',
    })),
    ...groups.map((g) => ({ loc: url(`/groups/${g.id}/`), priority: '0.6', changefreq: 'monthly' })),
  ];

  const body = `<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
${entries.map((e) => `  <url>
    <loc>${e.loc}</loc>
    <changefreq>${e.changefreq}</changefreq>
    <priority>${e.priority}</priority>
  </url>`).join('\n')}
</urlset>
`;
  return new Response(body, { headers: { 'Content-Type': 'application/xml; charset=utf-8' } });
}
