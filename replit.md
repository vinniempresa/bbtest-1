# Overview

This is a Flask-based web application that appears to simulate multiple financial and governmental services including:

- Banco do Brasil (Bank of Brazil) contest registration and payment processing
- SIGMA military registration system for hunters, shooters, and collectors
- DPVAT vehicle insurance services

The application implements a payment gateway system using PIX (Brazilian instant payment system) through multiple payment providers (TechByNet and For4Payments), with a comprehensive flow from user data collection to payment processing.

# User Preferences

Preferred communication style: Simple, everyday language.

# System Architecture

## Frontend Architecture
- **Template Engine**: Jinja2 templates with responsive HTML/CSS design
- **Styling Framework**: TailwindCSS for utility-first styling
- **Custom Typography**: Rawline font family with multiple weights (400, 500, 600, 700)
- **Analytics Integration**: Microsoft Clarity for user behavior tracking
- **Interactive Elements**: JavaScript for form validation, state detection, and dynamic content updates

## Backend Architecture
- **Framework**: Flask web framework with SQLAlchemy ORM
- **Session Management**: Flask sessions for maintaining user state across requests
- **Database Integration**: PostgreSQL database configured via DATABASE_URL environment variable
- **API Design**: RESTful endpoints handling user registration, payment processing, and data verification
- **Error Handling**: Comprehensive logging system with structured error messages
- **Environment Configuration**: Environment variable-based configuration for security and deployment flexibility

## Data Storage Solutions
- **Primary Database**: PostgreSQL with SQLAlchemy ORM
- **Connection Pooling**: Configured with pool recycling and pre-ping for reliability
- **Session Storage**: Flask sessions for temporary user data during registration flows

## Authentication and Authorization
- **Session-based Authentication**: Uses Flask sessions with secret key for security
- **Environment-based Security**: Session secret key stored in environment variables
- **No Traditional User Accounts**: Stateless design focused on registration and payment flows

## Payment Processing Architecture
- **Multi-Provider Support**: Integration with both TechByNet and For4Payments APIs
- **PIX Integration**: Brazilian instant payment system implementation
- **Payment Flow**: Customer data collection → validation → payment creation → QR code generation
- **Webhook Support**: Postback URL configuration for payment status notifications
- **Error Handling**: Comprehensive validation and fallback mechanisms

# External Dependencies

## Payment Gateways
- **TechByNet API**: Primary payment processor for PIX transactions via `api-gateway.techbynet.com`
- **For4Payments API**: Alternative payment processor via `app.for4payments.com.br/api/v1`

## Third-party Services
- **Microsoft Clarity**: User analytics and behavior tracking (`clarity.ms`)
- **IPApi.co**: Geolocation service for automatic state detection
- **External CDNs**: 
  - TailwindCSS (`cdn.tailwindcss.com`)
  - Font Awesome icons (`cdnjs.cloudflare.com`)
  - QR Code generation library

## Database
- **PostgreSQL**: Configured via DATABASE_URL environment variable with psycopg2-binary driver

## Python Dependencies
- **Core Framework**: Flask 3.1.0 with SQLAlchemy 2.0.37
- **Email Validation**: email-validator for user input validation
- **HTTP Requests**: requests library for external API communication
- **Web Scraping**: trafilatura for content extraction (though usage not evident in main codebase)
- **Production Server**: Gunicorn for WSGI deployment