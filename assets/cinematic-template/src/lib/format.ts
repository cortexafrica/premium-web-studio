/** Formatage unique des nombres affichés : ne jamais écrire un chiffre à la main dans le JSX. */
const LOCALE = 'fr-FR';

export function formatNumber(value: number, options?: Intl.NumberFormatOptions): string {
  return new Intl.NumberFormat(LOCALE, options).format(value);
}

/** Devises sans centimes courants (FCFA) : XAF (Afrique centrale), XOF (Afrique de l'Ouest). */
export function formatPrice(value: number, currency: string): string {
  const noDecimals = ['XAF', 'XOF'].includes(currency);
  return new Intl.NumberFormat(LOCALE, {
    style: 'currency',
    currency,
    maximumFractionDigits: noDecimals ? 0 : 2,
  }).format(value);
}
