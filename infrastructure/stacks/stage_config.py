"""Environment-specific defaults; review production values before deployment."""

from dataclasses import dataclass

from aws_cdk import aws_ec2 as ec2


@dataclass(frozen=True)
class StageConfig:
    name: str
    nat_gateways: int
    database_instance_type: ec2.InstanceType
    database_allocated_storage_gib: int
    database_multi_az: bool
    backup_retention_days: int
    log_retention_days: int

    @classmethod
    def for_name(cls, name: str) -> "StageConfig":
        configurations = {
            "dev": cls(
                name="dev",
                nat_gateways=1,
                database_instance_type=ec2.InstanceType.of(
                    ec2.InstanceClass.T4G, ec2.InstanceSize.MICRO
                ),
                database_allocated_storage_gib=20,
                database_multi_az=False,
                backup_retention_days=7,
                log_retention_days=7,
            ),
            "staging": cls(
                name="staging",
                nat_gateways=1,
                database_instance_type=ec2.InstanceType.of(
                    ec2.InstanceClass.T4G, ec2.InstanceSize.SMALL
                ),
                database_allocated_storage_gib=50,
                database_multi_az=False,
                backup_retention_days=7,
                log_retention_days=14,
            ),
            "prod": cls(
                name="prod",
                nat_gateways=2,
                database_instance_type=ec2.InstanceType.of(
                    ec2.InstanceClass.T4G, ec2.InstanceSize.MEDIUM
                ),
                database_allocated_storage_gib=100,
                database_multi_az=True,
                backup_retention_days=30,
                log_retention_days=30,
            ),
        }
        try:
            return configurations[name]
        except KeyError as exc:
            supported = ", ".join(configurations)
            raise ValueError(
                f"Ambiente desconhecido: {name!r}. Use um destes: {supported}."
            ) from exc
