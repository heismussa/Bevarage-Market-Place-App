import { zodResolver } from "@hookform/resolvers/zod";
import { Link, useLocalSearchParams } from "expo-router";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { Text, View } from "react-native";

import { Button } from "@/components/Button";
import { FormInput } from "@/components/Input";
import { Screen } from "@/components/Screen";
import { Banner } from "@/components/StateViews";
import { useAuth } from "@/lib/auth";
import { applyServerError } from "@/lib/forms";
import { loginSchema, type LoginForm } from "@/lib/validation";

export default function LoginScreen() {
  const { login } = useAuth();
  const params = useLocalSearchParams<{ notice?: string; phone?: string }>();
  const [formError, setFormError] = useState<string | null>(null);

  const { control, handleSubmit, setError, formState } = useForm<LoginForm>({
    resolver: zodResolver(loginSchema),
    defaultValues: { phone: params.phone ?? "", password: "" },
  });

  const onSubmit = handleSubmit(async (values) => {
    setFormError(null);
    try {
      await login(values.phone, values.password);
      // Root layout redirects to the app once the session is authenticated.
    } catch (error) {
      setFormError(applyServerError(error, setError, ["phone", "password"]));
    }
  });

  return (
    <Screen>
      <View className="mb-8 mt-10">
        <Text className="text-4xl font-bold text-foreground">BeverageMart</Text>
        <Text className="mt-2 text-base text-muted">Log in to order drinks near you.</Text>
      </View>

      {params.notice ? <Banner tone="info" message={params.notice} /> : null}
      {formError ? <Banner message={formError} /> : null}

      <FormInput
        control={control}
        name="phone"
        label="Phone number"
        placeholder="0712 345 678"
        keyboardType="phone-pad"
        autoComplete="tel"
        textContentType="telephoneNumber"
      />
      <FormInput
        control={control}
        name="password"
        label="Password"
        placeholder="Your password"
        secureTextEntry
        autoComplete="password"
        textContentType="password"
        returnKeyType="go"
        onSubmitEditing={() => void onSubmit()}
      />

      <Link href="/forgot-password" className="mb-6 self-end text-sm text-primary">
        Forgot password?
      </Link>

      <Button title="Log in" loading={formState.isSubmitting} onPress={() => void onSubmit()} />

      <View className="mt-6 flex-row justify-center">
        <Text className="text-sm text-muted">New here? </Text>
        <Link href="/register" className="text-sm font-semibold text-primary">
          Create an account
        </Link>
      </View>
    </Screen>
  );
}
