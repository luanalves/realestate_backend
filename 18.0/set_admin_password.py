#!/usr/bin/env python3
"""set_admin_password.py — Updates the Odoo 'admin' user's login password.

Usage:
    python3 set_admin_password.py DB_NAME DB_HOST DB_PORT DB_USER DB_PASS NEW_PASSWORD

Connects directly to PostgreSQL and writes the hashed password for the user
with login='admin', using Odoo 18's hashing scheme (pbkdf2_sha512 via passlib).
Called by odoo-init.sh after a fresh install or module upgrade.
"""

import sys


def main() -> None:
    if len(sys.argv) != 7:
        print(
            f"Usage: {sys.argv[0]} DB_NAME DB_HOST DB_PORT DB_USER DB_PASS NEW_PASSWORD",
            file=sys.stderr,
        )
        sys.exit(1)

    _, db_name, db_host, db_port, db_user, db_pass, new_password = sys.argv

    import psycopg2
    from passlib.context import CryptContext

    # Odoo 18 uses pbkdf2_sha512 (defined in auth_crypt/models/res_users.py)
    crypt_ctx = CryptContext(schemes=["pbkdf2_sha512"], deprecated="auto")
    hashed = crypt_ctx.hash(new_password)

    conn = psycopg2.connect(
        host=db_host,
        port=int(db_port),
        user=db_user,
        password=db_pass,
        dbname=db_name,
    )
    try:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE res_users SET password = %s WHERE login = %s RETURNING id",
                (hashed, "admin"),
            )
            if cur.rowcount == 0:
                print(
                    "[set_admin_password] WARNING: no user with login='admin' found",
                    file=sys.stderr,
                )
            else:
                uid = cur.fetchone()[0]
                print(f"[set_admin_password] ✅ Admin user (id={uid}) password updated")
        conn.commit()
    finally:
        conn.close()


if __name__ == "__main__":
    main()
