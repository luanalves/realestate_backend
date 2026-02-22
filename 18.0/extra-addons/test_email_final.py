# Get user 213
user = env['res.users'].browse(213)
print(f"User: {user.login}, email field: {user.email}")

# Get invite template
template = env.ref('thedevkitchen_user_onboarding.email_template_user_invite')
print(f"Template: {template.name}, email_to config: {template.email_to}")

# Set context
ctx = {
    'invite_link': 'https://example.com/set-password?token=TEST123_FINAL',
    'expires_hours': 99  # Use unusual number to identify this test
}

# Try to send email WITHOUT email_values
try:
    template.with_context(ctx).send_mail(
        user.id,
        force_send=False,
        raise_exception=True
    )
    print("✅ Email queued successfully")
except Exception as e:
    print(f"❌ Error: {e}")
    env.cr.rollback()
    exit(1)

# Commit to save the email
env.cr.commit()

# Check mail queue  
mail = env['mail.mail'].search([], order='create_date desc', limit=1)
if mail:
    print(f"\nMail in queue:")
    print(f"  To: {mail.email_to}")
    print(f"  State: {mail.state}")
    
    # Check if body contains rendered or unrendered variables
    if mail.body_html:
        if '${object.name}' in mail.body_html:
            print(f"  ❌ Contains unrendered ${'{object.name}'}")
        if 'TEST123_FINAL' in mail.body_html:
            print(f"  ✅ Contains context variable (token)")
        if '99 horas' in mail.body_html or '99 hours' in mail.body_html:
            print(f"  ✅ Contains context variable (expires_hours)")
        if user.name in mail.body_html:
            print(f"  ✅ Contains rendered user name: {user.name[:20]}...")
else:
    print("\n❌ No mail in queue")
