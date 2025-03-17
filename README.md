# ReplyRocket.io - AI-Powered Cold Email Automation SaaS

ReplyRocket is a powerful AI-driven cold email automation platform that helps businesses generate personalized cold emails, send them automatically, and follow up intelligently to maximize response rates.

## Features

- **AI-Powered Email Generation**: Leverage GPT-4 to create highly personalized cold emails based on recipient details and industry context.
- **Automated Follow-ups**: Automatically generate and send follow-up emails when recipients don't respond.
- **Email Tracking**: Monitor open rates, reply rates, and conversion rates for all your campaigns.
- **A/B Testing**: Test different email variations to see which performs best.
- **Campaign Management**: Organize your outreach into campaigns with specific targeting and messaging.
- **Multi-tenant Architecture**: Built as a SaaS platform that supports multiple businesses.

## Tech Stack

- **Backend**: FastAPI (Python)
- **Database**: PostgreSQL with SQLAlchemy ORM
- **Authentication**: JWT-based authentication
- **AI Integration**: OpenAI GPT-4 API
- **Email Sending**: SMTP integration with tracking capabilities
- **Payments**: Stripe integration for subscription management

## API Endpoints

### Authentication

- `POST /api/v1/auth/register`: Register a new user
- `POST /api/v1/auth/login/access-token`: Get JWT access token

### Email Generation & Sending

- `POST /api/v1/emails/generate`: Generate a personalized cold email using AI
- `POST /api/v1/emails/send`: Send an email to a recipient
- `GET /api/v1/emails/{email_id}`: Get metrics for a specific email
- `GET /api/v1/emails/campaign/{campaign_id}`: Get all emails for a campaign

### Follow-ups

- `POST /api/v1/follow-ups/generate`: Generate a follow-up email
- `POST /api/v1/follow-ups/send`: Send a follow-up email
- `POST /api/v1/follow-ups/schedule`: Schedule follow-ups for all campaigns (admin only)

### Campaigns

- `POST /api/v1/campaigns`: Create a new campaign
- `GET /api/v1/campaigns`: Get all campaigns for the current user
- `GET /api/v1/campaigns/{campaign_id}`: Get a specific campaign
- `PUT /api/v1/campaigns/{campaign_id}`: Update a campaign
- `DELETE /api/v1/campaigns/{campaign_id}`: Delete a campaign
- `POST /api/v1/campaigns/ab-test`: Configure A/B testing for a campaign

### Statistics

- `GET /api/v1/stats/campaign/{campaign_id}`: Get statistics for a specific campaign
- `GET /api/v1/stats/user`: Get statistics for all campaigns of the current user

### User Management

- `GET /api/v1/users/me`: Get current user
- `PUT /api/v1/users/me`: Update current user
- `POST /api/v1/users/smtp-config`: Update SMTP configuration

## Getting Started

### Prerequisites

- Python 3.8+
- PostgreSQL
- OpenAI API key
- SMTP server access

### Installation

1. Clone the repository:
   ```
   git clone https://github.com/yourusername/replyrocket.git
   cd replyrocket
   ```

2. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

3. Create a `.env` file with the following variables:
   ```
   # Database
   POSTGRES_SERVER=localhost
   POSTGRES_USER=postgres
   POSTGRES_PASSWORD=password
   POSTGRES_DB=replyrocket

   # Security
   SECRET_KEY=your-secret-key

   # CORS
   BACKEND_CORS_ORIGINS=["http://localhost:3000"]

   # OpenAI
   OPENAI_API_KEY=your-openai-api-key

   # Stripe
   STRIPE_API_KEY=your-stripe-api-key
   STRIPE_WEBHOOK_SECRET=your-stripe-webhook-secret
   ```

4. Initialize the database:
   ```
   alembic upgrade head
   ```

5. Run the application:
   ```
   uvicorn main:app --reload
   ```

## Deployment

The application is designed to be deployed on serverless platforms like AWS Lambda or Google Cloud Run. For production deployment, consider:

1. Setting up a production PostgreSQL database
2. Configuring proper CORS settings
3. Setting up a proper email service
4. Implementing rate limiting
5. Setting up monitoring and logging

## License

This project is licensed under the MIT License - see the LICENSE file for details. 