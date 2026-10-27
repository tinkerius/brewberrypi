/** Shared Tailwind class lists, in the BrewberryPi brand colours (styles.css). */

const BUTTON =
  "inline-flex items-center justify-center rounded-lg px-4 py-2 text-sm font-medium shadow-xs transition " +
  "focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-berry dark:focus-visible:outline-berry-light " +
  "disabled:cursor-not-allowed disabled:opacity-40";

export const BUTTON_STYLES = {
  primary:
    `${BUTTON} bg-berry text-paper hover:enabled:bg-berry-hover ` +
    "dark:bg-berry-light dark:text-paper-dark dark:hover:enabled:bg-berry-light-hover",
  secondary:
    `${BUTTON} bg-white text-ink ring-1 ring-stone-300 ring-inset hover:enabled:bg-stone-50 ` +
    "dark:bg-white/10 dark:text-ink-light dark:ring-white/10 dark:hover:enabled:bg-white/20",
  // Stopping is a safety action: red, not a brand colour.
  danger:
    `${BUTTON} bg-white text-red-600 ring-1 ring-red-300 ring-inset hover:enabled:bg-red-50 ` +
    "dark:bg-white/10 dark:text-red-400 dark:ring-red-400/40 dark:hover:enabled:bg-red-500/10",
  dangerSolid: `${BUTTON} bg-red-600 text-white hover:enabled:bg-red-500`,
} as const;

export const SELECT_STYLE =
  "rounded-lg bg-white px-3 py-2 text-sm font-medium text-ink shadow-xs ring-1 ring-stone-300 ring-inset " +
  "focus-visible:outline-2 focus-visible:outline-berry disabled:cursor-not-allowed disabled:opacity-40 " +
  "dark:bg-white/10 dark:text-ink-light dark:ring-white/10 dark:focus-visible:outline-berry-light";

export const CARD_STYLE =
  "rounded-xl bg-white p-5 shadow-sm ring-1 ring-ink/5 sm:p-6 dark:bg-surface-dark dark:ring-white/10";

/** Card and dialog titles: the brand typeface (Zilla Slab). */
export const TITLE_STYLE = "font-brand text-lg font-medium text-ink dark:text-ink-light";
