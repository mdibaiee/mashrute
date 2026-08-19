// One language per URL. Persian is the default and lives at the root, so every
// URL already shared or indexed keeps working; English is added under /en/.
//
// Components read the language from Astro.currentLocale rather than being
// handed it as a prop, so nothing has to be threaded through the tree.

export const LOCALES = ['fa', 'en'];

/** Strip the locale prefix, giving the path as the default locale sees it. */
export function neutralPath(pathname, base = '') {
  const b = base.replace(/\/$/, '');
  let p = pathname.startsWith(b) ? pathname.slice(b.length) : pathname;
  p = p.replace(/^\/en(?=\/|$)/, '');
  return p || '/';
}

/** The same page in the other language. */
export function counterpart(pathname, locale, base = '') {
  const b = base.replace(/\/$/, '');
  const p = neutralPath(pathname, base);
  return locale === 'fa' ? `${b}/en${p === '/' ? '/' : p}` : `${b}${p}`;
}

/** Prefix a root-relative path for the given locale. */
export function localePath(path, locale, base = '') {
  const b = base.replace(/\/$/, '');
  return locale === 'fa' ? `${b}${path}` : `${b}/en${path}`;
}
