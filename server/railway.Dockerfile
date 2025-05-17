FROM node:18-alpine AS builder

WORKDIR /app

# Install pnpm
RUN corepack enable && corepack prepare pnpm@8.7.0 --activate

# Copy package files
COPY server/package.json ./package.json
COPY server/pnpm-lock.yaml ./pnpm-lock.yaml
COPY .npmrc ./

# Install dependencies with verbose logging
RUN pnpm install

# Copy source files
COPY server/tsconfig.json ./tsconfig.json
COPY server/src ./src

# Build the application
RUN pnpm build

FROM node:18-alpine AS runner

WORKDIR /app

ENV NODE_ENV=production

# Install pnpm
RUN corepack enable && corepack prepare pnpm@8.7.0 --activate

# Copy package files and install production dependencies
COPY server/package.json ./package.json
COPY server/pnpm-lock.yaml ./pnpm-lock.yaml
COPY .npmrc ./
RUN pnpm install --prod

# Copy built app
COPY --from=builder /app/dist ./dist

# Expose the port the app will run on
EXPOSE 3001

# Start the application
CMD ["node", "dist/index.js"] 