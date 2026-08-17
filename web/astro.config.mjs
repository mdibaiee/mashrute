// @ts-check
import { defineConfig } from 'astro/config';

// GitHub Pages serves a repository at exactly one place, so which one it is
// decides the base path:
//
//   no custom domain -> https://mdibaiee.github.io/mashrute/    (base /mashrute)
//   custom domain    -> https://mashrute.ir/                    (base /)
//
// When a custom domain is configured, GitHub redirects the github.io URL to it,
// so both addresses keep working — the custom domain just becomes canonical.
// The deploy workflow sets these; the defaults are the github.io form so a
// local `astro build` matches what is published today.
const site = process.env.SITE_URL || 'https://mdibaiee.github.io';
const base = process.env.BASE_PATH || '/mashrute';

export default defineConfig({
  site,
  base,
  build: { format: 'directory' },
  devToolbar: { enabled: false },
  // The chronology was promoted to the site root; keep the old path working.
  redirects: { '/chronology': '/' },
});
