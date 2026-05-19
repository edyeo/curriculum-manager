FROM node:20-slim AS builder
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM node:20-slim
RUN npm install -g serve
WORKDIR /app
COPY --from=builder /app/dist .
EXPOSE 3010
CMD ["serve", "-s", ".", "-l", "3010"]
