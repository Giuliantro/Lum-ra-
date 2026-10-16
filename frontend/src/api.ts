import type {
  BoardKind, FeedbackType, ImageNode, LumeraProfile, Me, Mode, Option, ProfileSummary, Setting, StyleRequest, TryOnOp,
} from './types'

export class ApiError extends Error {
  status: number
  constructor(status: number, message: string) {
    super(message)
    this.status = status
  }
}

// Backend origin; empty in development, where Vite proxies /api to :8000
const API_URL = (import.meta.env.VITE_API_URL ?? '').replace(/\/+$/, '')

// Set by the signed-in app with Clerk's useAuth().getToken
let tokenGetter: (() => Promise<string | null>) | null = null
export const setTokenGetter = (fn: () => Promise<string | null>) => { tokenGetter = fn }

async function authFetch(path: string, init: RequestInit = {}): Promise<Response> {
  const token = tokenGetter ? await tokenGetter() : null
  const headers = new Headers(init.headers)
  if (token) headers.set('Authorization', `Bearer ${token}`)
  const res = await fetch(API_URL + path, { ...init, headers })
  if (!res.ok) {
    let detail = `Errore ${res.status}`
    try {
      const body = await res.json()
      if (typeof body.detail === 'string') detail = body.detail
    } catch { /* non-JSON error body */ }
    throw new ApiError(res.status, detail)
  }
  return res
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await authFetch(path, init)
  return (res.status === 204 ? undefined : await res.json()) as T
}

const json = (body: unknown, method = 'POST'): RequestInit => ({
  method,
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify(body),
})

const upload = (file: File): RequestInit => {
  const form = new FormData()
  form.append('photo', file)
  return { method: 'POST', body: form }
}

// Images need the auth header, so they are fetched as blobs. They are immutable: cache forever.
const imageCache = new Map<string, Promise<string>>()
export const resolvedImages = new Map<string, string>()

export function imageSrc(profileId: string, imageId: string): Promise<string> {
  let promise = imageCache.get(imageId)
  if (!promise) {
    promise = authFetch(`/api/profiles/${profileId}/images/${imageId}/file`)
      .then((res) => res.blob())
      .then((blob) => {
        const url = URL.createObjectURL(blob)
        resolvedImages.set(imageId, url)
        return url
      })
    promise.catch(() => imageCache.delete(imageId))
    imageCache.set(imageId, promise)
  }
  return promise
}

export const api = {
  me: () => request<Me>('/api/me'),
  updateMe: (body: { first_name: string; last_name: string; age: number }) => request<Me>('/api/me', json(body, 'PUT')),
  listProfiles: () => request<ProfileSummary[]>('/api/profiles'),
  createProfile: (file: File) => request<LumeraProfile>('/api/profiles', upload(file)),
  replacePhoto: (id: string, file: File) => request<LumeraProfile>(`/api/profiles/${id}/photo`, upload(file)),
  getProfile: (id: string) => request<LumeraProfile>(`/api/profiles/${id}`),
  setStyle: (id: string, req: StyleRequest) => request<LumeraProfile>(`/api/profiles/${id}/style`, json(req)),
  regenerateBoard: (id: string, kind: BoardKind) =>
    request<LumeraProfile>(`/api/profiles/${id}/boards/${kind}/regenerate`, { method: 'POST' }),
  tryOn: (id: string, body: { operation: TryOnOp; option: Option; parent_image_id: string | null; mode: Mode; setting: Setting }) =>
    request<ImageNode>(`/api/profiles/${id}/images`, json(body)),
  visualizeLook: (id: string, option: Option, body: { parent_image_id: string | null; mode: Mode; setting: Setting }) =>
    request<ImageNode[]>(`/api/profiles/${id}/looks/${option}/visualize`, json(body)),
  feedback: (id: string, type: FeedbackType, entity_type: 'board_option' | 'image', entity_id: string) =>
    request<LumeraProfile>(`/api/profiles/${id}/feedback`, json({ type, entity_type, entity_id })),
}
