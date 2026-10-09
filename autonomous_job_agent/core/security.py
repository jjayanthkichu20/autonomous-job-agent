"""Security, envelope encryption, and candidate privacy controls."""

import base64
import hashlib
import json
import os
import re
from typing import Any, Dict
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from autonomous_job_agent.core.config import config


class SecurityManager:
    """Provides envelope encryption, PII masking, and cryptographic shredding."""

    def __init__(self, master_key: str = None):
        raw_key = (master_key or config.master_encryption_key).encode("utf-8")
        # Derive consistent 32-byte key for AES-256
        self._root_key = hashlib.sha256(raw_key).digest()

    def generate_candidate_dek(self) -> bytes:
        """Generate a random 256-bit Data Encryption Key (DEK) for a specific candidate."""
        return AESGCM.generate_key(bit_length=256)

    def encrypt_candidate_dek(self, dek: bytes) -> str:
        """Encrypt candidate DEK using the Root/Master Key (Envelope Encryption)."""
        aesgcm = AESGCM(self._root_key)
        nonce = os.urandom(12)
        encrypted = aesgcm.encrypt(nonce, dek, None)
        payload = nonce + encrypted
        return base64.b64encode(payload).decode("utf-8")

    def decrypt_candidate_dek(self, encrypted_dek_b64: str) -> bytes:
        """Decrypt candidate DEK using the Root Key."""
        payload = base64.b64decode(encrypted_dek_b64.encode("utf-8"))
        nonce = payload[:12]
        ciphertext = payload[12:]
        aesgcm = AESGCM(self._root_key)
        return aesgcm.decrypt(nonce, ciphertext, None)

    def encrypt_payload(self, data: Dict[str, Any], dek: bytes) -> str:
        """Encrypt JSON serializable payload with a candidate's DEK."""
        json_bytes = json.dumps(data).encode("utf-8")
        aesgcm = AESGCM(dek)
        nonce = os.urandom(12)
        encrypted = aesgcm.encrypt(nonce, json_bytes, None)
        return base64.b64encode(nonce + encrypted).decode("utf-8")

    def decrypt_payload(self, encrypted_b64: str, dek: bytes) -> Dict[str, Any]:
        """Decrypt payload using the candidate's DEK."""
        payload = base64.b64decode(encrypted_b64.encode("utf-8"))
        nonce = payload[:12]
        ciphertext = payload[12:]
        aesgcm = AESGCM(dek)
        decrypted_bytes = aesgcm.decrypt(nonce, ciphertext, None)
        return json.loads(decrypted_bytes.decode("utf-8"))

    @staticmethod
    def sha256_hash(content: str) -> str:
        """Compute deterministic SHA-256 checksum."""
        return hashlib.sha256(content.encode("utf-8")).hexdigest()

    @staticmethod
    def mask_pii(text: str) -> str:
        """Mask candidate emails and phone numbers for sanitized log streaming."""
        # Mask emails: j***@example.com
        text = re.sub(r'([a-zA-Z0-9_.+-])[a-zA-Z0-9_.+-]*@([a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+)', r'\1***@\2', text)
        # Mask phone numbers (US/Intl patterns)
        text = re.sub(r'(\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}', r'***-***-XXXX', text)
        return text


security_manager = SecurityManager()
