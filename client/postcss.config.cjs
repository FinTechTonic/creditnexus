// PostCSS configuration for TailwindCSS
// Using CommonJS syntax for better compatibility

module.exports = {
  plugins: [
    require('tailwindcss'),
    require('autoprefixer'),
  ],
};

