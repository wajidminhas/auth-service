# 🔐 Auth Service

A scalable authentication and authorization microservice built with Python and FastAPI.

This service provides secure user authentication, JWT token management, user registration, login functionality, and role-based access control for modern applications and microservices architectures.

---

## 🚀 Features

* User Registration & Login
* JWT Authentication
* Access & Refresh Tokens
* Password Hashing
* Role-Based Authorization
* FastAPI Backend
* PostgreSQL Database
* Docker Support
* Environment-Based Configuration
* RESTful API Architecture
* Swagger API Documentation
* Scalable Microservice Structure

---

## 🛠️ Tech Stack

* Python
* FastAPI
* PostgreSQL
* SQLAlchemy / SQLModel
* Docker
* JWT
* Pydantic
* Alembic
* UV Package Manager

---

## 📂 Project Structure

```bash
auth-service/
│
├── app/
│   ├── api/
│   ├── core/
│   ├── models/
│   ├── schemas/
│   ├── services/
│   ├── db/
│   └── main.py
│
├── tests/
├── alembic/
├── docker/
├── .env
├── docker-compose.yml
├── pyproject.toml
└── README.md
```

---

## ⚙️ Installation

### 1️⃣ Clone the Repository

```bash
git clone https://github.com/wajidminhas/auth-service.git
cd auth-service
```

---

### 2️⃣ Install UV

#### Linux / Mac

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

#### Windows

```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

---

### 3️⃣ Create Virtual Environment

```bash
uv venv
```

Activate environment:

#### Linux / Mac

```bash
source .venv/bin/activate
```

#### Windows

```bash
.venv\Scripts\activate
```

---

### 4️⃣ Install Dependencies

Using UV:

```bash
uv sync
```

---

## 🔑 Environment Variables

Create a `.env` file in the root directory.

Example:

```env
DATABASE_URL=postgresql://postgres:password@localhost:5432/authdb

SECRET_KEY=your_secret_key

ALGORITHM=HS256

ACCESS_TOKEN_EXPIRE_MINUTES=30
```

---

## 🐳 Docker Setup

Run with Docker Compose:

```bash
docker-compose up --build
```

---

## ▶️ Run the Application

```bash
uvicorn app.main:app --reload
```

Application will run on:

```bash
http://127.0.0.1:8000
```

---

## 📘 API Documentation

After starting the server:

### Swagger UI

```bash
http://127.0.0.1:8000/docs
```

### ReDoc

```bash
http://127.0.0.1:8000/redoc
```

---

## 🔐 Authentication Flow

1. User registers
2. User logs in
3. Server generates JWT token
4. Protected routes require Bearer Token
5. Refresh token used for session renewal

---

## 📌 Example Endpoints

| Method | Endpoint    | Description            |
| ------ | ----------- | ---------------------- |
| POST   | `/register` | Register new user      |
| POST   | `/login`    | Login user             |
| GET    | `/profile`  | Get authenticated user |
| POST   | `/refresh`  | Refresh access token   |

---

## 🧪 Running Tests

```bash
pytest
```

---

## 📈 Future Improvements

* OAuth2 Integration
* Email Verification
* Multi-Factor Authentication
* Redis Caching
* Kafka Event Streaming
* API Gateway Integration
* Rate Limiting
* Audit Logging

---

## 🤝 Contributing

Contributions are welcome.

1. Fork the repository
2. Create your feature branch
3. Commit your changes
4. Push to the branch
5. Open a Pull Request

---

## 📄 License

This project is licensed under the MIT License.

---

## 👨‍💻 Author

### Wajid Shabbir

GitHub: [https://github.com/wajidminhas](https://github.com/wajidminhas)

---

## ⭐ Support

If you like this project, give it a ⭐ on GitHub.
