// @ts-check
import { defineConfig } from 'astro/config';

export default defineConfig({
  site: 'https://mashruteh.local',
  build: { format: 'directory' },
  devToolbar: { enabled: false },
  // The chronology was promoted to the site root; keep the old path working.
  redirects: { '/chronology': '/' },
});
