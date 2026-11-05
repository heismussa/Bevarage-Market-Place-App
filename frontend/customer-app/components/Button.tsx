import { ActivityIndicator, Pressable, Text, type PressableProps } from "react-native";

type Variant = "primary" | "secondary" | "danger" | "ghost";

type ButtonProps = Omit<PressableProps, "children"> & {
  title: string;
  variant?: Variant;
  loading?: boolean;
  small?: boolean;
  className?: string;
};

const containerStyles: Record<Variant, string> = {
  primary: "bg-primary",
  secondary: "bg-surface border border-border",
  danger: "bg-danger/15 border border-danger",
  ghost: "bg-transparent",
};

const labelStyles: Record<Variant, string> = {
  primary: "text-primary-foreground",
  secondary: "text-foreground",
  danger: "text-danger",
  ghost: "text-primary",
};

export function Button({
  title,
  variant = "primary",
  loading = false,
  small = false,
  disabled,
  className = "",
  ...rest
}: ButtonProps) {
  const inactive = disabled || loading;
  return (
    <Pressable
      accessibilityRole="button"
      accessibilityState={{ disabled: !!inactive, busy: loading }}
      disabled={inactive}
      className={`flex-row items-center justify-center rounded-xl active:opacity-80 ${
        small ? "px-4 py-2" : "px-5 py-3.5"
      } ${containerStyles[variant]} ${inactive ? "opacity-50" : ""} ${className}`}
      {...rest}
    >
      {loading ? (
        <ActivityIndicator
          size="small"
          color={variant === "primary" ? "#021024" : "#FFFFFF"}
        />
      ) : (
        <Text
          className={`font-semibold ${small ? "text-sm" : "text-base"} ${labelStyles[variant]}`}
        >
          {title}
        </Text>
      )}
    </Pressable>
  );
}
