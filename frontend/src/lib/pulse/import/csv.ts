/**
 * A small RFC 4180 reader: quoted fields (with doubled quotes and embedded
 * newlines), CRLF or LF, a leading byte-order mark, blank lines skipped.
 * The header is lower-cased and trimmed so callers can match synonyms.
 */
export interface CsvTable {
  header: string[];
  rows: string[][];
}

export function parseCsv(text: string): CsvTable {
  const src = text.charCodeAt(0) === 0xfeff ? text.slice(1) : text;
  const records: string[][] = [];
  let row: string[] = [];
  let field = "";
  let quoted = false;
  let i = 0;
  const endField = () => {
    row.push(field);
    field = "";
  };
  const endRow = () => {
    endField();
    if (row.length > 1 || row[0].trim() !== "") records.push(row);
    row = [];
  };
  while (i < src.length) {
    const ch = src[i];
    if (quoted) {
      if (ch === '"') {
        if (src[i + 1] === '"') {
          field += '"';
          i += 2;
          continue;
        }
        quoted = false;
        i++;
        continue;
      }
      field += ch;
      i++;
      continue;
    }
    if (ch === '"') {
      quoted = true;
      i++;
    } else if (ch === ",") {
      endField();
      i++;
    } else if (ch === "\r") {
      i++;
    } else if (ch === "\n") {
      endRow();
      i++;
    } else {
      field += ch;
      i++;
    }
  }
  if (field !== "" || row.length > 0) endRow();
  const header = (records.shift() ?? []).map((h) => h.trim().toLowerCase());
  return { header, rows: records };
}

/** Index of the first header that matches any of the names, or -1. */
export function findColumn(header: string[], names: string[]): number {
  for (const n of names) {
    const k = header.indexOf(n);
    if (k >= 0) return k;
  }
  return -1;
}

export function toNumber(s: string | undefined): number | null {
  if (s === undefined) return null;
  const t = s.trim();
  if (t === "") return null;
  const v = Number(t);
  return Number.isFinite(v) ? v : null;
}
