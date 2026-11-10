export const MEETING_DEFAULTS = Object.freeze({
  discussion: "Not Raised",
  action: "Not Started",
});
export function blankMeeting() {
  return Array.from({ length: 11 }, () => [
    "",
    "",
    "",
    MEETING_DEFAULTS.discussion,
    "",
    MEETING_DEFAULTS.action,
  ]);
}
export function meetingNeedsDefaults(initial) {
  return (
    initial.length < 11 ||
    initial
      .slice(0, 11)
      .some(
        (row) =>
          !String(row?.[3] ?? "").trim() || !String(row?.[5] ?? "").trim(),
      )
  );
}
export function meetingDraft(initial) {
  const rows = structuredClone(initial);
  for (let i = 0; i < 11; i++) {
    rows[i] ??= ["", "", "", "", "", ""];
    if (!String(rows[i][3] ?? "").trim())
      rows[i][3] = MEETING_DEFAULTS.discussion;
    if (!String(rows[i][5] ?? "").trim()) rows[i][5] = MEETING_DEFAULTS.action;
  }
  return rows;
}
