import { SignInButton, SignUpButton } from '@clerk/react'

export function Landing() {
  return (
    <section className="hero">
      <div>
        <p className="eyebrow">AI Personal Stylist</p>
        <h1>Scopri i colori, i capelli e lo stile che parlano di te.</h1>
        <p className="muted">
          Da un semplice ritratto Luméra individua la tua stagione cromatica, costruisce la tua palette e ti mostra
          hairstyle, colori, outfit e accessori direttamente sulla tua foto.
        </p>
        <div className="row" style={{ marginTop: 24 }}>
          <SignUpButton mode="modal">
            <button className="primary">Crea il tuo account</button>
          </SignUpButton>
          <SignInButton mode="modal">
            <button>Accedi</button>
          </SignInButton>
        </div>
      </div>
      <div className="card stack">
        <p className="eyebrow">Come funziona</p>
        <p><b>1.</b> Carica un ritratto in luce naturale</p>
        <p><b>2.</b> Scopri la tua stagione e la tua palette</p>
        <p><b>3.</b> Scegli lo stile che vuoi esprimere</p>
        <p><b>4.</b> Prova tagli, colori, outfit e occhiali sulla tua foto</p>
      </div>
    </section>
  )
}
