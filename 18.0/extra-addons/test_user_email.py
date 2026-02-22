# Test if res.users has email field/property
user = env['res.users'].browse(213)
print(f"user.login: {user.login}")
print(f"user.partner_id: {user.partner_id}")
print(f"user.partner_id.email: {user.partner_id.email if user.partner_id else 'N/A'}")
print(f"hasattr(user, 'email'): {hasattr(user, 'email')}")
if hasattr(user, 'email'):
    print(f"user.email: {user.email}")
