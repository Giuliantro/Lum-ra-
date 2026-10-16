import { useEffect, useState, type ImgHTMLAttributes } from 'react'
import { imageSrc, resolvedImages } from '../api'

/** Object URL of a protected image (fetched with the Clerk token). */
export function useImageSrc(profileId: string, imageId: string | null): string | null {
  const [src, setSrc] = useState<string | null>(imageId ? resolvedImages.get(imageId) ?? null : null)

  useEffect(() => {
    if (!imageId) return
    let alive = true
    setSrc(resolvedImages.get(imageId) ?? null)
    imageSrc(profileId, imageId).then((url) => alive && setSrc(url)).catch(() => alive && setSrc(null))
    return () => { alive = false }
  }, [profileId, imageId])

  return src
}

type Props = { profileId: string; imageId: string } & Omit<ImgHTMLAttributes<HTMLImageElement>, 'src'>

export function AuthImage({ profileId, imageId, alt, ...rest }: Props) {
  const src = useImageSrc(profileId, imageId)
  return src ? <img src={src} alt={alt} {...rest} /> : <div className="img-placeholder" aria-label={alt} />
}
