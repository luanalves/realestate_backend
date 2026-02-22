#!/usr/bin/env python3
"""
Test script to verify resend-invite email functionality
"""
import odoo
from odoo import api, SUPERUSER_ID

# Initialize Odoo environment
odoo.tools.config.parse_config([])
env = api.Environment(odoo.registry('realestate'), SUPERUSER_ID, {})

# Get user ID 213
user = env['res.users'].browse(213)
print(f"Testing resend-invite for user: {user.login} (ID: {user.id})")

# Get invite service
invite_service = env['thedevkitchen.user.onboarding.invite'].create({})

# Get settings
settings = env['thedevkitchen.email.link.settings'].get_settings()
print(f"Frontend base URL: {settings.frontend_base_url}")

# Generate token
token_service = env['thedevkitchen.password.token'].create({})
company = user.estate_company_ids[0] if user.estate_company_ids else None
raw_token, token_record = token_service.generate_token(
    user=user,
    token_type='invite',
    company=company
)
print(f"Generated token: {raw_token[:20]}...")

# Send invite email
result = invite_service.send_invite_email(
    user=user,
    raw_token=raw_token,
    expires_hours=settings.invite_link_ttl_hours,
    frontend_base_url=settings.frontend_base_url
)

print(f"Email send result: {result}")

# Check mail queue
mail_mails = env['mail.mail'].search([], order='create_date desc', limit=1)
if mail_mails:
    mail = mail_mails[0]
    print(f"\nMail queue:")
    print(f"  ID: {mail.id}")
    print(f"  State: {mail.state}")
    print(f"  To: {mail.email_to}")
    print(f"  Subject: {mail.mail_message_id.subject if mail.mail_message_id else 'N/A'}")
else:
    print("\nNo emails in queue!")
