// MathJax 3 configuration for pymdownx.arithmatex (generic mode).
// Arithmatex wraps math in elements with class "arithmatex" using \( \) and
// \[ \] delimiters; we scope MathJax to those and re-typeset after Zensical's
// instant navigation (the `document$` observable from the theme bundle).
window.MathJax = {
  tex: {
    inlineMath: [["\\(", "\\)"]],
    displayMath: [["\\[", "\\]"]],
    processEscapes: true,
    processEnvironments: true,
    tags: "none",
  },
  options: {
    ignoreHtmlClass: ".*|",
    processHtmlClass: "arithmatex",
  },
};

// Re-typeset on instant page loads. `typeof` guard keeps the script safe if the
// observable is ever unavailable (e.g. instant navigation disabled).
//
// Instant navigation swaps the page's DOM, which detaches the <style> element the
// CHTML output jax injected on the previous page. MathJax still holds a reference
// to that now-orphaned stylesheet, whose `.sheet` is null, so its next attempt to
// add CSS throws "Cannot read properties of null (reading 'insertRule')".
// `startup.output.clearCache()` drops that cached stylesheet/adaptor state so the
// output jax re-creates a fresh <style> in the new DOM on the next typeset.
if (typeof document$ !== "undefined") {
  document$.subscribe(function () {
    if (window.MathJax && window.MathJax.typesetPromise) {
      if (
        window.MathJax.startup &&
        window.MathJax.startup.output &&
        typeof window.MathJax.startup.output.clearCache === "function"
      ) {
        window.MathJax.startup.output.clearCache();
      }
      window.MathJax.typesetClear();
      window.MathJax.texReset();
      window.MathJax.typesetPromise();
    }
  });
}
