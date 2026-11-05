import { Ionicons } from "@expo/vector-icons";
import { Pressable, Text, View } from "react-native";

type QuantityStepperProps = {
  value: number;
  onChange: (next: number) => void;
  min?: number;
  max?: number;
  disabled?: boolean;
};

export function QuantityStepper({
  value,
  onChange,
  min = 1,
  max,
  disabled = false,
}: QuantityStepperProps) {
  const canDecrease = !disabled && value > min;
  const canIncrease = !disabled && (max === undefined || value < max);

  return (
    <View className="flex-row items-center rounded-full border border-border bg-surface">
      <Pressable
        onPress={() => onChange(value - 1)}
        disabled={!canDecrease}
        hitSlop={6}
        accessibilityRole="button"
        accessibilityLabel="Decrease quantity"
        className={`h-9 w-9 items-center justify-center ${canDecrease ? "" : "opacity-40"}`}
      >
        <Ionicons name="remove" size={20} color="#FFFFFF" />
      </Pressable>
      <Text className="min-w-[28px] text-center text-base font-semibold text-foreground">
        {value}
      </Text>
      <Pressable
        onPress={() => onChange(value + 1)}
        disabled={!canIncrease}
        hitSlop={6}
        accessibilityRole="button"
        accessibilityLabel="Increase quantity"
        className={`h-9 w-9 items-center justify-center ${canIncrease ? "" : "opacity-40"}`}
      >
        <Ionicons name="add" size={20} color="#FFFFFF" />
      </Pressable>
    </View>
  );
}
