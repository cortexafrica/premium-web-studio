# Chiffres exacts : registre des faits et vérification

Un chiffre faux sur un site client (prix, surface, délai, stock, capital, statistique) coûte plus cher qu'un défaut de design : il engage la marque, peut tromper un acheteur et détruit la confiance. Les graphiques sont le cas le plus dangereux, parce qu'une erreur de calcul y est invisible à l'œil. Exemple réel rencontré en test : une grille de 400 carrés légendée « chaque carré vaut 500 actions » pour un capital de 20 000 actions (il fallait 50).

## 1. Règles

1. **Un seul registre** : `studio/facts.json` contient chaque chiffre destiné à être affiché, avec sa source. Le projet en utilise une copie : `src/facts.json` (ou l'équivalent de la stack).
2. **Aucun chiffre saisi à la main** dans les textes (`content.ts`), le JSX, le Liquid ou le CSS affiché. Les textes interpolent les valeurs du registre ; le formatage passe par `src/lib/format.ts`.
3. **Les valeurs calculées sont déclarées** dans `derived` avec leur formule (nombre de carrés, pourcentage, prix au m², économie réalisée), jamais calculées de tête.
4. **Chaque visuel de données déclare son contrôle** avec `registerFactCheck` (`src/lib/fact-checks.ts`) : valeur attendue calculée depuis le registre, valeur réellement rendue (nombre d'éléments dessinés, largeur de barre en %, total affiché).
5. **Jamais de chiffre incrusté dans une image générée** (Higgsfield ou autre) : il ne peut pas être vérifié et se déforme souvent. Le chiffre est du texte HTML posé sur l'image.
6. **Rien d'inventé** : un chiffre non fourni par le client reste un emplacement `[À confirmer]`, signalé à la livraison.

## 2. Format de `studio/facts.json`

```json
{
  "facts": [
    { "id": "offer.price", "label": "Prix du pack", "value": 25000, "unit": "XAF", "source": "message client du 12/09" },
    { "id": "delivery.days", "label": "Délai de livraison", "value": 2, "unit": "jours", "source": "conditions de vente" },
    { "id": "capital.shares", "label": "Nombre d'actions", "value": 20000, "unit": "actions", "source": "projet de statuts" },
    { "id": "grid.unit", "label": "Actions par carré", "value": 50, "unit": "actions", "source": "choix de représentation" }
  ],
  "derived": [
    { "id": "grid.squares", "label": "Carrés affichés", "formula": "capital.shares / grid.unit" }
  ],
  "allowed_numbers": [2026],
  "ignore_patterns": ["\\+237[\\d ]+"]
}
```

- `source` est obligatoire et précise : document, message, page du site existant, choix de design.
- `aliases` (facultatif, sur un fait) : autres écritures du même nombre (ex. `2` pour « 2 M FCFA » quand la valeur est 2000000).
- `allowed_numbers` et `ignore_patterns` : réservés aux nombres qui ne sont pas des faits (année du copyright, numéro de téléphone, numéro de version). Ne jamais s'en servir pour faire taire une alerte.

## 3. Visuels de données

```tsx
import { useEffect, useRef } from 'react';
import facts from '../facts.json';
import { registerFactCheck } from '../lib/fact-checks';

const value = (id: string) => {
  const fact = facts.facts.find((f) => f.id === id);
  if (!fact) throw new Error(`Fait manquant : ${id}`);
  return fact.value;
};

export function CapitalGrid() {
  const ref = useRef<HTMLDivElement>(null);
  const squares = value('capital.shares') / value('grid.unit');

  useEffect(() => {
    registerFactCheck({
      name: 'grille du capital',
      fact: 'grid.squares',
      expected: squares,
      actual: ref.current?.children.length ?? 0,
    });
  });

  return (
    <div ref={ref} className="grid" aria-hidden="true">
      {Array.from({ length: squares }, (_, i) => <span key={i} />)}
    </div>
  );
}
```

La légende du graphique affiche `value('grid.unit')` formaté, pas un nombre écrit à la main.

## 4. Vérification

```bash
cp studio/facts.json src/facts.json      # après toute modification du registre
npm run build && npm run preview &
python3 <skill>/scripts/check_facts.py http://localhost:4173 --facts studio/facts.json --out studio/review/facts-report.json
```

Le script rend la page, extrait tous les nombres visibles (texte, `alt`, `aria-label`, `title`, métadonnées) et lit `window.__FACT_CHECKS__`.

- **« Nombre non sourcé »** : soit le chiffre manque au registre (l'ajouter avec sa source, ou le remplacer par une valeur du registre), soit c'est une erreur (le corriger). Les ordinaux (1er, 3e) sont ignorés automatiquement.
- **« Visuel … attendu X, rendu Y »** : le composant ne dessine pas ce qu'il devrait, ou la valeur attendue ne correspond pas au fait déclaré. Corriger le calcul, pas le contrôle.
- Aucun contrôle visuel déclaré alors que la page contient un graphique, une jauge ou un compteur : c'est un oubli à corriger.

Le script doit terminer sur « RÉSULTAT : OK » avant tout déploiement.

## 5. Relecture humaine

Au point de validation avant livraison, présenter à l'utilisateur un tableau court : chiffre affiché → où il apparaît → source. C'est la seule façon de détecter une source elle-même fausse (un prix périmé, un délai optimiste), ce qu'aucun script ne voit.
