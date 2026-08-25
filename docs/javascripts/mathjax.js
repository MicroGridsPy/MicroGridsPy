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
if (typeof document$ !== "undefined") {
  document$.subscribe(function () {
    if (window.MathJax && window.MathJax.typesetPromise) {
      window.MathJax.typesetClear();
      window.MathJax.texReset();
      window.MathJax.typesetPromise();
    }
  });
}
