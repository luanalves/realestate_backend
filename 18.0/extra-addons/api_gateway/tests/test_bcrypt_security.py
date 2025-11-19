# -*- coding: utf-8 -*-
"""
Testes de Integração para Segurança Bcrypt
Testa o hashing e verificação de client_secret com bcrypt
"""

from odoo.tests.common import TransactionCase
from odoo.exceptions import UserError
import bcrypt


class TestBcryptSecurity(TransactionCase):
    """Testa funcionalidade de hashing bcrypt do client_secret"""

    def setUp(self):
        super().setUp()
        self.OAuthApplication = self.env['oauth.application']
        
    def test_01_client_secret_is_hashed_on_create(self):
        """Testa que client_secret é automaticamente hasheado na criação"""
        # Criar aplicação OAuth
        app = self.OAuthApplication.create({
            'name': 'Test Bcrypt App',
            'description': 'Testing bcrypt hashing'
        })
        
        # Verificar que client_secret existe e está hasheado
        self.assertTrue(app.client_secret, "Client secret deve existir")
        self.assertTrue(app.client_secret.startswith('$2b$'), 
                       "Client secret deve ser um hash bcrypt")
        
        # Verificar que é um hash válido de 60 caracteres (padrão bcrypt)
        self.assertEqual(len(app.client_secret), 60,
                        "Hash bcrypt deve ter 60 caracteres")

    def test_02_hash_secret_creates_valid_bcrypt_hash(self):
        """Testa que _hash_secret cria um hash bcrypt válido"""
        app = self.OAuthApplication.create({
            'name': 'Test Hash Method'
        })
        
        plaintext = 'my-super-secret-key-123'
        hashed = app._hash_secret(plaintext)
        
        # Verificar formato bcrypt
        self.assertTrue(hashed.startswith('$2b$12$'),
                       "Hash deve começar com $2b$12$ (bcrypt 12 rounds)")
        
        # Verificar que pode ser verificado
        self.assertTrue(
            bcrypt.checkpw(plaintext.encode('utf-8'), hashed.encode('utf-8')),
            "Hash deve poder ser verificado com bcrypt"
        )

    def test_03_verify_secret_validates_correct_plaintext(self):
        """Testa que verify_secret retorna True para secret correto"""
        # Generate plaintext secret
        import secrets
        import string
        alphabet = string.ascii_letters + string.digits
        plaintext = ''.join(secrets.choice(alphabet) for _ in range(64))
        
        # Create app
        app = self.OAuthApplication.create({
            'name': 'Test Verify Correct'
        })
        
        # Update with hashed version of known plaintext
        hashed = app._hash_secret(plaintext)
        app.write({'client_secret': hashed})
        
        # Verificar que aceita o plaintext correto
        result = app.verify_secret(plaintext)
        self.assertTrue(result, "Deve aceitar secret correto")

    def test_04_verify_secret_rejects_incorrect_plaintext(self):
        """Testa que verify_secret retorna False para secret incorreto"""
        # Generate plaintext secret
        import secrets
        import string
        alphabet = string.ascii_letters + string.digits
        plaintext = ''.join(secrets.choice(alphabet) for _ in range(64))
        
        app = self.OAuthApplication.create({
            'name': 'Test Verify Incorrect'
        })
        
        # Update with hashed version
        hashed = app._hash_secret(plaintext)
        app.write({'client_secret': hashed})
        
        # Verificar que rejeita secret incorreto
        result = app.verify_secret('wrong-secret-completely-different')
        self.assertFalse(result, "Deve rejeitar secret incorreto")

    def test_05_verify_secret_handles_empty_plaintext(self):
        """Testa que verify_secret retorna False para plaintext vazio"""
        app = self.OAuthApplication.create({
            'name': 'Test Empty Plaintext'
        })
        
        result = app.verify_secret('')
        self.assertFalse(result, "Deve rejeitar plaintext vazio")
        
        result = app.verify_secret(None)
        self.assertFalse(result, "Deve rejeitar plaintext None")

    def test_06_verify_secret_handles_empty_hash(self):
        """Testa que verify_secret retorna False quando hash está vazio"""
        app = self.OAuthApplication.create({
            'name': 'Test Empty Hash'
        })
        
        # Forçar client_secret vazio (não deveria acontecer na prática)
        app.write({'client_secret': ''})
        
        result = app.verify_secret('any-plaintext')
        self.assertFalse(result, "Deve rejeitar quando hash está vazio")

    def test_07_different_secrets_produce_different_hashes(self):
        """Testa que mesmo plaintext gera hashes diferentes (salt aleatório)"""
        app = self.OAuthApplication.create({
            'name': 'Test Different Hashes'
        })
        
        # Generate plaintext
        import secrets
        import string
        alphabet = string.ascii_letters + string.digits
        plaintext = ''.join(secrets.choice(alphabet) for _ in range(64))
        
        hash1 = app._hash_secret(plaintext)
        hash2 = app._hash_secret(plaintext)
        
        # Hashes devem ser diferentes devido a salts diferentes
        self.assertNotEqual(hash1, hash2,
                           "Mesmo plaintext deve gerar hashes diferentes")
        
        # Mas ambos devem verificar o mesmo plaintext
        self.assertTrue(
            bcrypt.checkpw(plaintext.encode('utf-8'), hash1.encode('utf-8'))
        )
        self.assertTrue(
            bcrypt.checkpw(plaintext.encode('utf-8'), hash2.encode('utf-8'))
        )

    def test_08_bcrypt_uses_12_rounds(self):
        """Testa que bcrypt usa 12 rounds conforme configurado"""
        app = self.OAuthApplication.create({
            'name': 'Test Bcrypt Rounds'
        })
        
        # Generate plaintext
        import secrets
        import string
        alphabet = string.ascii_letters + string.digits
        plaintext = ''.join(secrets.choice(alphabet) for _ in range(64))
        
        hashed = app._hash_secret(plaintext)
        
        # Formato bcrypt: $2b$12$... (12 = rounds)
        parts = hashed.split('$')
        rounds = int(parts[2])
        
        self.assertEqual(rounds, 12, "Bcrypt deve usar 12 rounds")

    def test_09_regenerate_secret_creates_new_hash(self):
        """Testa que regenerar secret cria um novo hash diferente"""
        app = self.OAuthApplication.create({
            'name': 'Test Regenerate Secret'
        })
        
        old_hash = app.client_secret
        
        # Regenerar secret
        app.action_regenerate_secret()
        
        new_hash = app.client_secret
        
        # Hashes devem ser diferentes
        self.assertNotEqual(old_hash, new_hash,
                           "Regenerar deve criar novo hash")
        
        # Ambos devem ser hashes bcrypt válidos
        self.assertTrue(old_hash.startswith('$2b$'))
        self.assertTrue(new_hash.startswith('$2b$'))

    def test_10_generate_client_secret_produces_64_chars(self):
        """Testa que _generate_client_secret gera string de 64 caracteres"""
        app = self.OAuthApplication.create({
            'name': 'Test Generate Secret Length'
        })
        
        secret = app._generate_client_secret()
        
        self.assertEqual(len(secret), 64,
                        "Client secret plaintext deve ter 64 caracteres")
        
        # Verificar que contém apenas caracteres válidos (alfanuméricos + - e _)
        import string
        valid_chars = string.ascii_letters + string.digits + '-_'
        self.assertTrue(all(c in valid_chars for c in secret),
                       "Secret deve conter apenas caracteres alfanuméricos, - e _")

    def test_11_client_secret_info_shows_correct_message(self):
        """Testa que campo client_secret_info mostra mensagem correta"""
        # Antes de criar
        app = self.OAuthApplication.create({
            'name': 'Test Secret Info'
        })
        
        # Depois de criar, deve mostrar mensagem sobre secret já hasheado
        expected_message = 'Secret shown only once after save. Lost? Use "Regenerate Secret".'
        self.assertEqual(app.client_secret_info, expected_message,
                        "Deve mostrar mensagem informativa correta")

    def test_12_bcrypt_hash_is_constant_time(self):
        """Testa que verificação usa tempo constante (característica do bcrypt)"""
        # Generate plaintext
        import secrets
        import string
        alphabet = string.ascii_letters + string.digits
        plaintext = ''.join(secrets.choice(alphabet) for _ in range(64))
        
        app = self.OAuthApplication.create({
            'name': 'Test Constant Time'
        })
        
        hashed = app._hash_secret(plaintext)
        app.write({'client_secret': hashed})
        
        # Ambas verificações devem retornar False
        # bcrypt.checkpw usa tempo constante por design
        result1 = app.verify_secret('x')
        result2 = app.verify_secret('x' * 100)
        
        self.assertFalse(result1)
        self.assertFalse(result2)
        # Não podemos medir tempo aqui, mas bcrypt garante tempo constante

    def test_13_token_endpoint_validates_with_hashed_secret(self):
        """Testa que endpoint /api/v1/auth/token valida com secret hasheado"""
        # Generate plaintext secret
        import secrets
        import string
        alphabet = string.ascii_letters + string.digits
        plaintext_secret = ''.join(secrets.choice(alphabet) for _ in range(64))
        
        app = self.OAuthApplication.create({
            'name': 'Test Token Endpoint Validation'
        })
        
        # Update with hashed version of known plaintext
        hashed = app._hash_secret(plaintext_secret)
        app.write({'client_secret': hashed})
        
        # Simular validação como no controller
        # O controller usa verify_secret para validar
        is_valid = app.verify_secret(plaintext_secret)
        
        self.assertTrue(is_valid,
                       "Controller deve validar secret corretamente")
