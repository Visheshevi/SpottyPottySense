# Configuration Files

Environment-specific configuration for SpottyPottySense deployment.

## Directory Structure

```
config/
├── dev/
│   └── config.json         # Development environment config
├── staging/
│   └── config.json         # Staging environment config
├── prod/
│   └── config.json         # Production environment config
└── README.md               # This file
```

## Configuration Files

Each environment has a `config.json` file with the following structure:

### Common Settings

| Setting | Description | Dev | Staging | Prod |
|---------|-------------|-----|---------|------|
| `environment` | Environment name | dev | staging | prod |
| `region` | AWS region | us-east-1 | us-east-1 | us-east-1 |
| `stackName` | CloudFormation stack name | spotty-potty-sense-dev | spotty-potty-sense-staging | spotty-potty-sense-prod |
| `logLevel` | Logging verbosity | DEBUG | INFO | WARN |

### Application Settings

| Setting | Description | Default |
|---------|-------------|---------|
| `spotifyDefaultTimeoutMinutes` | Minutes before auto-stop | 5 |
| `motionDebounceMinutes` | Cooldown between motion triggers | 2 |
| `tokenRefreshIntervalMinutes` | How often to refresh Spotify tokens | 30 |
| `timeoutCheckIntervalMinutes` | How often to check for timeouts | 1 |
| `sessionTTLDays` | Days to keep session history | 30 (dev/staging), 90 (prod) |
| `enableXRayTracing` | Enable AWS X-Ray distributed tracing | true |
| `enableDetailedMetrics` | Enable detailed CloudWatch metrics | true (dev/staging), false (prod) |

### DynamoDB Settings

| Setting | Description | Dev | Staging | Prod |
|---------|-------------|-----|---------|------|
| `billingMode` | PAY_PER_REQUEST or PROVISIONED | PAY_PER_REQUEST | PAY_PER_REQUEST | PAY_PER_REQUEST |
| `pointInTimeRecovery` | Enable PITR backups | false | true | true |
| `deletionProtection` | Prevent accidental deletion | false | false | true |

### Lambda Settings

| Setting | Description | Dev | Staging | Prod |
|---------|-------------|-----|---------|------|
| `runtime` | Python runtime version | python3.11 | python3.11 | python3.11 |
| `timeout` | Function timeout (seconds) | 30 | 30 | 30 |
| `memorySize` | Memory allocation (MB) | 256 | 256 | 512 |
| `reservedConcurrency` | Reserved concurrent executions | null | 10 | 50 |

### API Gateway Settings

**Throttling:**
- Dev: 100 req/sec, burst 200
- Staging: 500 req/sec, burst 1000
- Prod: 1000 req/sec, burst 2000

**CORS:**
- Dev: localhost:5173, localhost:3000
- Staging: https://staging.spottypotty.example.com
- Prod: https://app.spottypotty.example.com

### Cognito Settings

**Password Policy:**
- Dev: 8 chars, upper/lower/numbers
- Staging: 10 chars, upper/lower/numbers/symbols
- Prod: 12 chars, upper/lower/numbers/symbols

**MFA:**
- Dev: Optional
- Staging: Optional
- Prod: Required

### Monitoring Settings

| Setting | Dev | Staging | Prod |
|---------|-----|---------|------|
| `logRetentionDays` | 7 | 30 | 90 |
| `createDashboard` | true | true | true |
| `alarmEmail` | your-email@example.com | alerts@example.com | ops-alerts@example.com |

## Usage

### During Deployment

SAM template reads these files via parameters:

```bash
sam deploy --config-env dev
```

This loads `config/dev/config.json` and passes values to CloudFormation.

### Updating Configuration

1. Edit the appropriate `config.json` file
2. Commit changes to Git
3. Redeploy:
   ```bash
   ./scripts/deploy.sh <environment>
   ```

### Adding New Settings

1. Add to `config.json` files
2. Update SAM `template.yaml` Parameters section
3. Reference in Resources:
   ```yaml
   Parameters:
     LogLevel:
       Type: String
       Default: INFO
   
   Resources:
     MyFunction:
       Environment:
         Variables:
           LOG_LEVEL: !Ref LogLevel
   ```

## Environment Variables (Secrets)

**DO NOT** store secrets in these files! Use AWS Secrets Manager instead.

Secrets stored in AWS Secrets Manager:
- `spotty-potty-sense/spotify/client-credentials`
- `spotty-potty-sense/spotify/users/{userId}/refresh-token`
- `spotty-potty-sense/spotify/users/{userId}/access-token`

See `scripts/setup-secrets.sh` for secret initialization.

## Best Practices

1. **Never commit secrets** to these files
2. **Use environment-appropriate values** (lower limits in dev, higher in prod)
3. **Test in dev first** before promoting to staging/prod
4. **Document changes** in commit messages
5. **Review differences** between environments periodically
6. **Keep prod most restrictive** (MFA required, deletion protection, etc.)

## Customization

To customize for your deployment:

1. Update `region` if not using us-east-1
2. Update `alarmEmail` with your email
3. Update CORS `allowOrigins` with your dashboard URL
4. Adjust timeout and debounce settings as needed
5. Update tags with your organization's requirements

## Validation

Validate JSON syntax:

```bash
# Using jq
jq empty config/dev/config.json
jq empty config/staging/config.json
jq empty config/prod/config.json

# Using Python
python3 -m json.tool config/dev/config.json > /dev/null
```

## Troubleshooting

**Q: My changes aren't taking effect**
- Ensure you redeployed after changing config
- Check CloudFormation stack events for errors
- Verify SAM is reading correct config file

**Q: How do I add a new environment?**
1. Create `config/newenv/config.json`
2. Copy from existing environment and modify
3. Add to `samconfig.toml`
4. Deploy: `sam deploy --config-env newenv`

**Q: Should I version control these files?**
- Yes, commit these files to Git
- They contain no secrets
- Track changes for audit trail

