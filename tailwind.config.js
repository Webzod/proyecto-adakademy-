/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ["./resources/templates/**/*.html"],
  theme: {
    extend: {
      fontFamily: { sans: ["Plus Jakarta Sans", "sans-serif"] },
      colors: {
        ink: "#171923",
        electric: "#5546f5",
        canvas: "#f7f8fc",
      },
    },
  },
  plugins: [],
};
