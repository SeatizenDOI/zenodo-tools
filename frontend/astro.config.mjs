// @ts-check
import { defineConfig } from 'astro/config';

// https://astro.build/config
export default defineConfig({
  i18n: {
    locales: ["fr", "en"],
    defaultLocale: "fr",
    routing: {
        prefixDefaultLocale: true
    }
  }
})