import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import test from 'node:test';
import { buildHistoryGraph, eventPeriod } from '../src/lib/graph-history.js';
import { chooseLabels, overlaps } from '../src/lib/graph-labels.js';
const wiki = Object.fromEntries(['people','groups','events','links'].map((name) => [name, JSON.parse(readFileSync(new URL(`../src/data/${name}.json`, import.meta.url), 'utf8'))]));

test('every record has a contextual path to the central revolution; recorded relationships stay distinct', () => {
  const graph = buildHistoryGraph(wiki, 'fa');
  const adjacent = new Map(graph.nodes.map((n) => [n.data.id, []]));
  for (const { data } of graph.edges) {
    adjacent.get(data.source).push(data.target);
    adjacent.get(data.target).push(data.source);
  }
  const seen = new Set(['revolution']);
  const todo = ['revolution'];
  while (todo.length) for (const id of adjacent.get(todo.pop())) if (!seen.has(id)) { seen.add(id); todo.push(id); }
  assert.equal(seen.size, graph.nodes.length);
  assert.equal(graph.totalRecords, wiki.people.length + wiki.groups.length + wiki.events.length);
  assert.equal(graph.nodes.find((n) => n.data.id === 'revolution').data.label, 'انقلاب مشروطه');
  assert.equal(graph.historicalEdges, 1326);
  assert.ok(graph.edges.filter((e) => e.data.organizing).every((e) => e.data.label === 'پیوند زمینه‌ای'));
});

test('historical boundaries follow the decree, coup, restoration, and dated aftermath', () => {
  assert.equal(eventPeriod({date_sort:'1905-00-00'}),'awakening');
  assert.equal(eventPeriod({date_sort:'1906-08-04'}),'awakening');
  assert.equal(eventPeriod({date_sort:'1906-08-05'}),'parliament');
  assert.equal(eventPeriod({date_sort:'1908-06-22'}),'parliament');
  assert.equal(eventPeriod({date_sort:'1908-06-23'}),'resistance');
  assert.equal(eventPeriod(wiki.events.find((e) => e.id === 'azerbaijan-civil-war-1908')), 'resistance');
  assert.equal(eventPeriod({date_sort:'1909-07-16'}),'restoration');
  assert.equal(eventPeriod({date_sort:'1914-11-17'}),'aftermath');
  assert.equal(eventPeriod({}),'context');
});

test('participants can appear in multiple periods; missing dates are explicit rather than invented', () => {
  const graph = buildHistoryGraph(wiki,'en');
  const sattar = graph.nodes.find((n) => n.data.id === 'person:sattar-khan').data;
  assert.ok(sattar.periods.includes('resistance'));
  assert.ok(sattar.periods.includes('restoration'));
  const untimed = graph.nodes.filter((n) => n.data.periodBasis === 'context');
  assert.ok(untimed.length);
  assert.ok(untimed.every((n) => n.data.primaryPeriod === 'context'));
  const custom = buildHistoryGraph({ people:[{id:'late',name_en:'Later scholar',birth_g_year:1907}], groups:[],events:[],links:{} },'en');
  assert.deepEqual(custom.nodes.find((n) => n.data.id==='person:late').data.periods,['context']);
});

test('visible label choices avoid overlaps, node markers, and viewport clipping while prioritizing selection', () => {
  const rect = (x,y,width=70,height=16) => ({x,y,width,height});
  const candidates = [
    {id:'ordinary',priority:1,rect:rect(20,40)},
    {id:'selected',priority:10000,rect:rect(25,40)},
    {id:'clear',priority:2,rect:rect(130,40)},
    {id:'marker-obscured',priority:500,rect:rect(20,100)},
    {id:'clipped',priority:99,rect:rect(250,40)},
  ];
  const obstacles=[{id:'node',rect:rect(20,100,20,20)}];
  const chosen=chooseLabels(candidates,obstacles,{width:300,height:200});
  assert.deepEqual(chosen,['selected','clear']);
  const visible=candidates.filter((c)=>chosen.includes(c.id));
  assert.ok(!overlaps(visible[0].rect,visible[1].rect));
});
