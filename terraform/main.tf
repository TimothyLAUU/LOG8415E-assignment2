terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = var.region # credentials come from ~/.aws/credentials
}

data "aws_vpc" "default" {
  default = true
}

data "aws_ami" "ubuntu" {
  most_recent = true
  owners      = ["099720109477"] # Canonical
  filter {
    name   = "name"
    values = ["ubuntu/images/hvm-ssd/ubuntu-jammy-22.04-amd64-server-*"]
  }
}

resource "aws_key_pair" "lab" {
  key_name   = "log8415e-tp2-key"
  public_key = file("${path.module}/../keys/lab-key.pub")
}

resource "aws_security_group" "tp2" {
  name        = "log8415e-tp2-sg"
  description = "TP2: SSH, HTTP 80, and 5000 only inside the group"
  vpc_id      = data.aws_vpc.default.id

  ingress {
    description = "SSH"
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = [var.allowed_ssh_cidr]
  }
  ingress {
    description = "Orchestrator HTTP"
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }
  ingress {
    description = "Workers (only from instances in this SG)"
    from_port   = 5000
    to_port     = 5000
    protocol    = "tcp"
    self        = true
  }
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

resource "aws_instance" "orchestrator" {
  ami                    = data.aws_ami.ubuntu.id
  instance_type          = var.instance_type
  key_name               = aws_key_pair.lab.key_name
  vpc_security_group_ids = [aws_security_group.tp2.id]
  user_data              = file("${path.module}/user_data.sh")
  root_block_device { volume_size = 20 }
  tags = { Name = "tp2-orchestrator" }
}

resource "aws_instance" "worker" {
  count                  = 2
  ami                    = data.aws_ami.ubuntu.id
  instance_type          = var.instance_type
  key_name               = aws_key_pair.lab.key_name
  vpc_security_group_ids = [aws_security_group.tp2.id]
  user_data              = file("${path.module}/user_data.sh")
  root_block_device { volume_size = 30 } # PyTorch image is big
  tags = { Name = "tp2-worker${count.index + 1}" }
}
