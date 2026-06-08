# QuickNotes: A Secure Web-Based Notes and File Management Application

[![Flask](https://img.shields.io/badge/Flask-2.3.3-blue.svg)](https://flask.palletsprojects.com/)
[![MySQL](https://img.shields.io/badge/MySQL-8.0-orange.svg)](https://www.mysql.com/)
[![Python](https://img.shields.io/badge/Python-3.8+-green.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

A robust, secure, and scalable web application for personal note-taking and file management, built with Flask and MySQL. Features comprehensive user authentication, OTP verification, and encrypted data handling.

## 🚀 Live Demo

**Production Deployment:** [http://98.80.74.218/](http://98.80.74.218/)

*Hosted on AWS EC2 with automated CI/CD pipeline.*

## 📋 Table of Contents

- [Features](#features)
- [Tech Stack](#tech-stack)
- [Architecture](#architecture)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Configuration](#configuration)
- [Usage](#usage)
- [API Endpoints](#api-endpoints)
- [Database Schema](#database-schema)
- [Deployment](#deployment)
- [Testing](#testing)
- [Contributing](#contributing)
- [Security](#security)
- [License](#license)
- [Acknowledgments](#acknowledgments)

## ✨ Features

### 🔐 Authentication & Security
- **User Registration & Login** with email verification
- **OTP-based Email Verification** for account activation
- **Password Reset** via secure email links
- **Session Management** with Flask-Session (filesystem-based)
- **Password Hashing** using bcrypt
- **Token Encryption** for sensitive data

### 📝 Notes Management
- **CRUD Operations**: Create, Read, Update, Delete notes
- **Rich Text Support** with HTML rendering
- **Search Functionality** across all notes
- **Bulk Operations**: Delete all notes at once
- **Download Notes** as text files

### 📁 File Management
- **File Upload** with size and type validation
- **File Viewing** and editing capabilities
- **File Download** functionality
- **Search Files** by name or content
- **Bulk File Deletion**
- **Secure File Storage** with access controls

### 👤 User Profile
- **Profile Management**: Update username and email
- **Password Change** with current password verification
- **Account Deletion** with confirmation
- **Dashboard Overview** of notes and files count

### 🎨 User Experience
- **Responsive Design** with Bootstrap/CSS
- **Flash Messages** for user feedback
- **Intuitive Navigation** with Jinja2 templates
- **Error Handling** with custom error pages

## 🛠 Tech Stack

### Backend
- **Framework**: Flask 2.3.3
- **Database**: MySQL 8.0
- **Authentication**: bcrypt, itsdangerous
- **Session Management**: Flask-Session
- **Email**: Custom SMTP integration
- **File Handling**: Werkzeug, flask-excel

### Frontend
- **Templates**: Jinja2
- **Styling**: CSS3, Bootstrap
- **JavaScript**: Vanilla JS for interactivity

### Infrastructure
- **Deployment**: AWS EC2
- **Web Server**: Gunicorn (recommended for production)
- **Database**: MySQL on AWS RDS (recommended)

## 🏗 Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Web Browser   │────│   Flask App     │────│     MySQL DB    │
│                 │    │  (app.py)       │    │                 │
│ - HTML/CSS/JS   │    │                 │    │ - users         │
│ - Templates     │    │ - Routes        │    │ - notes         │
└─────────────────┘    │ - Business Logic│    │ - files         │
                       │ - Email Service │    └─────────────────┘
                       │ - OTP Service   │
                       └─────────────────┘
                                │
                                ▼
                       ┌─────────────────┐
                       │   File System   │
                       │                 │
                       │ - Session Files │
                       │ - Uploaded Files│
                       └─────────────────┘
```

### Key Components:
- **app.py**: Main application with all routes and business logic
- **cmail.py**: Email service for OTP and password reset
- **otp.py**: OTP generation and validation
- **secret_token.py**: Token encryption/decryption utilities
- **secretkeys.py**: Configuration for sensitive keys

## 📋 Prerequisites

- **Python**: 3.8 or higher
- **MySQL**: 8.0 or higher
- **Git**: For version control
- **Virtual Environment**: venv or virtualenv

## 🚀 Installation

### 1. Clone the Repository
```bash
git clone https://github.com/your-username/quicknotes.git
cd quicknotes
```

### 2. Create Virtual Environment
```bash
# Windows
python -m venv quicknotes
quicknotes\Scripts\activate

# Linux/Mac
python3 -m venv quicknotes
source quicknotes/bin/activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Database Setup
```sql
-- Create database
CREATE DATABASE quicknotes;
USE quicknotes;

-- Create users table
CREATE TABLE users (
    user_email VARCHAR(50) NOT NULL,
    user_name VARCHAR(30) NOT NULL,
    password VARBINARY(255) DEFAULT NULL,
    PRIMARY KEY (user_email),
    UNIQUE KEY user_name (user_name)
);

-- Create notes table
CREATE TABLE notes (
    n_id INT UNSIGNED NOT NULL AUTO_INCREMENT,
    n_title VARCHAR(50) NOT NULL,
    n_description LONGTEXT NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    user_email VARCHAR(50) DEFAULT NULL,
    PRIMARY KEY (n_id),
    CONSTRAINT fk_notes_users FOREIGN KEY (user_email) REFERENCES users (user_email) ON DELETE CASCADE
);

-- Create files table
CREATE TABLE files (
    f_id INT UNSIGNED NOT NULL AUTO_INCREMENT,
    f_title VARCHAR(50) DEFAULT NULL,
    f_description LONGTEXT DEFAULT NULL,
    file_name VARCHAR(50) DEFAULT NULL,
    file_data LONGBLOB DEFAULT NULL,
    created_at DATETIME DEFAULT NULL,
    user_email VARCHAR(50) DEFAULT NULL,
    PRIMARY KEY (f_id),
    UNIQUE KEY unique_file_user (user_email, file_name),
    CONSTRAINT fk_files_users FOREIGN KEY (user_email) REFERENCES users (user_email) ON DELETE CASCADE
);
```

## ⚙️ Configuration

### Environment Variables
Create a `.env` file in the root directory:

```env
# Database Configuration
DB_HOST=localhost
DB_USER=your_db_user
DB_PASSWORD=your_db_password
DB_NAME=quicknotes

# Flask Configuration
SECRET_KEY=your_super_secret_key_here
SESSION_TYPE=filesystem

# Email Configuration
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your_email@gmail.com
SMTP_PASSWORD=your_app_password

# Security
TOKEN_EXPIRY=3600  # 1 hour
OTP_EXPIRY=300     # 5 minutes
```

### Email Setup
For email functionality, configure SMTP settings in `cmail.py` or use environment variables.

## 🎯 Usage

### Running the Application
```bash
# Development
python app.py

# Production (recommended)
gunicorn --bind 0.0.0.0:8000 app:app
```

### Accessing the Application
- **Local Development**: http://localhost:5000
- **Production**: http://98.80.74.218/

### User Workflow
1. **Register** with email and password
2. **Verify** account via OTP sent to email
3. **Login** to access dashboard
4. **Create Notes** and upload files
5. **Manage** content through intuitive interface
6. **Search** and organize notes/files
7. **Update Profile** or change password as needed

## 🔗 API Endpoints

| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| GET | `/` | Home page | No |
| GET/POST | `/register` | User registration | No |
| GET/POST | `/login` | User login | No |
| GET/POST | `/otp` | OTP verification | No |
| GET/POST | `/forgotpassword` | Password reset request | No |
| GET/POST | `/resetpassword/<token>` | Password reset | No |
| GET | `/dashboard` | User dashboard | Yes |
| GET/POST | `/addnote` | Add new note | Yes |
| GET/POST | `/addfile` | Upload file | Yes |
| GET | `/viewallnotes` | List all notes | Yes |
| GET | `/viewallfiles` | List all files | Yes |
| GET/POST | `/viewnote/<id>` | View/edit note | Yes |
| GET/POST | `/viewfile/<id>` | View file | Yes |
| GET | `/download/note/<id>` | Download note | Yes |
| GET | `/download/file/<id>` | Download file | Yes |
| GET/POST | `/profile` | User profile | Yes |
| POST | `/deleteallnotes` | Delete all notes | Yes |
| POST | `/deleteallfiles` | Delete all files | Yes |
| POST | `/deleteaccount` | Delete account | Yes |
| GET | `/logout` | Logout | Yes |

## 🗄️ Database Schema

### Users Table
```sql
+------------+--------------+------+-----+---------+-------+
| Field      | Type         | Null | Key | Default | Extra |
+------------+--------------+------+-----+---------+-------+
| user_email | varchar(50)  | NO   | PRI | NULL    |       |
| user_name  | varchar(30)  | NO   | UNI | NULL    |       |
| password   | varbinary(255)| YES |     | NULL    |       |
+------------+--------------+------+-----+---------+-------+
```

### Notes Table
```sql
+---------------+--------------+------+-----+-------------------+-------------------+
| Field         | Type         | Null | Key | Default           | Extra             |
+---------------+--------------+------+-----+-------------------+-------------------+
| n_id          | int unsigned | NO   | PRI | NULL              | auto_increment    |
| n_title       | varchar(50)  | NO   |     | NULL              |                   |
| n_description | longtext     | NO   |     | NULL              |                   |
| created_at    | datetime     | YES  |     | CURRENT_TIMESTAMP | DEFAULT_GENERATED |
| user_email    | varchar(50)  | YES  | MUL | NULL              |                   |
+---------------+--------------+------+-----+-------------------+-------------------+
```

### Files Table
```sql
+---------------+--------------+------+-----+---------+----------------+
| Field         | Type         | Null | Key | Default | Extra          |
+---------------+--------------+------+-----+---------+----------------+
| f_id          | int unsigned | NO   | PRI | NULL    | auto_increment |
| f_title       | varchar(50)  | YES  |     | NULL    |                |
| f_description | longtext     | YES  |     | NULL    |                |
| file_name     | varchar(50)  | YES  | MUL | NULL    |                |
| file_data     | longblob     | YES  |     | NULL    |                |
| created_at    | datetime     | YES  |     | NULL    |                |
| user_email    | varchar(50)  | YES  | MUL | NULL    |                |
+---------------+--------------+------+-----+---------+----------------+
```

## 🚀 Deployment

### AWS EC2 Deployment
1. **Launch EC2 Instance**
   - Ubuntu 20.04/22.04 LTS recommended.
   - Configure Security Groups: Allow HTTP (80), HTTPS (443), and SSH (22).

2. **Install Dependencies**
   ```bash
   sudo apt update
   sudo apt install python3 python3-pip python3-venv mysql-server nginx -y
   ```

3. **Deploy Application**
   ```bash
   # Clone repo
   git clone https://github.com/your-username/quicknotes.git /home/ubuntu/quicknotes
   cd /home/ubuntu/quicknotes

   # Setup virtual environment
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

4. **Configure Environment Variables**
   Create a `.env` file in the project root containing your database credentials and secret key.

5. **Configure systemd Service**
   Create a service configuration file at `/etc/systemd/system/quicknotes.service`:
   ```ini
   [Unit]
   Description=Gunicorn instance to serve QuickNotes Flask app
   After=network.target

   [Service]
   User=ubuntu
   Group=www-data
   WorkingDirectory=/home/ubuntu/quicknotes
   Environment="PATH=/home/ubuntu/quicknotes/venv/bin"
   ExecStart=/home/ubuntu/quicknotes/venv/bin/gunicorn --workers 3 --bind unix:/home/ubuntu/quicknotes/quicknotes.sock app:app

   [Install]
   WantedBy=multi-user.target
   ```
   Start and enable Gunicorn to run in the background on boot:
   ```bash
   sudo systemctl start quicknotes.service
   sudo systemctl enable quicknotes.service
   ```

6. **Configure Nginx as a Reverse Proxy**
   Create a configuration file at `/etc/nginx/sites-available/quicknotes`:
   ```nginx
   server {
       listen 80;
       server_name 98.80.74.218;

       location / {
           include proxy_params;
           proxy_pass http://unix:/home/ubuntu/quicknotes/quicknotes.sock;
       }
   }
   ```
   Enable the configuration and restart Nginx:
   ```bash
   sudo ln -s /etc/nginx/sites-available/quicknotes /etc/nginx/sites-enabled/
   sudo nginx -t
   sudo systemctl restart nginx
   ```

### Docker Deployment (Alternative)
```dockerfile
FROM python:3.9-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
EXPOSE 5000

CMD ["python", "app.py"]
```

## 🧪 Testing

### Unit Tests
```bash
# Install testing dependencies
pip install pytest flask-testing

# Run tests
pytest
```

### Manual Testing Checklist
- [ ] User registration with valid/invalid data
- [ ] OTP verification process
- [ ] Login/logout functionality
- [ ] Note CRUD operations
- [ ] File upload/download
- [ ] Search functionality
- [ ] Password reset flow
- [ ] Profile updates
- [ ] Account deletion

### Performance Testing
```bash
# Load testing with locust
pip install locust
locust -f locustfile.py
```

## 🤝 Contributing

1. **Fork** the repository
2. **Create** a feature branch (`git checkout -b feature/AmazingFeature`)
3. **Commit** your changes (`git commit -m 'Add some AmazingFeature'`)
4. **Push** to the branch (`git push origin feature/AmazingFeature`)
5. **Open** a Pull Request

### Development Guidelines
- Follow PEP 8 style guide
- Write comprehensive docstrings
- Add unit tests for new features
- Update documentation as needed
- Ensure all tests pass before submitting PR

## 🔒 Security

### Implemented Security Measures
- **Password Hashing**: bcrypt with salt
- **Session Security**: Secure session management
- **Input Validation**: Server-side validation for all forms
- **SQL Injection Prevention**: Parameterized queries
- **XSS Protection**: Template escaping with Jinja2
- **CSRF Protection**: Token-based form validation
- **Rate Limiting**: Implemented for sensitive endpoints

### Security Best Practices
- Never commit secrets to version control
- Use environment variables for configuration
- Regularly update dependencies
- Implement HTTPS in production
- Monitor for security vulnerabilities

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- **Flask Framework** for the robust web framework
- **Bootstrap** for responsive UI components
- **MySQL** for reliable database management
- **AWS** for cloud infrastructure
- **Open Source Community** for invaluable tools and libraries

---

## 👩‍💻 About the Author

### **Chintada Vasudharini**
**Python Full Stack Developer | AWS | AI-ML**
📍 *KL University | BTech CSE*

> I am dedicated to building scalable, efficient, and beautifully designed software.

- **GitHub:** [@chintadavasudharini](https://github.com/chintadavasudharini)
- **LinkedIn:** [Chintada Vasudharini](https://www.linkedin.com/in/chintada-vasudharini-nov21/)
- **Email:** [chintadavasudharini@gmail.com](mailto:chintadavasudharini@gmail.com)
- **Personal Portfolio:** [Visit Here](https://portfolio-lime-tau-36.vercel.app/)

---

