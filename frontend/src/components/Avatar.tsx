function initials(name: string): string {
  const parts = name.trim().split(/\s+/);
  const first = parts[0]?.[0] ?? "";
  const last = parts.length > 1 ? parts[parts.length - 1][0] : "";
  return (first + last).toUpperCase();
}

const SIZE_CLASSES = {
  sm: "h-7 w-7 text-xs",
  md: "h-10 w-10 text-sm",
  lg: "h-20 w-20 text-2xl",
};

export default function Avatar({
  name,
  url,
  size = "md",
}: {
  name: string;
  url?: string | null;
  size?: keyof typeof SIZE_CLASSES;
}) {
  const sizeClass = SIZE_CLASSES[size];
  if (url) {
    return (
      <img
        src={url}
        alt={name}
        className={`${sizeClass} shrink-0 rounded-full object-cover ring-1 ring-slate-200`}
      />
    );
  }
  return (
    <span
      className={`${sizeClass} flex shrink-0 items-center justify-center rounded-full bg-indigo-100 font-semibold text-indigo-700 ring-1 ring-slate-200`}
    >
      {initials(name) || "?"}
    </span>
  );
}
