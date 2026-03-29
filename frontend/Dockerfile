# Step 1: Build the React application
FROM --platform=linux/amd64 node:20-slim AS build

# Install essential build libs for Tailwind/Vite (Rust-based tools)
RUN apt-get update && apt-get install -y python3 make g++

WORKDIR /app
COPY package*.json ./
RUN npm install
COPY . .

# Run the build
RUN npm run build

# Step 2: Serve the application with Nginx (Debian based)
FROM --platform=linux/amd64 nginx:1.25

# Copy custom config as a template for envsubst
COPY nginx.conf /etc/nginx/templates/default.conf.template

# Copy the build output from Step 1
COPY --from=build /app/dist /usr/share/nginx/html

# Default values for local development (matches docker-compose)
ENV API_URL=http://api:9000
ENV API_HOST=localhost

# ONLY replace our custom variables, leave $host, $remote_addr, etc alone!
ENV NGINX_ENVSUBST_FILTER=API_URL,API_HOST

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
