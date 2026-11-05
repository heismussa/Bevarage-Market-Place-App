/**
 * Shared BeverageMart brand tokens.
 * Palette: #021024 #052659 #5483B3 #7DA0CA #C1E8FF
 */

export const brand = {
  navy950: "#021024",
  navy800: "#052659",
  navy700: "#173B65",
  navy600: "#082C54",
  blue500: "#5483B3",
  blue400: "#7DA0CA",
  blue100: "#C1E8FF",
  canvas: "#F4F8FC",
  borderLight: "#DCE8F3",
} as const;

export const colors = {
  light: {
    background: brand.canvas,
    sidebar: "#FFFFFF",
    surface: "#FFFFFF",
    surfaceMuted: "#EAF2F9",
    input: "#FFFFFF",
    text: brand.navy950,
    textMuted: brand.blue500,
    primary: brand.navy800,
    primaryHover: brand.navy950,
    primaryForeground: "#FFFFFF",
    primarySoft: brand.blue100,
    secondary: brand.blue500,
    border: brand.borderLight,
    success: "#16834A",
    danger: "#C62828",
    warning: "#B45309",
  },
  dark: {
    background: brand.navy950,
    sidebar: brand.navy950,
    surface: brand.navy800,
    surfaceMuted: brand.navy600,
    input: brand.navy600,
    text: "#FFFFFF",
    textMuted: brand.blue400,
    primary: brand.blue100,
    primaryHover: brand.blue400,
    primaryForeground: brand.navy950,
    primarySoft: brand.navy700,
    secondary: brand.blue400,
    border: brand.navy700,
    success: "#34D399",
    danger: "#F87171",
    warning: "#FBBF24",
  },
} as const;

export const spacing = {
  xs: 4,
  sm: 8,
  md: 16,
  lg: 24,
  xl: 32,
  "2xl": 48,
} as const;

export const radius = {
  sm: 6,
  md: 12,
  lg: 16,
  xl: 24,
} as const;

export type ColorScheme = keyof typeof colors;
