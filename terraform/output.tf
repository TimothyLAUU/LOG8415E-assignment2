output "orchestrator_public_ip" { value = aws_instance.orchestrator.public_ip }
output "worker_public_ips" { value = aws_instance.worker[*].public_ip }
output "worker_private_ips" { value = aws_instance.worker[*].private_ip }
