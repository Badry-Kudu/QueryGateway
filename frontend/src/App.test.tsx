import { render, screen } from "@testing-library/react";
import App from "./App";

describe("App", () => {
  it("renders the admin console heading", () => {
    render(<App />);
    expect(screen.getByText("DB2API Exposure")).toBeInTheDocument();
  });
});
