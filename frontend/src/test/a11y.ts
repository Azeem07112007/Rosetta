import axe from "axe-core";
import { expect } from "vitest";

export async function checkA11y(container: HTMLElement, options?: axe.RunOptions) {
  const results = await axe.run(container, {
    runOnly: {
      type: "tag",
      values: ["wcag2a", "wcag2aa"],
    },
    rules: {
      // Color contrast can have false positives in jsdom due to missing computed styles
      "color-contrast": { enabled: false },
    },
    ...options,
  });

  const violations = results.violations.map((v) => ({
    id: v.id,
    impact: v.impact,
    description: v.description,
    nodes: v.nodes.length,
  }));

  expect(violations).toEqual([]);
}
