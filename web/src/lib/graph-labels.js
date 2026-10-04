export const overlaps = (a, b, gap = 3) => a.x < b.x + b.width + gap && a.x + a.width + gap > b.x && a.y < b.y + b.height + gap && a.y + a.height + gap > b.y;

/** Greedy screen-space labels: important records first, never over another label or node. */
export function chooseLabels(candidates, obstacles, viewport) {
  const placed = [];
  const chosen = [];
  for (const item of [...candidates].sort((a, b) => b.priority - a.priority || a.id.localeCompare(b.id))) {
    const rect = item.rect;
    if (rect.x < 6 || rect.y < 6 || rect.x + rect.width > viewport.width - 6 || rect.y + rect.height > viewport.height - 6) continue;
    if (placed.some((r) => overlaps(rect, r)) || obstacles.some((o) => o.id !== item.id && overlaps(rect, o.rect))) continue;
    placed.push(rect);
    chosen.push(item.id);
  }
  return chosen;
}
