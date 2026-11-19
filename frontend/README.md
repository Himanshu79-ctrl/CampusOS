# CampusOS Frontend

The official React + Vite + TypeScript frontend application for CampusOS.

## Tech Stack

- **React 19**
- **Vite 6**
- **TypeScript 5**
- **Tailwind CSS v4** (via `@tailwindcss/vite`)
- **React Router 7**
- **Axios**
- **Lucide React**

## Microservices Environment Variables

CampusOS communicates with three distinct backend services. Configure their endpoints in `.env` or `.env.local`:

```env
# LMS Service (Django REST Framework - Academics, Content, Attendance, Grades, Reports, Notifications)
VITE_LMS_API_URL=http://127.0.0.1:8000

# Auth Service (Django - Authentication, JWT Token Issuance, Users)
VITE_AUTH_API_URL=http://127.0.0.1:8001

# Admin Service (Node.js/Express - Departments, Courses, Faculty Master)
VITE_ADMIN_API_URL=http://127.0.0.1:5000
```

## Getting Started

```bash
# Install dependencies
npm install

# Start local development server
npm run dev

# Type check & build for production
npm run build

# Preview production build
npm run preview
```
