// Where a reader's suggestion goes. The site is static, so it cannot hold a
// GitHub token; this endpoint is a Cloudflare Worker (see ../../worker) that
// keeps the token as a secret and opens the issue on the reader's behalf.
// Set this to the URL `wrangler deploy` prints, then rebuild. While it is
// empty the suggestion box is not rendered at all, so readers are never shown
// a form that cannot deliver.
export const SUGGEST_ENDPOINT = 'https://mashrute-suggestions.mdibaiee.workers.dev';

// Which file in the repo backs each kind of record, so a suggestion names the
// place the correction has to be made.
export const SOURCE_FILE = {
  event: 'data/extracted/events.jsonl',
  person: 'data/extracted/people.jsonl',
  group: 'data/extracted/groups.jsonl',
  place: 'data/extracted/places.jsonl',
  page: null,
};
