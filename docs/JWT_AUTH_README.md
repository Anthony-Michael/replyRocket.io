# JWT Refresh Token Authentication in ReplyRocket.io

This document explains how to use the JWT refresh token authentication mechanism in ReplyRocket.io.

## Overview

ReplyRocket.io uses a secure JWT (JSON Web Token) authentication system with refresh tokens. This approach enhances security by:

1. Using short-lived access tokens for API authentication
2. Using long-lived refresh tokens to obtain new access tokens without re-authentication
3. Storing refresh tokens in HttpOnly cookies to prevent JavaScript access
4. Storing refresh tokens in the database to enable revocation

## Authentication Flow

1. **Login**: User provides credentials and receives an access token and a refresh token
2. **API Requests**: Access token is used to authenticate API requests
3. **Token Expiration**: When the access token expires, the refresh token is used to get a new access token
4. **Logout**: Refresh token is revoked, preventing new access tokens from being issued

## API Endpoints

### Login

```
POST /api/v1/auth/login
```

**Request:**
```json
{
  "username": "user@example.com",
  "password": "password123"
}
```

**Response:**
```json
{
  "message": "Authentication successful",
  "expires_at": "2023-06-30T12:00:00Z",
  "user_id": "123e4567-e89b-12d3-a456-426614174000"
}
```

The response includes:
- `message`: Success message
- `expires_at`: Expiration time of the access token
- `user_id`: ID of the authenticated user

The tokens are set in cookies:
- `access_token`: Short-lived token (default: 30 minutes)
- `refresh_token`: Long-lived token (default: 7 days)

### Refresh Token

```
POST /api/v1/auth/refresh-token
```

**Request:**
No body needed if the refresh token is in cookies.

Alternatively, you can provide the refresh token in the request body:
```json
{
  "refresh_token": "your.refresh.token"
}
```

**Response:**
```json
{
  "access_token": "new.access.token",
  "token_type": "bearer",
  "expires_at": "2023-06-30T12:30:00Z"
}
```

The response includes:
- `access_token`: New access token
- `token_type`: Token type (always "bearer")
- `expires_at`: Expiration time of the new access token

The cookies are also updated with the new tokens.

### Logout

```
POST /api/v1/auth/logout
```

**Request:**
No body needed.

**Response:**
```json
{
  "message": "Successfully logged out"
}
```

This endpoint revokes the current refresh token and clears the authentication cookies.

### Logout All Sessions

```
POST /api/v1/auth/logout-all
```

**Request:**
No body needed.

**Response:**
```json
{
  "message": "Successfully logged out all sessions (5)"
}
```

This endpoint revokes all refresh tokens for the current user and clears the authentication cookies.

## Using Tokens in API Requests

### Option 1: Cookie-Based Authentication (Recommended for Web Apps)

For web applications, the tokens are automatically included in cookies, so no additional configuration is needed.

### Option 2: Bearer Authentication (Recommended for API Clients)

For API clients, include the access token in the Authorization header:

```
Authorization: Bearer your.access.token
```

## Security Considerations

1. **Access Token Expiration**: Access tokens expire quickly (default: 30 minutes) to limit the damage if they are stolen.
2. **Refresh Token Storage**: Refresh tokens are stored in HttpOnly cookies, which cannot be accessed by JavaScript.
3. **CSRF Protection**: Cookies are set with SameSite=Strict to prevent CSRF attacks.
4. **Secure Cookies**: In production, cookies are set with the Secure flag to ensure they are only sent over HTTPS.
5. **Token Revocation**: Refresh tokens can be revoked, making them invalid immediately.

## Configuration

JWT authentication can be configured in `.env`:

```
SECRET_KEY=your-secret-key
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7
SECURE_COOKIES=True
```

## Running the Migration

To add the refresh token table to the database, run:

```bash
python migrations/add_refresh_tokens_table.py [database_url]
```

If the database URL is not provided, it will use the default URL:
```
postgresql://postgres:password@localhost/replyrocket
``` 