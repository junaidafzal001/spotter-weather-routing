import { useQuery } from "@tanstack/react-query";
import { api } from "../lib/api";

/** Corridor heatmap lattice for the selected route. */
export function useCorridor(analysisId: string | undefined, routeId: string | null) {
  return useQuery({
    queryKey: ["corridor", analysisId, routeId],
    queryFn: () => api.corridor(analysisId as string, routeId as string),
    enabled: Boolean(analysisId && routeId),
    staleTime: 30 * 60 * 1000,
    gcTime: 60 * 60 * 1000,
    retry: 1,
  });
}
