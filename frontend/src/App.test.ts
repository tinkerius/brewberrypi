import { describe, expect, it } from "vitest";
import { APP_TITLE } from "./App";

describe("M0 smoke test", () => {
  it("uses the page title from the specification", () => {
    expect(APP_TITLE).toBe("Brewberry Pi");
  });
});
