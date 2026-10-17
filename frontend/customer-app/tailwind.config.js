/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ["./app/**/*.{js,jsx,ts,tsx}", "./components/**/*.{js,jsx,ts,tsx}"],
  presets: [require("nativewind/preset")],
  theme: {
    extend: {
      colors: {
        background: "#0B1220",
        surface: "#151E2E",
        foreground: "#F5F7FB",
        muted: "#9AA3B5",
        primary: "#2BB673",
        danger: "#F87171",
      },
    },
  },
  plugins: [],
};
