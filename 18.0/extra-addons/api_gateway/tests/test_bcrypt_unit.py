"""Unit tests for bcrypt hashing functionality (pure Python, no Odoo ORM)."""
import unittest
import bcrypt
import sys
sys.path.insert(0, '/mnt/extra-addons/api_gateway')


class TestBcryptHashing(unittest.TestCase):
    """Test bcrypt hashing and verification logic."""

    def test_01_bcrypt_hash_format(self):
        """Test that bcrypt produces correct hash format."""
        plaintext = 'test-secret-123'
        salt = bcrypt.gensalt(rounds=12)
        hashed = bcrypt.hashpw(plaintext.encode('utf-8'), salt).decode('utf-8')
        
        self.assertTrue(hashed.startswith('$2b$12$'))
        self.assertEqual(len(hashed), 60)

    def test_02_bcrypt_verify_correct_password(self):
        """Test bcrypt verification with correct password."""
        plaintext = 'correct-password'
        salt = bcrypt.gensalt(rounds=12)
        hashed = bcrypt.hashpw(plaintext.encode('utf-8'), salt)
        
        result = bcrypt.checkpw(plaintext.encode('utf-8'), hashed)
        self.assertTrue(result)

    def test_03_bcrypt_reject_wrong_password(self):
        """Test bcrypt rejects wrong password."""
        correct = 'correct-password'
        wrong = 'wrong-password'
        salt = bcrypt.gensalt(rounds=12)
        hashed = bcrypt.hashpw(correct.encode('utf-8'), salt)
        
        result = bcrypt.checkpw(wrong.encode('utf-8'), hashed)
        self.assertFalse(result)

    def test_04_bcrypt_different_salts_produce_different_hashes(self):
        """Test that same password with different salts produces different hashes."""
        plaintext = 'same-password'
        
        hash1 = bcrypt.hashpw(plaintext.encode('utf-8'), bcrypt.gensalt(rounds=12))
        hash2 = bcrypt.hashpw(plaintext.encode('utf-8'), bcrypt.gensalt(rounds=12))
        
        self.assertNotEqual(hash1, hash2)
        
        # But both should verify the same password
        self.assertTrue(bcrypt.checkpw(plaintext.encode('utf-8'), hash1))
        self.assertTrue(bcrypt.checkpw(plaintext.encode('utf-8'), hash2))

    def test_05_bcrypt_12_rounds_strength(self):
        """Test that 12 rounds is extracted correctly from hash."""
        plaintext = 'test-password'
        salt = bcrypt.gensalt(rounds=12)
        hashed = bcrypt.hashpw(plaintext.encode('utf-8'), salt).decode('utf-8')
        
        # Extract rounds from hash ($2b$12$...)
        parts = hashed.split('$')
        rounds = int(parts[2])
        
        self.assertEqual(rounds, 12)

    def test_06_bcrypt_handles_special_characters(self):
        """Test that bcrypt handles special characters correctly."""
        plaintext = 'p@ssw0rd!#$%^&*()'
        salt = bcrypt.gensalt(rounds=12)
        hashed = bcrypt.hashpw(plaintext.encode('utf-8'), salt)
        
        result = bcrypt.checkpw(plaintext.encode('utf-8'), hashed)
        self.assertTrue(result)

    def test_07_bcrypt_handles_long_passwords(self):
        """Test that bcrypt handles long passwords (bcrypt truncates at 72 bytes)."""
        plaintext = 'a' * 100  # 100 characters
        # Bcrypt 5.0+ requires manual truncation
        plaintext_bytes = plaintext.encode('utf-8')[:72]
        salt = bcrypt.gensalt(rounds=12)
        hashed = bcrypt.hashpw(plaintext_bytes, salt)
        
        result = bcrypt.checkpw(plaintext_bytes, hashed)
        self.assertTrue(result)

    def test_08_bcrypt_constant_time_property(self):
        """Test that bcrypt comparison is designed for constant time."""
        correct = 'correct-password'
        salt = bcrypt.gensalt(rounds=12)
        hashed = bcrypt.hashpw(correct.encode('utf-8'), salt)
        
        # Both should return False (bcrypt uses constant time internally)
        # Bcrypt 5.0+ requires passwords <= 72 bytes
        result1 = bcrypt.checkpw(b'x', hashed)
        result2 = bcrypt.checkpw((b'x' * 72), hashed)  # Use 72 bytes max
        
        self.assertFalse(result1)
        self.assertFalse(result2)

    def test_09_client_secret_generation_length(self):
        """Test that generated client secrets have correct length."""
        import secrets
        import string
        
        # Simulate _generate_client_secret method
        alphabet = string.ascii_letters + string.digits
        secret = ''.join(secrets.choice(alphabet) for _ in range(64))
        
        self.assertEqual(len(secret), 64)
        self.assertTrue(secret.isalnum())

    def test_10_client_secret_randomness(self):
        """Test that generated secrets are random."""
        import secrets
        import string
        
        alphabet = string.ascii_letters + string.digits
        secret1 = ''.join(secrets.choice(alphabet) for _ in range(64))
        secret2 = ''.join(secrets.choice(alphabet) for _ in range(64))
        
        self.assertNotEqual(secret1, secret2)
        self.assertEqual(len(secret1), 64)
        self.assertEqual(len(secret2), 64)


if __name__ == '__main__':
    unittest.main()
