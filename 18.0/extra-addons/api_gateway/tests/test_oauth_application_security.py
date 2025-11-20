"""Unit tests for OAuth Application security (bcrypt hashing)."""
from odoo.tests.common import TransactionCase
import bcrypt


class TestOAuthApplicationSecurity(TransactionCase):
    """Test OAuth application client_secret hashing with bcrypt."""

    def setUp(self):
        """Set up test fixtures."""
        super().setUp()
        self.OAuthApplication = self.env['oauth.application']
        self.plaintext_secret = 'test-secret-1234567890abcdef'
        
        # Generate a real bcrypt hash for testing
        secret_bytes = self.plaintext_secret.encode('utf-8')
        self.hashed_secret = bcrypt.hashpw(secret_bytes, bcrypt.gensalt(rounds=12)).decode('utf-8')

    def test_hash_secret_creates_valid_bcrypt_hash(self):
        """Test that _hash_secret creates a valid bcrypt hash."""
        app = self.OAuthApplication.create({
            'name': 'Test Hash Secret App'
        })
        
        hashed = app._hash_secret(self.plaintext_secret)
        
        # Verify it's a valid bcrypt hash
        self.assertIsInstance(hashed, str)
        self.assertTrue(hashed.startswith('$2b$'))  # bcrypt identifier
        
        # Verify the hash can be verified
        self.assertTrue(
            bcrypt.checkpw(
                self.plaintext_secret.encode('utf-8'),
                hashed.encode('utf-8')
            )
        )

    def test_verify_secret_valid_password(self):
        """Test verify_secret returns True for correct plaintext secret."""
        app = self.OAuthApplication.create({
            'name': 'Test Valid Password App',
            'client_secret': self.hashed_secret
        })
        
        result = app.verify_secret(self.plaintext_secret)
        self.assertTrue(result)

    def test_verify_secret_invalid_password(self):
        """Test verify_secret returns False for incorrect plaintext secret."""
        app = self.OAuthApplication.create({
            'name': 'Test Invalid Password App',
            'client_secret': self.hashed_secret
        })
        
        result = app.verify_secret('wrong-secret')
        self.assertFalse(result)

    def test_verify_secret_empty_plaintext(self):
        """Test verify_secret returns False for empty plaintext."""
        app = self.OAuthApplication.create({
            'name': 'Test Empty Plaintext App',
            'client_secret': self.hashed_secret
        })
        
        result = app.verify_secret('')
        self.assertFalse(result)

    def test_verify_secret_none_plaintext(self):
        """Test verify_secret returns False for None plaintext."""
        app = self.OAuthApplication.create({
            'name': 'Test None Plaintext App',
            'client_secret': self.hashed_secret
        })
        
        result = app.verify_secret(None)
        self.assertFalse(result)

    def test_verify_secret_empty_stored_hash(self):
        """Test verify_secret returns False when stored hash is empty."""
        app = self.OAuthApplication.create({
            'name': 'Test Empty Hash App',
            'client_secret': ''
        })
        
        result = app.verify_secret(self.plaintext_secret)
        self.assertFalse(result)

    def test_verify_secret_constant_time(self):
        """Test that verify_secret uses bcrypt's constant-time comparison."""
        # This is a basic test - bcrypt.checkpw is constant-time by design
        app = self.OAuthApplication.create({
            'name': 'Test Constant Time App',
            'client_secret': self.hashed_secret
        })
        
        # Both should return False, taking roughly the same time
        result1 = app.verify_secret('x')
        result2 = app.verify_secret('x' * 100)
        
        self.assertFalse(result1)
        self.assertFalse(result2)

    def test_bcrypt_rounds_configuration(self):
        """Test that bcrypt uses 12 rounds as configured."""
        app = self.OAuthApplication.create({
            'name': 'Test Bcrypt Rounds App'
        })
        
        hashed = app._hash_secret(self.plaintext_secret)
        
        # Extract rounds from hash (format: $2b$12$...)
        parts = hashed.split('$')
        rounds = int(parts[2])
        
        self.assertEqual(rounds, 12, "Bcrypt should use 12 rounds")

    def test_different_secrets_produce_different_hashes(self):
        """Test that the same secret hashed twice produces different salts."""
        app = self.OAuthApplication.create({
            'name': 'Test Different Hashes App'
        })
        
        hash1 = app._hash_secret(self.plaintext_secret)
        hash2 = app._hash_secret(self.plaintext_secret)
        
        # Hashes should be different due to different salts
        self.assertNotEqual(hash1, hash2)
        
        # But both should verify the same plaintext
        self.assertTrue(
            bcrypt.checkpw(
                self.plaintext_secret.encode('utf-8'),
                hash1.encode('utf-8')
            )
        )
        self.assertTrue(
            bcrypt.checkpw(
                self.plaintext_secret.encode('utf-8'),
                hash2.encode('utf-8')
            )
        )



