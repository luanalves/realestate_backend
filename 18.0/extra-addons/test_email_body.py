# Check template body_html for rendered vs unrendered variables
mail = env['mail.mail'].search([], order='create_date desc', limit=1)
if mail and mail.body_html:
    # Print first 500 characters of body_html
    print("Body HTML (first 500 chars):")
    print(mail.body_html[:500])
    print("\n" + "="*50)
    
    # Check for specific unrendered variables
    if '${object.name}' in mail.body_html:
        print("❌ Found unrendered: ${object.name}")
    if '${ctx.get(' in mail.body_html:
        print("❌ Found unrendered: ${ctx.get(")
    if '${object.company_id' in mail.body_html:
        print("❌ Found unrendered: ${object.company_id")
        
    # Check if it has any actual user name
    user = env['res.users'].browse(213)
    if user.name in mail.body_html:
        print(f"✅ Found rendered user name: {user.name}")
else:
    print("No mail found")
