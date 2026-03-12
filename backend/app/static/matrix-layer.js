/**
 * Matrix falling-code layer (inspired by andresz74/matrix).
 * Dark blue rain, single canvas, runs only when #matrix-layer exists.
 */
(function () {
  "use strict";

  var matrixChars = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789<>[]{}|;:";
  var characters = matrixChars.split("");

  function resizeCanvas(canvas, ctx) {
    var rect = canvas.getBoundingClientRect();
    var dpr = window.devicePixelRatio || 1;
    canvas.width = Math.round(rect.width * dpr);
    canvas.height = Math.round(rect.height * dpr);
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    return { width: rect.width, height: rect.height };
  }

  function matrixRain(canvas, opts) {
    opts = opts || {};
    var color = opts.color || "rgba(30, 50, 90, 0.85)";
    var trailOpacity = opts.trailOpacity != null ? opts.trailOpacity : 0.035;
    var fontSize = opts.fontSize || 12;
    var speedFactor = opts.speedFactor != null ? opts.speedFactor : 0.85;
    var delayFactor = opts.delayFactor != null ? opts.delayFactor : 3;
    var fps = opts.fps != null ? opts.fps : 24;

    var ctx = canvas.getContext("2d");
    var canvasWidth = 0;
    var canvasHeight = 0;
    var columns = 0;
    var drops = [];
    var delays = [];
    var frameInterval = 1000 / fps;
    var lastFrameTime = 0;

    function updateMetrics() {
      var size = resizeCanvas(canvas, ctx);
      canvasWidth = size.width;
      canvasHeight = size.height;
      columns = Math.floor(canvasWidth / fontSize);
      drops = new Array(columns);
      delays = new Array(columns);
      for (var i = 0; i < columns; i++) {
        drops[i] = Math.random() * -20;
        delays[i] = Math.random() * delayFactor;
      }
    }

    function draw(timestamp) {
      if (!timestamp) timestamp = 0;
      if (timestamp - lastFrameTime < frameInterval) {
        requestAnimationFrame(draw);
        return;
      }
      lastFrameTime = timestamp;

      ctx.fillStyle = "rgba(7, 12, 22, " + trailOpacity + ")";
      ctx.fillRect(0, 0, canvasWidth, canvasHeight);

      ctx.fillStyle = color;
      ctx.font = fontSize + "px \"JetBrains Mono\", \"Fira Mono\", monospace";

      for (var i = 0; i < columns; i++) {
        var ch = characters[Math.floor(Math.random() * characters.length)];
        var x = i * fontSize;
        var y = drops[i] * fontSize;

        ctx.fillText(ch, x, y);

        if (delays[i] <= 0) {
          drops[i] += 1;
          delays[i] = (Math.random() * delayFactor) / speedFactor;
        } else {
          delays[i] -= 1;
        }

        if (y > canvasHeight && Math.random() > 0.975) {
          drops[i] = 0;
        }
      }

      requestAnimationFrame(draw);
    }

    updateMetrics();
    window.addEventListener("resize", updateMetrics);
    draw(0);
    return canvas;
  }

  function start() {
    var layer = document.getElementById("matrix-layer");
    var canvas = layer && document.getElementById("matrixCanvas");
    if (!layer || !canvas) return;
    if (window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
      return;
    }

    matrixRain(canvas, {
      color: "rgba(25, 45, 85, 0.9)",
      trailOpacity: 0.04,
      fontSize: 11,
      speedFactor: 0.8,
      delayFactor: 4,
      fps: 28
    });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", start);
  } else {
    start();
  }
})();
