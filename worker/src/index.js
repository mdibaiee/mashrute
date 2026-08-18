/**
 * Turns a reader's suggestion into a GitHub issue.
 *
 * This exists only because a static site cannot hold a credential: shipping a
 * token to the browser would let anyone open issues on the repository. The
 * token lives here as a Worker secret, and the browser only ever talks to this
 * endpoint.
 *
 * Bindings expected:
 *   GITHUB_TOKEN  secret  fine-grained PAT, issues:write on REPO only
 *   RL            KV      rate-limit counters (keys expire on their own)
 *   REPO          var     "owner/name"
 *   ALLOWED_ORIGIN var    the site allowed to POST here
 */

const MIN_LEN = 20;
const MAX_LEN = 4000;
const RATE_LIMIT = 3;          // submissions ...
const RATE_WINDOW = 15 * 60;   // ... per this many seconds, per IP

// Which file backs each record type, so the issue says where to make the edit.
const SOURCE_FILE = {
  event: 'data/extracted/events.jsonl',
  person: 'data/extracted/people.jsonl',
  group: 'data/extracted/groups.jsonl',
  place: 'data/extracted/places.jsonl',
  page: null,
};

function cors(origin) {
  return {
    'Access-Control-Allow-Origin': origin,
    'Access-Control-Allow-Methods': 'POST, OPTIONS',
    'Access-Control-Allow-Headers': 'Content-Type',
    'Access-Control-Max-Age': '86400',
    Vary: 'Origin',
  };
}

function json(data, status, origin) {
  return new Response(JSON.stringify(data), {
    status,
    headers: { 'Content-Type': 'application/json; charset=utf-8', ...cors(origin) },
  });
}

export default {
  async fetch(request, env) {
    const allowed = env.ALLOWED_ORIGIN || '*';

    if (request.method === 'OPTIONS') {
      return new Response(null, { status: 204, headers: cors(allowed) });
    }
    if (request.method !== 'POST') {
      return json({ ok: false, error: 'method' }, 405, allowed);
    }
    // Reject cross-site posts outright; the browser sends Origin on CORS POSTs.
    const origin = request.headers.get('Origin');
    if (env.ALLOWED_ORIGIN && origin && origin !== env.ALLOWED_ORIGIN) {
      return json({ ok: false, error: 'origin' }, 403, allowed);
    }

    let payload;
    try {
      payload = await request.json();
    } catch {
      return json({ ok: false, error: 'json' }, 400, allowed);
    }

    // Honeypot: a field hidden from people, so anything in it is a bot.
    if (payload.hp) return json({ ok: true, skipped: true }, 200, allowed);

    const text = String(payload.text || '').trim();
    if (text.length < MIN_LEN) return json({ ok: false, error: 'short' }, 422, allowed);
    if (text.length > MAX_LEN) return json({ ok: false, error: 'long' }, 422, allowed);

    // Rate limit per IP. Counting in KV is eventually consistent, so a burst can
    // slip a little over the limit — acceptable for slowing bots down.
    const ip = request.headers.get('CF-Connecting-IP') || 'unknown';
    if (env.RL) {
      const key = `rl:${ip}`;
      const seen = parseInt((await env.RL.get(key)) || '0', 10);
      if (seen >= RATE_LIMIT) return json({ ok: false, error: 'rate' }, 429, allowed);
      await env.RL.put(key, String(seen + 1), { expirationTtl: RATE_WINDOW });
    }

    const kind = Object.prototype.hasOwnProperty.call(SOURCE_FILE, payload.kind)
      ? payload.kind : 'page';
    const id = String(payload.id || '').slice(0, 120);
    // The title stays English so issues sort predictably for the maintainer;
    // the Persian name goes in the body when the reader was reading Persian.
    const label = String(payload.label || '').slice(0, 120) || 'the site';
    const labelFa = String(payload.labelFa || '').slice(0, 120);
    const page = String(payload.page || '').slice(0, 300);
    const lang = payload.lang === 'fa' ? 'fa' : 'en';
    const file = SOURCE_FILE[kind];

    const rows = [`| Page | ${page || '—'} |`];
    if (kind !== 'page') rows.push(`| Record | \`${kind}:${id || '?'}\` |`);
    if (file) rows.push(`| Source file | \`${file}\` |`);
    if (labelFa) rows.push(`| Persian name | ${labelFa} |`);
    rows.push(`| Language shown | ${lang} |`);

    const body = [
      '### Suggestion', '',
      text, '', '---', '',
      '| | |', '| --- | --- |',
      ...rows, '',
      '<sub>Submitted through the suggestion box on the site. The sender was not asked for any contact details.</sub>',
    ].join('\n');

    const res = await fetch(`https://api.github.com/repos/${env.REPO}/issues`, {
      method: 'POST',
      headers: {
        Authorization: `Bearer ${env.GITHUB_TOKEN}`,
        Accept: 'application/vnd.github+json',
        'X-GitHub-Api-Version': '2022-11-28',
        'User-Agent': 'mashrute-suggestions',
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        title: `[Suggestion] ${label}`.slice(0, 200),
        body,
        labels: ['suggestion'],
      }),
    });

    if (!res.ok) {
      // Never surface GitHub's response: it can echo token/permission details.
      console.error('github issue failed', res.status, await res.text());
      return json({ ok: false, error: 'upstream' }, 502, allowed);
    }
    const issue = await res.json();
    return json({ ok: true, url: issue.html_url, number: issue.number }, 200, allowed);
  },
};
