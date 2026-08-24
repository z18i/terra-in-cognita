# Deployment

## Overview

The website is a static HTML website hosted on a Linode server.

The source repository is hosted on GitHub.

Deployment follows this process:

    Developer
        ↓
    git push
        ↓
    GitHub Actions
        ↓
    Generate index.html
        ↓
    GitHub repository
        ↓
    SSH to Linode
        ↓
    git pull
        ↓
    Nginx
        ↓
    Website

## Server

The website is deployed to:

    /var/www/html/project/terra-in-cognita/

The deployment user is:

    giter

The application does not require root privileges.

## Deployment trigger

The GitHub Actions workflow runs when a commit is pushed to:

    main
