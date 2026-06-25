import { render, screen } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import MatchesPage from "@/pages/matches";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

// Mock the API client and other dependencies
vi.mock("@/api-client", () => ({
  useListMatches: () => ({ data: { matches: [] }, isLoading: false }),
  useListRecentMatches: () => ({ data: { matches: [] }, isLoading: false }),
  useListCompletedMatches: () => ({ data: { matches: [] }, isLoading: false }),
  useSyncFixtures: () => ({ mutateAsync: vi.fn() }),
  useListLeagues: () => ({ data: { leagues: [] } }),
}));

vi.mock("@/lib/apiClient", () => ({
  apiGet: vi.fn(() => Promise.resolve({ matches: [] })),
}));

vi.mock("@/lib/websocket", () => ({
  vitWS: { on: () => () => {} },
}));

const queryClient = new QueryClient();

describe("MatchesPage Summary Logic", () => {
  it("renders the summary line with dynamic count", () => {
    render(
      <QueryClientProvider client={queryClient}>
        <MatchesPage />
      </QueryClientProvider>
    );
    // The upgraded UI uses different text: "Matches Found"
    expect(screen.getByText(/Matches Found/i)).toBeInTheDocument();
  });
});
