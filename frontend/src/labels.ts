import type { BoardKind, Option, Setting, TryOnOp } from './types'

// Section 24 — same labels the boards render above each panel
export const OPTION_LABEL: Record<Option, string> = {
  1: 'Scelta Luméra',
  2: 'Evoluzione Naturale',
  3: 'Prova Qualcosa di Nuovo',
}
export const OPTIONS: Option[] = [1, 2, 3]

export const OPERATION_LABEL: Record<string, string> = {
  ORIGINAL: 'Originale',
  BOARD: 'Board',
  HAIR: 'Taglio',
  HAIR_COLOR: 'Colore capelli',
  OUTFIT: 'Outfit',
  EYEWEAR: 'Occhiali',
}

export const BOARD_TITLE: Record<BoardKind, string> = {
  SEASON: 'La tua stagione e i tuoi colori',
  HAIR: 'Hairstyle',
  HAIR_COLOR: 'Colore capelli',
  OUTFIT: 'Outfit',
  ACCESSORIES: 'Occhiali e accessori',
}

// Board kind → try-on operation that uses its panels
export const BOARD_TRYON: Partial<Record<BoardKind, TryOnOp>> = {
  HAIR: 'HAIR',
  HAIR_COLOR: 'HAIR_COLOR',
  OUTFIT: 'OUTFIT',
  ACCESSORIES: 'EYEWEAR',
}

export const STYLES = [
  'Minimal', 'Elegant', 'Classic', 'Casual', 'Smart Casual', 'Streetwear',
  'Creative', 'Romantic', 'Luxury', 'Sporty', 'Business', 'Bold',
] as const

export const STYLE_IT: Record<string, string> = {
  Minimal: 'Minimal', Elegant: 'Elegante', Classic: 'Classico', Casual: 'Casual',
  'Smart Casual': 'Smart Casual', Streetwear: 'Streetwear', Creative: 'Creativo',
  Romantic: 'Romantico', Luxury: 'Luxury', Sporty: 'Sportivo', Business: 'Business', Bold: 'Audace',
}

// Location of full-body outfit try-ons
export const SETTING_LABEL: Record<Setting, string> = {
  auto: 'Come nella board',
  restaurant: 'Ristorante',
  office: 'Ufficio',
  garden: 'Giardino',
  city_street: 'Città',
  evening_event: 'Evento serale',
  cafe: 'Caffè',
}
