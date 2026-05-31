import { render, screen } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import { EmptyState } from "@/components/empty-state";
import { Search } from "lucide-react";

describe("EmptyState", () => {
  it("renders title", () => {
    render(<EmptyState title="No results found." />);
    expect(screen.getByText("No results found.")).toBeInTheDocument();
  });

  it("renders description when provided", () => {
    render(<EmptyState title="Empty" description="Try a different filter." />);
    expect(screen.getByText("Try a different filter.")).toBeInTheDocument();
  });

  it("renders icon when provided", () => {
    render(<EmptyState icon={Search} title="No results." />);
    const svg = document.querySelector("svg");
    expect(svg).toBeInTheDocument();
  });

  it("renders action button when provided", () => {
    const onClick = vi.fn();
    render(<EmptyState title="Empty" action={{ label: "Retry", onClick }} />);
    const btn = screen.getByRole("button", { name: "Retry" });
    expect(btn).toBeInTheDocument();
    btn.click();
    expect(onClick).toHaveBeenCalledTimes(1);
  });

  it("renders secondary action button when provided", () => {
    render(
      <EmptyState
        title="Empty"
        action={{ label: "Primary" }}
        secondaryAction={{ label: "Secondary", onClick: vi.fn() }}
      />
    );
    expect(screen.getByRole("button", { name: "Primary" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Secondary" })).toBeInTheDocument();
  });

  it("disables action button when loading", () => {
    render(<EmptyState title="Empty" action={{ label: "Go", onClick: vi.fn(), loading: true }} />);
    expect(screen.getByRole("button", { name: "Loading…" })).toBeDisabled();
  });
});
