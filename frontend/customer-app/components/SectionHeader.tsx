import type { ReactNode } from "react";
import { Text, View } from "react-native";

export function SectionHeader({ title, right }: { title: string; right?: ReactNode }) {
  return (
    <View className="mb-3 mt-5 flex-row items-center justify-between">
      <Text className="text-lg font-bold text-foreground">{title}</Text>
      {right}
    </View>
  );
}
