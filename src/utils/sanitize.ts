const SECRET_PATTERNS: Array<[RegExp, string]> = [
  [/\bBearer\s+[A-Za-z0-9._~+/=-]+/gi, 'Bearer [REDACTED]'],
  [/\beyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\b/g, '[REDACTED_JWT]'],
  [/\b(?:sk-[A-Za-z0-9_-]{12,}|AIza[A-Za-z0-9_-]{20,})\b/g, '[REDACTED_KEY]'],
  [/\b[A-Fa-f0-9]{32,}\b/g, '[REDACTED_SECRET]'],
  [/\b[A-Za-z0-9+/]{40,}={0,2}\b/g, '[REDACTED_SECRET]'],
  [/\b[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}\b/g, '[REDACTED_EMAIL]'],
  [
    /(["']?(?:password|passwd|pwd|token|api[_-]?key|secret)["']?\s*[:=]\s*)(["']?)[^"',;\s}]+(["']?)/gi,
    '$1[REDACTED]',
  ],
];

export function sanitizeDisplay(value: string): string {
  return SECRET_PATTERNS.reduce(
    (sanitized, [pattern, replacement]) => sanitized.replace(pattern, replacement),
    value,
  );
}
