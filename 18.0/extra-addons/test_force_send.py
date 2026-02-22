# Test with force_send=True to see if that triggers rendering
user = env['res.users'].browse(213)

# Delete previous test emails
env['mail.mail'].search([('email_to', 'like', 'teste@teste.com')]).unlink()

# Get invite template
template = env.ref('thedevkitchen_user_onboarding.email_template_user_invite')
ctx = {
    'invite_link': 'https://example.com/set-password?token=FORCE_SEND_TEST',
    'expires_hours': 88
}

# Try with force_send=True
print("Testing with force_send=True...")
try:
    template.with_context(ctx).send_mail(
        user.id,
        force_send=True,  # Send immediately
        raise_exception=True
    )
    print("✅ Email sent with force_send=True")
except Exception as e:
    print(f"❌ Error: {e}")

env.cr.commit()
