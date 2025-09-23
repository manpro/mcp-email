FROM node:20-slim

WORKDIR /app

# Copy package files
COPY package*.json ./

# Install dependencies
RUN npm ci

# Copy application files
COPY . .

# Environment variables (can be overridden)
ENV VITE_API_URL=http://172.16.16.148:3015
ENV VITE_EMAIL_API_URL=http://172.16.16.148:3015

# Expose port
EXPOSE 3623

# Start the application
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0", "--port", "3623"]