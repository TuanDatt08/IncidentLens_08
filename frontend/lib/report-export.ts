export type ExportSection = { title: string; lines: string[]; table?: { columns: string[]; rows: string[][] }; fields?: { label: string; value: string }[]; bulleted?: boolean };


export type ExportFigure = { caption: string; pngBase64: string; width: number; height: number };
export type ExportDocument = { id: string; version: string; status: string; exportedAt: string; sections: ExportSection[]; figures?: ExportFigure[] };


function record(value: unknown): Record<string, unknown> { return value && typeof value === "object" && !Array.isArray(value) ? value as Record<string, unknown> : {}; }


function prose(value: unknown, depth = 0): string {


  if (value == null) return "Unknown";


  if (typeof value !== "object") return String(value);


  if (depth > 5) return "Additional structured details";


  if (Array.isArray(value)) return value.map(entry => prose(entry, depth + 1)).join(", ") || "None recorded";


  return Object.entries(record(value)).map(([key, entry]) => `${key.replaceAll("_", " ")}: ${prose(entry, depth + 1)}`).join("; ") || "Unknown";


}


const list = (value: unknown): unknown[] => Array.isArray(value) ? value : [];


const unique = (items: string[]) => [...new Set(items)];


const time = (value: unknown) => typeof value === "number" && Number.isFinite(value) ? `${value}s` : "Unknown";


export function normalizeReport(id: string, report: unknown, exportedAt = new Date().toISOString()): ExportDocument {


  const saved = record(report), analysis = saved.analysis ? record(saved.analysis) : saved;


  const window = record(analysis.window ?? analysis.incident_window);


  const timeline = list(analysis.timeline), factors = list(analysis.factors ?? analysis.key_factors);


  const extra: string[] = [];


  function remaining(item: Record<string, unknown>, keys: string[], context: string) {


    const rest = Object.fromEntries(Object.entries(item).filter(([key]) => !keys.includes(key)));


    if (Object.keys(rest).length) extra.push(`${context}: ${prose(rest)}`);


  }


  const timelineRows = timeline.map((value, index) => {


    if (typeof value !== "object" || value === null) return ["Unknown", prose(value), "Unknown", "None recorded"];


    const item = record(value);


    remaining(item, ["timestamp_sec", "time_s", "time", "timestamp_s", "label", "observation", "description", "source", "certainty", "evidence_ids"], `Timeline ${index + 1}`);


    return [time(item.timestamp_sec ?? item.time_s ?? item.time ?? item.timestamp_s), `${item.label ? prose(item.label) + ": " : ""}${prose(item.observation ?? item.description)}`, [item.source, item.certainty].filter(v => v != null).map(v => prose(v)).join(" / ") || "Unknown", list(item.evidence_ids).map(v => prose(v)).join(", ") || "None recorded"];


  });


  const factorRows = factors.map((value, index) => {


    if (typeof value !== "object" || value === null) return ["Unknown", prose(value), "Unknown", "None recorded"];


    const item = record(value);


    remaining(item, ["category", "label", "description", "claim_status", "evidence_ids"], `Factor ${index + 1}`);


    return [prose(item.category), prose(item.label ?? item.description), prose(item.claim_status), list(item.evidence_ids).map(v => prose(v)).join(", ") || "None recorded"];


  });


  const fields = [


    { label: "Type", value: prose(analysis.event_type ?? analysis.incident_type) },


    { label: "Detected", value: analysis.incident_detected === true ? "Yes" : analysis.incident_detected === false ? "No" : "Unknown" },


    { label: "Time basis", value: analysis.time_basis === "video_seconds" ? "Video seconds (video_seconds)" : analysis.time_basis ? prose(analysis.time_basis) : "Collision-relative seconds" },


    { label: "Start", value: time(window.start_s ?? window.start) }, { label: "Critical", value: time(window.critical_s ?? window.critical) }, { label: "End", value: time(window.end_s ?? window.end) },


    ...(saved.recording_id ? [{ label: "Recording", value: prose(saved.recording_id) }] : []), ...(saved.candidate_id ? [{ label: "Candidate", value: prose(saved.candidate_id) }] : []),


  ];


  const evidence = unique([...list(analysis.evidence_ids), ...[...timeline, ...factors].flatMap(item => list(record(item).evidence_ids))].map(item => prose(item)));


  const sections: ExportSection[] = [


    { title: "Summary", lines: [prose(analysis.summary)] },


    { title: "Incident", fields, lines: fields.map(field => `${field.label}: ${field.value}`) },


    { title: "Timeline", lines: timelineRows.length ? timelineRows.map(row => row.join(" / ")) : ["None recorded"], ...(timelineRows.length ? { table: { columns: ["Time", "Observation", "Source / certainty", "Evidence"], rows: timelineRows } } : {}) },


    ...("observations" in analysis ? [{ title: "Observations", lines: list(analysis.observations).length ? list(analysis.observations).map(item => prose(item)) : ["None recorded"], bulleted: true }] : []),


    { title: "Factors", lines: factorRows.length ? factorRows.map(row => row.join(" / ")) : ["None recorded"], ...(factorRows.length ? { table: { columns: ["Category", "Description", "Claim", "Evidence"], rows: factorRows } } : {}) },


    { title: "Unknowns", lines: unique(list(analysis.unknowns).map(item => prose(item))).length ? unique(list(analysis.unknowns).map(item => prose(item))) : ["None recorded"], bulleted: true },


    { title: "Evidence references", lines: evidence.length ? evidence : ["None recorded"], bulleted: true },


    ...(saved.rejection_reason ? [{ title: "Rejection reason", lines: [prose(saved.rejection_reason)] }] : []),


    ...(extra.length ? [{ title: "Additional report details", lines: extra }] : []),


  ];


  return { id, version: prose(saved.version), status: prose(analysis.review_status), exportedAt, sections };


}


export function exportFilename(id: string, extension: string): string { return `report-${id.replace(/[^a-zA-Z0-9_-]/g, "_").slice(0, 100) || "incident"}.${extension}`; }


export function escapeMarkup(value: string): string { return value.replace(/[&<>"']/g, char => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&apos;" }[char]!)); }


function metadata(doc: ExportDocument): { label: string; value: string }[] { return [{ label: "Report", value: doc.id }, { label: "Version", value: doc.version }, { label: "Review status", value: `${({ DRAFT: "Not reviewed", IN_REVIEW: "In review", APPROVED: "Reviewed and approved", REJECTED: "Rejected" } as Record<string, string>)[doc.status] ?? "Unknown"} (${doc.status})` }, { label: "Exported", value: doc.exportedAt }]; }



function exportFigures(doc: ExportDocument): ExportFigure[] {
  return (doc.figures ?? []).slice(0, 6).filter(figure =>
    figure.pngBase64.startsWith("iVBORw0KGgo") && /^[A-Za-z0-9+/=]+$/.test(figure.pngBase64) && figure.pngBase64.length <= 6 * 1024 * 1024 &&
    Number.isFinite(figure.width) && Number.isFinite(figure.height) && figure.width > 0 && figure.height > 0);
}
function figureHtml(doc: ExportDocument): string {
  return exportFigures(doc).map((figure, index) => `<figure style="margin:20px 0;break-inside:avoid"><img src="data:image/png;base64,${figure.pngBase64}" alt="${escapeMarkup(figure.caption)}" style="max-width:100%;max-height:150mm;object-fit:contain"/><figcaption>Figure ${index + 1}. ${escapeMarkup(figure.caption)}</figcaption></figure>`).join("");
}

export function printableReport(doc: ExportDocument): string {


  const table = (columns: string[], rows: string[][]) => `<table>${columns.length === 4 ? '<colgroup><col style="width:12%"><col style="width:48%"><col style="width:22%"><col style="width:18%"></colgroup>' : ""}<thead><tr>${columns.map(value => `<th>${escapeMarkup(value)}</th>`).join("")}</tr></thead><tbody>${rows.map(row => `<tr>${row.map(value => `<td>${escapeMarkup(value)}</td>`).join("")}</tr>`).join("")}</tbody></table>`;


  const fields = (items: { label: string; value: string }[]) => `<table class="fields"><tbody>${items.map(field => `<tr><th>${escapeMarkup(field.label)}</th><td>${escapeMarkup(field.value)}</td></tr>`).join("")}</tbody></table>`;


  return `<!doctype html><html><head><meta charset="utf-8"><title>${escapeMarkup(doc.id)}</title><style>@page{size:A4;margin:20mm}*{box-sizing:border-box}body{font:11pt/1.45 Calibri,Arial,sans-serif;color:#111}h1{font-size:22pt;margin:0 0 16px}h2{font-size:14pt;margin:22px 0 9px;break-after:avoid}p,li{white-space:pre-wrap;overflow-wrap:anywhere}p{margin:7px 0}table{width:100%;border-collapse:separate;border-spacing:0;table-layout:fixed;font-size:10pt;margin:9px 0}th,td{border:1px solid #d4d4d4;padding:7px 8px;text-align:left;vertical-align:top;white-space:pre-wrap;overflow-wrap:anywhere}th{font-weight:600;background:#f3f3f3}thead{display:table-header-group;break-inside:avoid;break-after:avoid}tr,td,th{break-inside:avoid;page-break-inside:avoid}.fields th{width:24%}ul{padding-left:20px}.notice{font-weight:bold;font-size:10pt}</style></head><body><header><h1>Incident report</h1>${fields(metadata(doc))}${doc.status !== "APPROVED" ? '<p class="notice">UNAPPROVED REPORT</p>' : ""}</header>${doc.sections.map((section, index) => `<section><h2>${index + 1}. ${escapeMarkup(section.title)}</h2>${section.table ? table(section.table.columns, section.table.rows) : section.fields ? fields(section.fields) : section.bulleted ? `<ul>${section.lines.map(line => `<li>${escapeMarkup(line)}</li>`).join("")}</ul>` : section.lines.map(line => `<p>${escapeMarkup(line)}</p>`).join("")}</section>`).join("")}${figureHtml(doc)}</body></html>`;


}





// Store-only ZIP keeps this small OOXML document dependency-free and interoperable.


function crc32(bytes: Uint8Array): number {


  let crc = 0xffffffff;


  for (const byte of bytes) { crc ^= byte; for (let bit = 0; bit < 8; bit++) crc = (crc >>> 1) ^ ((crc & 1) ? 0xedb88320 : 0); }


  return (crc ^ 0xffffffff) >>> 0;


}


function zip(entries: Record<string, string | Uint8Array>): Uint8Array {


  const encoder = new TextEncoder();


  const chunks: Uint8Array[] = []; const central: Uint8Array[] = []; let offset = 0;


  for (const [path, content] of Object.entries(entries)) {


    const name = encoder.encode(path); const data = typeof content === "string" ? encoder.encode(content) : content; const crc = crc32(data);


    const local = new Uint8Array(30 + name.length); const lv = new DataView(local.buffer);


    lv.setUint32(0, 0x04034b50, true); lv.setUint16(4, 20, true); lv.setUint16(10, 0, true); lv.setUint16(12, 33, true); lv.setUint32(14, crc, true); lv.setUint32(18, data.length, true); lv.setUint32(22, data.length, true); lv.setUint16(26, name.length, true); local.set(name, 30);


    const directory = new Uint8Array(46 + name.length); const dv = new DataView(directory.buffer);


    dv.setUint32(0, 0x02014b50, true); dv.setUint16(4, 20, true); dv.setUint16(6, 20, true); dv.setUint16(12, 0, true); dv.setUint16(14, 33, true); dv.setUint32(16, crc, true); dv.setUint32(20, data.length, true); dv.setUint32(24, data.length, true); dv.setUint16(28, name.length, true); dv.setUint32(42, offset, true); directory.set(name, 46);


    chunks.push(local, data); central.push(directory); offset += local.length + data.length;


  }


  const directorySize = central.reduce((sum, item) => sum + item.length, 0);


  const end = new Uint8Array(22); const view = new DataView(end.buffer);


  view.setUint32(0, 0x06054b50, true); view.setUint16(8, central.length, true); view.setUint16(10, central.length, true); view.setUint32(12, directorySize, true); view.setUint32(16, offset, true);


  const result = new Uint8Array(offset + directorySize + end.length); let at = 0;


  for (const chunk of [...chunks, ...central, end]) { result.set(chunk, at); at += chunk.length; }


  return result;


}





export function reportDocx(doc: ExportDocument): Uint8Array {


  const ns = "http://schemas.openxmlformats.org/wordprocessingml/2006/main";


  const rel = "http://schemas.openxmlformats.org/officeDocument/2006/relationships";


  const xml = '<?xml version="1.0" encoding="UTF-8"?>';


  const paragraph = (text: string, style = "Normal", bullet = false) => {


    const clean = text.replace(/[\u0000-\u0008\u000b\u000c\u000e-\u001f]/g, "");


    const content = clean.split(/\r\n|\r|\n/).map(line => `<w:t xml:space="preserve">${escapeMarkup(line)}</w:t>`).join("<w:br/>");


    return `<w:p><w:pPr><w:pStyle w:val="${style}"/>${bullet ? '<w:numPr><w:ilvl w:val="0"/><w:numId w:val="1"/></w:numPr>' : ""}</w:pPr><w:r>${content}</w:r></w:p>`;


  };


  const table = (columns: string[], rows: string[][], metadataTable = false) => {


    const widths = columns.length === 4 ? [1157, 4626, 2120, 1735] : [2300, 7338];


    const cell = (value: string, index: number, heading: boolean) => `<w:tc><w:tcPr><w:tcW w:w="${widths[index]}" w:type="dxa"/>${heading ? '<w:shd w:fill="F3F3F3"/>' : ""}</w:tcPr>${paragraph(value, heading ? "TableHeader" : "TableText")}</w:tc>`;


    return `<w:tbl><w:tblPr><w:tblW w:w="9638" w:type="dxa"/><w:tblLayout w:type="fixed"/><w:tblBorders>${["top", "left", "bottom", "right", "insideH", "insideV"].map(side => `<w:${side} w:val="single" w:sz="4" w:color="D4D4D4"/>`).join("")}</w:tblBorders><w:tblCellMar><w:top w:w="90" w:type="dxa"/><w:left w:w="110" w:type="dxa"/><w:bottom w:w="90" w:type="dxa"/><w:right w:w="110" w:type="dxa"/></w:tblCellMar></w:tblPr><w:tblGrid>${widths.map(width => `<w:gridCol w:w="${width}"/>`).join("")}</w:tblGrid>${metadataTable ? "" : `<w:tr><w:trPr><w:tblHeader/><w:cantSplit/></w:trPr>${columns.map((value, index) => cell(value, index, true)).join("")}</w:tr>`}${rows.map(row => `<w:tr><w:trPr><w:cantSplit/></w:trPr>${row.map((value, index) => cell(value, index, metadataTable && index === 0)).join("")}</w:tr>`).join("")}</w:tbl>${paragraph("")}`;


  };


  const figures = exportFigures(doc);
  const imageParts: Record<string, Uint8Array> = {};
  const images = figures.map((figure, index) => {
    imageParts[`word/media/image${index}.png`] = Uint8Array.from(atob(figure.pngBase64), value => value.charCodeAt(0));
    const scale = Math.min(6120000 / figure.width, 4200000 / figure.height);
    const cx = Math.round(figure.width * scale), cy = Math.round(figure.height * scale);
    return `<w:p><w:pPr><w:keepNext/></w:pPr><w:r><w:drawing><wp:inline xmlns:wp="http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing"><wp:extent cx="${cx}" cy="${cy}"/><wp:docPr id="${index + 1}" name="Figure ${index + 1}" descr="${escapeMarkup(figure.caption)}"/><a:graphic xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main"><a:graphicData uri="http://schemas.openxmlformats.org/drawingml/2006/picture"><pic:pic xmlns:pic="http://schemas.openxmlformats.org/drawingml/2006/picture"><pic:nvPicPr><pic:cNvPr id="${index + 1}" name="image${index}.png"/><pic:cNvPicPr/></pic:nvPicPr><pic:blipFill><a:blip r:embed="rIdImage${index}"/><a:stretch><a:fillRect/></a:stretch></pic:blipFill><pic:spPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="${cx}" cy="${cy}"/></a:xfrm><a:prstGeom prst="rect"><a:avLst/></a:prstGeom></pic:spPr></pic:pic></a:graphicData></a:graphic></wp:inline></w:drawing></w:r></w:p>` + paragraph(`Figure ${index + 1}. ${figure.caption}`, "TableText");
  }).join("");
  const imageRelationships = figures.map((_, index) => `<Relationship Id="rIdImage${index}" Type="${rel}/image" Target="media/image${index}.png"/>`).join("");
  const body = paragraph("Incident report", "Title") + table(["Field", "Value"], metadata(doc).map(field => [field.label, field.value]), true) + (doc.status !== "APPROVED" ? paragraph("UNAPPROVED REPORT", "TableHeader") : "") + doc.sections.map((section, index) => paragraph(`${index + 1}. ${section.title}`, "Heading1") + (section.table ? table(section.table.columns, section.table.rows) : section.fields ? table(["Field", "Value"], section.fields.map(field => [field.label, field.value]), true) : section.lines.map(line => paragraph(line, "Normal", section.bulleted)).join(""))).join("");


  return zip({
    ...imageParts,


    "[Content_Types].xml": xml + '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="png" ContentType="image/png"/><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/>' + ["document", "styles", "numbering", "footer1"].map(part => `<Override PartName="/word/${part}.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.${part === "document" ? "document.main" : part === "footer1" ? "footer" : part}+xml"/>`).join("") + '</Types>',


    "_rels/.rels": xml + `<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="${rel}/officeDocument" Target="word/document.xml"/></Relationships>`,


    "word/_rels/document.xml.rels": xml + `<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="${rel}/styles" Target="styles.xml"/><Relationship Id="rId2" Type="${rel}/numbering" Target="numbering.xml"/><Relationship Id="rId3" Type="${rel}/footer" Target="footer1.xml"/>${imageRelationships}</Relationships>`,


    "word/styles.xml": xml + `<w:styles xmlns:w="${ns}"><w:docDefaults><w:rPrDefault><w:rPr><w:rFonts w:ascii="Calibri" w:hAnsi="Calibri"/><w:color w:val="111111"/><w:sz w:val="22"/></w:rPr></w:rPrDefault><w:pPrDefault><w:pPr><w:spacing w:after="100" w:line="276" w:lineRule="auto"/><w:widowControl/></w:pPr></w:pPrDefault></w:docDefaults><w:style w:type="paragraph" w:default="1" w:styleId="Normal"><w:name w:val="Normal"/></w:style><w:style w:type="paragraph" w:styleId="Title"><w:name w:val="Title"/><w:basedOn w:val="Normal"/><w:pPr><w:keepNext/><w:spacing w:after="220"/></w:pPr><w:rPr><w:b/><w:sz w:val="44"/></w:rPr></w:style><w:style w:type="paragraph" w:styleId="Heading1"><w:name w:val="heading 1"/><w:basedOn w:val="Normal"/><w:pPr><w:keepNext/><w:spacing w:before="260" w:after="120"/></w:pPr><w:rPr><w:b/><w:sz w:val="28"/></w:rPr></w:style><w:style w:type="paragraph" w:styleId="TableText"><w:name w:val="Table text"/><w:basedOn w:val="Normal"/><w:pPr><w:spacing w:after="30"/></w:pPr><w:rPr><w:sz w:val="20"/></w:rPr></w:style><w:style w:type="paragraph" w:styleId="TableHeader"><w:name w:val="Table header"/><w:basedOn w:val="TableText"/><w:rPr><w:b/></w:rPr></w:style></w:styles>`,


    "word/numbering.xml": xml + `<w:numbering xmlns:w="${ns}"><w:abstractNum w:abstractNumId="0"><w:multiLevelType w:val="singleLevel"/><w:lvl w:ilvl="0"><w:start w:val="1"/><w:numFmt w:val="bullet"/><w:lvlText w:val="&#x2022;"/><w:lvlJc w:val="left"/><w:pPr><w:tabs><w:tab w:val="num" w:pos="360"/></w:tabs><w:ind w:left="360" w:hanging="180"/></w:pPr></w:lvl></w:abstractNum><w:num w:numId="1"><w:abstractNumId w:val="0"/></w:num></w:numbering>`,


    "word/footer1.xml": xml + `<w:ftr xmlns:w="${ns}"><w:p><w:pPr><w:jc w:val="right"/></w:pPr><w:r><w:rPr><w:sz w:val="18"/></w:rPr><w:t xml:space="preserve">${escapeMarkup(doc.id)} / Page </w:t></w:r><w:fldSimple w:instr="PAGE"><w:r><w:t>1</w:t></w:r></w:fldSimple></w:p></w:ftr>`,


    "word/document.xml": xml + `<w:document xmlns:w="${ns}" xmlns:r="${rel}"><w:body>${body}${images}<w:sectPr><w:footerReference w:type="default" r:id="rId3"/><w:pgSz w:w="11906" w:h="16838"/><w:pgMar w:top="1134" w:right="1134" w:bottom="1134" w:left="1134" w:footer="567"/></w:sectPr></w:body></w:document>`,


  });


}
