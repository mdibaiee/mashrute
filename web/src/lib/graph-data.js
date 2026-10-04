import people from '../data/people.json';
import groups from '../data/groups.json';
import events from '../data/events.json';
import links from '../data/links.json';
import { buildHistoryGraph } from './graph-history.js';

export function wikiGraph(locale, base) {
  return buildHistoryGraph({ people, groups, events, links }, locale, base);
}
