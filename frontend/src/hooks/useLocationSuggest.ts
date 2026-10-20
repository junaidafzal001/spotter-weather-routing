import { useQuery } from "@tanstack/react-query";
import { api } from "../lib/api";

/** Debounced location autocomplete. */
export function useLocationSuggest(query: string) {
  const trimmed = query.trim();
  return useQuery({
    queryKey: ["suggest", trimmed.toLowerCase()],
    queryFn: () => api.suggest(trimmed),
    enabled: trimmed.length >= 3,
    staleTime: 5 * 60 * 1000,
    gcTime: 30 * 60 * 1000,
    retry: 0,
  });
}
