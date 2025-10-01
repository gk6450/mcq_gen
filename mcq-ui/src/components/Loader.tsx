import React from "react";

export const Loader: React.FC<{ size?: number; label?: string }> = ({ size = 20, label }) => {
  const s = `${size}px`;
  return (
    <div className="flex items-center gap-2">
      <svg
        style={{ width: s, height: s }}
        className="animate-spin"
        viewBox="0 0 24 24"
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
      >
        <circle cx="12" cy="12" r="10" stroke="var(--color-primary)" strokeOpacity="0.2" strokeWidth="4" />
        <path d="M22 12a10 10 0 0 0-10-10" stroke="var(--color-primary)" strokeWidth="4" strokeLinecap="round" />
      </svg>
      {label ? <span className="text-sm text-muted-foreground">{label}</span> : null}
    </div>
  );
};

export default Loader;
