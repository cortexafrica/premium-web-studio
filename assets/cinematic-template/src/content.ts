/**
 * Tout le texte du site vient d'ici, rempli depuis studio/brief.md.
 * Règle : aucune valeur entre crochets ne doit rester au moment du déploiement
 * (vérification : grep -n "\[" src/content.ts).
 */
export const content = {
  brand: '[Nom de marque]',
  cta: {
    label: '[Action précise : Commander, Réserver un appel…]',
    // Lien de paiement, formulaire, page produit Shopify ou WhatsApp (https://wa.me/<numéro>?text=…)
    href: '#offre',
  },
  sequence: {
    alt: '[Description de ce que montre la séquence, pour les lecteurs d\'écran]',
    beats: [
      { from: 0, to: 0.22, title: '[Promesse principale, 4 à 8 mots]', text: '[Pour qui et quel résultat, une phrase]' },
      { from: 0.3, to: 0.52, title: '[Premier bénéfice concret]', text: '[Preuve ou détail tangible]' },
      { from: 0.6, to: 0.8, title: '[Deuxième bénéfice ou matière]', text: '[Détail sensoriel ou chiffré]' },
      { from: 0.86, to: 1, title: '[Phrase qui déclenche l\'action]', text: '' },
    ],
  },
  proof: {
    title: '[Titre de preuve : ce que disent les clients, chiffres réels]',
    items: [
      { quote: '[Témoignage réel, jamais inventé]', author: '[Prénom, ville ou fonction]' },
    ],
  },
  offer: {
    title: '[Nom de l\'offre ou du produit]',
    description: '[Ce que la personne reçoit, en langage simple]',
    // Ne jamais écrire le prix ici : App.tsx l'affiche avec formatPrice() depuis src/facts.json (fait offer.price)
    price: '[Prix : vient de src/facts.json]',
    details: ['[Détail 1]', '[Détail 2]', '[Détail 3]'],
    image: '/images/offer.webp',
    imageAlt: '[Description de l\'image produit]',
  },
  faq: [
    { q: '[Objection fréquente n°1 : livraison, délai, paiement…]', a: '[Réponse directe]' },
  ],
  footer: {
    legal: '[Mentions : raison sociale, contact]',
  },
};
