# AWS RDS PostgreSQL Deployment Guide

## Part 1: Host Database in AWS RDS

### Step 1: Create RDS PostgreSQL Instance

**Via AWS Console:**

1. **Login to AWS Console**
   - Go to https://console.aws.amazon.com/
   - Navigate to RDS service

2. **Create Database**
   - Click "Create database"
   - Choose "Standard create"
   - **Engine**: PostgreSQL 15.x
   - **Templates**: Free tier (for testing) or Production (for live)

3. **Settings**
   ```
   DB instance identifier: linkedin-bot-db
   Master username: dbadmin
   Master password: [Generate strong password - save it!]
   Confirm password: [Same password]
   ```

4. **Instance Configuration**
   ```
   DB instance class: db.t3.micro (Free tier) or db.t4g.micro
   Storage type: General Purpose SSD (gp3)
   Allocated storage: 20 GB
   Enable storage autoscaling: Yes (max 100 GB)
   ```

5. **Connectivity**
   ```
   Virtual Private Cloud (VPC): Default VPC
   Public access: Yes (for testing from your local machine)
   VPC security group: Create new
   Security group name: linkedin-bot-sg
   Availability Zone: No preference
   ```

6. **Database Authentication**
   ```
   Password authentication: Enable
   ```

7. **Additional Configuration**
   ```
   Initial database name: linkedin_bot
   Backup retention: 7 days
   Enable encryption: Yes
   Enable Performance Insights: No (save costs)
   Enable automated backups: Yes
   Backup window: 03:00-04:00 UTC
   Enable deletion protection: Yes (for production)
   ```

8. **Click "Create database"** (Takes 5-10 minutes)

---

### Step 2: Configure Security Group

1. **Go to RDS → Databases → linkedin-bot-db**
2. **Click on VPC security group** (e.g., `sg-xxxxx`)
3. **Edit inbound rules:**
   ```
   Type: PostgreSQL
   Protocol: TCP
   Port: 5432
   Source: My IP (for testing)
   Description: My local machine
   ```

4. **For production, add EC2 security group:**
   ```
   Type: PostgreSQL
   Protocol: TCP
   Port: 5432
   Source: [EC2 security group ID]
   Description: EC2 bot server
   ```

---

### Step 3: Get RDS Endpoint

1. **Go to RDS → Databases → linkedin-bot-db**
2. **Copy "Endpoint":**
   ```
   Example: linkedin-bot-db.abc123.us-east-1.rds.amazonaws.com
   ```
3. **Save this - you'll need it for .env**

---

### Step 4: Test Connection from Local Machine

```bash
# Install PostgreSQL client if not already installed
# Windows: Already have it (PostgreSQL 18)

# Test connection
psql -h linkedin-bot-db.abc123.us-east-1.rds.amazonaws.com \
     -U dbadmin \
     -d linkedin_bot \
     -p 5432

# Enter password when prompted
# If successful, you'll see: linkedin_bot=>
```

---

### Step 5: Apply Database Schema to RDS

```bash
# Run schema creation on RDS
psql -h linkedin-bot-db.abc123.us-east-1.rds.amazonaws.com \
     -U dbadmin \
     -d linkedin_bot \
     -p 5432 \
     -f migrations/schema.sql
```

**Or using Python:**
```python
import psycopg2
import os

# Read schema
with open('migrations/schema.sql', 'r') as f:
    schema = f.read()

# Connect to RDS
conn = psycopg2.connect(
    host='linkedin-bot-db.abc123.us-east-1.rds.amazonaws.com',
    database='linkedin_bot',
    user='dbadmin',
    password='YOUR_RDS_PASSWORD',
    port=5432
)

cursor = conn.cursor()
cursor.execute(schema)
conn.commit()
cursor.close()
conn.close()

print("Schema created on RDS!")
```

---

### Step 6: Migrate Data from Local to RDS

**Option A: Using pg_dump (Recommended)**

```bash
# 1. Dump local database
pg_dump -h localhost -U postgres -d linkedin_bot -F c -f linkedin_bot_backup.dump

# 2. Restore to RDS
pg_restore -h linkedin-bot-db.abc123.us-east-1.rds.amazonaws.com \
           -U dbadmin \
           -d linkedin_bot \
           --no-owner \
           --no-acl \
           linkedin_bot_backup.dump
```

**Option B: Using Python migration script**

```bash
# Create migration script for local → RDS
python migrate_local_to_rds.py
```

---

### Step 7: Update .env for RDS

```bash
# Update .env file with RDS credentials
DATABASE_HOST=linkedin-bot-db.abc123.us-east-1.rds.amazonaws.com
DATABASE_PORT=5432
DATABASE_NAME=linkedin_bot
DATABASE_USER=dbadmin
DATABASE_PASSWORD=YOUR_RDS_PASSWORD
DATABASE_SSLMODE=require  # IMPORTANT for RDS
```

---

### Step 8: Test Connection from Bot

```bash
# Test PostgreSQL connection to RDS
python test_postgres_connection.py
```

**Expected output:**
```
============================================================
POSTGRESQL CONNECTION TEST
============================================================

1. Checking environment variables...
   ✓ DATABASE_HOST: linkedin-bot-db.abc123.us-east-1.rds.amazonaws.com
   ✓ DATABASE_PORT: 5432
   ...

✅ ALL TESTS PASSED!
```

---

### Step 9: Run Bot with RDS

```bash
# Start bot with RDS database
python telegram_bot.py
```

**Test:**
- `/start` - Should work
- `/stats` - Should show migrated data
- `/post` - Should create post and save to RDS

---

## Security Best Practices

### 1. Use AWS Secrets Manager

**Store database password securely:**

```bash
# Create secret in AWS Secrets Manager
aws secretsmanager create-secret \
    --name linkedin-bot/database \
    --secret-string '{
      "username":"dbadmin",
      "password":"YOUR_RDS_PASSWORD",
      "host":"linkedin-bot-db.abc123.us-east-1.rds.amazonaws.com",
      "database":"linkedin_bot"
    }'
```

**Update bot to fetch from Secrets Manager:**
```python
import boto3
import json

def get_db_credentials():
    secret_name = "linkedin-bot/database"
    region_name = "us-east-1"

    client = boto3.client('secretsmanager', region_name=region_name)
    response = client.get_secret_value(SecretId=secret_name)
    secret = json.loads(response['SecretString'])

    return secret

# Usage
creds = get_db_credentials()
DATABASE_HOST = creds['host']
DATABASE_PASSWORD = creds['password']
```

### 2. Enable SSL/TLS

**Update connection string:**
```python
conn = psycopg2.connect(
    host=DATABASE_HOST,
    database=DATABASE_NAME,
    user=DATABASE_USER,
    password=DATABASE_PASSWORD,
    port=5432,
    sslmode='require'  # Force SSL
)
```

### 3. Restrict Security Group

**Production setup:**
- Remove "My IP" rule
- Only allow EC2 security group
- No public access if possible

### 4. Enable RDS Monitoring

- **CloudWatch Logs:** Enable PostgreSQL logs
- **Performance Insights:** Monitor query performance
- **Enhanced Monitoring:** CPU, memory, disk I/O

---

## Backup Strategy

### Automated Backups (Built-in RDS)
- Daily snapshots at 03:00 UTC
- 7-day retention
- Point-in-time recovery enabled

### Manual Backups (pg_dump to S3)

**Create backup script:**
```bash
#!/bin/bash
# backup_rds_to_s3.sh

DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="linkedin_bot_backup_${DATE}.dump"

# Dump database
pg_dump -h linkedin-bot-db.abc123.us-east-1.rds.amazonaws.com \
        -U dbadmin \
        -d linkedin_bot \
        -F c \
        -f $BACKUP_FILE

# Compress
gzip $BACKUP_FILE

# Upload to S3
aws s3 cp ${BACKUP_FILE}.gz s3://linkedin-bot-backups/

# Clean up local file
rm ${BACKUP_FILE}.gz

echo "Backup complete: ${BACKUP_FILE}.gz"
```

**Schedule via cron:**
```bash
# Run daily at 2 AM
0 2 * * * /path/to/backup_rds_to_s3.sh
```

---

## Cost Estimation

### Free Tier (First 12 months)
- **RDS:** db.t3.micro, 750 hours/month
- **Storage:** 20 GB General Purpose (SSD)
- **Backups:** 20 GB backup storage
- **Cost:** $0/month (within free tier limits)

### After Free Tier
- **RDS db.t4g.micro:** ~$15/month
- **Storage (20 GB gp3):** ~$2.5/month
- **Backup storage (20 GB):** ~$2/month
- **Data transfer:** ~$1/month
- **Total:** ~$20-25/month

---

## Troubleshooting

### Connection Refused
**Cause:** Security group not allowing your IP

**Solution:**
1. Go to RDS security group
2. Add your IP to inbound rules
3. Port: 5432, Source: My IP

### Authentication Failed
**Cause:** Wrong password or username

**Solution:**
1. Double-check credentials
2. Reset password in RDS console if needed

### SSL Error
**Cause:** RDS requires SSL but connection doesn't use it

**Solution:**
```python
# Add sslmode parameter
DATABASE_SSLMODE=require
```

---

## Next Steps

1. ✅ Create RDS instance
2. ✅ Apply schema
3. ✅ Migrate data
4. ✅ Update .env
5. ✅ Test connection
6. 🔄 Deploy bot to EC2 (Week 3 of migration plan)
7. 🔄 Set up automated backups to S3
8. 🔄 Configure CloudWatch monitoring

---

## Rollback Plan

If RDS has issues, rollback to local PostgreSQL:

```bash
# 1. Update .env
DATABASE_HOST=localhost
DATABASE_PORT=5432
DATABASE_NAME=linkedin_bot
DATABASE_USER=postgres
DATABASE_PASSWORD=YOUR_LOCAL_PASSWORD

# 2. Restart bot
python telegram_bot.py
```

Your local PostgreSQL data remains untouched!
