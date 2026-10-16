import { BOARD_TITLE, BOARD_TRYON, OPTION_LABEL, OPTIONS } from '../labels'
import type { BoardKind, LumeraProfile, Option, TryOnOp } from '../types'
import { AuthImage, useImageSrc } from './AuthImage'

export interface BoardActions {
  vote: (type: 'LIKE' | 'DISLIKE', boardId: string, option: Option) => void
  tryOn: (op: TryOnOp, option: Option) => void
  regenerate: (kind: BoardKind) => void
  busy: string | null
}

interface Props {
  profile: LumeraProfile
  kind: BoardKind
  actions: BoardActions
}

export function Board({ profile, kind, actions }: Props) {
  const boardId = profile.boards[kind]
  const op = BOARD_TRYON[kind]
  const fb = profile.user_feedback
  const regenerating = actions.busy === `board:${kind}`
  const src = useImageSrc(profile.id, boardId ?? null)
  if (!boardId) return null

  return (
    <section className="card board">
      <div className="row" style={{ justifyContent: 'space-between' }}>
        <h2>{BOARD_TITLE[kind]}</h2>
        <button className="ghost icon" disabled={!!actions.busy} onClick={() => actions.regenerate(kind)}>
          ↻ Rigenera
        </button>
      </div>

      <div className="board-image">
        <a href={src ?? undefined} target="_blank" rel="noreferrer">
          <AuthImage profileId={profile.id} imageId={boardId} alt={BOARD_TITLE[kind]} />
        </a>
        {regenerating && (
          <div className="busy"><div><div className="pulse" style={{ margin: '0 auto 12px' }} />Rigenero la board…</div></div>
        )}
      </div>

      {op && (
        <div className="options">
          {OPTIONS.map((o) => {
            const key = `${boardId}:${o}`
            return (
              <div className="option" key={o}>
                <span className="label">{o} · {OPTION_LABEL[o]}</span>
                <div className="row">
                  <button className="primary icon" disabled={!!actions.busy} onClick={() => actions.tryOn(op, o)}>
                    Prova sulla foto
                  </button>
                  <button className={`icon ${fb.liked.includes(key) ? 'on' : ''}`} onClick={() => actions.vote('LIKE', boardId, o)} aria-label="Mi piace">♥</button>
                  <button className={`icon ${fb.disliked.includes(key) ? 'on' : ''}`} onClick={() => actions.vote('DISLIKE', boardId, o)} aria-label="Non mi piace">✕</button>
                </div>
              </div>
            )
          })}
        </div>
      )}
      {op && (
        <p className="muted small">
          ♥ e ✕ guidano la prossima versione: premi "Rigenera" per sostituire le proposte che non ti convincono.
        </p>
      )}
    </section>
  )
}
