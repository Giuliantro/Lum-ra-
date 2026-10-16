// Mirrors backend/app/models.py

export type BoardKind = 'SEASON' | 'HAIR' | 'HAIR_COLOR' | 'OUTFIT' | 'ACCESSORIES'
export type TryOnOp = 'HAIR' | 'HAIR_COLOR' | 'OUTFIT' | 'EYEWEAR'
export type Operation = 'ORIGINAL' | 'BOARD' | TryOnOp
export type Option = 1 | 2 | 3
export type Mode = 'preview' | 'final'
export type Setting = 'auto' | 'restaurant' | 'office' | 'garden' | 'city_street' | 'evening_event' | 'cafe'

export interface ImageNode {
  image_id: string
  parent_image_id: string | null
  operation: Operation
  board_kind: BoardKind | null
  reference_board_id: string | null
  option: number | null
  setting: Setting | null
  prompt_version: string | null
  quality: string | null
  created_at: string
}

export interface StyleRequest {
  selected_styles: string[]
  trend_preference: 'low' | 'moderate' | 'high'
  free_text_style_request: string
  occasion: string
  comfort_preferences: string
}

export interface LumeraProfile {
  id: string
  status: 'created' | 'analyzed' | 'styled'
  created_at: string
  original_image_id: string | null
  boards: Partial<Record<BoardKind, string>>
  style_request: StyleRequest | null
  user_feedback: { liked: string[]; disliked: string[]; saved: string[] }
  images: ImageNode[]
}

export type FeedbackType = 'LIKE' | 'DISLIKE' | 'SAVE' | 'TRY' | 'REGENERATE' | 'UNDO'

export interface Me {
  id: string
  email: string
  first_name: string | null
  last_name: string | null
  age: number | null
  profile_complete: boolean
}

export interface ProfileSummary {
  id: string
  status: string
  original_image_id: string | null
  created_at: string
}
