import { OPERATION_LABEL, OPTION_LABEL, OPTIONS, SETTING_LABEL } from '../labels'
import type { ImageNode, LumeraProfile, Mode, Option, Setting, TryOnOp } from '../types'
import { AuthImage, useImageSrc } from './AuthImage'

interface Props {
  profile: LumeraProfile
  currentId: string
  setCurrentId: (id: string) => void
  busy: string | null
  mode: Mode
  setMode: (m: Mode) => void
  setting: Setting
  setSetting: (s: Setting) => void
  tryOn: (op: TryOnOp, option: Option) => void
  visualizeLook: (option: Option) => void
  onSave: (imageId: string) => void
}

function lineage(images: ImageNode[], id: string): ImageNode[] {
  const byId = new Map(images.map((n) => [n.image_id, n]))
  const chain: ImageNode[] = []
  let node = byId.get(id)
  while (node) {
    chain.unshift(node)
    node = node.parent_image_id ? byId.get(node.parent_image_id) : undefined
  }
  return chain
}

const GROUPS: { op: TryOnOp; title: string }[] = [
  { op: 'HAIR', title: 'Taglio' },
  { op: 'HAIR_COLOR', title: 'Colore capelli' },
  { op: 'OUTFIT', title: 'Outfit' },
  { op: 'EYEWEAR', title: 'Occhiali' },
]

export function Studio({ profile, currentId, setCurrentId, busy, mode, setMode, setting, setSetting, tryOn, visualizeLook, onSave }: Props) {
  const current = profile.images.find((n) => n.image_id === currentId)
  const currentSrc = useImageSrc(profile.id, current?.image_id ?? null)
  const chain = lineage(profile.images, currentId)
  const photos = profile.images.filter((n) => n.operation !== 'BOARD')
  const saved = current ? profile.user_feedback.saved.includes(current.image_id) : false

  return (
    <section className="studio">
      <div>
        <div className="stage">
          {current && <AuthImage profileId={profile.id} imageId={current.image_id} alt="Anteprima look" />}
          {busy && (
            <div className="busy">
              <div>
                <div className="pulse" style={{ margin: '0 auto 16px' }} />
                <p>{busy}</p>
                <p className="muted">Ogni modifica può richiedere fino a un minuto.</p>
              </div>
            </div>
          )}
        </div>

        <div className="breadcrumb">
          {chain.map((n, i) => (
            <button key={n.image_id} className={n.image_id === currentId ? 'chip selected' : 'chip'} onClick={() => setCurrentId(n.image_id)}>
              {i > 0 && '→ '}{OPERATION_LABEL[n.operation]}{n.option ? ` ${n.option}` : ''}{n.setting && n.setting !== 'auto' ? ` · ${SETTING_LABEL[n.setting]}` : ''}
            </button>
          ))}
        </div>

        <div className="row">
          {current?.parent_image_id && (
            <button onClick={() => setCurrentId(current.parent_image_id!)}>↶ Annulla</button>
          )}
          {current && current.operation !== 'ORIGINAL' && (
            <>
              <button disabled={saved} onClick={() => onSave(current.image_id)}>{saved ? 'Salvato ✓' : 'Salva nel profilo'}</button>
              {currentSrc && <a className="btn-link" href={currentSrc} download={`lumera-${current.image_id}.webp`}>Scarica</a>}
            </>
          )}
        </div>
      </div>

      <aside className="panel">
        <p className="eyebrow">Qualità</p>
        <div className="toggle">
          <button className={mode === 'preview' ? 'selected' : ''} onClick={() => setMode('preview')}>Anteprima</button>
          <button className={mode === 'final' ? 'selected' : ''} onClick={() => setMode('final')}>Alta qualità</button>
        </div>
        <p className="muted small" style={{ marginTop: 8 }}>
          Ogni modifica parte dall'immagine selezionata: combina taglio, colore, outfit e occhiali passo dopo passo.
          I numeri corrispondono ai pannelli delle board.
        </p>

        <h3>Location outfit</h3>
        <select value={setting} onChange={(e) => setSetting(e.target.value as Setting)}>
          {(Object.keys(SETTING_LABEL) as Setting[]).map((k) => (
            <option key={k} value={k}>{SETTING_LABEL[k]}</option>
          ))}
        </select>
        <p className="muted small" style={{ marginTop: 6 }}>
          Gli outfit vengono mostrati a figura intera in questa ambientazione.
        </p>

        <h3>Look completo</h3>
        <div className="option-list">
          {OPTIONS.map((o) => (
            <button key={o} disabled={!!busy} onClick={() => visualizeLook(o)}>
              <span>{o} · {OPTION_LABEL[o]}</span><span className="muted">＋</span>
            </button>
          ))}
        </div>

        {GROUPS.map((g) => (
          <div key={g.op}>
            <h3>{g.title}</h3>
            <div className="row">
              {OPTIONS.map((o) => (
                <button key={o} className="icon" title={OPTION_LABEL[o]} disabled={!!busy} onClick={() => tryOn(g.op, o)}>
                  Opzione {o}
                </button>
              ))}
            </div>
          </div>
        ))}

        <h3>Cronologia</h3>
        <div className="thumbs">
          {photos.map((n) => (
            <button key={n.image_id} className={n.image_id === currentId ? 'active' : ''} onClick={() => setCurrentId(n.image_id)} title={OPERATION_LABEL[n.operation]}>
              <AuthImage profileId={profile.id} imageId={n.image_id} alt={OPERATION_LABEL[n.operation]} />
            </button>
          ))}
        </div>
      </aside>
    </section>
  )
}
