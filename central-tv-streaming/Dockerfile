FROM node:20-alpine

WORKDIR /app

# Install dependencies and media utilities
RUN apk add --no-cache ffmpeg
COPY package*.json ./
RUN npm install --omit=dev

# Copy source code and static assets
COPY server.js ./
COPY public/ ./public/
COPY mediamtx.yml ./

# Create data and media directories
RUN mkdir -p data media certs

EXPOSE 8080 8443

CMD ["node", "server.js"]
