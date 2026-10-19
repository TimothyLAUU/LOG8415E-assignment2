variable "region" {
  default = "us-east-1"
}

variable "instance_type" {
  default = "t2.large" # use the type specified on Moodle if different
}

variable "allowed_ssh_cidr" {
  default     = "0.0.0.0/0" # better: "<your_public_ip>/32"
  description = "CIDR allowed to SSH"
}
