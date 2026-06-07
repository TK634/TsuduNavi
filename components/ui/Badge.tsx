interface BadgeProps {
  label: string;
  variant?: "low" | "medium" | "high" | "default";
}

export function Badge({ label, variant = "default" }: BadgeProps) {
  const variants = {
    low: "bg-green-100 text-green-700",
    medium: "bg-yellow-100 text-yellow-700",
    high: "bg-red-100 text-red-700",
    default: "bg-gray-100 text-gray-700",
  };

  return (
    <span className={`inline-block text-xs font-semibold px-2 py-0.5 rounded-full ${variants[variant]}`}>
      {label}
    </span>
  );
}
