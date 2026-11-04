FROM node:24-slim
WORKDIR /app/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend ./
COPY art/roger.json art/plane.json /app/art/
RUN npm run build
EXPOSE 3100
CMD ["npm", "run", "start", "--", "--port", "3100"]
