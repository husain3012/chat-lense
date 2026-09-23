export const momentStyles: Record<string, { emoji: string; label: string }> = {
  sweet: { emoji: "🥹", label: "The soft stuff" },
  funny: { emoji: "😂", label: "You had to be there" },
  golden: { emoji: "✨", label: "A golden little moment" },
  repair: { emoji: "🩹", label: "Finding your way back" },
  tension: { emoji: "🌧️", label: "A bump in the road" },
  ritual: { emoji: "🫶", label: "Such a you thing" },
  connection: { emoji: "💬", label: "Between the lines" },
  romance: { emoji: "💞", label: "Romance" },
  intimacy: { emoji: "🔥", label: "Flirting & intimacy" },
  missing: { emoji: "🥹", label: "Missing you & reunions" },
  friendship: { emoji: "🫶", label: "Friendship" },
  deep: { emoji: "🌙", label: "Deep conversations" },
  ideas: { emoji: "💡", label: "Ideas & rabbit holes" },
  support: { emoji: "🤝", label: "Showing up" },
};
export function sticker(category: string) {
  const icons = ["🌙", "💌", "🪩", "🌻", "☕", "🎈", "🧩", "🍿"];
  return icons[
    Array.from(category).reduce((n, c) => n + c.codePointAt(0)!, 0) %
      icons.length
  ];
}
