import { localePath } from './locale.js';
import { EVENT_TYPE_LABEL, GROUP_TYPE_LABEL } from './util.js';

export const NODE_TYPES = {
  person: { en: 'People', fa: 'اشخاص', shape: 'ellipse', color: '#344aa0' },
  group: { en: 'Groups', fa: 'گروه‌ها', shape: 'round-rectangle', color: '#128463' },
  event: { en: 'Events', fa: 'رویدادها', shape: 'diamond', color: '#b23b72' },
};

const RELATIONS = {
  leader: ['Leader', 'رهبر'], participant: ['Participant', 'شرکت‌کننده'],
  victim: ['Victim', 'قربانی'], perpetrator: ['Perpetrator', 'عامل'],
  signatory: ['Signatory', 'امضاکننده'], opponent: ['Opponent', 'مخالف'],
  witness: ['Witness', 'شاهد'], author: ['Author', 'نویسنده'], target: ['Target', 'هدف'],
  mediator: ['Mediator', 'میانجی'], founder: ['Founder', 'بنیان‌گذار'],
  member: ['Member', 'عضو'], affiliate: ['Affiliate', 'وابسته'],
  representative: ['Representative', 'نماینده'], editor: ['Editor', 'سردبیر'],
  patron: ['Patron', 'حامی'], ally: ['Ally', 'هم‌پیمان'], allied: ['Allied', 'هم‌پیمان'],
  rival: ['Rival', 'رقیب'], kin: ['Kin', 'خویشاوند'],
  assassinated: ['Assassination', 'ترور'], mentor: ['Mentor / student', 'استاد یا شاگرد'],
  collaborator: ['Collaborator', 'همکار'],
  branch_of: ['Branch of', 'شعبهٔ'], split_from: ['Split from', 'منشعب از'],
  successor: ['Successor to', 'جانشین'], opposed: ['Opposed', 'مخالف'],
};

const pick = (record, field, fa) => fa ? record[`${field}_fa`] || '' : record[`${field}_en`] || '';
const label = (type, fa) => RELATIONS[type]?.[fa ? 1 : 0] || (fa ? 'پیوند' : 'Connection');

/** Build one canonical graph from the wiki's cross-link index, without its inverse duplicates. */
export function buildGraph({ people, groups, events, links }, locale = 'fa', base = '') {
  const fa = locale === 'fa';
  const nodes = [];
  const edges = [];
  const byId = new Map();
  const seen = new Set();
  const addNode = (record, kind, directory, name, summary, meta) => {
    const data = {
      id: `${kind}:${record.id}`, slug: record.id, kind,
      label: pick(record, name, fa) || (fa ? 'ترجمه نشده' : 'Untranslated'),
      // Search either language even when the graph labels use the current locale.
      search: [record[`${name}_en`], record[`${name}_fa`], record.full_name_en,
        record.full_name_fa, record.title_en, record.title_fa].filter(Boolean).join(' '),
      summary: pick(record, summary, fa), meta,
      href: localePath(`/${directory}/${record.id}/`, locale, base),
      color: NODE_TYPES[kind].color, shape: NODE_TYPES[kind].shape,
      degree: 0,
    };
    nodes.push({ data });
    byId.set(data.id, data);
  };
  people.forEach((p) => addNode(p, 'person', 'people', 'name', 'biography',
    [pick(p, 'role', fa), !p.is_historical_actor && (fa ? 'پژوهشگر مورد استناد' : 'Cited scholar')].filter(Boolean).join(' · ')));
  groups.forEach((g) => addNode(g, 'group', 'groups', 'name', 'description',
    GROUP_TYPE_LABEL[g.type]?.[fa ? 1 : 0] || ''));
  events.forEach((e) => addNode(e, 'event', 'events', 'title', 'summary',
    [EVENT_TYPE_LABEL[e.type]?.[fa ? 1 : 0], pick(e, 'date_display', fa)].filter(Boolean).join(' · ')));

  const addEdge = (source, target, type, r = {}, directed = false) => {
    if (!byId.has(source) || !byId.has(target)) return;
    const endpoints = directed ? [source, target] : [source, target].sort();
    const key = JSON.stringify([...endpoints, type]);
    if (seen.has(key)) return;
    seen.add(key);
    edges.push({ data: {
      id: `edge:${edges.length}`, source, target, type,
      label: label(type, fa), role: pick(r, 'role', fa), note: pick(r, 'note', fa),
      directed, arrow: directed ? 'triangle' : 'none',
    } });
    byId.get(source).degree++;
    byId.get(target).degree++;
  };
  const rows = (key) => Object.values(links[key] || {}).flat();
  rows('eventPeople').forEach((r) => addEdge(`person:${r.person_id}`, `event:${r.event_id}`, r.role_type, r));
  rows('eventGroups').forEach((r) => addEdge(`group:${r.group_id}`, `event:${r.event_id}`, r.role_type, r));
  rows('personGroups').forEach((r) => addEdge(`person:${r.person_id}`, `group:${r.group_id}`, r.role_type, r));
  // The exporter mirrors personal relations for the detail pages. Keep each once.
  rows('personRelations').forEach((r) => addEdge(`person:${r.person_a}`, `person:${r.person_b}`, r.type, r));
  rows('groupRelations').forEach((r) => addEdge(`group:${r.group_a}`, `group:${r.group_b}`, r.type, r,
    ['branch_of', 'split_from', 'successor'].includes(r.type)));
  groups.filter((g) => g.parent_id).forEach((g) => addEdge(`group:${g.id}`, `group:${g.parent_id}`, 'branch_of', {}, true));
  nodes.forEach(({ data }) => { data.size = 16 + Math.min(22, Math.sqrt(data.degree) * 3); });
  return { nodes, edges };
}

export function normalizeSearch(value) {
  return value.normalize('NFKC').toLowerCase().replace(/[يى]/g, 'ی').replace(/ك/g, 'ک')
    .replace(/[\u200c\u200e\u200f\u064b-\u065f]/g, '').replace(/\s+/g, ' ').trim();
}
