# Step 1: Build the React application
FROM --platform=linux/amd64 node:20-slim AS build

# Install essential build libs for Tailwind/Vite (Rust-based tools)
RUN apt-get update && apt-get install -y python3 make g++

WORKDIR /app
COPY package*.json ./
RUN npm install
COPY . .

# Vite env vars must exist at build-time (npm run build), not only runtime.
ARG VITE_TELEGRAM_BOT_USERNAME
ENV VITE_TELEGRAM_BOT_USERNAME=${VITE_TELEGRAM_BOT_USERNAME}

# Run the build
RUN npm run build

# Step 2: Serve the application with Nginx (Debian based)
FROM --platform=linux/amd64 nginx:1.25

# Copy custom config directly
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Copy the build output from Step 1
COPY --from=build /app/dist /usr/share/nginx/html

# Copy the entrypoint script
COPY entrypoint.sh /app/entrypoint.sh
RUN sed -i 's/\r$//' /app/entrypoint.sh && chmod +x /app/entrypoint.sh

# Default values for local development (matches docker-compose)
ENV API_URL=http://api:9000
ENV API_HOST=localhost

EXPOSE 80

# Execute the debug entrypoint using /bin/sh directly to avoid permission issues
ENTRYPOINT ["/bin/sh", "/app/entrypoint.sh"]
