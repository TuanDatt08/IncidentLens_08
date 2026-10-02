import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import ts from "../../frontend/node_modules/typescript/lib/typescript.js";

const source = readFileSync(new URL("../../frontend/lib/report-editor-values.ts", import.meta.url), "utf8");
const compiled = ts.transpileModule(source, { compilerOptions: { module: ts.ModuleKind.ES2022 } }).outputText;
const { parseEditorItems } = await import(`data:text/javascript;base64,${Buffer.from(compiled).toString("base64")}`);
const original = [{ label: "Rain", claim_status: "OBSERVED", evidence_ids: ["EVD-1"], source: "VIDEO", time_s: 3 }];
assert.deepEqual(parseEditorItems(JSON.stringify(original[0]), original), original);
assert.throws(() => parseEditorItems("Rain", original), /structured/);
assert.deepEqual(parseEditorItems("one\n two", ["old"]), ["one", "two"]);
console.log("report editor preserves typed claims: passed");
