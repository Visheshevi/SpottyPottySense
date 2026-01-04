# Deployment Scripts

Automation scripts for SpottyPottySense deployment and management.

## Scripts Overview

| Script | Purpose | Usage |
|--------|---------|-------|
| `deploy.sh` | Deploy backend to AWS | `./scripts/deploy.sh <env>` |
| `setup-secrets.sh` | Initialize AWS Secrets Manager | `./scripts/setup-secrets.sh <env>` |
| `provision-device.sh` | Provision new IoT device | `./scripts/provision-device.sh <sensor-id>` |
| `test-integration.sh` | Run integration tests | `./scripts/test-integration.sh` |
| `cleanup.sh` | Clean up AWS resources | `./scripts/cleanup.sh <env>` |

## Coming Soon

These scripts will be created in subsequent phases:

- `deploy.sh` - Full deployment automation
- `setup-secrets.sh` - Secret initialization
- `provision-device.sh` - Device provisioning
- `test-integration.sh` - End-to-end testing
- `cleanup.sh` - Resource cleanup

## Development

Scripts should:
1. Be idempotent (safe to run multiple times)
2. Validate inputs
3. Provide clear error messages
4. Log actions taken
5. Exit with appropriate status codes

## Security

- Never hardcode credentials in scripts
- Use AWS CLI profiles or environment variables
- Validate AWS credentials before running
- Ask for confirmation on destructive actions

