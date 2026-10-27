/** A browser language the page can format numbers with (UI-020).
 *
 * Browsers can report a language tag that `Intl` rejects: Chromium on Linux without a system locale (a kiosk on the
 * Pi, `LANG` unset) reports `en-US@posix`. uPlot creates `new Intl.NumberFormat(navigator.language)` when it loads,
 * which throws for such a tag and stopped the whole page before it rendered. main.tsx imports this module first, so
 * that `navigator.language` is valid before uPlot loads. */

const FALLBACK_LANGUAGE = "en-US";

function isValid(tag: string): boolean {
  try {
    return Intl.getCanonicalLocales(tag).length === 1;
  } catch {
    return false;
  }
}

/** `tag` if `Intl` accepts it, else its POSIX-style form cleaned up (`en_US.UTF-8@posix` → `en-US`), else en-US. */
export function validLanguage(tag: string | undefined): string {
  const cleaned = tag?.split(/[@.]/)[0]?.replace(/_/g, "-");
  return [tag, cleaned].find((candidate) => candidate !== undefined && isValid(candidate)) ?? FALLBACK_LANGUAGE;
}

/** Replaces an invalid `navigator.language` with a valid one; a valid one stays as it is. */
export function fixLanguage(nav: { readonly language: string }): void {
  const language = validLanguage(nav.language);
  if (language !== nav.language) {
    Object.defineProperty(nav, "language", { value: language, configurable: true });
  }
}

if (typeof navigator !== "undefined") {
  fixLanguage(navigator);
}
