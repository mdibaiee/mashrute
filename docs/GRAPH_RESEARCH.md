# Graph exploration design research

Reviewed 4 October 2026. Scope: improve the browser graph of people, groups, and events in the Constitutional Revolution wiki. Product observations below come from first-party documentation. Proposed implementation choices are explicitly recommendations, not claims made by those products.

## Patterns in comparable interfaces

**Kumu: cluster by meaning, then focus locally.** Kumu creates a hub for each value of a chosen field and connects records to those hubs. It supports multiple clustering rules and reuse of existing hub entities. This offers a useful model for connecting a historical period to its events and actors without relying on arbitrary force-layout communities. [Kumu clustering](https://docs.kumu.io/guides/clustering)

Kumu's focus control can show a selected field value and its first- or second-degree connections. Its settings include a minimum readable font threshold below which labels disappear, zoom limits, and static layouts. Those controls directly address an overview that becomes either a wall of text or an illegible field of dots. [Kumu focus control](https://docs.kumu.io/guides/controls/focus-control), [Kumu settings reference](https://docs.kumu.io/overview/advanced-editor-hub/settings-reference)

**Neo4j Bloom: reveal manageable scenes progressively.** Bloom starts exploration from a graph sample or search. Users can expand immediate neighbors, restrict expansion by relationship type/direction, and limit the number returned. It can group multiple nodes into a larger aggregate, provides an inspector for details, and scales label text with node size during zoom. It supports hierarchical and coordinate layouts as well as force layouts; a minimap helps navigation. [Bloom scene interactions](https://neo4j.com/docs/bloom-user-guide/current/bloom-visual-tour/bloom-scene-interactions/)

**Graph Commons: explore relationships and shared context.** Its documentation describes interactive network maps, knowledge graphs with semantic connections, and curating content through conceptual/category relationships. It identifies clusters and bridges as useful network insights. The current homepage similarly presents finding bridges and clusters as an exploration goal. This supports organizing around a comprehensible historical question rather than displaying maximum data density. [Graph Commons documentation](https://docs.graphcommons.com/), [Graph Commons homepage](https://graphcommons.com/?locale=en)

Graph Commons' deeper navigation/customization pages were linked from its documentation index but could not be retrieved during this research. No detailed interaction behavior is inferred from those unavailable pages.

## Recommendations for this wiki

These are design inferences from the product patterns above and the user's requested historical organization.

1. **Make the first screen a readable map of the revolution.** Place a central `انقلاب مشروطه` / `Constitutional Revolution` hub and a small set of clearly named chronological period hubs. Show selected landmark events around those hubs. Keep the overview's node count low enough that every displayed title is useful. All records remain discoverable through a period or search.
2. **Expand a period into its events, people, and groups.** Use stable, deterministic positions within a clearly visible cluster boundary. Show a few important items initially; provide an explicit way to reveal more. Expanding should fit that cluster, not refit the entire database into the viewport. Offer a clear return to the overview.
3. **Use three levels of detail.** Overview: period titles and landmark events. Period view: salient event/actor titles. Local view: a selected record and its immediate historical connections. Search should jump directly to the last level while retaining a route back to its period.
4. **Make labels respond to both zoom and available space.** Scale node-attached text along with nodes, with sensible upper/lower bounds. Hide low-priority labels when their projected size becomes unreadable. Resolve label rectangle collisions in screen space; always prioritize selected/hovered records, hubs, and landmark events. Preserve a full title in a tooltip and details panel.
5. **Assign visual channels a consistent meaning.** Shape represents entity type (circle/person, square/group, diamond/event). Color represents the period cluster, allowing the reader to recognize chronology across entity types. Use a legend; selection needs an additional outline so color is not its only signal.
6. **Reduce edge clutter.** Show the contextual backbone in the overview; reveal historical relationships for a chosen period, hovered record, or selected neighborhood. Emphasize the active connections and fade unrelated ones. Keep relationship descriptions in the inspector rather than labeling every edge simultaneously.
7. **Keep controls predictable.** Support drag-to-pan, wheel/pinch zoom around the pointer, node dragging, readable hit targets, zoom buttons, reset, and fit-current-view. Clicking a node should expose its summary and relationships without navigating away; offer a separate full-entry link.

## Contextual structure and historical evidence

The proposed navigation backbone is:

`Constitutional Revolution → historical periods → dated events → connected actors/groups`

Possible period headings are background, the 1905–1906 uprising, the First Majlis, the 1908–1909 resistance, the Second Majlis, and later consequences. These are proposed editorial navigation categories. Exact boundaries and wording should be checked against the existing chronology and dated records; this interface research does not independently establish historical periodization.

Use event dates to assign events. Derive actor/group participation in periods from their existing dated event relationships. An actor may be active in multiple periods: keep one stable identity and show its cross-period activity in the details panel. A default placement can use the period with the strongest documented participation. Do not assign historical activity from birth dates or a layout algorithm.

The data model already separates event participation, membership, person relationships, and group relationships. Preserve those sourced edges. [Repository data model](DATA_MODEL.md)

Add a distinct **contextual** edge category for the central root and period membership. Draw these with a dashed/light style and explain their meaning in the legend. They organize the encyclopedia; they do not assert that two people met or that one event caused another. Missing relationship data should remain explicit. Records without a dated affiliation can connect to a clearly labeled context/background hub instead of inventing a historical link. This makes every record reachable from the revolution while preserving the difference between navigation and historical evidence.

## Acceptance checks

- At the initial desktop and mobile sizes, the root and period names are legible without zooming.
- Every displayed record has a visible contextual or historical connection and every record has a path to the root.
- Zoomed screenshots do not show overlapping visible labels; selected titles remain readable.
- A period opens its events plus relevant actors/groups, and selected relationships explain what the connection means.
- Search, pan, pinch/wheel zoom, drag, node details, return to overview, and article links work in both languages.
- Contextual edges are distinguishable from sourced historical edges, and uncertain period assignment is disclosed.

## Implemented organization and checks

The graph opens with the revolution hub, seven period/context hubs, and one landmark per dated period. Opening a period reveals chronological event and actor/group lanes, with progressive expansion. Recorded relationships between displayed nodes remain visible at low opacity. Hovering highlights only that node's connections at full opacity; leaving restores the selected node's highlight, or the faint background when nothing is selected.

Period boundaries use the existing chronology: 1905; the constitutional decree on 5 August 1906; the bombardment on 23 June 1908; the reconquest on 16 July 1909; and the end of 1911. Undated records use wider context. The Tabriz civil-war/siege range is explicitly placed in resistance because its recorded summary says it followed the coup; treating its unspecified June start as 1 June would put it in the wrong period. Actor/group affiliation-based placement is disclosed separately from direct event links and does not assert dated membership. [Wiki event records](../web/src/data/events.json), [Classification implementation](../web/src/lib/graph-history.js)

The original opening reproduced 824 targets below 12 pixels and 133 disconnected records. The redesigned graph has a contextual path from all 824 records to the root, preserves all 1,326 historical relationships, and keeps visible targets at least 20 pixels wide. Browser checks measure actual rendered label bounds at multiple zoom levels, rather than only checking that the graph loads. Visible text is clamped between 10 and 16 screen pixels; collision detection hides lower-priority labels. [Graph regression tests](../web/test/graph-history.test.js), [Label selection](../web/src/lib/graph-labels.js)
