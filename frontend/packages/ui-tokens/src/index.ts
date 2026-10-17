/**
 * Shared design tokens. A-11 will refine these against the mockups;
 * both apps import from here so colours stay in sync.
 */

export const colors = {
  light: {
    background: "#F5F7FB",
    surface: "#FFFFFF",
    text: "#172033",
    textMuted: "#5B6475",
    primary: "#147D55",
    primaryForeground: "#FFFFFF",
    secondary: "#174A8B",
    border: "#E4E8F0",
    success: "#16834A",
    danger: "#C62828",
    warning: "#B45309",
  },
  dark: {
    background: "#0B1220",
    surface: "#151E2E",
    text: "#F5F7FB",
    textMuted: "#9AA3B5",
    primary: "#2BB673",
    primaryForeground: "#062015",
    secondary: "#5B8FD9",
    border: "#243044",
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
