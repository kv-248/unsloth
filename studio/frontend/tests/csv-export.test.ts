// SPDX-License-Identifier: AGPL-3.0-only
// Copyright 2026-present the Unsloth AI Inc. team. All rights reserved. See /studio/LICENSE.AGPL-3.0

import assert from "node:assert/strict";
import test from "node:test";

import { csvDocument, csvEscape } from "../src/features/chat/utils/csv-export.ts";
import { parseCsv } from "../src/features/chat/utils/csv-parse.ts";

test("csvDocument prefixes a UTF-8 byte-order mark", () => {
  const doc = csvDocument(["a,b", "1,2"]);
  assert.equal(doc.charCodeAt(0), 0xfeff);
  assert.equal(doc, "\ufeffa,b\n1,2");
});

test("escaped rows survive a csvDocument/parseCsv round trip with non-Latin1 and multiline text", () => {
  const header = ["name", "text"];
  const rows = [
    ["comma", "a,b"],
    ["quotes", 'she said "hi"'],
    ["crlf", "line one\r\nline two"],
    ["lf", "line one\nline two"],
    ["czech", "není potřeba"],
    ["russian", "это"],
    ["cjk", "日本語"],
    ["emoji", "👍🏽"],
  ];

  const doc = csvDocument([
    header.map(csvEscape).join(","),
    ...rows.map((cells) => cells.map(csvEscape).join(",")),
  ]);

  assert.equal(doc.charCodeAt(0), 0xfeff);

  const parsed = parseCsv(doc);
  assert.deepEqual(parsed[0], header);
  assert.deepEqual(parsed.slice(1), rows);
});

test("a trailing comma keeps its empty field when the file has no final newline", () => {
  // The same record already kept the field when a newline followed the comma.
  assert.deepEqual(parseCsv("a,b,"), [["a", "b", ""]]);
  assert.deepEqual(parseCsv("a,b,"), parseCsv("a,b,\n"));
  assert.deepEqual(parseCsv('"a","b",'), [["a", "b", ""]]);
  assert.deepEqual(parseCsv("a,b\nc,"), [
    ["a", "b"],
    ["c", ""],
  ]);
  assert.deepEqual(parseCsv(","), [["", ""]]);
  assert.deepEqual(parseCsv(",,"), [["", "", ""]]);

  // Chat import joins every column after the role, so a dropped field eats a trailing comma.
  const chat = "role,content\nuser,See you,";
  const rows = parseCsv(chat);
  assert.deepEqual(rows, [
    ["role", "content"],
    ["user", "See you", ""],
  ]);
  assert.equal(rows[1].slice(1).join(","), "See you,");
  assert.deepEqual(parseCsv(chat), parseCsv(`${chat}\n`));
});

test("parseCsv returns identical rows with and without a leading BOM", () => {
  const body = 'name,text\nczech,není potřeba\ncjk,日本語\nemoji,👍🏽';
  const withBom = "\ufeff" + body;

  assert.deepEqual(parseCsv(withBom), parseCsv(body));
});
