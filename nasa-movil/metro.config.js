const { getDefaultConfig } = require("expo/metro-config");
const http = require("http");

const config = getDefaultConfig(__dirname);

config.server = config.server || {};
config.server.enhanceMiddleware = (metroMiddleware) => {
  return (req, res, next) => {
    if (req.url && req.url.startsWith("/agro-api/")) {
      const targetPath = "/api/" + req.url.slice("/agro-api/".length);
      const headers = { ...req.headers, host: "127.0.0.1:8000" };
      delete headers["accept-encoding"];

      if (typeof req.setTimeout === "function") {
        req.setTimeout(60000);
      }

      const proxyReq = http.request(
        {
          hostname: "127.0.0.1",
          port: 8000,
          path: targetPath,
          method: req.method,
          headers,
        },
        (proxyRes) => {
          res.writeHead(proxyRes.statusCode || 502, proxyRes.headers);
          proxyRes.pipe(res, { end: true });
        }
      );

      proxyReq.setTimeout(60000, () => {
        proxyReq.destroy(new Error("Upstream timeout (>60s)"));
      });

      proxyReq.on("error", (err) => {
        if (!res.headersSent) {
          res.writeHead(502, { "Content-Type": "application/json" });
        }
        if (!res.writableEnded) {
          res.end(
            JSON.stringify({
              detail: `Backend local en puerto 8000 no disponible: ${err.message}`,
            })
          );
        }
      });

      req.on("aborted", () => {
        proxyReq.destroy();
      });

      req.pipe(proxyReq, { end: true });
      return;
    }

    return metroMiddleware(req, res, next);
  };
};

module.exports = config;
