// In-browser port of scam_triage (signals.py, model.py, triage.py).
// Loads the JSON exported by scripts/export_web.py and reproduces triage() exactly.
// Parity with Python is checked by tests/test_web_parity.py.

// ---------- Python-regex -> JS-regex translation ----------
// Python's re is Unicode-aware for \w \d \b; JS is ASCII-only for those even with the u flag.
const W = "\\p{L}\\p{N}_";
const WORD_BOUNDARY = `(?:(?<=[${W}])(?![${W}])|(?<![${W}])(?=[${W}]))`;

export function pyRegex(src, flags = "") {
  let out = "";
  let inClass = false;
  for (let i = 0; i < src.length; i++) {
    const c = src[i];
    if (c === "\\" && i + 1 < src.length) {
      const n = src[i + 1];
      i++;
      if (n === "w") out += inClass ? W : `[${W}]`;
      else if (n === "d") out += "\\p{Nd}";
      else if (n === "b" && !inClass) out += WORD_BOUNDARY;
      else if (n === '"' || n === "'") out += n; // identity escapes invalid under /u
      else out += "\\" + n;
      continue;
    }
    if (c === "[" && !inClass) inClass = true;
    else if (c === "]" && inClass) inClass = false;
    out += c;
  }
  out = out.replace(/^\(\?u\)/, "");
  return new RegExp(out, "u" + flags);
}

const cp = (s) => Array.from(s); // code points (Python indexes by code point, JS by UTF-16 unit)
const lastCodePoints = (s, n) => cp(s).slice(-n).join("");

// ---------- Engine ----------
export class Engine {
  constructor(m) {
    this.m = m;
    const r = m.regex;
    this.urlRe = pyRegex(r.url, "gi");
    this.phoneRe = pyRegex(r.phone, "g");
    this.amountRe = pyRegex(r.amount, "gi");
    this.refRe = pyRegex(r.reference, "i");
    this.negRe = pyRegex(r.negation, "i");
    this.tokenRe = pyRegex(r.token, "g");
    this.digitsRe = /\p{Nd}+/gu;
    this.patterns = Object.entries(m.patterns).map(([sid, pats]) => [sid, pats.map((p) => pyRegex(p, "gi"))]);
    this.negatable = new Set(m.negatable);
    this.shorteners = new Set(m.url_shorteners);
    this.riskyTlds = new Set(m.risky_tlds);
    this.stop = new Set(m.stop_words);
    this.context = new Set(m.context_signals);
    this.wordIndex = new Map(m.word.vocab.map((t, i) => [t, i]));
    this.charIndex = new Map(m.char.vocab.map((t, i) => [t, i]));
    this.nWord = m.word.vocab.length;
    this.nChar = m.char.vocab.length;
    this.signalIds = m.signal_ids;
    // Dense type weights: typeCoef[featureIndex] -> Float32Array(classes)
    this.typeCoef = new Map(m.type.index.map((j, k) => [j, Float32Array.from(m.type.coef[k])]));
  }

  static async load(url) {
    const res = await fetch(url);
    if (!res.ok) throw new Error(`model fetch failed: ${res.status}`);
    return new Engine(await res.json());
  }

  // ----- signals.py -----
  normalize(text) {
    let t = text.normalize("NFKC");
    for (const z of this.m.zero_width) t = t.split(z).join("");
    t = t.replace(/’|‘/g, "'").replace(/“|”/g, '"');
    return t.replace(/\s+/gu, " ").trim();
  }

  extractUrls(text) {
    return [...text.matchAll(this.urlRe)].map((m) => m[0].replace(/[.,;:!?)]+$/u, ""));
  }

  findPhones(text) {
    const out = [];
    for (const m of text.matchAll(this.phoneRe)) {
      const digits = (m[0].match(/\p{Nd}/gu) || []).length;
      if (digits < 9 || this.refRe.test(lastCodePoints(text.slice(0, m.index), 16))) continue;
      out.push(m[0].trim());
    }
    return out;
  }

  host(url) {
    if (!/^https?:\/\//i.test(url)) url = "http://" + url;
    let rest = url.replace(/^[a-z][a-z0-9+.-]*:\/\//i, "");
    const netloc = rest.split(/[/?#]/)[0];
    let h = netloc.slice(netloc.lastIndexOf("@") + 1);
    h = h.startsWith("[") ? h.slice(1, h.indexOf("]")) : h.split(":")[0];
    return h.toLowerCase();
  }

  isSuspiciousUrl(url) {
    const host = this.host(url);
    if (!host) return false;
    if (this.shorteners.has(host)) return true;
    if (/^\d{1,3}(\.\d{1,3}){3}$/.test(host)) return true;
    const labels = host.split(".");
    if (this.riskyTlds.has(labels[labels.length - 1])) return true;
    const reg = labels.length >= 2 ? labels[labels.length - 2] : host;
    const brands = this.m.imitated_brands;
    if (reg.includes("-") && brands.some((b) => reg.includes(b))) return true;
    if (reg.includes("-") && reg.split("-").some((p) => this.m.lure_words.includes(p))) return true;
    if (labels.length >= 4 && brands.some((b) => labels.slice(0, -2).join(".").includes(b))) return true;
    return false;
  }

  negated(sid, text, index) {
    return this.negatable.has(sid) && this.negRe.test(lastCodePoints(text.slice(0, index), 60));
  }

  /** Signals that fire, with evidence. Returns [{id, reason, evidence}] in Python's order. */
  detect(text) {
    const norm = this.normalize(text);
    const hits = [];
    for (const [sid, pats] of this.patterns) {
      let found = null;
      for (const re of pats) {
        for (const m of norm.matchAll(re)) {
          if (!this.negated(sid, norm, m.index)) { found = m[0]; break; }
        }
        if (found !== null) break;
      }
      if (found !== null) hits.push({ id: sid, reason: this.m.reasons[sid], evidence: found });
    }
    const urls = this.extractUrls(norm);
    if (urls.length) {
      hits.push({ id: "has_link", reason: this.m.reasons.has_link, evidence: urls[0] });
      const bad = urls.filter((u) => this.isSuspiciousUrl(u));
      if (bad.length) hits.push({ id: "suspicious_link", reason: this.m.reasons.suspicious_link, evidence: bad[0] });
    }
    const phones = this.findPhones(norm);
    if (phones.length) hits.push({ id: "has_phone_number", reason: this.m.reasons.has_phone_number, evidence: phones[0] });
    const amount = norm.match(new RegExp(this.amountRe.source, "iu"));
    if (amount) hits.push({ id: "money_amount", reason: this.m.reasons.money_amount, evidence: amount[0] });
    return hits;
  }

  // ----- model.py -----
  preprocess(text) {
    let t = this.normalize(text).toLowerCase();
    t = t.replace(this.urlRe, " __url__ ");
    for (const p of this.findPhones(t)) t = t.split(p).join(" __phone__ ");
    t = t.replace(this.amountRe, " __amount__ ");
    t = t.replace(this.digitsRe, "0");
    return t.replace(/\s+/gu, " ").trim();
  }

  wordNgrams(pre) {
    const toks = [...pre.toLowerCase().matchAll(this.tokenRe)].map((m) => m[0]);
    const [lo, hi] = this.m.word.ngram_range;
    const grams = [];
    for (let n = lo; n <= hi; n++) for (let i = 0; i + n <= toks.length; i++) grams.push(toks.slice(i, i + n).join(" "));
    return grams;
  }

  charNgrams(pre) {
    const doc = pre.toLowerCase().replace(/\s\s+/gu, " ");
    const [lo, hi] = this.m.char.ngram_range;
    const grams = [];
    for (const raw of doc.split(/\s+/u).filter(Boolean)) {
      const w = cp(" " + raw + " ");
      for (let n = lo; n <= hi; n++) {
        let off = 0;
        grams.push(w.slice(off, off + n).join(""));
        while (off + n < w.length) { off++; grams.push(w.slice(off, off + n).join("")); }
        if (off === 0) break;
      }
    }
    return grams;
  }

  tfidf(grams, index, idf, offset) {
    const counts = new Map();
    for (const g of grams) {
      const j = index.get(g);
      if (j !== undefined) counts.set(j, (counts.get(j) || 0) + 1);
    }
    const vals = [];
    let norm = 0;
    for (const [j, c] of counts) {
      const v = (Math.log(c) + 1) * idf[j];
      vals.push([j, v]);
      norm += v * v;
    }
    norm = Math.sqrt(norm) || 1;
    return vals.map(([j, v]) => [j + offset, v / norm]);
  }

  /** Sparse feature vector [[index, value], ...] in the same column order as the Python featurizer. */
  features(text) {
    const pre = this.preprocess(text);
    const fired = new Set(this.detect(text).map((h) => h.id));
    const x = [
      ...this.tfidf(this.wordNgrams(pre), this.wordIndex, this.m.word.idf, 0),
      ...this.tfidf(this.charNgrams(pre), this.charIndex, this.m.char.idf, this.nWord),
    ];
    this.signalIds.forEach((sid, k) => { if (fired.has(sid)) x.push([this.nWord + this.nChar + k, this.m.signal_weight]); });
    return { pre, x };
  }

  featureName(j) {
    if (j < this.nWord) return this.m.word.vocab[j];
    if (j < this.nWord + this.nChar) return "char:" + this.m.char.vocab[j - this.nWord];
    return "signal:" + this.signalIds[j - this.nWord - this.nChar];
  }

  level(score) {
    const t = this.m.thresholds;
    return score >= t.high ? "high" : score >= t.medium ? "medium" : "low";
  }

  isReadablePhrase(name) {
    if (name.startsWith("char:") || name.startsWith("signal:") || name.includes("__")) return false;
    return !name.split(" ").every((w) => this.stop.has(w) || w.startsWith("__") || /^\d+$/.test(w) || cp(w).length < 3);
  }

  // ----- triage.py -----
  triage(text) {
    const t0 = performance.now();
    const { pre, x } = this.features(text);
    const w = this.m.risk.coef;
    let logit = this.m.risk.intercept;
    const contrib = [];
    for (const [j, v] of x) { const c = v * w[j]; logit += c; contrib.push([j, c]); }
    const score = 1 / (1 + Math.exp(-logit));
    const level = this.level(score);

    const classes = this.m.type.classes;
    const z = Float64Array.from(this.m.type.intercept);
    for (const [j, v] of x) {
      const wc = this.typeCoef.get(j);
      if (wc) for (let k = 0; k < z.length; k++) z[k] += v * wc[k];
    }
    const zmax = Math.max(...z);
    const ez = Array.from(z, (v) => Math.exp(v - zmax));
    const zs = ez.reduce((a, b) => a + b, 0);
    const probs = ez.map((v) => v / zs);
    const best = probs.indexOf(Math.max(...probs));

    contrib.sort((a, b) => b[1] - a[1] || a[0] - b[0]); // ties broken by column index, like scipy
    const byName = new Map(contrib.map(([j, c]) => [this.featureName(j), c]));
    const allHits = this.detect(text);
    let hits = allHits.filter((h) => (byName.get("signal:" + h.id) || 0) > 0);
    const fired = new Set(hits.map((h) => h.id));
    if (fired.has("suspicious_link")) hits = hits.filter((h) => h.id !== "has_link");
    if (level === "low") hits = hits.filter((h) => !this.context.has(h.id));
    hits.sort((a, b) => (this.context.has(a.id) - this.context.has(b.id)) || (byName.get("signal:" + b.id) - byName.get("signal:" + a.id)));
    const reasons = hits.slice(0, this.m.max_reasons).map((h) => h.reason);
    let phrases = [...byName].filter(([n, c]) => c > 0 && this.isReadablePhrase(n)).slice(0, this.m.max_phrases).map(([n]) => n);

    const tax = this.m.taxonomy;
    let typeId = classes[best], typeConf = probs[best], summary;
    if (level === "low") {
      phrases = [];
      typeId = "legit";
      typeConf = 1 - score;
      summary = "No strong scam patterns found." + (reasons.length ? " A few things are worth double-checking, though." : "");
    } else {
      const st = tax[classes[best]];
      summary = `${level === "high" ? "This looks like a scam" : "This could be a scam"}: ${st.label.toLowerCase()}. ${st.description}`;
    }
    return {
      risk_score: round4(score),
      risk_level: level,
      scam_type: typeId,
      scam_type_label: tax[typeId].label,
      type_confidence: round4(typeConf),
      summary,
      reasons,
      key_phrases: phrases,
      next_steps: tax[typeId].next_steps,
      // Extras for the site's explainability UI (not part of the Python result).
      extras: {
        signals: allHits,
        reason_ids: hits.slice(0, this.m.max_reasons).map((h) => h.id),
        type_probs: Object.fromEntries(classes.map((c, k) => [c, probs[k]])),
        top_features: contrib.slice(0, 12).map(([j, c]) => ({ name: this.featureName(j), contribution: c })),
        bottom_features: contrib.slice(-6).reverse().map(([j, c]) => ({ name: this.featureName(j), contribution: c })),
        preprocessed: pre,
        n_features: x.length,
        logit,
        ms: performance.now() - t0,
      },
    };
  }
}

const round4 = (v) => Math.round(v * 1e4) / 1e4;
