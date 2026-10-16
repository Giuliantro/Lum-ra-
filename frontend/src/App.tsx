import { Show, UserButton, useAuth } from '@clerk/react'
import { useEffect, useState } from 'react'
import { api, setTokenGetter } from './api'
import { Board, type BoardActions } from './components/Board'
import { Landing } from './components/Landing'
import { Onboarding } from './components/Onboarding'
import { Studio } from './components/Studio'
import { StylePicker } from './components/StylePicker'
import { Upload } from './components/Upload'
import { OPERATION_LABEL, OPTION_LABEL } from './labels'
import type {
  BoardKind, LumeraProfile, Me, Mode, Option, ProfileSummary, Setting, StyleRequest, TryOnOp,
} from './types'

type Tab = 'colori' | 'capelli' | 'look' | 'accessori' | 'studio' | 'stile'

const TABS: { id: Tab; label: string }[] = [
  { id: 'colori', label: 'I tuoi colori' },
  { id: 'capelli', label: 'Capelli' },
  { id: 'look', label: 'Look' },
  { id: 'accessori', label: 'Accessori' },
  { id: 'studio', label: 'Studio' },
  { id: 'stile', label: 'Il tuo stile' },
]

const dateLabel = (iso: string) =>
  new Date(iso).toLocaleDateString('it-IT', { day: 'numeric', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit' })

export default function App() {
  return (
    <main className="app">
      <Show when="signed-out">
        <header className="topbar">
          <div className="brand">Luméra<small>AI Personal Stylist</small></div>
        </header>
        <Landing />
      </Show>
      <Show when="signed-in">
        <Workspace />
      </Show>
    </main>
  )
}

function Workspace() {
  const { getToken } = useAuth()
  setTokenGetter(getToken)

  const [me, setMe] = useState<Me | null>(null)
  const [editingMe, setEditingMe] = useState(false)
  const [profiles, setProfiles] = useState<ProfileSummary[]>([])
  const [profile, setProfile] = useState<LumeraProfile | null>(null)
  const [loading, setLoading] = useState<string | null>('Carico il tuo account…')
  const [error, setError] = useState<string | null>(null)
  const [tab, setTab] = useState<Tab>('colori')
  const [currentId, setCurrentId] = useState<string | null>(null)
  const [busy, setBusy] = useState<string | null>(null)
  const [mode, setMode] = useState<Mode>('preview')
  const [setting, setSetting] = useState<Setting>('auto')

  const accept = (p: LumeraProfile) => {
    setProfile(p)
    setCurrentId(p.original_image_id)
  }

  const loadProfiles = async (openLatest: boolean) => {
    const list = await api.listProfiles()
    setProfiles(list)
    if (openLatest && list.length > 0) {
      const p = await api.getProfile(list[0].id)
      accept(p)
      setTab(p.status === 'styled' ? 'look' : 'colori')
    }
  }

  useEffect(() => {
    (async () => {
      try {
        const user = await api.me()
        setMe(user)
        if (user.profile_complete) await loadProfiles(true)
      } catch (e) {
        setError((e as Error).message)
      } finally {
        setLoading(null)
      }
    })()
  }, [])

  const run = async (message: string, fn: () => Promise<void>) => {
    setError(null)
    setLoading(message)
    try {
      await fn()
    } catch (e) {
      setError((e as Error).message)
    } finally {
      setLoading(null)
    }
  }

  const saveMe = async (body: { first_name: string; last_name: string; age: number }) => {
    setError(null)
    try {
      const wasComplete = me?.profile_complete
      setMe(await api.updateMe(body))
      setEditingMe(false)
      if (!wasComplete) await loadProfiles(true)
    } catch (e) {
      setError((e as Error).message)
    }
  }

  const analyze = (file: File) =>
    run('Analizzo luce, colori naturali, viso e capelli…', async () => {
      // A profile whose analysis failed keeps its id: replace its photo instead of creating another one.
      const p = profile?.status === 'created' ? await api.replacePhoto(profile.id, file) : await api.createProfile(file)
      accept(p)
      setTab('colori')
      setProfiles(await api.listProfiles())
    })

  const submitStyle = (req: StyleRequest) =>
    run('Creo le board di hairstyle, colore, outfit e accessori…', async () => {
      accept(await api.setStyle(profile!.id, req))
      setTab('capelli')
    })

  const openProfile = (id: string) =>
    run('Carico il profilo…', async () => {
      const p = await api.getProfile(id)
      accept(p)
      setTab(p.status === 'styled' ? 'look' : 'colori')
    })

  // Long-running image work that keeps the current view visible.
  const work = async (label: string, fn: () => Promise<void>) => {
    setError(null)
    setBusy(label)
    try {
      await fn()
    } catch (e) {
      setError((e as Error).message)
    } finally {
      setBusy(null)
    }
  }

  const refreshAndShow = async (imageId: string) => {
    setProfile(await api.getProfile(profile!.id))
    setCurrentId(imageId)
  }

  const tryOn = (op: TryOnOp, option: Option) => {
    setTab('studio')
    return work(`Applico ${OPERATION_LABEL[op].toLowerCase()} · ${OPTION_LABEL[option]}…`, async () => {
      const node = await api.tryOn(profile!.id, { operation: op, option, parent_image_id: currentId, mode, setting })
      await refreshAndShow(node.image_id)
    })
  }

  const visualizeLook = (option: Option) => {
    setTab('studio')
    return work(`Compongo il look "${OPTION_LABEL[option]}": taglio → colore → outfit → occhiali…`, async () => {
      const nodes = await api.visualizeLook(profile!.id, option, { parent_image_id: profile!.original_image_id, mode, setting })
      await refreshAndShow(nodes[nodes.length - 1].image_id)
    })
  }

  const regenerate = (kind: BoardKind) =>
    work(`board:${kind}`, async () => setProfile(await api.regenerateBoard(profile!.id, kind)))

  const vote = (type: 'LIKE' | 'DISLIKE', boardId: string, option: Option) =>
    api.feedback(profile!.id, type, 'board_option', `${boardId}:${option}`).then(setProfile).catch((e) => setError(e.message))

  const save = (imageId: string) =>
    api.feedback(profile!.id, 'SAVE', 'image', imageId).then(setProfile).catch((e) => setError(e.message))

  const newPortrait = () => { setProfile(null); setCurrentId(null); setError(null) }

  const actions: BoardActions = { vote, tryOn, regenerate, busy }

  let body
  if (loading) {
    body = (
      <div className="loading">
        <div className="pulse" />
        <h3>{loading}</h3>
        {loading !== 'Carico il tuo account…' && <p className="muted">Può richiedere fino a qualche minuto.</p>}
      </div>
    )
  } else if (!me) {
    body = null
  } else if (!me.profile_complete || editingMe) {
    body = <Onboarding me={me} onSubmit={saveMe} onCancel={me.profile_complete ? () => setEditingMe(false) : undefined} />
  } else if (!profile || profile.status === 'created') {
    body = <Upload onSubmit={analyze} />
  } else if (profile.status === 'analyzed') {
    body = (
      <div className="stack">
        <Board profile={profile} kind="SEASON" actions={actions} />
        <StylePicker initial={profile.style_request} onSubmit={submitStyle} />
      </div>
    )
  } else {
    body = (
      <>
        <nav className="tabs">
          {TABS.map((t) => (
            <button key={t.id} className={tab === t.id ? 'active' : ''} onClick={() => setTab(t.id)}>{t.label}</button>
          ))}
        </nav>
        {tab === 'colori' && <Board profile={profile} kind="SEASON" actions={actions} />}
        {tab === 'capelli' && (
          <div className="stack">
            <Board profile={profile} kind="HAIR" actions={actions} />
            <Board profile={profile} kind="HAIR_COLOR" actions={actions} />
          </div>
        )}
        {tab === 'look' && <Board profile={profile} kind="OUTFIT" actions={actions} />}
        {tab === 'accessori' && <Board profile={profile} kind="ACCESSORIES" actions={actions} />}
        {tab === 'studio' && currentId && (
          <Studio
            profile={profile} currentId={currentId} setCurrentId={setCurrentId} busy={busy}
            mode={mode} setMode={setMode} setting={setting} setSetting={setSetting}
            tryOn={tryOn} visualizeLook={visualizeLook} onSave={save}
          />
        )}
        {tab === 'stile' && <StylePicker initial={profile.style_request} onSubmit={submitStyle} />}
      </>
    )
  }

  const ready = !loading && me?.profile_complete && !editingMe

  return (
    <>
      <header className="topbar">
        <div className="brand">Luméra<small>AI Personal Stylist</small></div>
        <div className="row">
          {ready && profiles.length > 1 && (
            <select
              className="profile-select"
              value={profile?.id ?? ''}
              onChange={(e) => e.target.value && openProfile(e.target.value)}
              aria-label="I miei profili"
            >
              {!profile && <option value="">Nuovo ritratto</option>}
              {profiles.map((p) => <option key={p.id} value={p.id}>Profilo del {dateLabel(p.created_at)}</option>)}
            </select>
          )}
          {ready && profile && <button className="ghost" onClick={newPortrait}>Nuovo ritratto</button>}
          {ready && <button className="ghost" onClick={() => setEditingMe(true)}>I miei dati</button>}
          <UserButton />
        </div>
      </header>
      {error && <div className="error">{error}</div>}
      {body}
    </>
  )
}
