"""SimHash 64-bit deduplication and canonical URL normalization."""

import hashlib
import re
from typing import List
from urllib.parse import urlparse, urlunparse, parse_qsl, urlencode


class SimHash:
    """Computes a 64-bit SimHash for fuzzy deduplication of job descriptions."""

    def __init__(self, bit_length: int = 64):
        self.bit_length = bit_length

    def _tokenize(self, text: str) -> List[str]:
        # Lowercase and extract alphanumeric words
        clean = re.sub(r"[^\w\s]", " ", text.lower())
        tokens = [t for t in clean.split() if len(t) > 2]
        return tokens

    def _hash_token(self, token: str) -> int:
        md5_hex = hashlib.md5(token.encode("utf-8")).hexdigest()
        return int(md5_hex[:16], 16) & ((1 << self.bit_length) - 1)

    def compute(self, text: str) -> int:
        tokens = self._tokenize(text)
        if not tokens:
            return 0

        v = [0] * self.bit_length
        for token in tokens:
            token_hash = self._hash_token(token)
            for i in range(self.bit_length):
                bit_mask = 1 << i
                if token_hash & bit_mask:
                    v[i] += 1
                else:
                    v[i] -= 1

        fingerprint = 0
        for i in range(self.bit_length):
            if v[i] > 0:
                fingerprint |= (1 << i)
        return fingerprint

    @staticmethod
    def hamming_distance(hash1: int, hash2: int) -> int:
        """Calculate bit differences between two 64-bit hashes."""
        x = hash1 ^ hash2
        return bin(x).count("1")

    def is_duplicate(self, text1: str, text2: str, max_distance: int = 3) -> bool:
        """Return True if texts are near-duplicates based on Hamming distance threshold."""
        h1 = self.compute(text1)
        h2 = self.compute(text2)
        return self.hamming_distance(h1, h2) <= max_distance


def normalize_job_url(raw_url: str) -> str:
    """Normalize job posting URLs by stripping marketing parameters and fragments."""
    parsed = urlparse(raw_url)
    # Strip tracking query params
    drop_params = {
        "utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content",
        "gh_src", "lever-source", "ref", "source", "s", "tracking"
    }
    filtered_queries = [
        (k, v) for k, v in parse_qsl(parsed.query)
        if k.lower() not in drop_params
    ]
    new_query = urlencode(filtered_queries)
    # Reassemble without fragment
    normalized = urlunparse((
        parsed.scheme.lower(),
        parsed.netloc.lower(),
        parsed.path.rstrip("/"),
        parsed.params,
        new_query,
        ""  # No fragment
    ))
    return normalized
