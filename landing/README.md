# LegalEase Landing Site

This directory contains the public marketing and documentation site that accompanies the LegalEase application. It is a Nuxt Content project powered by Nuxt UI.

## Local Development

```bash
cd landing
pnpm install
pnpm dev
```

The site runs on http://localhost:3100 by default (Nuxt picks an available port). The content in `content/` powers the documentation navigation.

## Building for Production

```bash
pnpm build
pnpm preview
```

## Content Structure

- `content/0.index.yml` – landing page hero and feature highlights
- `content/1.docs` – docs navigation, split into Getting Started and Essentials sections
- `content/4.changelog` – release notes displayed on the landing page

If you update documentation inside this directory, make sure it stays in sync with the main repository README.
