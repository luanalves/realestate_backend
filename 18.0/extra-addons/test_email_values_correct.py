# Test with email_values to override email_to but let other fields render
user = env['res.users'].browse(213)

# Get template
template = env.ref('thedevkitchen_user_onboarding.email_template_user_invite')
ctx = {
    'invite_link': 'https://example.com/set-password?token=EMAIL_VALUES_TEST',
    'expires_hours': 77
}

# Pass email_values to override email_to
email_values = {'email_to': user.email}  # Use user.email (related field)

print(f"Testing with email_values={{'email_to': '{user.email}'}}")
try:
    mail_id = template.with_context(ctx).send_mail(
        user.id,
        force_send=False,
        raise_exception=True,
        email_values=email_values
    )
    print(f"✅ Email queued with ID: {mail_id}")
except Exception as e:
    print(f"❌ Error: {e}")
    env.cr.rollback()
    exit(1)

env.cr.commit()

# Check the mail that was created
mail = env['mail.mail'].browse(mail_id)
print(f"\nMail details:")
print(f"  To: {mail.email_to}")
print(f"  State: {mail.state}")

if mail.body_html:
    if '${object.name}' in mail.body_html:
        print(f"  ❌ Body has unrendered ${'{object.name}'}")
    if 'EMAIL_VALUES_TEST' in mail.body_html:
        print(f"��� Body has context variable (token)")
    if '77 horas' in mail.body_html or '77 hours' in mail.body_html:
        print(f"  ✅ Body has context variable (expires_hours)")
    if user.name in mail.body_html:
        print(f"  ✅ Body has rendered user name")
