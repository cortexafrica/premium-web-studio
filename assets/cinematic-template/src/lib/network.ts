type NetworkInformation = { saveData?: boolean; effectiveType?: string };

/**
 * Vrai si le visiteur doit recevoir la version légère (image fixe au lieu de la séquence) :
 * mouvement réduit demandé, économiseur de données, réseau lent, ou ?lite=1 dans l'URL (pour tester).
 * L'API Network Information n'existe que sur Chromium (Chrome Android inclus) : ailleurs,
 * seuls le mouvement réduit et ?lite=1 s'appliquent.
 */
export function prefersLightExperience(): boolean {
  if (typeof window === 'undefined') return false;
  if (new URLSearchParams(window.location.search).get('lite') === '1') return true;
  if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) return true;
  const connection = (navigator as Navigator & { connection?: NetworkInformation }).connection;
  if (connection?.saveData) return true;
  return ['slow-2g', '2g', '3g'].includes(connection?.effectiveType ?? '');
}
