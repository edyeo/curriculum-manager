environment          = "staging"
aws_region          = "us-east-1"
vpc_cidr            = "10.1.0.0/16"

# EKS
k8s_version         = "1.29"
desired_node_count  = 3
min_node_count      = 2
max_node_count      = 5
node_instance_types = ["t3.small"]

# RDS
db_instance_class   = "db.t3.small"
postgres_version    = "16.3"
db_storage_gb       = 50
db_max_storage_gb   = 200

# Redis
redis_node_type     = "cache.t3.small"
redis_version       = "7.1"
redis_num_nodes     = 2
