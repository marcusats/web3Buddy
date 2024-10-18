# Use Node.js image as a parent image
FROM node:18-alpine
 
RUN apk add --no-cache python3 make g++ bash

WORKDIR /app
 
COPY package*.json ./
 
RUN npm install
 
COPY . .
 
EXPOSE 3000
 
CMD ["npm", "run", "dev"]