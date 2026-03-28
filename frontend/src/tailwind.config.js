/** @type {import('tailwindcss').Config} */
export default {
  theme: {
    extend: {
      spacing: {
        page: "var(--page-px)",
        card: "var(--card-px)",
      },
      fontSize: {
        "ui-h1": "var(--font-h1)",
        "ui-title": "var(--font-ui-title)",
        "ui-desc": "var(--font-ui-desc)",
        "ui-detail": "var(--font-ui-detail)",
        "ui-amount": "var(--font-ui-amount)",
        "exp-title": "var(--title-size)",
        "exp-detail": "var(--detail-size)",
        pag: "var(--pag-font)",
        'table-title': 'var(--table-title)',
        'table-detail': 'var(--table-detail)',
        'table-amount': 'var(--table-amount)',
      },
      size: {
        'icon-sm': 'var(--size-icon-sm)',
        'icon-md': 'var(--size-icon-md)',
        'icon-lg': 'var(--size-icon-lg)',
      },
      height: {
        'btn': 'var(--size-btn-h)',
        'exp-icon': 'var(--icon-size)',
        'pag-btn': 'var(--pag-btn-h)',
      },
      width: {
        'exp-icon': 'var(--icon-size)',
        'pag-btn': 'var(--pag-btn-h)',
      },
      gap: {
        'rowg': 'var(--row-gap)',
      },
      fontFamily: {
        sans: [
          "Inter",
          "system-ui",
          "-apple-system",
          "BlinkMacSystemFont",
          "Segoe UI",
          "Roboto",
          "Helvetica",
          "Arial",
          "sans-serif",
        ],
      },
    },
  },
};
