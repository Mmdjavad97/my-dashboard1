// Assemble only calendar components: Intl's formatted string can append an AP era.
export function solarDate(date = new Date(), timeZone = "Asia/Tehran") {
  const parts = new Intl.DateTimeFormat("en-US-u-ca-persian", {
    timeZone,
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
  }).formatToParts(date);
  const value = (type) => parts.find((part) => part.type === type).value;
  return `${value("year")}/${value("month").padStart(2, "0")}/${value("day").padStart(2, "0")}`;
}
export function solarValue(value) {
  const raw = String(value ?? "")
    .replace(/[۰-۹]/g, (c) => String("۰۱۲۳۴۵۶۷۸۹".indexOf(c)))
    .replace(/[٠-٩]/g, (c) => String("٠١٢٣٤٥٦٧٨٩".indexOf(c)))
    .replace(/[\u200e\u200f\u061c]/g, "")
    .replace(/\s*AP\s*$/i, "")
    .trim()
    .replaceAll("-", "/");
  const match = raw.match(/^(\d{4})\/(\d{1,2})\/(\d{1,2})$/);
  if (match && Number(match[1]) >= 1700) {
    return solarDate(
      new Date(
        Date.UTC(Number(match[1]), Number(match[2]) - 1, Number(match[3])),
      ),
      "UTC",
    );
  }
  return raw;
}
