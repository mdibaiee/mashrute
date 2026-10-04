import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import test from 'node:test';
import { buildGraph, normalizeSearch } from '../src/lib/graph-model.js';

const load = (name) => JSON.parse(readFileSync(new URL(`../src/data/${name}.json`, import.meta.url), 'utf8'));
const wiki = Object.fromEntries(['people', 'groups', 'events', 'links'].map((name) => [name, load(name)]));

test('every wiki person, group, and event is represented, including disconnected records', () => {
  const graph = buildGraph(wiki, 'en');
  const ids = new Set(graph.nodes.map((n) => n.data.id));
  assert.equal(ids.size, wiki.people.length + wiki.groups.length + wiki.events.length);
  for (const [records, kind] of [[wiki.people, 'person'], [wiki.groups, 'group'], [wiki.events, 'event']]) {
    for (const record of records) assert.ok(ids.has(`${kind}:${record.id}`));
  }
  assert.ok(graph.nodes.some((n) => n.data.degree === 0));
  const degree = new Map(graph.nodes.map((n) => [n.data.id, 0]));
  const pairs = new Set();
  for (const { data: edge } of graph.edges) {
    assert.ok(ids.has(edge.source) && ids.has(edge.target));
    const ends = edge.directed ? [edge.source, edge.target] : [edge.source, edge.target].sort();
    const key = JSON.stringify([...ends, edge.type]);
    assert.ok(!pairs.has(key), `Duplicate relationship ${key}`);
    pairs.add(key);
    degree.set(edge.source, degree.get(edge.source) + 1);
    degree.set(edge.target, degree.get(edge.target) + 1);
  }
  graph.nodes.forEach((n) => assert.equal(n.data.degree, degree.get(n.data.id)));
});

test('inverse display indexes are not double counted; roles and directed group relations survive', () => {
  const input = {
    people: [{ id: 'same', name_en: 'A' }, { id: 'b', name_en: 'B' }],
    groups: [{ id: 'same', name_en: 'Group', parent_id: 'parent' }, { id: 'parent', name_en: 'Parent' }],
    events: [{ id: 'same', title_en: 'Event' }],
    links: {
      eventPeople: { same: [{ person_id: 'same', event_id: 'same', role_type: 'leader' }] },
      personEvents: { same: [{ person_id: 'same', event_id: 'same', role_type: 'leader' }] },
      personGroups: { same: [
        { person_id: 'same', group_id: 'same', role_type: 'member' },
        { person_id: 'same', group_id: 'same', role_type: 'founder' },
      ] },
      personRelations: {
        same: [{ person_a: 'same', person_b: 'b', type: 'ally' }],
        b: [{ person_a: 'b', person_b: 'same', type: 'ally' }],
      },
      groupRelations: { same: [{ group_a: 'same', group_b: 'parent', type: 'branch_of' }] },
    },
  };
  const graph = buildGraph(input, 'en');
  assert.equal(graph.nodes.length, 5);
  assert.equal(graph.edges.length, 5);
  assert.equal(graph.edges.filter((e) => e.data.type === 'ally').length, 1);
  assert.equal(graph.edges.filter((e) => e.data.type === 'branch_of').length, 1);
  assert.ok(graph.edges.find((e) => e.data.type === 'branch_of').data.directed);
  assert.ok(graph.edges.some((e) => e.data.source === 'person:same' && e.data.target === 'event:same'));
});

test('URLs respect language and deployment base; labels and descriptions use the requested language', () => {
  const en = buildGraph(wiki, 'en', '/mashrute/');
  const fa = buildGraph(wiki, 'fa', '/mashrute/');
  const p = wiki.people.find((p) => p.name_fa && p.biography_fa);
  const find = (graph) => graph.nodes.find((n) => n.data.id === `person:${p.id}`).data;
  assert.equal(find(en).href, `/mashrute/en/people/${p.id}/`);
  assert.equal(find(fa).href, `/mashrute/people/${p.id}/`);
  assert.equal(find(en).label, p.name_en);
  assert.equal(find(fa).label, p.name_fa);
  assert.equal(find(fa).summary, p.biography_fa);
  assert.ok(find(fa).search.includes(p.name_en) && find(fa).search.includes(p.name_fa));
  assert.ok(fa.edges.every((e, i) => e.data.source === en.edges[i].data.source && e.data.target === en.edges[i].data.target));
});

test('search normalizes Persian and Arabic letter variants, joining marks, and Latin case', () => {
  assert.equal(normalizeSearch('  كِيا\u200cني  '), normalizeSearch('کیانی'));
  assert.equal(normalizeSearch('SATTAR Khan'), normalizeSearch('sattar khan'));
});
