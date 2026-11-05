import { useQuery } from "@tanstack/react-query";

import { api, unwrap } from "./api";
import { keys } from "./query";
import type { Category } from "./types";
import type { ChipOption } from "@/components/Chip";

export function useCategories() {
  return useQuery({
    queryKey: keys.categories,
    queryFn: async () =>
      unwrap(await api.GET("/api/v1/categories/", { params: { query: { page_size: 100 } } }))
        .results,
    staleTime: 5 * 60_000,
  });
}

/** "All" plus one chip per category, for `ChipRow`. */
export function categoryOptions(categories: Category[] | undefined): ChipOption<number | null>[] {
  return [
    { value: null, label: "All" },
    ...(categories ?? []).map((category) => ({ value: category.id, label: category.name })),
  ];
}
