# Get user 213
user = env['res.users'].browse(213)
print(f"User: {user.login}")

# Get invite template
template = env.ref('thedevkitchen_user_onboarding.email_template_user_invite')
print(f"Template: {template.name}")

# Set context
ctx = {
    'invite_link': 'https://example.com/set-password?token=TEST123',
    'expires_hours': 24
}

# Try to send email with email_values
email_values = {'email_to': user.login}
try:
    template.with_context(ctx).send_mail(
        user.id,
        force_send=False,
        raise_exception=True,
        email_values=email_values
    )
    print("✅ Email queued successfully")
except Exception as e:
    print(f"❌ Error: {e}")

# Check mail queue  
mail = env['mail.mail'].search([], order='create_date desc', limit=1)
if mail:
    print(f"\nMail in queue:")
    print(f"  To: {mail.email_to}")
    print(f"  State: {mail.state}")
    # Check body_html contains rendered variables
    if mail.body_html:
        if '${' in mail.body_html:
            print(f"  ❌ Contains unrendered variables!")
        else:
            print(f"  ✅ Variables rendered correctly")
else:
    print("\n❌ No mail in queue")

env.cr.rollback()  # Don't save
