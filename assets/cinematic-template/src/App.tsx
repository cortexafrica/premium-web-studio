import { useEffect } from 'react';
import { ScrollSequence, type Beat } from './components/ScrollSequence';
import { startSmoothScroll } from './lib/smooth-scroll';
import { content } from './content';

export default function App() {
  useEffect(() => startSmoothScroll(), []);

  const beats: Beat[] = content.sequence.beats.map((beat, index, all) => ({
    from: beat.from,
    to: beat.to,
    position: index === all.length - 1 ? 'center' : 'start',
    content: (
      <>
        {index === 0 ? <h1 className="beat__title">{beat.title}</h1> : <h2 className="beat__title">{beat.title}</h2>}
        {beat.text && <p className="beat__text">{beat.text}</p>}
        {index === all.length - 1 && (
          <a className="button" href={content.cta.href}>{content.cta.label}</a>
        )}
      </>
    ),
  }));

  return (
    <>
      <header className="site-header">
        <a href="/" className="site-header__brand">{content.brand}</a>
        <a href={content.cta.href} className="button button--small">{content.cta.label}</a>
      </header>

      <main>
        <ScrollSequence
          manifestUrl="/frames/manifest.json"
          alt={content.sequence.alt}
          scrollLength={4}
          beats={beats}
        />

        <section className="section proof" aria-labelledby="proof-title">
          <h2 id="proof-title" className="section__title">{content.proof.title}</h2>
          <ul className="proof__list">
            {content.proof.items.map((item) => (
              <li key={item.author}>
                <blockquote>
                  <p>{item.quote}</p>
                  <footer>{item.author}</footer>
                </blockquote>
              </li>
            ))}
          </ul>
        </section>

        <section id="offre" className="section offer" aria-labelledby="offer-title">
          <img className="offer__image" src={content.offer.image} alt={content.offer.imageAlt} loading="lazy" width={1200} height={1500} />
          <div className="offer__body">
            <h2 id="offer-title" className="section__title">{content.offer.title}</h2>
            <p>{content.offer.description}</p>
            <ul className="offer__details">
              {content.offer.details.map((detail) => <li key={detail}>{detail}</li>)}
            </ul>
            <p className="offer__price">{content.offer.price}</p>
            <a className="button" href={content.cta.href}>{content.cta.label}</a>
          </div>
        </section>

        <section className="section faq" aria-labelledby="faq-title">
          <h2 id="faq-title" className="section__title">Questions fréquentes</h2>
          {content.faq.map((item) => (
            <details key={item.q} className="faq__item">
              <summary>{item.q}</summary>
              <p>{item.a}</p>
            </details>
          ))}
        </section>
      </main>

      <footer className="site-footer">
        <p>{content.footer.legal}</p>
      </footer>
    </>
  );
}
