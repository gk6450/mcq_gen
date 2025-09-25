// src/components/Avatar.tsx
import React from "react"

export const Avatar: React.FC<{ name?: string; size?: number }> = ({ name = "U", size = 36 }) => {
  const initial = (name && name.trim().length > 0) ? name.trim()[0].toUpperCase() : "U"
  return (
    <div
      className="flex items-center justify-center rounded-full bg-primary text-white font-semibold select-none"
      style={{ width: size, height: size, minWidth: size }}
      title={name}
    >
      {initial}
    </div>
  )
}

export default Avatar
