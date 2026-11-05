import { forwardRef } from "react";
import {
  useController,
  type Control,
  type FieldValues,
  type Path,
} from "react-hook-form";
import { Text, TextInput, View, type TextInputProps } from "react-native";

export type InputProps = TextInputProps & {
  label?: string;
  error?: string | null;
  hint?: string;
  containerClassName?: string;
};

export const Input = forwardRef<TextInput, InputProps>(function Input(
  { label, error, hint, containerClassName = "", ...rest },
  ref,
) {
  return (
    <View className={`mb-4 ${containerClassName}`}>
      {label ? (
        <Text className="mb-1.5 text-sm font-medium text-foreground">{label}</Text>
      ) : null}
      <TextInput
        ref={ref}
        placeholderTextColor="#7DA0CA"
        autoCapitalize="none"
        className={`rounded-xl border bg-surface px-4 py-3 text-base text-foreground ${
          error ? "border-danger" : "border-border"
        }`}
        {...rest}
      />
      {error ? (
        <Text className="mt-1 text-sm text-danger">{error}</Text>
      ) : hint ? (
        <Text className="mt-1 text-xs text-muted">{hint}</Text>
      ) : null}
    </View>
  );
});

type FormInputProps<T extends FieldValues> = Omit<
  InputProps,
  "value" | "onChangeText" | "onBlur" | "error"
> & {
  control: Control<T>;
  name: Path<T>;
};

/** react-hook-form bound input for string fields. */
export function FormInput<T extends FieldValues>({
  control,
  name,
  ...rest
}: FormInputProps<T>) {
  const { field, fieldState } = useController({ control, name });
  return (
    <Input
      {...rest}
      value={typeof field.value === "string" ? field.value : ""}
      onChangeText={field.onChange}
      onBlur={field.onBlur}
      error={fieldState.error?.message ?? null}
    />
  );
}
