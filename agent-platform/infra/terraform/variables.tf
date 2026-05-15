variable "aws_region" {
  description = "AWS region for resources"
  type        = string
  default     = "us-east-1"
}

variable "environment" {
  description = "Environment name (development, staging, production)"
  type        = string
  default     = "development"

  validation {
    condition     = contains(["development", "staging", "production"], var.environment)
    error_message = "Environment must be one of: development, staging, production."
  }
}

variable "project_name" {
  description = "Project name for resource naming"
  type        = string
  default     = "curriculum-manager"
}

# VPC Configuration
variable "vpc_cidr" {
  description = "CIDR block for VPC"
  type        = string
  default     = "10.0.0.0/16"
}

# EKS Configuration
variable "k8s_version" {
  description = "Kubernetes version for EKS"
  type        = string
  default     = "1.29"
}

variable "desired_node_count" {
  description = "Desired number of worker nodes"
  type        = number
  default     = 3

  validation {
    condition     = var.desired_node_count >= 1 && var.desired_node_count <= 10
    error_message = "Desired node count must be between 1 and 10."
  }
}

variable "min_node_count" {
  description = "Minimum number of worker nodes"
  type        = number
  default     = 1
}

variable "max_node_count" {
  description = "Maximum number of worker nodes"
  type        = number
  default     = 5
}

variable "node_instance_types" {
  description = "EC2 instance types for worker nodes"
  type        = list(string)
  default     = ["t3.medium"]
}

# RDS Configuration
variable "db_instance_class" {
  description = "Database instance class"
  type        = string
  default     = "db.t3.micro"
}

variable "postgres_version" {
  description = "PostgreSQL version"
  type        = string
  default     = "16.3"
}

variable "db_name" {
  description = "Database name"
  type        = string
  default     = "curriculum_db"
  sensitive   = true
}

variable "db_user" {
  description = "Database user"
  type        = string
  default     = "curriculum_user"
  sensitive   = true
}

variable "db_password" {
  description = "Database password (use environment variable TF_VAR_db_password)"
  type        = string
  sensitive   = true
}

variable "db_storage_gb" {
  description = "Initial allocated storage in GB"
  type        = number
  default     = 20

  validation {
    condition     = var.db_storage_gb >= 20 && var.db_storage_gb <= 1000
    error_message = "Storage must be between 20 and 1000 GB."
  }
}

variable "db_max_storage_gb" {
  description = "Maximum allocated storage in GB for autoscaling"
  type        = number
  default     = 100

  validation {
    condition     = var.db_max_storage_gb >= 20 && var.db_max_storage_gb <= 65536
    error_message = "Max storage must be between 20 and 65536 GB."
  }
}

# Redis Configuration
variable "redis_node_type" {
  description = "Redis node type"
  type        = string
  default     = "cache.t3.micro"
}

variable "redis_version" {
  description = "Redis version"
  type        = string
  default     = "7.1"
}

variable "redis_num_nodes" {
  description = "Number of Redis nodes"
  type        = number
  default     = 1

  validation {
    condition     = var.redis_num_nodes >= 1 && var.redis_num_nodes <= 6
    error_message = "Number of Redis nodes must be between 1 and 6."
  }
}

# Common Tags
variable "tags" {
  description = "Additional tags to apply to resources"
  type        = map(string)
  default     = {}
}
