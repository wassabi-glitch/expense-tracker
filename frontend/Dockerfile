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

# Copy custom config directly
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Copy the build output from Step 1
COPY --from=build /app/dist /usr/share/nginx/html

# Install curl to perform health checks against the backend
RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*

EXPOSE 80

# Wait for the backend to be reachable before starting Nginx
CMD sh -c "until curl -s http://api:9000/health; do echo 'Waiting for API...'; sleep 2; done && echo 'API is up - starting Nginx' && nginx -g 'daemon off;'"
