# Use Node.js image as a parent image
FROM node:18-alpine

# Set the working directory in the container
WORKDIR /app

# Copy the package.json and install dependencies
COPY package*.json ./

RUN npm install

# Copy the rest of the app's code
COPY . .

# Expose port 3000 for Next.js
EXPOSE 3000

# Command to run the Next.js app
CMD ["npm", "run", "dev"]
