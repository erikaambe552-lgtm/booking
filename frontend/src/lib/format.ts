export const peso = (v: string | number) =>
  `₱${Number(v).toLocaleString("en-PH", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;

export const dateTime = (iso: string) =>
  new Date(iso).toLocaleString("en-PH", { weekday: "short", month: "short", day: "numeric", hour: "numeric", minute: "2-digit" });

export const dateOnly = (iso: string) =>
  new Date(iso).toLocaleDateString("en-PH", { weekday: "short", month: "short", day: "numeric", year: "numeric" });

export const timeRange = (a: string, b: string) => {
  const f = (d: string) => new Date(d).toLocaleTimeString("en-PH", { hour: "numeric", minute: "2-digit" });
  return `${f(a)} – ${f(b)}`;
};

export const roleLabel: Record<string, string> = {
  CAMPER: "Camper", VENUE_OPERATOR: "Venue Operator", GUIDE: "Tour Guide", ADMIN: "Administrator",
};

export const locationText = (d: { municipality: string; barangay: string; province: string }) =>
  [d.barangay && `Brgy. ${d.barangay}`, d.municipality, `${d.province || "Biliran"} Province`].filter(Boolean).join(", ");
