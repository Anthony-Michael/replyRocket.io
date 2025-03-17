# Production Deployment Guide for ReplyRocket.io

This guide provides step-by-step instructions for deploying the ReplyRocket.io FastAPI backend to production using Render.

## Overview

Our production deployment uses:
- **Render** for hosting the FastAPI application
- **Render PostgreSQL** for the database
- **GitHub Actions** for CI/CD
- **Sentry** for error tracking and monitoring

## Prerequisites

1. GitHub repository with your ReplyRocket.io code
2. Render account: [signup at render.com](https://render.com/)
3. Sentry account: [signup at sentry.io](https://sentry.io/)

## Deployment Files

The following files in the `/infrastructure` directory are used for production deployment:

- `Dockerfile` - Container definition for the application
- `docker-compose.prod.yml` - Docker Compose configuration for production
- `Caddyfile` - Caddy server configuration for HTTPS and routing
- `.github/workflows/deploy.yml` - GitHub Actions workflow for CI/CD

## Step 1: Set Up Sentry Project

1. Create a new Sentry project:
   - Go to [sentry.io](https://sentry.io/) and log in
   - Create a new project for Python → FastAPI
   - Get your DSN (you'll need it for environment variables)

## Step 2: Set Up Render Services

### Database Setup

1. Log in to Render Dashboard
2. Go to "New +" → "PostgreSQL"
3. Configure the database:
   - **Name**: `replyrocket-db` (or your preferred name)
   - **Database**: `replyrocket`
   - **User**: (auto-generated)
   - **Region**: Choose closest to your user base
   - **Plan**: Start with the smallest plan for MVP ($7/month)
4. Click "Create Database" and note the connection details

### Web Service Setup

1. Go to "New +" → "Web Service"
2. Connect your GitHub repository
3. Configure the service:
   - **Name**: `replyrocket-api`
   - **Environment**: Docker
   - **Region**: Same as your database
   - **Branch**: `main`
   - **Plan**: Starter ($7/month) is sufficient for MVP
   
4. Add Environment Variables:
   - `DATABASE_URL`: The internal Render connection string (provided by Render)
   - `SECRET_KEY`: Generate with `openssl rand -hex 32`
   - `OPENAI_API_KEY`: Your OpenAI API key
   - `ENVIRONMENT`: `production`
   - `SENTRY_DSN`: Your Sentry DSN from Step 1
   - `BACKEND_CORS_ORIGINS`: Your frontend URLs (e.g., `"https://replyrocket.io,https://app.replyrocket.io"`)

5. Click "Create Web Service"

## Step 3: Set Up GitHub Actions

1. Create `.github/workflows/deploy.yml` with the following:

```yaml
name: Test and Deploy

on:
  push:
    branches: [ main ]
  pull_request:
    branches: [ main ]

jobs:
  test:
    runs-on: ubuntu-latest
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.10'
        
    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install pytest pytest-cov
        if [ -f requirements.txt ]; then pip install -r requirements.txt; fi
        if [ -f pyproject.toml ]; then pip install poetry && poetry install; fi
        
    - name: Run tests
      run: |
        pytest --cov=app
    
    - name: Upload coverage reports to Codecov
      uses: codecov/codecov-action@v3
      with:
        token: ${{ secrets.CODECOV_TOKEN }}
        fail_ci_if_error: false
        
  deploy:
    needs: test
    if: github.ref == 'refs/heads/main' && github.event_name == 'push'
    runs-on: ubuntu-latest
    
    steps:
    - name: Deploy to Render
      uses: JorgeLNJunior/render-deploy@v1.4.3
      with:
        service_id: ${{ secrets.RENDER_SERVICE_ID }}
        api_key: ${{ secrets.RENDER_API_KEY }}
        wait_deploy: true
        github_token: ${{ secrets.GITHUB_TOKEN }}

    - name: Send deployment notification to Sentry
      uses: getsentry/action-release@v1
      env:
        SENTRY_AUTH_TOKEN: ${{ secrets.SENTRY_AUTH_TOKEN }}
        SENTRY_ORG: ${{ vars.SENTRY_ORG }}
        SENTRY_PROJECT: ${{ vars.SENTRY_PROJECT }}
      with:
        environment: production
        version: ${{ github.sha }}
```

2. Add GitHub Repository Secrets:
   - Go to Repository Settings → Secrets and Variables → Actions
   - Add the following:
     - `RENDER_API_KEY`: Your Render API key from Account Settings
     - `RENDER_SERVICE_ID`: Your service ID (from the URL of your web service)
     - `SENTRY_AUTH_TOKEN`: From Sentry → Account Settings → API → Auth Tokens
     - `CODECOV_TOKEN` (optional): For code coverage reports

3. Add GitHub Repository Variables:
   - `SENTRY_ORG`: Your Sentry organization slug
   - `SENTRY_PROJECT`: Your Sentry project slug

## Step 4: Custom Domain Setup (Optional)

1. In Render Dashboard, go to your web service
2. Navigate to "Settings" → "Custom Domain"
3. Click "Add Custom Domain"
4. Enter your domain (e.g., `api.replyrocket.io`)
5. Follow the instructions to configure your DNS

## Step 5: Verify Deployment

1. Once deployed, verify the health endpoint:
   ```
   curl https://your-render-url.onrender.com/api/v1/health
   ```

2. Check Sentry to ensure events are being captured:
   - Go to your Sentry project
   - Navigate to "Performance" to see application performance
   - Generate a test error to confirm error tracking is working

## Monitoring and Maintenance

### Render Dashboard
- Monitor resource usage, logs, and deployments through the Render dashboard
- Set up spending alerts if needed

### Sentry Monitoring
- Set up alert rules for error thresholds
- Configure team notifications
- Use performance monitoring to identify bottlenecks

### Database Backups
- Render PostgreSQL includes automated daily backups
- You can manually create backups before major changes

## Cost Optimization

For an MVP launch on Render, expect to pay:
- Web Service: $7/month (Starter)
- PostgreSQL: $7/month (Starter)
- **Total: ~$14/month**

You can scale up resources as your user base grows.

## Troubleshooting

### Common Issues

1. **Database Connection Issues**:
   - Verify the `DATABASE_URL` environment variable is correct
   - Check that the database is running and accessible

2. **Application Errors**:
   - Check application logs in the Render dashboard
   - Investigate errors in Sentry

3. **Deployment Failures**:
   - Check GitHub Actions workflow runs
   - Verify Docker build process works locally

For more complex issues, consult Render documentation or Render support. 