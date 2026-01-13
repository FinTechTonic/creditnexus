// PostCSS configuration for TailwindCSS
// Using import syntax for ES modules compatibility

import tailwindcss from 'tailwindcss';
import autoprefixer from 'autoprefixer';

export default {
  plugins: [
    tailwindcss(),
    autoprefixer(),
  ],
};

