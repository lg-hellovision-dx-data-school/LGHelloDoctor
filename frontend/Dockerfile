# 1단계: 빌드
FROM node:20-alpine AS builder

WORKDIR /app

COPY package*.json ./
RUN npm ci

COPY . .

# 백엔드 URL은 빌드 시 ARG로 주입 (docker-compose에서 설정)
ARG VITE_CHAT_API_URL=http://localhost:8000/chat
ENV VITE_CHAT_API_URL=$VITE_CHAT_API_URL

RUN npm run build

# 2단계: nginx 서빙
FROM nginx:alpine

COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
