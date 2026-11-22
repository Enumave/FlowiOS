import { describe, expect, it } from "vitest";
import { nextBarHidden } from "./barVisibility";

describe("bottom bar scroll rule", () => {
  it("stays put until the page has travelled down a little", () => {
    expect(nextBarHidden(false, 100, 10, 0)).toEqual({ hidden: false, travelled: 10 });
    expect(nextBarHidden(false, 130, 20, 10)).toEqual({ hidden: true, travelled: 30 });
  });
  it("comes back on the first scroll up", () => {
    expect(nextBarHidden(true, 500, -10, 0).hidden).toBe(false);
  });
  it("is always showing at the top of the page", () => {
    expect(nextBarHidden(true, 0, -50, 0)).toEqual({ hidden: false, travelled: 0 });
  });
  it("restarts the count when the direction changes", () => {
    expect(nextBarHidden(true, 400, -4, 20)).toEqual({ hidden: true, travelled: -4 });
  });
});
