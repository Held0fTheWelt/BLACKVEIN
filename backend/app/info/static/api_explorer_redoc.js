(function () {
  var el = document.getElementById("redoc-container");
  var url = el && el.getAttribute("data-spec-url");
  if (!url || typeof Redoc === "undefined") {
    return;
  }
  Redoc.init(url, { hideDownloadButton: false, scrollYOffset: 50 }, el);
})();
