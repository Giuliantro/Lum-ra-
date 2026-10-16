import { useState } from 'react'
import type { Me } from '../types'

interface Props {
  me: Me
  onSubmit: (body: { first_name: string; last_name: string; age: number }) => Promise<void>
  onCancel?: () => void
}

export function Onboarding({ me, onSubmit, onCancel }: Props) {
  const [firstName, setFirstName] = useState(me.first_name ?? '')
  const [lastName, setLastName] = useState(me.last_name ?? '')
  const [age, setAge] = useState(me.age ? String(me.age) : '')
  const [saving, setSaving] = useState(false)

  const ageNum = Number(age)
  const valid = firstName.trim() && lastName.trim() && Number.isInteger(ageNum) && ageNum >= 14 && ageNum <= 120

  const submit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!valid) return
    setSaving(true)
    try {
      await onSubmit({ first_name: firstName.trim(), last_name: lastName.trim(), age: ageNum })
    } finally {
      setSaving(false)
    }
  }

  return (
    <form className="card stack narrow" onSubmit={submit}>
      <div>
        <h2>{onCancel ? 'I tuoi dati' : 'Ti diamo il benvenuto in Luméra'}</h2>
        {!onCancel && <p className="muted">Completa il tuo profilo per iniziare.</p>}
      </div>
      <label>
        <span className="eyebrow">Email</span>
        <input value={me.email} disabled />
      </label>
      <div className="grid grid-2">
        <label>
          <span className="eyebrow">Nome</span>
          <input value={firstName} onChange={(e) => setFirstName(e.target.value)} maxLength={100} required autoComplete="given-name" />
        </label>
        <label>
          <span className="eyebrow">Cognome</span>
          <input value={lastName} onChange={(e) => setLastName(e.target.value)} maxLength={100} required autoComplete="family-name" />
        </label>
      </div>
      <label>
        <span className="eyebrow">Età</span>
        <input type="number" inputMode="numeric" min={14} max={120} value={age} onChange={(e) => setAge(e.target.value)} required />
      </label>
      <p className="muted small">
        Devi avere almeno 14 anni. L'età resta nel tuo account e non viene usata per i suggerimenti di stile.
      </p>
      <div className="row">
        <button className="primary" type="submit" disabled={!valid || saving}>{saving ? 'Salvo…' : 'Salva e continua'}</button>
        {onCancel && <button type="button" className="ghost" onClick={onCancel}>Annulla</button>}
      </div>
    </form>
  )
}
