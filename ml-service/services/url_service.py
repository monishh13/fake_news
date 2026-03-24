"""
URL Service — article extraction with SSRF protection.

Security: Before making any outbound HTTP request, the URL is validated to:
1. Only allow http/https schemes.
2. Resolve the hostname and block RFC 1918 / loopback / link-local ranges and
   AWS/GCP/Azure instance-metadata endpoints that attackers commonly probe.
"""

import ipaddress
import re
import socket
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup
from fastapi import HTTPException

# Canonical blocked IP ranges (RFC 1918, loopback, link-local, private cloud metadata)
_BLOCKED_NETWORKS = [
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"),
    ipaddress.ip_network("127.0.0.0/8"),        # loopback
    ipaddress.ip_network("169.254.0.0/16"),     # link-local / AWS metadata
    ipaddress.ip_network("100.64.0.0/10"),      # shared address space
    ipaddress.ip_network("::1/128"),            # IPv6 loopback
    ipaddress.ip_network("fc00::/7"),           # IPv6 unique local
    ipaddress.ip_network("fe80::/10"),          # IPv6 link-local
]

# Only these TLDs / IPs are allowed (additional heuristic — not a block-list substitute)
_ALLOWED_SCHEMES = {"http", "https"}


def _validate_url(url: str) -> None:
    """
    Raise HTTPException(400) if the URL fails SSRF validation.
    Checks performed:
    - Scheme must be http or https.
    - Hostname must resolve to a public IP address.
    - Resolved IP must not fall in any private / reserved range.
    """
    try:
        parsed = urlparse(url)
    except Exception:
        raise HTTPException(status_code=400, detail="Malformed URL.")

    if parsed.scheme not in _ALLOWED_SCHEMES:
        raise HTTPException(
            status_code=400,
            detail=f"URL scheme '{parsed.scheme}' is not allowed. Only http and https are permitted.",
        )

    hostname = parsed.hostname
    if not hostname:
        raise HTTPException(status_code=400, detail="URL has no hostname.")

    # Block bare IP literals immediately
    try:
        ip_obj = ipaddress.ip_address(hostname)
        _assert_public_ip(ip_obj, url)
        return  # bare IP is fine if public
    except ValueError:
        pass  # not an IP literal, resolve below

    # Resolve hostname to IP(s) and block any private result
    try:
        infos = socket.getaddrinfo(hostname, None)
    except socket.gaierror:
        raise HTTPException(status_code=400, detail=f"Could not resolve hostname: {hostname}")

    for info in infos:
        ip_str = info[4][0]
        try:
            ip_obj = ipaddress.ip_address(ip_str)
        except ValueError:
            continue
        _assert_public_ip(ip_obj, url)


def _assert_public_ip(ip: ipaddress.IPv4Address | ipaddress.IPv6Address, url: str) -> None:
    """Raise HTTPException if the IP falls in any blocked network."""
    for network in _BLOCKED_NETWORKS:
        if ip in network:
            raise HTTPException(
                status_code=400,
                detail=(
                    "The URL resolves to a private or reserved IP address and cannot be fetched "
                    "for security reasons."
                ),
            )


def extract_article_from_url(url: str) -> tuple[str, str]:
    """
    Downloads the HTML of the given URL and parses it using BeautifulSoup.
    Returns a tuple of (title, text).

    Raises HTTPException(400) if the URL fails SSRF validation.
    Raises ValueError for network / parsing errors.
    """
    # Security: validate before making any outbound connection
    _validate_url(url)

    try:
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/114.0.0.0 Safari/537.36"
            )
        }
        res = requests.get(url, headers=headers, timeout=10)
        res.raise_for_status()

        soup = BeautifulSoup(res.text, "html.parser")

        # Title
        title = ""
        if soup.title and soup.title.string:
            title = soup.title.string.strip()

        # Main content — join all paragraph text
        paragraphs = soup.find_all("p")
        text = "\n\n".join(
            [p.get_text().strip() for p in paragraphs if p.get_text().strip()]
        )

        return title, text

    except HTTPException:
        raise  # re-raise SSRF errors unchanged
    except Exception as e:
        raise ValueError(f"Failed to extract URL content: {str(e)}")
