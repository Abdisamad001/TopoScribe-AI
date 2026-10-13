# Contributing to TopoScribe-AI

Thank you for contributing to TopoScribe-AI.

## Branching Model

- **`main`**: Production release branch. Protected against direct pushes. Changes merge strictly via Pull Requests.
- **`dev`**: Active development branch. All feature branches and updates target `dev`.

## Setup & Local Development

### Prerequisites
- Python 3.11+
- Node.js 20+
- Git

### Backend Setup
1. Navigate to `backend/`.
2. Create and activate a virtual environment:
   ```bash
   python -m venv venv
   .\venv\Scripts\activate