import { useState } from 'react'
import { STYLES, STYLE_IT } from '../labels'
import type { StyleRequest } from '../types'

interface Props {
  initial: StyleRequest | null
  onSubmit: (req: StyleRequest) => void
}

const TRENDS = [
  { value: 'low', label: 'Senza tempo' },
  { value: 'moderate', label: 'Equilibrato' },
  { value: 'high', label: 'Di tendenza' },
] as const

export function StylePicker({ initial, onSubmit }: Props) {
  const [styles, setStyles] = useState<string[]>(initial?.selected_styles ?? [])
  const [trend, setTrend] = useState<StyleRequest['trend_preference']>(initial?.trend_preference ?? 'moderate')
  const [freeText, setFreeText] = useState(initial?.free_text_style_request ?? '')
  const [occasion, setOccasion] = useState(initial?.occasion ?? '')
  const [comfort, setComfort] = useState(initial?.comfort_preferences ?? '')

  // First click = primary style, second = optional secondary.
  const toggle = (s: string) =>
    setStyles((cur) => (cur.includes(s) ? cur.filter((x) => x !== s) : cur.length < 2 ? [...cur, s] : [cur[0], s]))

  return (
    <section className="card stack">
      <div>
        <h2>Che immagine vuoi esprimere?</h2>
        <p className="muted">Scegli uno stile principale e, se vuoi, uno secondario.</p>
      </div>
      <div className="row">
        {STYLES.map((s) => {
          const idx = styles.indexOf(s)
          return (
            <button key={s} className={`chip ${idx >= 0 ? 'selected' : ''}`} onClick={() => toggle(s)}>
              {STYLE_IT[s]}{idx === 0 && styles.length > 1 ? ' · 1°' : idx === 1 ? ' · 2°' : ''}
            </button>
          )
        })}
      </div>
      <div>
        <p className="eyebrow">Rapporto con le tendenze</p>
        <div className="toggle">
          {TRENDS.map((t) => (
            <button key={t.value} className={trend === t.value ? 'selected' : ''} onClick={() => setTrend(t.value)}>
              {t.label}
            </button>
          ))}
        </div>
      </div>
      <div className="grid grid-3">
        <label>
          <span className="eyebrow">Occasione (opzionale)</span>
          <input value={occasion} onChange={(e) => setOccasion(e.target.value)} placeholder="es. ufficio, cena, weekend" />
        </label>
        <label>
          <span className="eyebrow">Comfort e guardaroba</span>
          <input value={comfort} onChange={(e) => setComfort(e.target.value)} placeholder="es. niente tacchi, amo i blazer" />
        </label>
        <label>
          <span className="eyebrow">Altro da sapere</span>
          <input value={freeText} onChange={(e) => setFreeText(e.target.value)} placeholder="es. voglio un look più deciso" />
        </label>
      </div>
      <button
        className="primary"
        disabled={styles.length === 0}
        onClick={() => onSubmit({
          selected_styles: styles,
          trend_preference: trend,
          free_text_style_request: freeText,
          occasion,
          comfort_preferences: comfort,
        })}
      >
        Crea i miei suggerimenti
      </button>
    </section>
  )
}
