import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import Page from "./page";

describe("Home page", () => {
  it("renders the Agentic FilmOps placeholder heading", () => {
    render(<Page />);
    expect(
      screen.getByRole("heading", { name: /agentic filmops/i })
    ).toBeInTheDocument();
  });
});
