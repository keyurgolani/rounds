# Alpine-based Chromium image keeps the layer slim. Using puppeteer-core
# + system Chromium avoids puppeteer's bundled-browser download (which
# pulls ~300 MB and breaks on many CI mirrors).

FROM node:22-alpine

RUN apk add --no-cache \
    chromium \
    nss \
    freetype \
    harfbuzz \
    ca-certificates \
    ttf-freefont \
    font-noto-emoji

ENV PUPPETEER_SKIP_CHROMIUM_DOWNLOAD=true \
    NODE_ENV=production \
    PORT=4000

WORKDIR /app

COPY package.json ./
RUN npm install --omit=dev --no-audit --no-fund

COPY server.js ./

EXPOSE 4000

CMD ["node", "server.js"]
