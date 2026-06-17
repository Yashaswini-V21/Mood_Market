# Build stage
FROM node:20-alpine as builder

WORKDIR /app

COPY package*.json ./

RUN npm install

COPY . .

RUN npm run build

# Production serve stage
FROM node:20-alpine

WORKDIR /app

# Copy node_modules to run serve locally
COPY --from=builder /app/node_modules ./node_modules
# Vite build outputs to 'dist' folder instead of 'build'
COPY --from=builder /app/dist ./dist

EXPOSE 3000

CMD ["sh", "-c", "npx serve -s dist -l ${PORT:-3000}"]
