import colors from 'tailwindcss/colors';

// Explicit fallbacks retain Classic's original Tailwind colors, including alpha variants.
const themed = (name, hex) => {
  const rgb = hex.match(/\w\w/g).map(value => parseInt(value, 16)).join(' ');
  return `rgb(var(--ui-${name}, ${rgb}) / <alpha-value>)`;
};
const tones = ['amber', 'emerald', 'blue', 'green', 'red', 'rose', 'purple', 'indigo', 'cyan', 'teal', 'orange', 'yellow'];
const statusColors = Object.fromEntries(tones.flatMap(tone =>
  ['ink', 'fill', 'line'].map(role => [`ui-${role}-${tone}`, Object.fromEntries(
    Object.entries(colors[tone]).map(([shade, hex]) => [shade, themed(`${role}-${tone}-${shade}`, hex)]),
  )]),
));

/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        ...statusColors,
        'ui-heading': themed('heading', '#ffffff'),
        'ui-primary': themed('primary', colors.slate[100]),
        'ui-secondary': themed('secondary', colors.slate[200]),
        'ui-body': themed('body-text', colors.slate[300]),
        'ui-muted': themed('muted', colors.slate[400]),
        'ui-subtle': themed('subtle', colors.slate[500]),
        'ui-faint': themed('faint', colors.slate[600]),
        'ui-page': themed('page', colors.slate[950]),
        'ui-panel': themed('panel', colors.slate[900]),
        'ui-raised': themed('raised', colors.slate[800]),
        'ui-hover': themed('hover', colors.slate[700]),
        'ui-fill-muted': themed('fill-muted', colors.slate[600]),
        'ui-line-soft': themed('line-soft', colors.slate[800]),
        'ui-line': themed('line', colors.slate[700]),
        'ui-line-strong': themed('line-strong', colors.slate[600]),
        'ui-line-subtle': themed('line-subtle', colors.slate[900]),
        'ui-overlay': themed('overlay', '#000000'),
        'ui-on-action': themed('on-action', '#ffffff'),
        'ui-on-action-icon': themed('on-action-icon', colors.amber[200]),
        'ui-on-color': themed('on-color', '#ffffff'),
        'ui-brand-mark': themed('brand-mark', colors.amber[50]),
        brand: {
          50: '#fbf8f3',
          100: '#f5efe4',
          200: '#ebdcc5',
          300: '#dec29f',
          400: '#cfa276',
          500: '#c28654',
          600: '#b47045',
          700: '#965839',
          800: '#794732',
          900: '#643c2c',
        }
      },
      borderRadius: {
        lg: 'var(--ui-radius-lg, 0.5rem)',
        xl: 'var(--ui-radius-xl, 0.75rem)',
        '2xl': 'var(--ui-radius-2xl, 1rem)',
      },
    },
  },
  plugins: [],
}
