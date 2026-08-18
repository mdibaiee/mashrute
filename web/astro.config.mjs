// @ts-check
import { defineConfig } from 'astro/config';

// GitHub Pages serves a repository at exactly one place, so which one it is
// decides the base path:
//
//   custom domain    -> https://mashrute.wiki/                  (base /)
//   no custom domain -> https://mdibaiee.github.io/mashrute/    (base /mashrute)
//
// mashrute.wiki is configured, so GitHub redirects the github.io URL to it and
// both addresses keep working. The deploy workflow can override these; the
// defaults match what is published so a local build behaves the same.
const site = process.env.SITE_URL || 'https://mashrute.wiki';
const base = process.env.BASE_PATH || '/';

export default defineConfig({
  site,
  base,
  build: { format: 'directory' },
  devToolbar: { enabled: false },
  // The chronology was promoted to the site root; keep the old path working.
  redirects: { '/chronology': '/' },
});
