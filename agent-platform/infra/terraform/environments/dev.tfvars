environment          = "development"
aws_region          = "us-east-1"
vpc_cidr            = "10.0.0.0/16"

# EKS
k8s_version         = "1.29"
desired_node_count  = 2
min_node_count      = 1
max_node_count      = 3
node_instance_types = ["t3.medium"]

# RDS
db_instance_class   = "db.t3.micro"
postgres_version    = "16.3"
db_storage_gb       = 20
db_max_storage_gb   = 50

# Redis
redis_node_type     = "cache.t3.micro"
redis_version       = "7.1"
redis_num_nodes     = 1
