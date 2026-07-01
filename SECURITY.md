# Security Policy

## Supported versions

This is an educational open-source project. Security fixes are applied on the `main` branch when reported and confirmed.

| Version | Supported |
| ------- | --------- |
| latest `main` | yes |

There are no long-term release branches or deployed production instances maintained by this project.

## Reporting a vulnerability

If you discover a security issue, please report it responsibly:

1. **Do not** open a public GitHub issue for exploitable vulnerabilities.
2. Email the repository owner via the contact method on the [GitHub profile](https://github.com/pueraeternis) associated with this repository, or use GitHub's private vulnerability reporting if enabled for the repository.
3. Include a clear description, reproduction steps, and impact assessment.

We aim to acknowledge reports within a reasonable timeframe and will coordinate disclosure after a fix is available.

## Scope notes

This project is a **local educational demo**. It does not ship authentication, deployment infrastructure, or production monitoring. Reports about missing enterprise security controls (auth, WAF, SOC2 operations) are out of scope unless they expose a concrete vulnerability in this repository's code or documented workflows.

## Secrets

Never commit:

* `.env` files with real credentials;
* API keys or tokens;
* internal hostnames or customer data.

Use `.env.example` as a template only. Load secrets into your shell locally; the CLI does not auto-read `.env`.
