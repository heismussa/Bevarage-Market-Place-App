import { zodResolver } from "@hookform/resolvers/zod";
import { Link, useRouter } from "expo-router";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { Text, View } from "react-native";

import { Button } from "@/components/Button";
import { FormInput } from "@/components/Input";
import { Screen } from "@/components/Screen";
import { Banner } from "@/components/StateViews";
import { useAuth } from "@/lib/auth";
import { applyServerError } from "@/lib/forms";
import { registerSchema, type RegisterForm } from "@/lib/validation";

export default function RegisterScreen() {
  const { register } = useAuth();
  const router = useRouter();
  const [formError, setFormError] = useState<string | null>(null);

  const { control, handleSubmit, setError, formState } = useForm<RegisterForm>({
    resolver: zodResolver(registerSchema),
    defaultValues: {
      full_name: "",
      phone: "",
      email: "",
      password: "",
      confirm_password: "",
    },
  });

  const onSubmit = handleSubmit(async (values) => {
    setFormError(null);
    try {
      const { loggedIn } = await register({
        full_name: values.full_name,
        phone: values.phone,
        email: values.email,
        password: values.password,
      });
      if (!loggedIn) {
        router.replace({
          pathname: "/login",
          params: { notice: "Account created. Please log in.", phone: values.phone },
        });
      }
      // When logged in, the root layout redirects into the app.
    } catch (error) {
      setFormError(
        applyServerError(error, setError, ["full_name", "phone", "email", "password"]),
      );
    }
  });

  return (
    <Screen title="Create account" back>
      <Text className="mb-6 mt-2 text-base text-muted">
        Sign up as a customer to order from stores near you.
      </Text>

      {formError ? <Banner message={formError} /> : null}

      <FormInput
        control={control}
        name="full_name"
        label="Full name"
        placeholder="Amina Juma"
        autoCapitalize="words"
        autoComplete="name"
      />
      <FormInput
        control={control}
        name="phone"
        label="Phone number"
        placeholder="0712 345 678"
        keyboardType="phone-pad"
        autoComplete="tel"
        hint="We use +255 numbers for payments and delivery calls."
      />
      <FormInput
        control={control}
        name="email"
        label="Email (optional)"
        placeholder="you@example.com"
        keyboardType="email-address"
        autoComplete="email"
      />
      <FormInput
        control={control}
        name="password"
        label="Password"
        placeholder="At least 8 characters"
        secureTextEntry
        autoComplete="new-password"
      />
      <FormInput
        control={control}
        name="confirm_password"
        label="Confirm password"
        placeholder="Repeat your password"
        secureTextEntry
        autoComplete="new-password"
      />

      <Button
        title="Create account"
        className="mt-2"
        loading={formState.isSubmitting}
        onPress={() => void onSubmit()}
      />

      <View className="mt-6 flex-row justify-center">
        <Text className="text-sm text-muted">Already have an account? </Text>
        <Link href="/login" className="text-sm font-semibold text-primary">
          Log in
        </Link>
      </View>
    </Screen>
  );
}
