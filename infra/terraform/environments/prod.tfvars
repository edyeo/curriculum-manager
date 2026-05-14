environment          = "production"
aws_region          = "us-east-1"
vpc_cidr            = "10.2.0.0/16"

# EKS
k8s_version         = "1.29"
desired_node_count  = 5
min_node_count      = 3
max_node_count      = 10
node_instance_types = ["t3.large"]

# RDS
db_instance_class   = "db.t3.medium"
postgres_version    = "16.3"
db_storage_gb       = 100
db_max_storage_gb   = 500

# Redis
redis_node_type     = "cache.t3.medium"
redis_version       = "7.1"
redis_num_nodes     = 3
