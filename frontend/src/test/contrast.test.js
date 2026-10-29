// @vitest-environment node
import { readFileSync } from 'node:fs';
import { describe, expect, it } from 'vitest';

const css = readFileSync(new URL('../styles.css', import.meta.url), 'utf8');
const tokens = Object.fromEntries([...css.matchAll(/(--[\w-]+):\s*(#[0-9a-fA-F]{6})/g)].map((m) => [m[1], m[2]]));

function luminance(hex) {
  const [r, g, b] = [1, 3, 5].map((i) => parseInt(hex.slice(i, i + 2), 16) / 255).map((c) => (c <= 0.03928 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4));
  return 0.2126 * r + 0.7152 * g + 0.0722 * b;
}
const ratio = (a, b) => {
  const [hi, lo] = [luminance(a), luminance(b)].sort((x, y) => y - x);
  return (hi + 0.05) / (lo + 0.05);
};

// [foreground token, background token] pairs actually used for text in styles.css
const PAIRS = [
  ['--text', '--bg'], ['--text', '--panel'], ['--text', '--field'],
  ['--muted', '--bg'], ['--muted', '--panel'], ['--muted', '--aside'],
  ['--nav', '--aside'], ['--nav', '--panel'], ['--nav-active', '--nav-active-bg'], ['--nav-active', '--panel'],
  ['--cyan', '--panel'], ['--good', '--panel'], ['--warn', '--panel'],
  ['--btn-text', '--btn-bg'], ['--warning-text', '--warning-bg'], ['--pill-text', '--pill-bg'],
  ['--low-text', '--low-bg'], ['--mod-text', '--mod-bg'], ['--high-text', '--high-bg'],
  ['--notice-text', '--notice-bg'], ['--error-text', '--error-bg'],
];

describe('WCAG AA text contrast (4.5:1)', () => {
  it('finds the design tokens', () => {
    expect(Object.keys(tokens).length).toBeGreaterThan(20);
  });
  it.each(PAIRS)('%s on %s', (fg, bg) => {
    expect(tokens[fg], `${fg} missing`).toBeDefined();
    expect(tokens[bg], `${bg} missing`).toBeDefined();
    expect(ratio(tokens[fg], tokens[bg])).toBeGreaterThanOrEqual(4.5);
  });
});
