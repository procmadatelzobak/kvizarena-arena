# Kvizarena

Initial project scaffolding for the Kvizarena application. The stack is centred around a Flask
application with SQLAlchemy for persistence. The repository is structured to encourage modular
blueprints, dedicated static and template directories, and an extensible testing setup.

## Project structure

```
.
├── app
│   ├── __init__.py
│   ├── app.py
│   ├── blueprints
│   │   └── __init__.py
│   ├── database.py
│   ├── static
│   └── templates
├── requirements.txt
├── tests
│   ├── __init__.py
│   └── test_app.py
├── .env.example
├── .gitignore
└── README.md
```

## Getting started

1. **Create and activate a virtual environment:**
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   ```
2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```
3. **Set environment variables:**
   Copy `.env.example` to `.env` and adjust the values as needed.

4. **Run the development server:**
   ```bash
   flask --app app.app run --debug
   ```

5. **Execute the test suite:**
   ```bash
   pytest
   ```

## Branching workflow

The repository follows a four-branch workflow:

- `server` and `client` branches branch off from `dev`.
- Changes from `server` or `client` merge into `dev`.
- The `master` branch stays stable and only receives code promoted from `dev`.

Ensure documentation updates accompany each change to keep the workflow transparent.
