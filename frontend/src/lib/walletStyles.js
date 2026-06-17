/**
 * Curated color palettes for wallets.
 * Reordered: Natural/Solids -> Banks -> Gradients.
 * Readability: Darker stop always placed in top-left (from) for white text clarity.
 */

export const WALLET_STYLES = {
  // --- Natural / High-Contrast Solids ---
  "obsidian": {
    name: "Obsidian Black",
    className: "bg-black text-white ring-1 ring-white/20",
  },
  "charcoal": {
    name: "Charcoal",
    className: "bg-[#1F2937] text-white",
  },
  "default": {
    name: "Default Emerald",
    className: "bg-primary text-primary-foreground",
  },

  // --- Banks / Traditional ---
  "uzcard-blue": {
    name: "Uzcard Blue",
    className: "bg-linear-to-br from-[#005CB9] to-[#0078E8] text-white",
  },
  "humo-orange": {
    name: "Humo Orange",
    className: "bg-linear-to-br from-[#F05A28] to-[#FF8C69] text-white",
  },
  "visa-indigo": {
    name: "VISA Indigo",
    className: "bg-linear-to-br from-[#1A1F71] to-[#2B3A92] text-white",
  },
  "mastercard-red": {
    name: "Mastercard Red",
    className: "bg-linear-to-br from-[#EB001B] to-[#FF5F00] text-white",
  },

  // --- Premium Elite Gradients (Readability Flipped) ---
  "midnight-aurora": {
    name: "Aurora",
    className: "bg-linear-to-br from-[#0F172A] via-[#1E293B] to-[#581C87] text-white",
  },
  "electric-ocean": {
    name: "Electric Ocean",
    className: "bg-linear-to-br from-[#1E3A8A] via-[#1D4ED8] to-[#06B6D4] text-white",
  },
  "golden-emerald": {
    name: "Golden Emerald",
    className: "bg-linear-to-br from-[#064E3B] via-[#065F46] to-[#CA8A04] text-white",
  },
  "solar-eclipse": {
    name: "Solar Eclipse",
    className: "bg-linear-to-br from-[#000000] via-[#1F2937] to-[#D97706] text-white",
  },
  "rose-carbon": {
    name: "Rose Carbon",
    className: "bg-linear-to-br from-[#111827] via-[#374151] to-[#BE185D] text-white",
  },
  "titanium-burn": {
    name: "Titanium",
    className: "bg-linear-to-br from-[#334155] via-[#475569] to-[#6366f1] text-white",
  },
  "mahogany": {
    name: "Mahogany",
    className: "bg-linear-to-br from-[#000000] via-[#2D0606] to-[#450a0a] text-white",
  },
  "cosmic-void": {
    name: "Cosmic",
    className: "bg-linear-to-br from-[#000000] via-[#1e1b4b] to-[#4c1d95] text-white",
  },
  "ruby-wine": {
    name: "Ruby",
    className: "bg-linear-to-br from-[#50071C] via-[#881337] to-[#000000] text-white",
  },
  "royal-velvet": {
    name: "Royal Velvet",
    className: "bg-linear-to-br from-[#4C0519] to-[#881337] text-white",
  },
  "forest-deep": {
    name: "Forest",
    className: "bg-linear-to-br from-[#064e3b] to-[#065f46] text-white",
  },
  "glacier-melt": {
    name: "Glacier",
    className: "bg-linear-to-br from-[#1e3a8a] via-[#38bdf8] to-[#bae6fd] text-white",
  },
  "champagne": {
    name: "Champagne",
    className: "bg-linear-to-br from-[#92400E] via-[#D87D0F] to-[#FEF3C7] text-white",
  },
  "obsidian-pearl": {
    name: "Pearl",
    className: "bg-linear-to-br from-[#334155] via-[#94A3B8] to-[#F8FAFC] text-white",
  },
  "desert-mirage": {
    name: "Mirage",
    className: "bg-linear-to-br from-[#4c1d95] via-[#991b1b] to-[#7c2d12] text-white",
  },
  "cyber-pink": {
    name: "Cyber Pink",
    className: "bg-linear-to-br from-[#701a75] to-[#f472b6] text-white",
  },
  "midnight-purple": {
    name: "Midnight",
    className: "bg-linear-to-br from-[#1E293B] via-[#334155] to-[#475569] text-white",
  },
  "emerald-city": {
    name: "Emerald City",
    className: "bg-linear-to-br from-[#059669] to-[#10B981] text-white",
  },
  "ocean-deep": {
    name: "Ocean Deep",
    className: "bg-linear-to-br from-[#0C4A6E] to-[#0369A1] text-white",
  },
  "sunset-blaze": {
    name: "Sunset Blaze",
    className: "bg-linear-to-br from-[#BE123C] to-[#E11D48] text-white",
  },
  "lavender-dream": {
    name: "Lavender",
    className: "bg-linear-to-br from-[#6D28D9] to-[#7C3AED] text-white",
  }
};

export const WALLET_STYLE_KEYS = Object.keys(WALLET_STYLES);

export function getWalletStyle(key) {
  return WALLET_STYLES[key] || WALLET_STYLES["default"];
}
