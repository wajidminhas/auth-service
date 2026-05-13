# 🔐 Auth Service

> Production-ready Authentication Microservice built with FastAPI, Apache Kafka, PostgreSQL and Docker.

[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://www.python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.109+-green.svg)](https://fastapi.tiangolo.com)
[![Docker](https://img.shields.io/badge/Docker-✓-2496ED.svg)](https://www.docker.com)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15+-336791.svg)](https://www.postgresql.org)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

## 📋 Overview

A secure, scalable authentication microservice designed for event-driven architectures. This service handles user registration, login, token management, and emits authentication events via Apache Kafka for integration with other microservices.

### ✨ Features

- 🔑 **JWT Authentication**: Stateless token-based authentication with refresh token support
- 🔒 **Secure Password Handling**: bcrypt password hashing via `passlib`
- 📨 **Event-Driven Architecture**: Publishes auth events (user registered, logged in, token refreshed) to Kafka topics
- 🐳 **Docker-Ready**: Fully containerized with multi-stage Dockerfile and docker-compose orchestration
- 🧪 **Test Coverage**: Comprehensive pytest suite with security-focused test cases
- ⚙️ **SQLModel ORM**: Type-safe database interactions with PostgreSQL
- 📦 **uv Package Manager**: Fast, modern Python dependency management
- 🛡️ **Production Hardened**: Environment-based configuration, CORS setup, and security middleware

## 🏗️ Architecture




## 🚀 Quick Start

### Prerequisites

- Docker & Docker Compose
- Python 3.11+ (for local development)
- `uv` package manager: `curl -LsSf https://astral.sh/uv/install.sh | sh`

### Run with Docker Compose (Recommended)

```bash
# Clone the repository
git clone https://github.com/wajidminhas/auth-service.git
cd auth-service

# Start all services (app, postgres, kafka, zookeeper)
docker-compose up --build

# Service will be available at: http://localhost:8000
# API Docs: http://localhost:8000/docs

# Install dependencies with uv
uv sync

# Set environment variables (copy example)
cp .env.example .env
# Edit .env with your configuration

# Run database migrations (if applicable)
# uv run alembic upgrade head

# Start the development server
uv run fastapi dev main.py




