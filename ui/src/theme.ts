declare global {
  interface Window {
    __TOOLATLAS_PRIMARY_COLOR__?: string;
  }
}

function hexToRgb(hex: string): [number, number, number] {
  const h = hex.replace("#", "");
  return [
    parseInt(h.substring(0, 2), 16),
    parseInt(h.substring(2, 4), 16),
    parseInt(h.substring(4, 6), 16),
  ];
}

function rgbToHex(r: number, g: number, b: number): string {
  return (
    "#" +
    [r, g, b]
      .map((c) => {
        const v = Math.round(Math.max(0, Math.min(255, c)));
        return v.toString(16).padStart(2, "0");
      })
      .join("")
  );
}

function mix(hex1: string, hex2: string, weight: number): string {
  const [r1, g1, b1] = hexToRgb(hex1);
  const [r2, g2, b2] = hexToRgb(hex2);
  return rgbToHex(
    r1 + (r2 - r1) * weight,
    g1 + (g2 - g1) * weight,
    b1 + (b2 - b1) * weight
  );
}

function lighten(hex: string, amount: number): string {
  return mix(hex, "#ffffff", amount);
}

function darken(hex: string, amount: number): string {
  return mix(hex, "#000000", amount);
}

export function generateShades(baseHex: string): Record<string, string> {
  return {
    "50": lighten(baseHex, 0.95),
    "100": lighten(baseHex, 0.9),
    "200": lighten(baseHex, 0.8),
    "300": lighten(baseHex, 0.6),
    "400": lighten(baseHex, 0.35),
    "500": baseHex,
    "600": darken(baseHex, 0.05),
    "700": darken(baseHex, 0.15),
    "800": darken(baseHex, 0.25),
    "900": darken(baseHex, 0.4),
    "950": darken(baseHex, 0.55),
  };
}

export function applyTheme(): void {
  const color = window.__TOOLATLAS_PRIMARY_COLOR__ || "#2563eb";
  const shades = generateShades(color);
  const root = document.documentElement;
  for (const [key, value] of Object.entries(shades)) {
    root.style.setProperty(`--primary-${key}`, value);
  }
}

export const primary = (shade: string | number) => `var(--primary-${shade})`;

export const cssVar = (shade: string | number) => `var(--primary-${shade})`;

export function getComputedColor(shade: string | number): string {
  return getComputedStyle(document.documentElement).getPropertyValue(`--primary-${shade}`).trim() || "#3b82f6";
}
