import { StreamLanguage, type StreamParser } from "@codemirror/language";

const KEYWORDS = new Set(["let", "if", "else", "while", "print", "and", "or", "not"]);
const TYPES = new Set(["int", "float", "string", "bool"]);
const ATOMS = new Set(["true", "false"]);

interface CodeBridgeState {
  inString: boolean;
}

/** Highlighting for the CodeBridge source language (mirrors the lexer). */
const codebridgeParser: StreamParser<CodeBridgeState> = {
  name: "codebridge",
  startState: () => ({ inString: false }),
  token(stream) {
    if (stream.eatSpace()) return null;
    if (stream.peek() === "#") {
      stream.skipToEnd();
      return "comment";
    }
    if (stream.peek() === '"') {
      stream.next();
      let escaped = false;
      while (!stream.eol()) {
        const ch = stream.next();
        if (ch === '"' && !escaped) break;
        escaped = !escaped && ch === "\\";
      }
      return "string";
    }
    if (stream.match(/^\d+(\.\d+)?([eE][+-]?\d+)?/)) return "number";
    if (stream.match(/^[A-Za-z][A-Za-z0-9_]*/)) {
      const word = stream.current();
      if (KEYWORDS.has(word)) return "keyword";
      if (TYPES.has(word)) return "typeName";
      if (ATOMS.has(word)) return "atom";
      return "variableName";
    }
    if (stream.match(/^(==|!=|<=|>=|[+\-*/%=<>])/)) return "operator";
    if (stream.match(/^[(){},;:]/)) return "punctuation";
    stream.next();
    return "invalid";
  },
  languageData: { commentTokens: { line: "#" } },
};

/** Highlighting for the three-address code listing. */
const tacParser: StreamParser<null> = {
  name: "tac",
  startState: () => null,
  token(stream) {
    if (stream.eatSpace()) return null;
    if (stream.sol() && stream.match(/^L\d+:/)) return "labelName";
    if (stream.match(/^(ifFalse|ifTrue|goto|print|not)\b/)) return "keyword";
    if (stream.match(/^L\d+\b/)) return "labelName";
    if (stream.match(/^\(float\)/)) return "typeName";
    if (stream.match(/^t\d+\b/)) return "variableName.special";
    if (stream.match(/^(true|false)\b/)) return "atom";
    if (stream.peek() === '"') {
      stream.next();
      let escaped = false;
      while (!stream.eol()) {
        const ch = stream.next();
        if (ch === '"' && !escaped) break;
        escaped = !escaped && ch === "\\";
      }
      return "string";
    }
    if (stream.match(/^-?\d+(\.\d+)?([eE][+-]?\d+)?/)) return "number";
    if (stream.match(/^[A-Za-z][A-Za-z0-9_]*/)) return "variableName";
    if (stream.match(/^(==|!=|<=|>=|[+\-*/%=<>])/)) return "operator";
    stream.next();
    return "punctuation";
  },
};

export const codebridgeLanguage = StreamLanguage.define(codebridgeParser);
export const tacLanguage = StreamLanguage.define(tacParser);
