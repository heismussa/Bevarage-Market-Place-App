/** @type {import('tailwindcss').Config} */
/** Brand palette: #021024 #052659 #5483B3 #7DA0CA #C1E8FF */
module.exports = {
  content: [
    "./app/**/*.{js,jsx,ts,tsx}",
    "./components/**/*.{js,jsx,ts,tsx}",
    "./lib/**/*.{js,jsx,ts,tsx}",
  ],
  presets: [require("nativewind/preset")],
  theme: {
    extend: {
      colors: {
        background: "#021024",
        surface: "#052659",
        "surface-muted": "#082C54",
        foreground: "#FFFFFF",
        muted: "#7DA0CA",
        primary: "#C1E8FF",
        "primary-foreground": "#021024",
        "primary-soft": "#173B65",
        border: "#173B65",
        danger: "#F87171",
        success: "#34D399",
        warning: "#FBBF24",
        secondary: "#7DA0CA",
      },
    },
  },
  plugins: [],
};
