# Terraform Infrastructure Configuration

Complete Infrastructure as Code configuration for deploying curriculum-manager to AWS.

## Overview

This Terraform configuration provisions:

- **EKS Cluster**: Kubernetes cluster for container orchestration
- **VPC**: Custom VPC with public/private subnets across 2 AZs
- **RDS PostgreSQL**: Managed database with automated backups
- **ElastiCache Redis**: In-memory cache for sessions and data
- **NAT Gateway**: For private subnet outbound access
- **Security Groups**: Network access control
- **IAM Roles**: Service roles for EKS nodes

## File Structure

```
terraform/
├── main.tf              # Main infrastructure definitions
├── variables.tf         # Input variables
├── outputs.tf          # Output values
├── terraform.tfvars    # Default values (git-ignored)
├── environments/       # Environment-specific configurations
│   ├── dev.tfvars     # Development settings
│   ├── staging.tfvars # Staging settings
│   └── prod.tfvars    # Production settings
└── README.md           # This file
```

## Prerequisites

1. **AWS Account**: With appropriate permissions
2. **Terraform**: Version 1.5+
   ```bash
   brew install terraform  # macOS
   ```

3. **AWS CLI**: Configured with credentials
   ```bash
   aws configure
   ```

4. **S3 Bucket & DynamoDB** (for remote state):
   ```bash
   # Create S3 bucket
   aws s3 mb s3://curriculum-manager-state

   # Create DynamoDB table for locking
   aws dynamodb create-table \
     --table-name terraform-locks \
     --attribute-definitions AttributeName=LockID,AttributeType=S \
     --key-schema AttributeName=LockID,KeyType=HASH \
     --provisioned-throughput ReadCapacityUnits=5,WriteCapacityUnits=5
   ```

## Setup

### 1. Initialize Terraform

```bash
cd infra/terraform

# Initialize with backend configuration
terraform init

# Verify initialization
terraform version
```

### 2. Configure Database Password

```bash
# Set environment variable
export TF_VAR_db_password="your-secure-password"

# Or create terraform.tfvars (git-ignored)
cat > terraform.tfvars << EOF
db_password = "your-secure-password"
EOF
```

### 3. Plan Infrastructure

```bash
# Development
terraform plan -var-file="environments/dev.tfvars" -out=dev.tfplan

# Staging
terraform plan -var-file="environments/staging.tfvars" -out=staging.tfplan

# Production
terraform plan -var-file="environments/prod.tfvars" \
  -var db_password=$TF_VAR_db_password -out=prod.tfplan
```

## Deployment

### Development

```bash
# Plan
terraform plan -var-file="environments/dev.tfvars" -out=dev.tfplan

# Review changes
terraform show dev.tfplan

# Apply
terraform apply dev.tfplan

# Get outputs
terraform output deployment_summary
```

### Staging

```bash
terraform plan -var-file="environments/staging.tfvars" -out=staging.tfplan
terraform apply staging.tfplan
```

### Production

```bash
# Requires explicit approval
terraform plan -var-file="environments/prod.tfvars" \
  -var db_password=$TF_VAR_db_password -out=prod.tfplan

# Review plan carefully before applying
terraform show prod.tfplan

# Apply with auto-approval (use with caution)
terraform apply prod.tfplan
```

## Configuration Management

### Variables

Edit `environments/*.tfvars` to customize:

#### EKS Cluster
- `k8s_version`: Kubernetes version (default: 1.29)
- `desired_node_count`: Initial number of worker nodes
- `node_instance_types`: EC2 instance types (default: t3.medium)

#### Database
- `db_instance_class`: RDS instance size
- `db_storage_gb`: Initial storage (20-1000 GB)
- `db_max_storage_gb`: Maximum storage for autoscaling

#### Redis
- `redis_node_type`: ElastiCache node type
- `redis_num_nodes`: Number of cache nodes (1-6)

### Environment Variables

Override variables without modifying files:

```bash
export TF_VAR_aws_region="us-west-2"
export TF_VAR_environment="staging"
export TF_VAR_desired_node_count=5
```

## Post-Deployment

### 1. Configure kubectl

```bash
# Get cluster name from outputs
CLUSTER_NAME=$(terraform output -raw eks_cluster_name)

# Update kubeconfig
aws eks update-kubeconfig --name $CLUSTER_NAME --region us-east-1

# Verify connection
kubectl cluster-info
kubectl get nodes
```

### 2. Deploy Applications

```bash
# Apply Kubernetes manifests
kubectl apply -f ../k8s/

# Wait for deployments
kubectl rollout status deployment -n curriculum --timeout=5m
```

### 3. Setup Database

```bash
# Get RDS endpoint
RDS_ENDPOINT=$(terraform output -raw rds_endpoint)

# Connect and run migrations
psql -h $RDS_ENDPOINT -U curriculum_user -d curriculum_db \
  -f ../db/schemas/01_knowledge_graph.sql
```

## Monitoring

### Infrastructure Metrics

```bash
# Get cluster info
terraform output deployment_summary

# Check node status
kubectl get nodes

# Monitor RDS
aws rds describe-db-instances --db-instance-identifier curriculum-manager-postgres
```

### CloudWatch Logs

```bash
# View EKS cluster logs
aws logs tail /aws/eks/curriculum-manager-production --follow

# View RDS logs
aws logs tail /aws/rds/instance/curriculum-manager-postgres --follow
```

## Updates & Scaling

### Scale Worker Nodes

```bash
# Edit desired_node_count in environments/*.tfvars
# Then plan and apply

terraform plan -var-file="environments/prod.tfvars" -out=scale.tfplan
terraform apply scale.tfplan
```

### Upgrade Kubernetes

```bash
# Update k8s_version in environments/*.tfvars

terraform plan -var-file="environments/prod.tfvars" \
  -var k8s_version="1.30" -out=upgrade.tfplan

terraform apply upgrade.tfplan
```

### Database Instance Changes

```bash
# Update db_instance_class in environments/*.tfvars

terraform plan -var-file="environments/prod.tfvars" -out=db-upgrade.tfplan

# Note: May require downtime
terraform apply db-upgrade.tfplan
```

## Backup & Disaster Recovery

### Database Backups

```bash
# Automated: RDS automatic backups enabled (30-day retention)
# View backups
aws rds describe-db-snapshots \
  --db-instance-identifier curriculum-manager-postgres

# Create manual backup
aws rds create-db-snapshot \
  --db-instance-identifier curriculum-manager-postgres \
  --db-snapshot-identifier curriculum-snapshot-$(date +%Y%m%d)
```

### State File Backup

```bash
# S3 backend automatically maintains backup
# Download local backup
aws s3 cp s3://curriculum-manager-state/terraform.tfstate ./backup/

# View state
terraform state list
terraform state show aws_eks_cluster.main
```

## Troubleshooting

### Terraform Issues

```bash
# Validate configuration
terraform validate

# Check syntax
terraform fmt -check

# Detailed logging
TF_LOG=DEBUG terraform plan

# Refresh state
terraform refresh
```

### AWS Issues

```bash
# Check API limits
aws service-quotas list-service-quotas --service-code ec2

# Verify IAM permissions
aws iam list-attached-user-policies --user-name your-user

# Check resource tags
aws resourcegroupstaggingapi get-resources \
  --tag-filter Key=Project,Values=curriculum-manager
```

### EKS Issues

```bash
# Check cluster status
aws eks describe-cluster --name curriculum-manager-production

# View error logs
kubectl logs -n kube-system deployment/aws-node

# Verify pod networking
kubectl get pods -A
kubectl describe pod <pod-name> -n curriculum
```

## Cost Optimization

### Reduce Costs

```bash
# Use spot instances for non-production
# Edit node_instance_types to include spot

# Scale down development cluster
# Edit environments/dev.tfvars:
# - desired_node_count = 1
# - db_instance_class = "db.t3.micro"
```

### Cost Estimation

```bash
# Estimate before applying
terraform plan -var-file="environments/prod.tfvars" | grep -i cost

# Use AWS Pricing Calculator
# https://calculator.aws/
```

## Cleanup

### Destroy Infrastructure

```bash
# Plan destruction
terraform plan -destroy -var-file="environments/dev.tfvars" -out=destroy.tfplan

# Review what will be deleted
terraform show destroy.tfplan

# Apply destruction
terraform apply destroy.tfplan
```

### Important Notes

- Destroying production infrastructure is irreversible
- Database snapshots are created before deletion (if Multi-AZ)
- Persistent volumes should be backed up first

## Advanced Topics

### Custom VPC CIDR

```bash
# Edit environments/*.tfvars
vpc_cidr = "10.3.0.0/16"  # Change default
```

### Multi-Region Setup

```bash
# Create new backend for additional region
# Create separate directories:
terraform/
├── us-east-1/
├── us-west-2/
└── eu-west-1/
```

### Workspace Management

```bash
# Create workspace
terraform workspace new production
terraform workspace select production

# List workspaces
terraform workspace list
```

## References

- [Terraform AWS Provider Documentation](https://registry.terraform.io/providers/hashicorp/aws/latest/docs)
- [AWS EKS Best Practices](https://aws.github.io/aws-eks-best-practices/)
- [Terraform Best Practices](https://www.terraform.io/docs/cloud/best-practices.html)
- [AWS Security Best Practices](https://aws.amazon.com/architecture/security-identity-compliance/)

## Support

For issues:

1. Check Terraform logs: `TF_LOG=DEBUG terraform plan`
2. Verify AWS credentials: `aws sts get-caller-identity`
3. Review CloudFormation events: AWS Console → CloudFormation
4. Check AWS service health: https://status.aws.amazon.com/
