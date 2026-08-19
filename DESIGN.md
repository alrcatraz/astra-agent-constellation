---
version: alpha
name: Constellation
description: IBM Carbon design language applied to the astra-agent-constellation documentation site — engineering-spec precision, single blue accent, zero radius, 8px grid.
colors:
  primary: "#161616"
  secondary: "#0F62FE"
  tertiary: "#525252"
  neutral: "#FFFFFF"
  surface: "#F4F4F4"
  border: "#C6C6C6"
  on-accent: "#FFFFFF"
typography:
  h1:
    fontFamily: "IBM Plex Sans, Noto Sans SC, Source Han Sans SC, PingFang SC, sans-serif"
    fontSize: 2.63rem
    fontWeight: 300
    lineHeight: 1.19
    letterSpacing: 0
  h2:
    fontFamily: "IBM Plex Sans, Noto Sans SC, Source Han Sans SC, PingFang SC, sans-serif"
    fontSize: 2rem
    fontWeight: 400
    lineHeight: 1.25
    letterSpacing: 0
  h3:
    fontFamily: "IBM Plex Sans, Noto Sans SC, Source Han Sans SC, PingFang SC, sans-serif"
    fontSize: 1.5rem
    fontWeight: 400
    lineHeight: 1.33
    letterSpacing: 0
  body-md:
    fontFamily: "IBM Plex Sans, Noto Sans SC, Source Han Sans SC, PingFang SC, sans-serif"
    fontSize: 1rem
    fontWeight: 400
    lineHeight: 1.5
    letterSpacing: 0
  caption:
    fontFamily: "IBM Plex Sans, Noto Sans SC, Source Han Sans SC, PingFang SC, sans-serif"
    fontSize: 0.875rem
    fontWeight: 400
    lineHeight: 1.29
    letterSpacing: "0.01em"
  code:
    fontFamily: "IBM Plex Mono, JetBrains Mono, Noto Sans Mono CJK SC, monospace"
    fontSize: 0.875rem
    fontWeight: 400
    lineHeight: 1.43
    letterSpacing: "0.01em"
rounded:
  sm: 0px
  md: 0px
  lg: 0px
spacing:
  sm: 8px
  md: 16px
  lg: 24px
  xl: 48px
components:
  link:
    textColor: "{colors.secondary}"
  link-hover:
    textColor: "#0043CE"
  button-primary:
    backgroundColor: "{colors.secondary}"
    textColor: "{colors.on-accent}"
    rounded: 0px
    height: 48px
  button-primary-hover:
    backgroundColor: "#0353E9"
  code-inline:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.primary}"
    rounded: 0px
  admonition-note:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.primary}"
    rounded: 0px
  table-header:
    backgroundColor: "{colors.primary}"
    textColor: "{colors.neutral}"
---

## Overview

This site applies IBM's Carbon design language — the same system behind
ibm.com — to the `astra-agent-constellation` blueprint documentation. The
visual identity is corporate precision distilled into pixels: a white canvas
with near-black (`#161616`) text, punctuated by a single unwavering accent,
IBM Blue 60 (`#0f62fe`). Every element snaps to the 8px grid; every radius is
0px; depth comes from background-colour layering, never shadows.

The design reads like an engineering specification rendered as a webpage —
the correct mood for a specification document about agent orchestration.

## Colors

- **Primary (#161616)** — Gray 100. Primary text, headings, header masthead,
  table header fills.
- **Secondary (#0F62FE)** — IBM Blue 60. The single interactive accent:
  links, focus states, active indicators.
- **Tertiary (#525252)** — Gray 70. Secondary text, helper text.
- **Neutral (#FFFFFF)** — White. Page background, text on blue.
- **Surface (#F4F4F4)** — Gray 10. Cards, alternating table rows.
- **Border (#C6C6C6)** — Gray 30. Divider lines, subtle borders.
- **On-accent (#FFFFFF)** — Text colour on blue surfaces.

Dark theme (slate): background Gray 100 (`#161616`), text Gray 10
(`#f4f4f4`), links shift to Blue 40 (`#78a9ff`) for contrast.

## Typography

IBM Plex Sans is the backbone: weight 300 (Light) for display headlines —
corporate gravitas through typographic restraint; 400 for body; 600 for
emphasis. Weight 700 is intentionally absent. IBM Plex Mono serves code.
Micro-tracking: 0.16px at 14px, 0.32px at 12px — never on display text.

Fonts load from the system stack (no Google Fonts CDN — the site must remain
loadable in mainland China): `IBM Plex Sans` first, falling back to
`Noto Sans SC` / `Source Han Sans SC` / `PingFang SC`, then generic
sans-serif. Users with IBM Plex installed get exact rendering; others get the
same hierarchy in CJK-safe faces.

## Layout & Spacing

- Base unit 8px (Carbon 2x grid). Layout scale: 16/24/32/48px.
- Content column: MkDocs Material default (max 61rem), 16px page gutter.
- Navigation: left sidebar (sections expanded) — the spec is read
  top-to-bottom.
- Functional density: sections are tightly packed; separation comes from
  background-colour zoning (white → Gray 10 → white), not whitespace padding.

## Elevation & Depth

Deliberately shadow-averse. Depth is communicated through background-colour
layering: white page → Gray 10 surface → Gray 20. Shadows are reserved
exclusively for floating elements (dropdowns, tooltips, modals). The sticky
header uses a 1px bottom border, not a shadow.

## Shapes

- Border radius is 0px everywhere: buttons, cards, tables, admonitions —
  rectangles are the identity.
- Sole exception: tags/labels may use pill radius (24px), per Carbon.

## Components

- `link` / `link-hover` — Blue 60, hover Blue 70 with underline.
- `button-primary` — Blue 60 fill, white text, 0px radius, 48px height.
- `code-inline` — Gray 10 chip, primary text, 0px radius.
- `admonition-note` — Gray 10 fill, primary text, 0px radius, 2px left
  border in Blue 60. `warning` uses Yellow 30 border, `danger` Red 60.
- `table-header` — Gray 100 fill, white text, weight 600.
- Header masthead — Gray 100 fill, white title, 48px height.

## Do's and Don'ts

- **Do** use Blue 60 as the sole accent; **don't** introduce a second hue.
- **Do** use 0px border radius; **don't** round corners — rectangles are the
  Carbon identity.
- **Do** layer background colours for depth; **don't** add card shadows.
- **Do** use weight 300 for display and 600 for emphasis; **don't** use 700.
- **Do** apply letter-spacing only at 14px and below; **don't** track display
  text.
- **Do** write token values here and reference `{colors.*}` in components;
  **don't** hard-code hex values outside this spec.
