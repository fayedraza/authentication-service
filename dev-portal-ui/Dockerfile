# Stage 1: Build the React app
FROM node:18 AS builder

WORKDIR /app
COPY dev-portal-ui/package*.json ./
RUN npm install
COPY dev-portal-ui/. .
RUN npm run build

# Stage 2: Serve with nginx
FROM nginx:alpine

COPY --from=builder /app/build /usr/share/nginx/html
COPY dev-portal-ui/nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]