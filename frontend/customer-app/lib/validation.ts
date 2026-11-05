import { normalizePhone } from "@beverage/api";
import { z } from "zod";

export const phoneField = z
  .string()
  .trim()
  .min(1, "Phone number is required")
  .refine((value) => normalizePhone(value) !== null, {
    message: "Enter a valid Tanzanian number, e.g. 0712 345 678",
  });

export const passwordField = z
  .string()
  .min(8, "Use at least 8 characters");

/** Optional email: empty string means "none". */
export const optionalEmailField = z
  .string()
  .trim()
  .refine((v) => v === "" || z.string().email().safeParse(v).success, {
    message: "Enter a valid email or leave it empty",
  });

export const loginSchema = z.object({
  phone: phoneField,
  password: z.string().min(1, "Password is required"),
});
export type LoginForm = z.infer<typeof loginSchema>;

export const registerSchema = z
  .object({
    full_name: z.string().trim().min(2, "Enter your full name"),
    phone: phoneField,
    email: optionalEmailField,
    password: passwordField,
    confirm_password: z.string().min(1, "Confirm your password"),
  })
  .refine((v) => v.password === v.confirm_password, {
    path: ["confirm_password"],
    message: "Passwords do not match",
  });
export type RegisterForm = z.infer<typeof registerSchema>;

export const resetRequestSchema = z.object({ phone: phoneField });
export type ResetRequestForm = z.infer<typeof resetRequestSchema>;

export const resetConfirmSchema = z
  .object({
    code: z.string().trim().min(4, "Enter the code from your SMS"),
    new_password: passwordField,
    confirm_password: z.string().min(1, "Confirm your password"),
  })
  .refine((v) => v.new_password === v.confirm_password, {
    path: ["confirm_password"],
    message: "Passwords do not match",
  });
export type ResetConfirmForm = z.infer<typeof resetConfirmSchema>;

export const profileSchema = z.object({
  full_name: z.string().trim().min(2, "Enter your full name"),
  phone: phoneField,
  email: optionalEmailField,
});
export type ProfileForm = z.infer<typeof profileSchema>;

export const changePasswordSchema = z
  .object({
    current_password: z.string().min(1, "Enter your current password"),
    new_password: passwordField,
    confirm_password: z.string().min(1, "Confirm your new password"),
  })
  .refine((v) => v.new_password === v.confirm_password, {
    path: ["confirm_password"],
    message: "Passwords do not match",
  });
export type ChangePasswordForm = z.infer<typeof changePasswordSchema>;

const coordinate = (label: string, min: number, max: number) =>
  z
    .string()
    .trim()
    .refine(
      (v) => {
        if (v === "") return true;
        const n = Number(v);
        return Number.isFinite(n) && n >= min && n <= max;
      },
      { message: `${label} must be between ${min} and ${max}` },
    );

export const addressSchema = z.object({
  address_name: z.string().trim().min(1, "Give this address a name, e.g. Home"),
  address_line: z.string().trim().min(3, "Enter the street or building"),
  city: z.string().trim().min(2, "Enter the city"),
  area: z.string().trim(),
  phone: phoneField,
  latitude: coordinate("Latitude", -90, 90),
  longitude: coordinate("Longitude", -180, 180),
});
export type AddressForm = z.infer<typeof addressSchema>;

export function phoneForApi(value: string): string {
  return normalizePhone(value) ?? value.trim();
}
