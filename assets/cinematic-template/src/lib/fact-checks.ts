/**
 * Contrôles lus par scripts/check_facts.py.
 * Tout composant qui dessine une donnée (grille, barre, jauge, compteur, carte de prix)
 * déclare ici la valeur attendue (calculée depuis src/facts.json) et la valeur réellement rendue.
 */
export type FactCheck = {
  /** Nom lisible du visuel, ex. « grille du capital » */
  name: string;
  /** Identifiant du fait ou du dérivé dans facts.json, si le visuel en représente un */
  fact?: string;
  expected: number;
  actual: number;
};

declare global {
  interface Window {
    __FACT_CHECKS__?: FactCheck[];
  }
}

export function registerFactCheck(check: FactCheck): void {
  if (typeof window === 'undefined') return;
  const list = (window.__FACT_CHECKS__ ??= []);
  const index = list.findIndex((c) => c.name === check.name);
  if (index >= 0) list[index] = check;
  else list.push(check);
}
