// One editable quantity state shared by keyboard, + and −. Integers only:
// no empty, negative, decimal or above-limit value can be confirmed.
(function (root) {
  function parse(text, max) {
    const value = String(text ?? "").trim();
    if (!value) return { value: null, error: "Escribe una cantidad." };
    if (!/^\d+$/.test(value))
      return { value: null, error: "Solo números enteros positivos." };
    const number = Number(value);
    if (number < 1) return { value: null, error: "La cantidad mínima es 1." };
    if (!Number.isSafeInteger(number) || number > max)
      return {
        value: null,
        error:
          max > 0
            ? `El máximo que cabe ahora es ${max}.`
            : "No cabe ninguna unidad más.",
      };
    return { value: number, error: null };
  }
  function step(text, delta, max) {
    if (max < 1) return "0";
    const current = /^\d+$/.test(String(text ?? "").trim())
      ? Number(String(text).trim())
      : 0;
    return String(Math.min(max, Math.max(1, current + delta)));
  }
  // Keyboard edits keep only digits so typing, deleting and pasting stay coherent.
  function clean(text) {
    return String(text ?? "")
      .replace(/[^0-9]/g, "")
      .slice(0, 4);
  }
  const api = { parse, step, clean };
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  else root.PokeQuantity = api;
})(this);
