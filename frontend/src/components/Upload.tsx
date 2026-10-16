import { useRef, useState } from 'react'

interface Props {
  onSubmit: (file: File) => void
  guidance?: string
  title?: string
}

export function Upload({ onSubmit, guidance, title }: Props) {
  const input = useRef<HTMLInputElement>(null)
  const [file, setFile] = useState<File | null>(null)
  const [preview, setPreview] = useState<string | null>(null)
  const [drag, setDrag] = useState(false)

  const pick = (f: File | undefined) => {
    if (!f || !f.type.startsWith('image/')) return
    setFile(f)
    setPreview(URL.createObjectURL(f))
  }

  return (
    <section className="hero">
      <div>
        <p className="eyebrow">AI Personal Stylist</p>
        <h1>{title ?? 'Scopri i colori, i capelli e lo stile che parlano di te.'}</h1>
        {guidance ? (
          <p className="notice">{guidance}</p>
        ) : (
          <p className="muted">
            Carica un ritratto: Luméra individua la tua stagione cromatica, costruisce la tua palette e ti
            mostra hairstyle, colori e look direttamente sulla tua foto.
          </p>
        )}
        <ul className="tips">
          <li>Viso frontale e ben visibile</li>
          <li>Luce naturale indiretta, senza filtri</li>
          <li>Sfondo neutro, capelli visibili</li>
        </ul>
      </div>

      <div className="stack">
        <div
          className={`dropzone ${drag ? 'drag' : ''}`}
          onClick={() => input.current?.click()}
          onDragOver={(e) => { e.preventDefault(); setDrag(true) }}
          onDragLeave={() => setDrag(false)}
          onDrop={(e) => { e.preventDefault(); setDrag(false); pick(e.dataTransfer.files[0]) }}
        >
          {preview && <img src={preview} alt="Anteprima ritratto" />}
          <p>{file ? file.name : 'Trascina qui il tuo ritratto o clicca per sceglierlo'}</p>
          <input ref={input} type="file" accept="image/*" hidden onChange={(e) => pick(e.target.files?.[0])} />
        </div>
        <button className="primary" disabled={!file} onClick={() => file && onSubmit(file)} style={{ width: '100%' }}>
          Analizza il mio stile
        </button>
      </div>
    </section>
  )
}
