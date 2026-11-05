import { ApiError, applyFieldErrors } from "@beverage/api";
import { zodResolver } from "@hookform/resolvers/zod";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { Link, useLocation, useNavigate } from "react-router";
import { z } from "zod";

import { AuthShell, FormBanner } from "@/pages/auth/AuthShell";
import { Button } from "@/components/ui/button";
import { Field, Input } from "@/components/ui/input";
import { errorMessage } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { phoneForApi, phoneSchema } from "@/lib/validation";

const schema = z.object({
  phone: phoneSchema,
  password: z.string().min(1, "Enter your password."),
});
type Values = z.infer<typeof schema>;

export default function LoginPage() {
  const { login, notice } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [banner, setBanner] = useState<string | null>(null);
  const {
    register,
    handleSubmit,
    setError,
    formState: { errors, isSubmitting },
  } = useForm<Values>({
    resolver: zodResolver(schema),
    defaultValues: { phone: "", password: "" },
  });

  const from = (location.state as { from?: string } | null)?.from ?? "/";

  const onSubmit = handleSubmit(async (values) => {
    setBanner(null);
    try {
      await login(phoneForApi(values.phone), values.password);
      navigate(from, { replace: true });
    } catch (error) {
      if (error instanceof ApiError) {
        applyFieldErrors(error, (name, err) => setError(name as keyof Values, err));
      }
      setBanner(errorMessage(error));
    }
  });

  return (
    <AuthShell
      title="Welcome back"
      subtitle="Log in to manage your store, orders and stock."
      footer={
        <>
          New store owner?{" "}
          <Link to="/register" className="font-semibold text-primary hover:underline">
            Create an account
          </Link>
        </>
      }
    >
      <FormBanner message={banner ?? notice} />
      <form onSubmit={onSubmit} className="space-y-4" noValidate>
        <Field label="Phone number" htmlFor="login-phone" error={errors.phone?.message}>
          <Input
            id="login-phone"
            type="tel"
            autoComplete="tel"
            placeholder="0712 345 678"
            {...register("phone")}
          />
        </Field>
        <Field label="Password" htmlFor="login-password" error={errors.password?.message}>
          <Input
            id="login-password"
            type="password"
            autoComplete="current-password"
            {...register("password")}
          />
        </Field>
        <div className="text-right">
          <Link
            to="/forgot-password"
            className="text-sm font-medium text-primary hover:underline"
          >
            Forgot password?
          </Link>
        </div>
        <Button type="submit" className="w-full" loading={isSubmitting}>
          Log in
        </Button>
      </form>
    </AuthShell>
  );
}
