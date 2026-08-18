# Suggestions relay

Takes a reader's suggestion from the site and opens a GitHub issue for it.

It exists for one reason: the site is static, so it cannot keep a GitHub token.
Anything shipped to the browser is readable by anyone, who could then open
issues on the repository at will. The token lives here as a Worker secret and
the browser only ever talks to this endpoint.

## Deploy

```sh
cd worker
npm install

# 1. Rate-limit storage. Put the printed id into wrangler.jsonc.
npx wrangler kv namespace create RL

# 2. A fine-grained personal access token, scoped to this repository only,
#    with Issues: Read and write. Nothing else. Do not commit it.
npx wrangler secret put GITHUB_TOKEN

# 3. Ship it.
npx wrangler deploy
```

Then put the deployed URL into `web/src/lib/site.js` as `SUGGEST_ENDPOINT`.

## Abuse handling

No captcha, so nothing is asked of a genuine sender and no third-party script
is loaded:

- a honeypot field, hidden from people, that bots fill in — silently accepted
  and discarded, so the bot sees success and does not retry;
- a minimum and maximum body length;
- three submissions per IP per fifteen minutes, counted in KV.

KV counts are eventually consistent, so a burst can slip slightly over the
limit. That is fine here — the goal is to slow bots down, not to be exact.

If spam does get through, the issues all carry the `suggestion` label, so they
can be filtered and closed in bulk.

## Checking on it

```sh
npm test                     # validation, honeypot, rate limit; GitHub stubbed
npx wrangler tail            # live logs from the deployed Worker
```

Failures from the GitHub API are logged here but never returned to the browser,
since the response can name the token or its permissions.
