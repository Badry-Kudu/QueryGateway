import { render, screen } from "@testing-library/react";
import App from "./App";

describe("App", () => {
  it("renders the dashboard page h1 heading", () => {
    render(<App />);
    // The <h1> on the DashboardPage (not the sidebar nav link)
    expect(
      screen.getByRole("heading", { name: "Dashboard", level: 1 }),
    ).toBeInTheDocument();
  });

  it("renders at least one connections link", () => {
    render(<App />);
    const links = screen.getAllByRole("link", { name: /connections/i });
    expect(links.length).toBeGreaterThan(0);
  });
});
