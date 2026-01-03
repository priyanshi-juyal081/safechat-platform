# SafeChat Platform 🚀

A real-time chat and live streaming platform with AI-powered content moderation. Built with Django Channels (WebSockets), React, and AI toxicity detection.
## ✨ Features

- 🔴 **Live Streaming** - Go live with camera access, real-time viewer counts
- 💬 **Real-Time Chat** - WebSocket-powered instant messaging
- 🤖 **AI Moderation** - Automatic toxicity detection and content filtering
- ⚠️ **Warning System** - 3-strike system with automatic restrictions
- 🛡️ **Manual Moderation** - Tools to warn and restrict users manually
- 📺 **Stream Discovery** - Browse and join live streams
- 🎯 **Stream Chat** - Dedicated chat rooms for each live stream

## 🎥 Demo

[Add screenshots or demo GIF here]

## 🏗️ Tech Stack

### Backend
- **Django 4.2+** - Web framework
- **Django Channels** - WebSocket support
- **Django REST Framework** - RESTful API
- **Daphne** - ASGI server
- **SQLite** - Database (upgradeable to PostgreSQL)

### Frontend
- **React 18** - UI framework
- **Vite** - Build tool
- **Tailwind CSS** - Styling
- **Lucide React** - Icons
- **WebSocket API** - Real-time communication

### AI/ML
- Keyword-based toxicity detection (default)
- Upgradeable to transformer models (Hugging Face)
- Support for external APIs (Perspective API, OpenAI Moderation)

## 📋 Prerequisites

Before you begin, ensure you have the following installed:

- **Python 3.9+** - [Download](https://www.python.org/downloads/)
- **Node.js 18+** - [Download](https://nodejs.org/)
- **Git** - [Download](https://git-scm.com/)
- **pip** (comes with Python)
- **npm** (comes with Node.js)

### Verify Installation

```bash
python --version    # Should be 3.9 or higher
node --version      # Should be 18 or higher
npm --version       # Should be 9 or higher
git --version
```

## 🚀 Quick Start

### 1. Clone the Repository

```bash
git clone https://github.com/YOUR_USERNAME/safechat-platform.git
cd safechat-platform
```

### 2. Backend Setup (Django)

```bash
# Navigate to backend folder
cd backend

# Create virtual environment
python -m venv venv

# Activate virtual environment
# Windows:
venv\Scripts\activate
# Mac/Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# If requirements.txt doesn't exist, install manually:
pip install django djangorestframework django-cors-headers channels daphne Pillow

# Create database tables
python manage.py makemigrations
python manage.py migrate

# Create admin user (optional but recommended)
python manage.py createsuperuser
# Enter username, email, and password when prompted

# Start Django server
python manage.py runserver
```

The backend should now be running at **http://localhost:8000**

### 3. Frontend Setup (React)

Open a **NEW terminal window** (keep the backend running):

```bash
# Navigate to frontend folder
cd frontend

# Install dependencies
npm install

# Start development server
npm run dev
```

The frontend should now be running at **http://localhost:5173**

### 4. Access the Application

Open your browser and go to: **http://localhost:5173**

## 📖 Detailed Setup Guide

### Backend Configuration

#### Environment Variables (Optional)

Create a `.env` file in the `backend` folder:

```env
DEBUG=True
SECRET_KEY=your-secret-key-here
ALLOWED_HOSTS=localhost,127.0.0.1
DATABASE_URL=sqlite:///db.sqlite3
```

#### Database Setup

The project uses SQLite by default. To use PostgreSQL:

1. Install PostgreSQL
2. Install psycopg2: `pip install psycopg2-binary`
3. Update `settings.py`:

```python
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'safechat',
        'USER': 'your_username',
        'PASSWORD': 'your_password',
        'HOST': 'localhost',
        'PORT': '5432',
    }
}
```

### Frontend Configuration

#### Environment Variables (Optional)

Create a `.env` file in the `frontend` folder:

```env
VITE_API_URL=http://localhost:8000
VITE_WS_URL=ws://localhost:8000
```

## 🎮 Usage Guide

### For Users

1. **Join Platform**: Enter a username to start
2. **Global Chat**: Send messages in the public chat room
3. **Go Live**: Click "Go Live", enter a title, and start streaming
4. **Watch Streams**: Browse live streams and join any stream
5. **Stream Chat**: Comment on live streams in real-time

### For Moderators

- **Warn Users**: Click the ⚠️ icon on any message
- **Restrict Users**: Click the 🚫 icon to immediately restrict a user
- **View Warnings**: Check user warning counts in the header
- **Admin Panel**: Access http://localhost:8000/admin for full moderation tools

### Moderation System

- **Automatic Detection**: AI scans all messages for toxicity
- **Warning System**: Users get 3 warnings before restriction
- **Manual Actions**: Moderators can warn or restrict at any time
- **Restrictions**: Restricted users cannot send messages

## 🔧 Troubleshooting

### Common Issues

#### 1. Virtual Environment Not Activating

**Windows PowerShell:**
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
venv\Scripts\Activate.ps1
```

**Alternative - Use Python directly:**
```bash
venv\Scripts\python.exe manage.py runserver
```

#### 2. Port Already in Use

**Kill process on port 8000 (Backend):**

Windows:
```bash
netstat -ano | findstr :8000
taskkill /PID <PID_NUMBER> /F
```

Mac/Linux:
```bash
lsof -ti:8000 | xargs kill -9
```

**Kill process on port 5173 (Frontend):**

Windows:
```bash
netstat -ano | findstr :5173
taskkill /PID <PID_NUMBER> /F
```

Mac/Linux:
```bash
lsof -ti:5173 | xargs kill -9
```

#### 3. WebSocket Connection Failed

- Ensure backend is running on port 8000
- Check browser console (F12) for errors
- Verify CORS settings in `settings.py`
- Make sure `ASGI_APPLICATION` is set correctly

#### 4. Camera Not Working

- Use **localhost** (not 127.0.0.1) for camera access
- Grant camera permissions in browser
- Try Chrome/Firefox (best WebRTC support)
- Check browser console for permission errors

#### 5. Database Errors

```bash
# Reset database
cd backend
del db.sqlite3  # or rm db.sqlite3 on Mac/Linux
python manage.py migrate
```

#### 6. Module Not Found Errors

```bash
# Backend
cd backend
pip install -r requirements.txt

# Frontend
cd frontend
npm install
```

## 🔄 Resetting the Database

If you need to start fresh:

```bash
cd backend

# Delete database
del db.sqlite3  # Windows
rm db.sqlite3   # Mac/Linux

# Delete migration files (keep __init__.py)
# Windows:
del chat\migrations\0*.py
del moderation\migrations\0*.py
del users\migrations\0*.py

# Mac/Linux:
rm chat/migrations/0*.py
rm moderation/migrations/0*.py
rm users/migrations/0*.py

# Recreate database
python manage.py makemigrations
python manage.py migrate
python manage.py createsuperuser
```

## 🚀 Upgrading AI Detection

### Option 1: Transformer Models (More Accurate)

```bash
cd backend
pip install transformers torch

# Update moderation/ai_detector.py
# Change: detector = ToxicityDetector(method='transformer')
```

### Option 2: Google Perspective API

1. Get API key from [Perspective API](https://developers.perspectiveapi.com/)
2. Add to `.env`: `PERSPECTIVE_API_KEY=your_key_here`
3. Update code to use `method='api'`

### Option 3: OpenAI Moderation API

1. Get API key from [OpenAI](https://platform.openai.com/)
2. Install: `pip install openai`
3. Configure in `ai_detector.py`

## 📁 Project Structure

```
safechat-platform/
├── backend/                    # Django backend
│   ├── safechat/              # Main project settings
│   │   ├── settings.py        # Django settings
│   │   ├── urls.py            # URL routing
│   │   ├── asgi.py            # ASGI config for WebSockets
│   │   └── wsgi.py            # WSGI config
│   ├── chat/                  # Chat app
│   │   ├── models.py          # Message & Stream models
│   │   ├── views.py           # REST API views
│   │   ├── serializers.py     # JSON serializers
│   │   ├── consumers.py       # WebSocket consumers
│   │   ├── routing.py         # WebSocket routing
│   │   └── urls.py            # Chat URLs
│   ├── moderation/            # Moderation app
│   │   ├── models.py          # Warning & Restriction models
│   │   ├── views.py           # Moderation API
│   │   ├── ai_detector.py     # AI toxicity detection
│   │   └── urls.py            # Moderation URLs
│   ├── users/                 # User management
│   │   ├── models.py          # Custom User model
│   │   ├── views.py           # Auth views
│   │   └── urls.py            # User URLs
│   ├── manage.py              # Django CLI
│   ├── requirements.txt       # Python dependencies
│   └── db.sqlite3             # Database (auto-generated)
├── frontend/                  # React frontend
│   ├── src/
│   │   ├── App.jsx            # Main application
│   │   ├── main.jsx           # Entry point
│   │   └── index.css          # Tailwind CSS
│   ├── public/                # Static assets
│   ├── package.json           # Node dependencies
│   └── vite.config.js         # Vite configuration
└── README.md                  # This file
```

## 🔌 API Endpoints

### Authentication
- `POST /api/auth/register/` - Register new user
- `POST /api/auth/login/` - User login
- `POST /api/auth/logout/` - User logout
- `GET /api/auth/me/` - Get current user

### Chat
- `GET /api/chat/messages/` - List messages
- `POST /api/chat/messages/` - Send message
- `GET /api/chat/streams/` - List active streams
- `POST /api/chat/streams/start/` - Start streaming
- `POST /api/chat/streams/<id>/end/` - End streaming

### Moderation
- `POST /api/moderation/check/` - Check text toxicity
- `GET /api/moderation/warnings/` - List warnings
- `GET /api/moderation/warnings/user/<id>/` - User warnings
- `POST /api/moderation/restrict/` - Restrict user
- `GET /api/moderation/restrictions/` - List restrictions

### WebSocket Endpoints
- `ws://localhost:8000/ws/chat/` - Global chat
- `ws://localhost:8000/ws/chat/<stream_id>/` - Stream chat
- `ws://localhost:8000/ws/streams/` - Stream updates

## 🤝 Contributing

Contributions are welcome! Please follow these steps:

1. Fork the repository
2. Create a new branch: `git checkout -b feature/your-feature`
3. Make your changes
4. Commit: `git commit -m 'Add some feature'`
5. Push: `git push origin feature/your-feature`
6. Submit a pull request

### Development Guidelines

- Follow PEP 8 for Python code
- Use ESLint for JavaScript/React code
- Write clear commit messages
- Add tests for new features
- Update documentation

## 📝 To-Do / Future Features

- [ ] User profiles with avatars
- [ ] Private messaging
- [ ] Group chat rooms
- [ ] Stream recording and playback
- [ ] Emoji reactions
- [ ] File/image sharing
- [ ] Mobile app (React Native)
- [ ] Advanced analytics dashboard
- [ ] Multi-language support
- [ ] OAuth integration (Google, GitHub)

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- Django Channels team for WebSocket support
- React team for the amazing framework
- Hugging Face for AI models
- All contributors who help improve this project

## 📞 Support

Having issues? Here's how to get help:

1. **Check Issues**: Look for similar issues on GitHub
2. **Documentation**: Read this README carefully
3. **Create Issue**: Open a new issue with detailed information
4. **Contact**: Reach out via [priyanshijuyal2024@gmail.com]

---

**Made with ❤️ by [KaliedosCode]**

Star ⭐ this repository if you found it helpful!