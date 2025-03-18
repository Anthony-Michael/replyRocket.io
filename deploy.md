# ReplyRocket.io Deployment Guide

This guide explains how to securely deploy ReplyRocket.io to different cloud environments.

## Table of Contents

1. [Pre-Deployment Checklist](#pre-deployment-checklist)
2. [Environment Configuration](#environment-configuration)
3. [Docker Deployment](#docker-deployment)
4. [Deployment Options](#deployment-options)
   - [AWS Deployment](#aws-deployment)
   - [Google Cloud Platform](#google-cloud-platform)
   - [Azure](#azure)
   - [Heroku](#heroku)
5. [Database Configuration](#database-configuration)
6. [Security Best Practices](#security-best-practices)
7. [Monitoring and Logging](#monitoring-and-logging)
8. [CI/CD Setup](#cicd-setup)

## Pre-Deployment Checklist

Before deploying to any environment, ensure you have completed these steps:

- [ ] Run the full test suite and ensure all tests pass
- [ ] Set `DEBUG=False` for staging and production environments
- [ ] Generate a strong `SECRET_KEY` for production
- [ ] Configure proper database credentials for the target environment
- [ ] Configure CORS settings to restrict access to trusted domains
- [ ] Set up proper logging for the target environment
- [ ] Ensure all required environment variables are documented in `.env.example`
- [ ] Configure SSL/TLS certificates for secure connections

## Environment Configuration

ReplyRocket.io uses environment-specific configurations for development, staging, and production. 

### Create Environment Variables

1. Copy `.env.example` to a new file for your target environment:

```bash
cp .env.example .env.production
```

2. Fill in all required environment variables for your target environment:

```
# Environment setting
ENVIRONMENT=production

# Security (use strong, unique values)
SECRET_KEY=your-generated-secret-key
SECURE_COOKIES=True

# Database credentials
POSTGRES_SERVER=your-db-host
POSTGRES_USER=your-db-user
POSTGRES_PASSWORD=your-secure-password
POSTGRES_DB=replyrocket

# API keys
OPENAI_API_KEY=your-openai-api-key

# Other configuration...
```

3. Generate a strong secret key:

```bash
# Option 1: Using Python
python -c "import secrets; print(secrets.token_hex(32))"

# Option 2: Using OpenSSL
openssl rand -hex 32
```

## Docker Deployment

For production deployments, we recommend using Docker with Docker Compose.

### Docker Compose for Production

The `docker-compose.prod.yml` file is configured for production deployment. Here's how to use it:

1. Ensure your environment variables are properly set (either in `.env.production` or through your cloud provider's secrets management)

2. Build and start the containers:

```bash
docker-compose -f docker-compose.prod.yml up -d
```

3. Run initial database migrations:

```bash
docker-compose -f docker-compose.prod.yml exec app alembic upgrade head
```

### Docker Security Best Practices

- Use specific version tags for base images, not `latest`
- Scan Docker images for vulnerabilities before deployment
- Use multi-stage builds to minimize image size
- Run containers with non-root users
- Use read-only file systems where possible
- Set resource limits on containers
- Keep the Docker daemon and client updated

## Deployment Options

### AWS Deployment

#### ECS (Elastic Container Service)

1. **Create an ECR Repository for your images**

```bash
aws ecr create-repository --repository-name replyrocket-api
```

2. **Build and push your Docker image**

```bash
# Login to ECR
aws ecr get-login-password --region <region> | docker login --username AWS --password-stdin <account-id>.dkr.ecr.<region>.amazonaws.com

# Build and tag the image
docker build -t <account-id>.dkr.ecr.<region>.amazonaws.com/replyrocket-api:latest .

# Push the image
docker push <account-id>.dkr.ecr.<region>.amazonaws.com/replyrocket-api:latest
```

3. **Create an ECS cluster, task definition, and service**

Use AWS CloudFormation or the AWS console to set up:
- A VPC with public and private subnets
- An ECS cluster
- A task definition that references your ECR image
- A service to run your task with the desired number of instances
- Application Load Balancer for routing traffic

4. **Set environment variables securely with AWS Parameter Store or Secrets Manager**

```bash
# Store a secret in Parameter Store
aws ssm put-parameter --name /replyrocket/prod/SECRET_KEY --value "your-secret-key" --type SecureString

# Reference in your task definition
{
  "name": "SECRET_KEY",
  "valueFrom": "arn:aws:ssm:<region>:<account-id>:parameter/replyrocket/prod/SECRET_KEY"
}
```

#### RDS for Database

1. Create a PostgreSQL RDS instance in a private subnet
2. Configure security groups to allow connections only from your application
3. Use AWS Secrets Manager to store database credentials

### Google Cloud Platform

#### Google Kubernetes Engine (GKE)

1. **Create a GKE cluster**

```bash
gcloud container clusters create replyrocket-cluster \
  --num-nodes=3 \
  --machine-type=e2-standard-2 \
  --region=us-central1
```

2. **Build and push to Google Container Registry**

```bash
# Build the image
docker build -t gcr.io/[PROJECT_ID]/replyrocket-api:latest .

# Push to GCR
docker push gcr.io/[PROJECT_ID]/replyrocket-api:latest
```

3. **Store secrets in Secret Manager**

```bash
# Create a secret
gcloud secrets create SECRET_KEY --data-file=/path/to/secret.txt

# Grant access to the service account
gcloud secrets add-iam-policy-binding SECRET_KEY \
  --member=serviceAccount:SERVICE_ACCOUNT_EMAIL \
  --role=roles/secretmanager.secretAccessor
```

4. **Deploy using Kubernetes manifests or Helm charts**

Create Kubernetes deployment, service, and ingress resources to deploy your application.

### Azure

#### Azure Container Instances or Azure Kubernetes Service

1. **Create an Azure Container Registry**

```bash
az acr create --resource-group myResourceGroup --name myRegistry --sku Basic
```

2. **Build and push your image**

```bash
# Login to ACR
az acr login --name myRegistry

# Build and push
az acr build --registry myRegistry --image replyrocket-api:latest .
```

3. **Create container instance or AKS cluster**

```bash
# For simple container instance
az container create \
  --resource-group myResourceGroup \
  --name replyrocket-container \
  --image myRegistry.azurecr.io/replyrocket-api:latest \
  --dns-name-label replyrocket \
  --ports 80 \
  --environment-variables SECRET_KEY=<secret-key> ...
```

4. **Use Azure Key Vault for secrets**

```bash
# Create a key vault
az keyvault create --name myKeyVault --resource-group myResourceGroup

# Add a secret
az keyvault secret set --vault-name myKeyVault --name SECRET-KEY --value <secret-key>
```

### Heroku

1. **Login to Heroku and create an app**

```bash
heroku login
heroku create replyrocket-api
```

2. **Set environment variables**

```bash
heroku config:set ENVIRONMENT=production
heroku config:set SECRET_KEY=<your-secret-key>
heroku config:set POSTGRES_SERVER=<db-server>
# Set other required environment variables
```

3. **Push to Heroku**

```bash
# Option 1: Using Git
git push heroku main

# Option 2: Using Docker
heroku container:push web
heroku container:release web
```

4. **Provision a PostgreSQL database**

```bash
heroku addons:create heroku-postgresql:hobby-dev
```

## Database Configuration

### Production Database Setup

1. **Create a dedicated database user with limited permissions**

```sql
CREATE USER replyrocket_app WITH PASSWORD 'secure-password';
GRANT CONNECT ON DATABASE replyrocket TO replyrocket_app;
GRANT USAGE ON SCHEMA public TO replyrocket_app;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO replyrocket_app;
GRANT USAGE ON ALL SEQUENCES IN SCHEMA public TO replyrocket_app;
```

2. **Configure connection pooling**

Adjust the database pool settings in `.env.production`:

```
DB_POOL_SIZE=10
DB_MAX_OVERFLOW=20
DB_POOL_TIMEOUT=30
DB_POOL_RECYCLE=1800
```

3. **Database backups**

Set up automated backups for your production database. Most cloud providers offer built-in backup solutions.

### Database Migrations

Run migrations during deployment:

```bash
alembic upgrade head
```

## Security Best Practices

### API Security

1. **Rate Limiting**

Implement rate limiting for API endpoints to prevent abuse.

2. **API Tokens**

Use short-lived tokens and secure token refresh mechanisms.

3. **Input Validation**

Ensure all user inputs are properly validated and sanitized.

### Infrastructure Security

1. **Firewalls**

Configure firewalls to restrict traffic to necessary ports and services.

2. **Network Isolation**

Place application components in isolated network segments (VPCs, subnets).

3. **Regular Security Scans**

Perform regular vulnerability scans and penetration testing.

### Secrets Management

1. **Never commit sensitive data to version control**
2. **Use environment variables or cloud provider secrets services**
3. **Rotate secrets regularly**
4. **Use principle of least privilege for service accounts**

## Monitoring and Logging

### Logging Configuration

Configure appropriate logging for production:

```
LOG_LEVEL=INFO
LOG_FORMAT=json
```

### Monitoring Services

Set up monitoring using:
- AWS CloudWatch
- Google Cloud Monitoring
- Azure Monitor
- Third-party services like Datadog, New Relic, or Sentry

Monitor:
- Application performance
- Error rates
- Database performance
- System resources (CPU, memory, disk)
- API response times

## CI/CD Setup

### GitHub Actions Example

Create a `.github/workflows/deploy.yml` file:

```yaml
name: Deploy to Production

on:
  push:
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
          pip install -r requirements.txt
      - name: Run tests
        run: |
          pytest
  
  deploy:
    needs: test
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Build and push Docker image
        uses: docker/build-push-action@v4
        with:
          context: .
          push: true
          tags: your-registry/replyrocket:latest
      - name: Deploy to production
        run: |
          # Deploy commands specific to your cloud provider
```

### Continuous Deployment Best Practices

1. **Environment Promotion**
   - Deploy to development → staging → production
   - Test thoroughly at each stage

2. **Rollback Plan**
   - Have a clear process for rolling back failed deployments
   - Test rollback procedures regularly

3. **Feature Flags**
   - Use feature flags to gradually roll out changes
   - Disable problematic features without full rollback 