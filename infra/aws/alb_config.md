# ALB Configuration for Minerva Core
#
# Purpose:
#     Documents the Application Load Balancer configuration for the
#     Core ECS service.
#
# Key Settings:
#     - Sticky sessions: ENABLED (cookie-based, using minerva_token)
#     - Duration: 30 minutes (matches JWT TTL)
#     - Health check: GET /internal/health
#     - Target group: Core ECS tasks (port 8000)
#     - Listener: HTTPS on 443 with SSL certificate
#
# Why Sticky Sessions:
#     Core holds conversation memory in-process on each ECS task.
#     All requests for a given session must route to the same task
#     to maintain continuity. The ALB uses the JWT cookie for affinity.
