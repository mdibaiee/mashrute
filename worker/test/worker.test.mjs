import worker from '../src/index.js';

// In-memory stand-in for the KV binding.
const store = new Map();
const KV = {
  get: async (k) => (store.has(k) ? store.get(k) : null),
  put: async (k, v) => void store.set(k, v),
};
let ghCalls = [];
globalThis.fetch = async (url, init) => {
  ghCalls.push({ url, body: JSON.parse(init.body) });
  return new Response(JSON.stringify({ html_url: 'https://github.com/x/y/issues/7', number: 7 }),
                      { status: 201 });
};
const env = { GITHUB_TOKEN: 'test', RL: KV, REPO: 'mdibaiee/mashrute',
              ALLOWED_ORIGIN: 'https://mashrute.wiki' };

const post = (body, origin = 'https://mashrute.wiki', ip = '1.2.3.4') =>
  worker.fetch(new Request('https://w/', {
    method: 'POST', headers: { 'Content-Type': 'application/json', Origin: origin, 'CF-Connecting-IP': ip },
    body: JSON.stringify(body),
  }), env);

const ok = (label, cond) => console.log((cond ? '  PASS  ' : '  FAIL  ') + label);
const good = { text: 'The date given for the Tabriz siege looks a day early; Kasravi gives 20 Jumada.', kind: 'event', id: 'x', label: 'Tabriz', page: 'https://mashrute.wiki/', lang: 'fa' };

let r = await worker.fetch(new Request('https://w/', { method: 'OPTIONS', headers: { Origin: 'https://mashrute.wiki' } }), env);
ok('CORS preflight -> 204', r.status === 204);

r = await worker.fetch(new Request('https://w/', { method: 'GET' }), env);
ok('GET rejected -> 405', r.status === 405);

r = await post(good, 'https://evil.example');
ok('foreign origin -> 403', r.status === 403);

r = await post({ ...good, text: 'too short' });
ok('short body -> 422', r.status === 422);

r = await post({ ...good, text: 'x'.repeat(5000) });
ok('over-long body -> 422', r.status === 422);

ghCalls = [];
r = await post({ ...good, hp: 'http://spam.example' }, undefined, '9.9.9.9');
ok('honeypot -> 200 and no issue created', r.status === 200 && ghCalls.length === 0);

ghCalls = [];
r = await post(good, undefined, '5.5.5.5');
let body = await r.json();
ok('valid -> 200 with issue url', r.status === 200 && body.ok && body.url.includes('/issues/'));
const issue = ghCalls[0].body;
ok('issue titled from label', issue.title === '[Suggestion] Tabriz');
ok('issue labelled suggestion', issue.labels.includes('suggestion'));
ok('issue names the source file', issue.body.includes('data/extracted/events.jsonl'));
ok('issue names the record', issue.body.includes('`event:x`'));

// Fourth submission from the same IP inside the window is refused.
let last;
for (let i = 0; i < 3; i++) last = await post(good, undefined, '7.7.7.7');
ok('rate limit -> 429 on 4th', (await post(good, undefined, '7.7.7.7')).status === 429);

// Unknown record kind must not reach through to a file path.
ghCalls = [];
await post({ ...good, kind: '../../etc/passwd' }, undefined, '8.8.8.8');
ok('unknown kind falls back to page', !ghCalls[0].body.body.includes('passwd'));
