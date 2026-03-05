# Stage 1: Build React App
FROM node:18-alpine AS build
WORKDIR /app
COPY package*.json ./
RUN npm install
COPY . .
RUN npm run build

# Stage 2: Serve with Nginx
FROM nginx:alpine
COPY --from=build /app/dist /usr/share/nginx/html

# Copy a basic nginx config if necessary, or just rely on default
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
