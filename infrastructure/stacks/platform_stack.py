from aws_cdk import (
    CfnOutput,
    Duration,
    RemovalPolicy,
    Stack,
    aws_ec2 as ec2,
    aws_ecr as ecr,
    aws_ecs as ecs,
    aws_logs as logs,
    aws_rds as rds,
    aws_s3 as s3,
)
from constructs import Construct

from stacks.stage_config import StageConfig


LOG_RETENTION_BY_DAYS = {
    7: logs.RetentionDays.ONE_WEEK,
    14: logs.RetentionDays.TWO_WEEKS,
    30: logs.RetentionDays.ONE_MONTH,
}


class PlatformStack(Stack):
    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        *,
        config: StageConfig,
        **kwargs: object,
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        app_name = f"commercial-platform-{config.name}"
        vpc = ec2.Vpc(
            self,
            "Vpc",
            vpc_name=app_name,
            max_azs=2,
            nat_gateways=config.nat_gateways,
            subnet_configuration=[
                ec2.SubnetConfiguration(
                    name="Public",
                    subnet_type=ec2.SubnetType.PUBLIC,
                    cidr_mask=24,
                ),
                ec2.SubnetConfiguration(
                    name="Application",
                    subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS,
                    cidr_mask=24,
                ),
                ec2.SubnetConfiguration(
                    name="Database",
                    subnet_type=ec2.SubnetType.PRIVATE_ISOLATED,
                    cidr_mask=24,
                ),
            ],
        )

        application_security_group = ec2.SecurityGroup(
            self,
            "ApplicationSecurityGroup",
            vpc=vpc,
            description="Security group reserved for private application tasks",
            allow_all_outbound=False,
        )
        database_security_group = ec2.SecurityGroup(
            self,
            "DatabaseSecurityGroup",
            vpc=vpc,
            description="PostgreSQL access limited to application tasks",
            allow_all_outbound=False,
        )
        application_security_group.add_egress_rule(
            ec2.Peer.any_ipv4(),
            ec2.Port.tcp(443),
            "HTTPS egress for approved external integrations and AWS endpoints",
        )
        application_security_group.add_egress_rule(
            database_security_group,
            ec2.Port.tcp(5432),
            "PostgreSQL to the platform database",
        )
        database_security_group.add_ingress_rule(
            application_security_group,
            ec2.Port.tcp(5432),
            "PostgreSQL from application tasks",
        )

        database = rds.DatabaseInstance(
            self,
            "Database",
            database_name="platform",
            engine=rds.DatabaseInstanceEngine.postgres(
                version=rds.PostgresEngineVersion.VER_17_6
            ),
            credentials=rds.Credentials.from_generated_secret(
                "platform_admin",
                secret_name=f"{app_name}/database/master",
            ),
            instance_type=config.database_instance_type,
            allocated_storage=config.database_allocated_storage_gib,
            max_allocated_storage=max(
                config.database_allocated_storage_gib,
                config.database_allocated_storage_gib * 2,
            ),
            storage_type=rds.StorageType.GP3,
            storage_encrypted=True,
            multi_az=config.database_multi_az,
            publicly_accessible=False,
            vpc=vpc,
            vpc_subnets=ec2.SubnetSelection(
                subnet_type=ec2.SubnetType.PRIVATE_ISOLATED
            ),
            security_groups=[database_security_group],
            backup_retention=Duration.days(config.backup_retention_days),
            delete_automated_backups=False,
            deletion_protection=True,
            auto_minor_version_upgrade=True,
            cloudwatch_logs_exports=["postgresql"],
            removal_policy=RemovalPolicy.RETAIN,
        )
        if database.secret is None:
            raise RuntimeError("RDS did not create the expected master secret.")

        object_bucket = s3.Bucket(
            self,
            "ObjectBucket",
            encryption=s3.BucketEncryption.S3_MANAGED,
            enforce_ssl=True,
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            versioned=True,
            removal_policy=RemovalPolicy.RETAIN,
            auto_delete_objects=False,
        )

        repositories = {
            name: ecr.Repository(
                self,
                f"{name.title()}Repository",
                repository_name=f"{app_name}/{name}",
                image_scan_on_push=True,
                image_tag_mutability=ecr.TagMutability.IMMUTABLE,
                removal_policy=RemovalPolicy.RETAIN,
                empty_on_delete=False,
            )
            for name in ("api", "web", "worker")
        }

        cluster = ecs.Cluster(
            self,
            "EcsCluster",
            cluster_name=app_name,
            vpc=vpc,
        )

        for service_name in ("api", "web", "worker"):
            logs.LogGroup(
                self,
                f"{service_name.title()}LogGroup",
                log_group_name=f"/{app_name}/{service_name}",
                retention=LOG_RETENTION_BY_DAYS[config.log_retention_days],
                removal_policy=RemovalPolicy.RETAIN,
            )

        CfnOutput(self, "VpcId", value=vpc.vpc_id)
        CfnOutput(self, "EcsClusterName", value=cluster.cluster_name)
        CfnOutput(self, "DatabaseEndpoint", value=database.db_instance_endpoint_address)
        CfnOutput(self, "DatabaseSecretArn", value=database.secret.secret_arn)
        CfnOutput(self, "ObjectBucketName", value=object_bucket.bucket_name)
        for name, repository in repositories.items():
            CfnOutput(
                self,
                f"{name.title()}RepositoryUri",
                value=repository.repository_uri,
            )
