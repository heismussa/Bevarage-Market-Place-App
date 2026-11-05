import { ApiError, applyFieldErrors } from "@beverage/api";
import { zodResolver } from "@hookform/resolvers/zod";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { Link, useNavigate } from "react-router";
import { z } from "zod";

import { AuthShell, FormBanner } from "@/pages/auth/AuthShell";
import { Button } from "@/components/ui/button";
import { Field, Input } from "@/components/ui/input";
import { errorMessage } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { passwordSchema, phoneForApi, phoneSchema } from "@/lib/validation";

const schema = z
  .object({
    full_name: z.string().trim().min(2, "Enter your full name."),
    phone: phoneSchema,
    email: z
      .string()
      .trim()
      .refine((value) => value === "" || z.email().safeParse(value).success, {
        message: "Enter a valid email address.",
      }),
    password: passwordSchema,
    confirm: z.string(),
  })
  .refine((values) => values.password === values.confirm, {
    path: ["confirm"],
    message: "Passwords do not match.",
  });
type Values = z.infer<typeof schema>;

export default function RegisterPage() {
  const { register: registerOwner } = useAuth();
  const navigate = useNavigate();
  const [banner, setBanner] = useState<string | null>(null);
  const {
    register,
    handleSubmit,
    setError,
    formState: { errors, isSubmitting },
  } = useForm<Values>({
    resolver: zodResolver(schema),
    defaultValues: { full_name: "", phone: "", email: "", password: "", confirm: "" },
  });

  const onSubmit = handleSubmit(async (values) => {
    setBanner(null);
    try {
      await registerOwner({
        full_name: values.full_name.trim(),
        phone: phoneForApi(values.phone),
        password: values.password,
        email: values.email || null,
      });
      navigate("/store/new", { replace: true });
    } catch (error) {
      if (error instanceof ApiError) {
        applyFieldErrors(error, (name, err) => setError(name as keyof Values, err));
      }
      setBanner(errorMessage(error));
    }
  });

  return (
    <AuthShell
      title="Create your owner account"
      subtitle="Register as a store owner, then set up your store."
      footer={
        <>
          Already registered?{" "}
          <Link to="/login" className="font-semibold text-primary hover:underline">
            Log in
          </Link>
        </>
      }
    >
      <FormBanner message={banner} />
      <form onSubmit={onSubmit} className="space-y-4" noValidate>
        <Field label="Full name" htmlFor="reg-name" error={errors.full_name?.message}>
          <Input id="reg-name" autoComplete="name" {...register("full_name")} />
        </Field>
        <Field label="Phone number" htmlFor="reg-phone" error={errors.phone?.message}>
          <Input
            id="reg-phone"
            type="tel"
            autoComplete="tel"
            placeholder="0712 345 678"
            {...register("phone")}
          />
        </Field>
        <Field
          label="Email (optional)"
          htmlFor="reg-email"
          error={errors.email?.message}
        >
          <Input id="reg-email" type="email" autoComplete="email" {...register("email")} />
        </Field>
        <Field label="Password" htmlFor="reg-password" error={errors.password?.message}>
          <Input
            id="reg-password"
            type="password"
            autoComplete="new-password"
            {...register("password")}
          />
        </Field>
        <Field
          label="Confirm password"
          htmlFor="reg-confirm"
          error={errors.confirm?.message}
        >
          <Input
            id="reg-confirm"
            type="password"
            autoComplete="new-password"
            {...register("confirm")}
          />
        </Field>
        <Button type="submit" className="w-full" loading={isSubmitting}>
          Create account
        </Button>
      </form>
    </AuthShell>
  );
}
