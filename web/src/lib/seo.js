// Search-facing helpers. Kept apart from the layout so the rules live in one
// place rather than being restated per page.

export const SITE_EN = 'The Iranian Constitutional Revolution';
export const SITE_FA = 'انقلاب مشروطهٔ ایران';

export const DEFAULT_DESC_EN =
  'A bilingual database of the Iranian Constitutional Revolution, 1906–1911: '
  + 'every person, group and dated event, cross-linked, with Gregorian, Solar '
  + 'Hijri and Lunar Hijri dates.';
export const DEFAULT_DESC_FA =
  'پایگاه دادهٔ دوزبانهٔ انقلاب مشروطهٔ ایران، ۱۲۸۵–۱۲۹۰: هر شخص، گروه و رویداد '
  + 'تاریخ‌دار، پیوسته به یکدیگر، با تاریخ میلادی، هجری شمسی و هجری قمری.';

/** Trim to a length search engines will actually show, without cutting a word. */
export function clamp(text, max = 165) {
  const s = String(text || '').replace(/\s+/g, ' ').trim();
  if (s.length <= max) return s;
  const cut = s.slice(0, max);
  const at = cut.lastIndexOf(' ');
  return (at > max * 0.6 ? cut.slice(0, at) : cut).replace(/[،,;:.\s]+$/, '') + '…';
}

/** Absolute URL for canonical and og:url, which must not be relative. */
export function absolute(site, pathname) {
  const base = String(site || '').replace(/\/$/, '');
  return base + pathname;
}

/** Breadcrumbs, so a result shows its place in the site rather than a bare URL. */
export function breadcrumbs(origin, base, trail) {
  return {
    '@type': 'BreadcrumbList',
    itemListElement: trail.map((t, i) => ({
      '@type': 'ListItem',
      position: i + 1,
      name: t.name,
      item: `${origin}${base}${t.path}`,
    })),
  };
}
