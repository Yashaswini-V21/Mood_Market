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

RUN npm install -g serve

# Vite build outputs to 'dist' folder instead of 'build'
COPY --from=builder /app/dist ./dist

EXPOSE 3000

CMD ["npx", "serve", "-s", "dist", "-l", "3000"]
