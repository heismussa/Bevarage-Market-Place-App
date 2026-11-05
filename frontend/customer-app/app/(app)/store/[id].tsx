import { formatMoney } from "@beverage/api";
import { useInfiniteQuery, useQuery } from "@tanstack/react-query";
import { useLocalSearchParams, useRouter } from "expo-router";
import { useMemo, useState } from "react";
import { FlatList, Text, TextInput, View } from "react-native";

import { ChipRow } from "@/components/Chip";
import { ProductCard } from "@/components/ProductCard";
import { Screen } from "@/components/Screen";
import { EmptyState, ErrorView, LoadingView } from "@/components/StateViews";
import { Badge } from "@/components/StatusBadge";
import { api, unwrap } from "@/lib/api";
import { useAddToCart } from "@/lib/cart";
import { categoryOptions, useCategories } from "@/lib/catalog";
import { useDebouncedValue } from "@/lib/hooks";
import { flattenPages, keys, nextPageParam } from "@/lib/query";
import type { PublicProduct } from "@/lib/types";

export default function StoreScreen() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const storeId = Number(id);
  const router = useRouter();
  const { addToCart, isAdding, conflictDialog } = useAddToCart();
  const [search, setSearch] = useState("");
  const [category, setCategory] = useState<number | null>(null);
  const debouncedSearch = useDebouncedValue(search);
  const categories = useCategories();

  const storeQuery = useQuery({
    queryKey: keys.store(storeId),
    enabled: Number.isFinite(storeId),
    queryFn: async () =>
      unwrap(await api.GET("/api/v1/stores/{id}/", { params: { path: { id: storeId } } })),
  });

  const productsQuery = useInfiniteQuery({
    queryKey: keys.storeProducts(storeId, debouncedSearch, category),
    enabled: Number.isFinite(storeId),
    initialPageParam: 1,
    queryFn: async ({ pageParam }) =>
      unwrap(
        await api.GET("/api/v1/stores/{store_id}/products/", {
          params: {
            path: { store_id: storeId },
            query: {
              page: pageParam,
              page_size: 20,
              search: debouncedSearch || undefined,
              category: category ?? undefined,
            },
          },
        }),
      ),
    getNextPageParam: nextPageParam,
  });

  const products = flattenPages<PublicProduct>(productsQuery.data);
  const chips = useMemo(() => categoryOptions(categories.data), [categories.data]);
  const store = storeQuery.data;

  return (
    <Screen title={store?.store_name ?? "Store"} back scroll={false} padded={false}>
      {conflictDialog}
      {storeQuery.isError ? (
        <ErrorView error={storeQuery.error} onRetry={() => void storeQuery.refetch()} />
      ) : (
        <FlatList
          data={products}
          numColumns={2}
          keyExtractor={(item) => String(item.id)}
          columnWrapperStyle={{ gap: 12, paddingHorizontal: 16 }}
          contentContainerStyle={{ paddingBottom: 32 }}
          onEndReached={() => {
            if (productsQuery.hasNextPage && !productsQuery.isFetchingNextPage) {
              void productsQuery.fetchNextPage();
            }
          }}
          ListHeaderComponent={
            <View className="px-4 pb-4">
              {store ? (
                <View className="mb-4">
                  <View className="flex-row items-center justify-between">
                    <Text className="flex-1 text-base text-muted">
                      {[store.area, store.city].filter(Boolean).join(", ")}
                    </Text>
                    <Badge
                      label={store.status === "OPEN" ? "Open" : "Closed"}
                      tone={store.status === "OPEN" ? "success" : "danger"}
                    />
                  </View>
                  <Text className="mt-1 text-sm text-muted">
                    Delivery {formatMoney(store.delivery_fee)}
                  </Text>
                </View>
              ) : (
                <LoadingView />
              )}
              <TextInput
                value={search}
                onChangeText={setSearch}
                placeholder="Search products"
                placeholderTextColor="#7DA0CA"
                className="mb-3 rounded-xl border border-border bg-surface px-4 py-3 text-base text-foreground"
              />
              <ChipRow options={chips} value={category} onChange={setCategory} />
            </View>
          }
          renderItem={({ item }) => (
            <View className="mb-3 flex-1">
              <ProductCard
                product={item}
                adding={isAdding}
                onPress={() => router.push(`/product/${item.id}`)}
                onAdd={() => void addToCart(item.id)}
              />
            </View>
          )}
          ListEmptyComponent={
            productsQuery.isLoading ? (
              <LoadingView />
            ) : productsQuery.isError ? (
              <ErrorView
                error={productsQuery.error}
                onRetry={() => void productsQuery.refetch()}
              />
            ) : (
              <EmptyState icon="beer-outline" title="No products" message="Try another search." />
            )
          }
        />
      )}
    </Screen>
  );
}
