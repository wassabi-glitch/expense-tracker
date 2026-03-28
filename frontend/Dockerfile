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

# Clean default config
RUN rm /etc/nginx/conf.d/default.conf

# Copy custom config
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Copy the build output from Step 1
COPY --from=build /app/dist /usr/share/nginx/html

EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
